#!/usr/bin/env python3
"""
MyJarvis - JEDNODUCHÝ a FUNKČNÍ český hlasový asistent
Napísaný znovu od základů podle požadavků uživatele
"""

import logging
import yaml
import subprocess
import time
import pyaudio
import numpy as np
import speech_recognition as sr

# Imports s error handling
try:
    from llama_cpp import Llama

    LLM_OK = True
except ImportError:
    print("⚠️ LLM nedostupný")
    LLM_OK = False

try:
    import pvporcupine

    PORCUPINE_OK = True
except ImportError:
    print("⚠️ Porcupine nedostupný")
    PORCUPINE_OK = False

# Jednoduché logování
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger("Jarvis")


class SimpleJarvis:
    """Jednoduchý funkční Jarvis"""

    def __init__(self):
        print("🤖 Spouštím SimpleJarvis...")

        # Načti config
        with open("config.yaml", "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        # Inicializace
        self.audio = pyaudio.PyAudio()
        self.recognizer = sr.Recognizer()
        self.running = True
        self.porcupine = None
        self.wake_stream = None

        # Setup
        self.init_microphone()
        self.init_porcupine()

        print("✅ SimpleJarvis připraven!")

    def init_microphone(self):
        """Najdi fungující mikrofon"""
        print("🎤 Hledám mikrofon...")

        # Test default
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.1)
            self.mic_device = None  # Default
            print("✅ Mikrofon OK (default)")
            return
        except:
            pass

        # Test all devices
        for i in range(self.audio.get_device_count()):
            try:
                device_info = self.audio.get_device_info_by_index(i)
                if device_info["maxInputChannels"] > 0:
                    with sr.Microphone(device_index=i) as source:
                        self.recognizer.adjust_for_ambient_noise(source, duration=0.1)
                    self.mic_device = i
                    print(f"✅ Mikrofon OK: {device_info['name']}")
                    return
            except:
                continue

        print("❌ Žádný funkční mikrofon!")
        self.mic_device = None

    def init_porcupine(self):
        """Inicializuj Porcupine wake word"""
        if not PORCUPINE_OK or not self.mic_device:
            print("⚠️ Porcupine nedostupný")
            return

        try:
            wake_config = self.config["wake_word"]
            self.porcupine = pvporcupine.create(
                access_key=wake_config["access_key"],
                keyword_paths=[wake_config["model_path"]],
                sensitivities=[wake_config["threshold"]],
            )

            # Wake word stream
            self.wake_stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                input_device_index=self.mic_device,
                frames_per_buffer=self.porcupine.frame_length,
            )

            print(f"✅ Wake word '{wake_config['keyword']}' aktivní")

        except Exception as e:
            print(f"❌ Porcupine chyba: {e}")
            self.porcupine = None

    def detect_wake_word(self):
        """Detekce wake word"""
        if not self.porcupine or not self.wake_stream:
            return False

        try:
            pcm = self.wake_stream.read(
                self.porcupine.frame_length, exception_on_overflow=False
            )
            pcm = np.frombuffer(pcm, dtype=np.int16)

            result = self.porcupine.process(pcm)
            return result >= 0

        except:
            return False

    def listen_for_command(self):
        """Poslouchej příkaz - VELMI JEDNODUŠE"""
        if not self.mic_device:
            return None

        try:
            # Zavři wake stream
            if self.wake_stream:
                self.wake_stream.close()
                self.wake_stream = None

            # Setup recognizer - VELMI CITLIVĚ
            mic = sr.Microphone(device_index=self.mic_device)
            stt_config = self.config["stt"]

            with mic as source:
                # Krátká kalibrace
                self.recognizer.adjust_for_ambient_noise(source, duration=0.2)

                # VELMI nízký threshold
                self.recognizer.energy_threshold = 50
                self.recognizer.dynamic_energy_threshold = False  # Fixní
                self.recognizer.pause_threshold = 0.3

                print("🎤 Mluvte NORMÁLNĚ (threshold: 50)...")

                # Poslech
                audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=5)

                # STT
                text = self.recognizer.recognize_google(
                    audio, language=stt_config["language"]
                )

                print(f"✅ Slyším: '{text}'")
                return text.strip()

        except sr.WaitTimeoutError:
            print("⏰ Timeout")
            return None
        except sr.UnknownValueError:
            print("❓ Nerozuměl jsem")
            return None
        except Exception as e:
            print(f"❌ STT chyba: {e}")
            return None
        finally:
            # Obnov wake stream
            self.restore_wake_stream()

    def restore_wake_stream(self):
        """Obnov wake word stream"""
        if self.porcupine and self.mic_device is not None:
            try:
                self.wake_stream = self.audio.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=16000,
                    input=True,
                    input_device_index=self.mic_device,
                    frames_per_buffer=self.porcupine.frame_length,
                )
            except:
                pass

    def speak(self, text):
        """Jednoduchý TTS"""
        print(f"🗣️ {text}")
        try:
            tts_config = self.config["tts"]
            cmd = [
                "espeak",
                "-v",
                tts_config["voice"],
                "-s",
                str(tts_config["speed"]),
                text,
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            print(f"💬 {text}")  # Fallback

    def handle_command(self, text):
        """Zpracuj příkaz - JEDNODUŠE"""
        text_lower = text.lower()

        # Konec
        if any(word in text_lower for word in ["konec", "stop", "ukončit"]):
            self.speak("Návrat do wake word režimu")
            return True

        # Čas
        if any(word in text_lower for word in ["čas", "hodin", "kolik je"]):
            from datetime import datetime

            now = datetime.now()
            response = f"Je {now.hour} hodin a {now.minute:02d} minut"
            self.speak(response)
            return False

        # Jednoduchá odpověď
        self.speak("Ano, slyším vás")
        return False

    def run(self):
        """Hlavní smyčka"""
        print("👂 Čekám na wake word 'hello bitch'...")

        try:
            while self.running:
                if self.porcupine:
                    # Wake word režim
                    if self.detect_wake_word():
                        print("🎯 Wake word detekován!")
                        self.speak("Ano")

                        # Poslouchej příkaz
                        command = self.listen_for_command()
                        if command:
                            if self.handle_command(command):
                                continue  # Zpět do wake word

                else:
                    # Fallback bez wake word
                    print("⚠️ Bez wake word - mluvte:")
                    command = self.listen_for_command()
                    if command:
                        if self.handle_command(command):
                            break

                time.sleep(0.01)

        except KeyboardInterrupt:
            print("\n✅ Ukončuji...")
        finally:
            self.cleanup()

    def cleanup(self):
        """Úklid"""
        if self.wake_stream:
            self.wake_stream.close()
        if self.porcupine:
            self.porcupine.delete()
        self.audio.terminate()


def main():
    jarvis = SimpleJarvis()
    jarvis.run()


if __name__ == "__main__":
    main()
