#!/usr/bin/env python3
"""
MyJarvis - Český hlasový asistent
Hlavní soubor podle README.md specifikace
"""

import asyncio
import logging
import yaml
import subprocess
import webbrowser
import urllib.parse
from datetime import datetime
import pyaudio
import numpy as np
import speech_recognition as sr

try:
    from llama_cpp import Llama

    LLM_OK = True
except ImportError:
    LLM_OK = False

try:
    import pvporcupine

    PORCUPINE_OK = True
except ImportError:
    PORCUPINE_OK = False

# Logging podle config
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger("MyJarvis")


class MyJarvis:
    """Hlavní třída podle README specifikace"""

    def __init__(self):
        logger.info("🤖 MyJarvis startuje...")

        self.audio = pyaudio.PyAudio()
        self.recognizer = sr.Recognizer()
        self.running = True
        self.porcupine = None
        self.llm = None
        self.wake_stream = None

        # Inicializace podle pořadí v README
        self.load_config()
        self.init_microphone()
        self.init_porcupine()
        self.init_llm()

    def load_config(self):
        """Načtení konfigurace podle README specifikace"""
        with open("config.yaml", "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

    def init_microphone(self):
        """Najdi nejlepší mikrofon podle config"""
        logger.info("🎤 Inicializuji mikrofon...")

        device_index = self.config["audio"].get("device_index")
        if device_index is not None:
            self.mic_device = device_index
            info = self.audio.get_device_info_by_index(device_index)
            logger.info("✅ Mikrofon (config): %s", info["name"])
            return

        # Automatická detekce
        for i in range(self.audio.get_device_count()):
            try:
                info = self.audio.get_device_info_by_index(i)
                if info["maxInputChannels"] > 0:
                    # Test mikrofonu s parametry z config
                    stream = self.audio.open(
                        format=pyaudio.paInt16,
                        channels=self.config["audio"]["channels"],
                        rate=16000,  # Porcupine vyžaduje 16kHz
                        input=True,
                        input_device_index=i,
                        frames_per_buffer=self.config["wake_word"]["chunk_size"],
                    )
                    stream.close()
                    self.mic_device = i
                    logger.info("✅ Mikrofon (auto): %s", info["name"])
                    return
            except Exception:
                continue

        logger.error("❌ Žádný funkční mikrofon!")
        self.mic_device = None

    def init_porcupine(self):
        """Inicializace Porcupine podle config"""
        if not PORCUPINE_OK:
            logger.warning("⚠️ Porcupine nedostupný - wake word vypnut")
            return

        try:
            wake_config = self.config["wake_word"]
            self.porcupine = pvporcupine.create(
                access_key=wake_config["access_key"],
                keyword_paths=[wake_config["model_path"]],
                sensitivities=[wake_config["threshold"]],
            )

            # Vytvoř kontinuální stream pro wake word
            if self.mic_device is not None:
                self.wake_stream = self.audio.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=16000,
                    input=True,
                    input_device_index=self.mic_device,
                    frames_per_buffer=self.porcupine.frame_length,
                )

            logger.info("✅ Wake word aktivní: '%s'", wake_config["keyword"])

        except Exception as e:
            logger.error("❌ Porcupine chyba: %s", e)
            self.porcupine = None

    def init_llm(self):
        """Inicializace LLM podle config"""
        if not LLM_OK:
            logger.warning("⚠️ LLM nedostupný")
            return

        try:
            llm_config = self.config["llm"]
            self.llm = Llama(
                model_path=llm_config["model_path"],
                n_ctx=llm_config["n_ctx"],
                n_threads=llm_config["n_threads"],
                verbose=False,
            )
            logger.info("✅ LLM načten (%s)", llm_config["model_path"].split("/")[-1])
        except Exception as e:
            logger.error("❌ LLM chyba: %s", e)

    def detect_wake_word(self):
        """Kontinuální detekce wake word pomocí stream"""
        if not self.porcupine or not self.wake_stream:
            return False

        try:
            # Čti z kontinuálního streamu
            audio_data = self.wake_stream.read(
                self.porcupine.frame_length, exception_on_overflow=False
            )

            # Konverze na numpy array
            audio_np = np.frombuffer(audio_data, dtype=np.int16)

            # Porcupine detekce
            keyword_index = self.porcupine.process(audio_np)

            return keyword_index >= 0

        except Exception as e:
            logger.debug("Wake word detekce chyba: %s", e)
            return False

    def listen_for_command(self):
        """Poslech příkazu po aktivaci wake word"""
        if not self.mic_device:
            return None

        try:
            # Dočasně zavři wake word stream
            if self.wake_stream:
                self.wake_stream.close()
                self.wake_stream = None

            # Krátká pauza pro uvolnění zařízení
            import time

            time.sleep(0.1)

            # Použij speech_recognition s parametry z config
            mic = sr.Microphone(device_index=self.mic_device)
            stt_config = self.config["stt"]

            with mic as source:
                # DŮLEŽITÉ: Adaptivní kalibrace podle prostředí
                logger.info("🔧 Kalibrace mikrofonu...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)

                # Použij přesně hodnoty z config - NE max()!
                self.recognizer.energy_threshold = stt_config["energy_threshold"]
                self.recognizer.dynamic_energy_threshold = stt_config[
                    "dynamic_energy_threshold"
                ]
                # Delší pauza pro rozpoznání celých vět
                self.recognizer.pause_threshold = 1.2

                logger.info(
                    "🎤 Poslouchám příkaz... (threshold: %d)",
                    self.recognizer.energy_threshold,
                )

                # Poslech s optimalizovanými timeouty
                logger.info("🎧 Začínám poslouchat...")
                audio = self.recognizer.listen(
                    source,
                    timeout=stt_config["timeout"],
                    phrase_time_limit=stt_config["phrase_timeout"],
                )

                logger.info("🎙️ Audio zachyceno, přepisuji...")
                # STT s českou lokalizací
                text = self.recognizer.recognize_google(
                    audio, language=stt_config["language"]
                )

                result = text.strip()
                logger.info("✅ Rozpoznáno: %s", result)

        except sr.WaitTimeoutError:
            logger.info("⏰ Časový limit pro příkaz - pokračuji v poslouchání")
            result = None
        except sr.UnknownValueError:
            logger.info("🔇 Nerozpoznaný audio - zkuste mluvit hlasitěji")
            result = None
        except sr.RequestError as e:
            logger.error("STT služba nedostupná: %s", e)
            result = None
        except Exception as e:
            logger.error("STT chyba: %s", e)
            logger.error("STT chyba detaily: %s", type(e).__name__)
            result = None

        finally:
            # Vždy obnov wake word stream
            self.restore_wake_stream()

        return result

    def restore_wake_stream(self):
        """Obnov wake word stream po STT"""
        if self.porcupine and self.mic_device is not None:
            try:
                # Krátká pauza před obnovením
                import time

                time.sleep(0.2)

                self.wake_stream = self.audio.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=16000,
                    input=True,
                    input_device_index=self.mic_device,
                    frames_per_buffer=self.porcupine.frame_length,
                )
                logger.debug("Wake word stream obnoven")
            except Exception as e:
                logger.error("Chyba obnovení wake word stream: %s", e)

    def speak(self, text):
        """TTS podle config"""
        try:
            tts_config = self.config["tts"]
            logger.info("🗣️ %s", text)

            if tts_config["service"] == "espeak":
                cmd = [
                    "espeak",
                    "-v",
                    tts_config["voice"],
                    "-s",
                    str(tts_config["speed"]),
                    "-a",
                    str(tts_config["volume"]),
                    "-p",
                    str(tts_config["pitch"]),
                    "-g",
                    str(tts_config["gap"]),
                    text,
                ]
                subprocess.run(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )

        except Exception as e:
            logger.error("TTS chyba: %s", e)

    def generate_ai_response(self, text):
        """Generuj odpověď pomocí LLM"""
        if not self.llm:
            return "LLM není dostupný"

        try:
            llm_config = self.config["llm"]

            # Lepší český prompt
            prompt = f"""Otázka: {text}
Odpověz česky jednoduše a stručně.
Odpověď:"""

            response = self.llm(
                prompt,
                max_tokens=llm_config["max_tokens"],
                temperature=llm_config["temperature"],
                stop=["\n", "Otázka:", "Odpověz:"],
            )

            answer = response["choices"][0]["text"].strip()

            # Filtrování
            if len(answer) > 3 and answer:
                return answer
            else:
                return "Nerozumím této otázce"

        except Exception as e:
            logger.debug("LLM chyba: %s", e)
            return "Promiňte, momentálně nemohu odpovědět"

    def handle_system_command(self, text):
        """Systémové příkazy s bezpečnostními kontrolami"""
        text_lower = text.lower()

        # Ukončení
        if any(
            word in text_lower for word in ["konec", "stop", "ukončit", "vypni jarvis"]
        ):
            self.speak("Přecházím do wake word režimu")
            return True

        # Čas
        if any(word in text_lower for word in ["čas", "hodin", "kolik je"]):
            now = datetime.now()
            response = f"Je {now.hour} hodin a {now.minute:02d} minut"
            self.speak(response)
            return False

        # Vypnutí systému (s potvrzením podle README)
        if "vypni počítač" in text_lower:
            self.speak("Opravdu chcete vypnout počítač? Řekněte ano pro potvrzení")
            confirm = self.listen_for_command()
            if confirm and "ano" in confirm.lower():
                self.speak("Vypínám počítač")
                subprocess.run(["systemctl", "poweroff"], check=False)
            else:
                self.speak("Vypnutí zrušeno")
            return False

        # Firefox
        if any(word in text_lower for word in ["firefox", "prohlížeč", "internet"]):
            self.speak("Spouštím Firefox")
            subprocess.Popen(
                ["firefox"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            return False

        # Vyhledávání (podle README)
        if any(word in text_lower for word in ["najdi", "vyhledej", "hledej"]):
            # Extrakce dotazu
            query = text_lower
            for word in ["najdi", "vyhledej", "hledej", "na", "internetu"]:
                query = query.replace(word, "")
            query = query.strip()

            if query:
                self.speak(f"Vyhledávám {query}")
                url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
                webbrowser.open(url)
                self.speak("Výsledky jsou otevřené v prohlížeči")
            else:
                self.speak("Co mám vyhledat?")
            return False

        return None  # Není systémový příkaz

    async def main_loop(self):
        """Hlavní smyčka podle README specifikace"""
        logger.info("✅ MyJarvis připraven!")

        if self.porcupine:
            logger.info(
                "👂 Čekám na wake word: '%s'", self.config["wake_word"]["keyword"]
            )
        else:
            logger.info("👂 Wake word není dostupný - kontinuální poslech")

        try:
            while self.running:
                if self.porcupine:
                    # Režim wake word
                    if self.detect_wake_word():
                        logger.info("🎯 Wake word detekován!")
                        self.speak("Ano, poslouchám")

                        # Poslech příkazu
                        command = self.listen_for_command()
                        if command:
                            logger.info("👤 Příkaz: %s", command)

                            # Zpracování systémových příkazů
                            sys_result = self.handle_system_command(command)
                            if sys_result is True:
                                # Návrat do wake word režimu
                                logger.info(
                                    "👂 Čekám na wake word: '%s'",
                                    self.config["wake_word"]["keyword"],
                                )
                                continue
                            elif sys_result is False:
                                # Systémový příkaz byl vykonán - pokračuj v wake word režimu
                                logger.info(
                                    "👂 Čekám na wake word: '%s'",
                                    self.config["wake_word"]["keyword"],
                                )
                                continue
                            else:
                                # Není systémový - použij AI
                                response = self.generate_ai_response(command)
                                self.speak(response)
                                logger.info(
                                    "👂 Čekám na wake word: '%s'",
                                    self.config["wake_word"]["keyword"],
                                )
                                continue
                        else:
                            self.speak("Nerozuměl jsem, zkuste to znovu")
                            logger.info(
                                "👂 Čekám na wake word: '%s'",
                                self.config["wake_word"]["keyword"],
                            )
                            continue

                    # Krátká pauza pro CPU
                    await asyncio.sleep(0.01)

                else:
                    # Fallback - bez wake word
                    self.speak("Říkejte příkazy")
                    command = self.listen_for_command()
                    if command:
                        logger.info("👤 %s", command)
                        sys_result = self.handle_system_command(command)
                        if sys_result is True:
                            break
                        elif sys_result is None:
                            response = self.generate_ai_response(command)
                            self.speak(response)
                    await asyncio.sleep(1)

        except KeyboardInterrupt:
            logger.info("⏹️ Ukončování MyJarvis...")
        finally:
            self.cleanup()

    def cleanup(self):
        """Úklid zdrojů"""
        if self.wake_stream:
            self.wake_stream.close()
        if self.porcupine:
            self.porcupine.delete()
        if self.audio:
            self.audio.terminate()
        logger.info("✅ MyJarvis ukončen")


def main():
    """Hlavní funkce podle README"""
    print("🤖 MyJarvis - Český Hlasový Asistent")
    print("=" * 50)
    print(f"📖 Řekněte: 'hello bitch' pro aktivaci")
    print(f"🗣️ Pak libovolný příkaz česky")
    print(f"🛑 'konec' = návrat do wake word režimu")
    print("=" * 50)

    try:
        jarvis = MyJarvis()
        asyncio.run(jarvis.main_loop())
    except Exception as e:
        logger.error("Kritická chyba: %s", e)
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
