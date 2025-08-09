"""Orchestrátor Jarvise: propojí STT, TTS, wake-word, LLM a systémové akce."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

import yaml
import pyaudio
import speech_recognition as sr

from src.audio.text_to_speech import TextToSpeech
from src.audio.speech_to_text import SpeechToText, STTConfig
from src.audio.wake_word_detector import WakeWordDetector, WakeWordConfig
from src.system.action_executor import ActionExecutor
from src.llm.engine import LlmEngine, LlmConfig


logger = logging.getLogger("JarvisOrchestrator")


class JarvisOrchestrator:
    """Hlavní orchestrátor hlasového asistenta.

    Odpovídá za inicializaci komponent, běh smyčky a řízení režimů.
    """

    def __init__(self):
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
        logger.info("🤖 Orchestrátor startuje…")

        self.audio = pyaudio.PyAudio()
        self.recognizer = sr.Recognizer()
        self.running = True

        # Konfig
        with open("config.yaml", "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        # Mikrofon
        self.mic_device: Optional[int] = self._pick_microphone()

        # STT / TTS
        stt_cfg_raw = self.config.get("stt", {})
        self.stt = SpeechToText(
            STTConfig(
                language=stt_cfg_raw.get("language", "cs"),
                service=stt_cfg_raw.get("service", "google"),
                whisper_model=stt_cfg_raw.get("model", "small"),
                hf_model=stt_cfg_raw.get("hf_model", "openai/whisper-small"),
                device=stt_cfg_raw.get("device", "auto"),
                energy_threshold=stt_cfg_raw.get("energy_threshold", 300),
                pause_threshold=stt_cfg_raw.get("pause_threshold", 0.8),
                dynamic_energy=stt_cfg_raw.get("dynamic_energy_threshold", True),
            )
        )
        self.tts = TextToSpeech(
            self.config.get("tts", {}), self.recognizer, self.mic_device
        )

        # Wake-word
        ww_cfg_raw = self.config.get("wake_word", {})
        self.detector = WakeWordDetector(
            self.audio,
            self.mic_device,
            WakeWordConfig(
                access_key=ww_cfg_raw.get("access_key", ""),
                model_path=ww_cfg_raw.get("model_path", ""),
                keyword=ww_cfg_raw.get("keyword", ""),
                threshold=float(ww_cfg_raw.get("threshold", 0.5)),
            ),
        )
        if not self.detector.start():
            logger.warning("⚠️ Wake word nedostupný; poběží kontinuální režim")

        # LLM
        llm_cfg_raw = self.config.get("llm", {})
        self.llm = LlmEngine(
            LlmConfig(
                model_path=llm_cfg_raw.get(
                    "model_path", "models/Llama-3.2-1B-Instruct.Q5_K_M.gguf"
                ),
                n_ctx=int(llm_cfg_raw.get("n_ctx", 4096)),
                n_threads=int(llm_cfg_raw.get("n_threads", 4)),
                max_tokens=int(llm_cfg_raw.get("max_tokens", 200)),
                temperature=float(llm_cfg_raw.get("temperature", 0.2)),
                top_p=float(llm_cfg_raw.get("top_p", 0.9)),
                repeat_penalty=float(llm_cfg_raw.get("repeat_penalty", 1.1)),
            )
        )

        # Akce
        self.actions = ActionExecutor(
            speak=self.speak, listen=self.listen_for_command, config=self.config
        )

        # Napoj TTS hooky na wake stream pause/resume
        self.tts.set_wake_stream_hooks(
            self._pause_wake_stream, self._resume_wake_stream
        )

        self.failed_attempts = 0

    def _pick_microphone(self) -> Optional[int]:
        """Zvol funkční vstupní zařízení (mikrofon)."""
        logger.info("🎤 Výběr mikrofonu…")
        device_index = self.config.get("audio", {}).get("device_index")
        if device_index is not None:
            return device_index
        for i in range(self.audio.get_device_count()):
            try:
                info = self.audio.get_device_info_by_index(i)
                if info.get("maxInputChannels", 0) > 0:
                    # zkus krátce otevřít se vzorkováním 16kHz kvůli Porcupine
                    stream = self.audio.open(
                        format=pyaudio.paInt16,
                        channels=1,
                        rate=16000,
                        input=True,
                        input_device_index=i,
                        frames_per_buffer=256,
                    )
                    stream.close()
                    logger.info("✅ Mikrofon: %s", info.get("name"))
                    return i
            except OSError:
                continue
        logger.error("❌ Žádný funkční mikrofon")
        return None

    def _pause_wake_stream(self) -> None:
        """Pozastav wake-word audio stream (kvůli STT/TTS)."""
        self.detector.stop_stream()

    def _resume_wake_stream(self) -> None:
        """Obnov wake-word audio stream."""
        self.detector.start_stream()

    def speak(self, text: str) -> None:
        """Řekni text přes TTS a zaloguj ho."""
        logger.info("🗣️ %s", text)
        self.tts.speak(text)

    def listen_for_command(self) -> Optional[str]:
        """Získá jeden hlasový příkaz z mikrofonu pomocí STT."""
        if self.mic_device is None:
            return None
        # pauza wake-streamu a krátká prodleva na uvolnění zařízení
        self._pause_wake_stream()
        # Některé ALSA/Pulse konfigurace potřebují delší čas na uvolnění
        time.sleep(0.2)
        stt_cfg = self.config.get("stt", {})
        try:
            result = self.stt.recognize_once(
                device_index=self.mic_device,
                timeout=stt_cfg.get("timeout", 5),
                phrase_time_limit=stt_cfg.get("phrase_timeout", 6),
            )
            return result if isinstance(result, str) else None
        finally:
            # Krátká prodleva, a pak obnov wake stream
            time.sleep(0.05)
            self._resume_wake_stream()

    def _load_system_prompt(self) -> Optional[str]:
        """Načti systémový prompt z disku, pokud existuje."""
        for path in (
            "prompt/system_prompt_cs.txt",
            "system_prompt_cs.txt",
            "prompt.txt",
        ):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
            except OSError:
                continue
        return None

    def generate_ai_response(self, text: str) -> str:
        """Vygeneruj odpověď LLM s lehkým očištěním prefixů."""
        base = self._load_system_prompt()
        if base:
            prompt = base.replace("{otazka}", text).replace("{question}", text)
        else:
            prompt = (
                "Jsi užitečný český asistent. Odpovídej vždy pravdivě a stručně.\n\n"
                f"Otázka: {text}\n\nOdpověď:"
            )
        ans = self.llm.generate(prompt)
        # lehké očištění
        for prefix in ("Odpověď:", "Asistent:", "Assistant:"):
            if ans.startswith(prefix):
                ans = ans[len(prefix) :].strip()
        return ans or "Nevím"

    async def run(self) -> None:
        """Hlavní asynchronní smyčka aplikace."""
        logger.info("✅ Jarvis připraven")
        conversation_mode = False
        if self.detector.active:
            logger.info("👂 Čekám na wake word…")
        else:
            logger.info("👂 Wake word nevhodný – kontinuální režim")

        try:
            while self.running:
                if self.detector.active and not conversation_mode:
                    if self.detector.detect():
                        self.speak("Ano, poslouchám")
                        conversation_mode = True
                        self.failed_attempts = 0
                        continue
                    await asyncio.sleep(0.01)
                    continue

                # konverzační režim
                command = self.listen_for_command()
                if command:
                    sys_result = self.actions.handle(command)
                    if sys_result is True:
                        conversation_mode = False
                        continue
                    if sys_result is False:
                        continue
                    # AI odpověď
                    self.speak(self.generate_ai_response(command))
                    continue

                self.failed_attempts += 1
                if self.failed_attempts >= 3:
                    if conversation_mode:
                        self.speak("Přecházím zpět do wake word režimu")
                    conversation_mode = False
                    self.failed_attempts = 0
                else:
                    self.speak("Nerozuměl jsem, zkuste to znovu")
                await asyncio.sleep(0.2)
        except KeyboardInterrupt:
            pass
        finally:
            self.cleanup()

    def cleanup(self) -> None:
        """Ukonči audio zdroje a wake word detektor."""
        try:
            self.detector.stop()
        except (OSError, AttributeError):  # pragma: no cover - best effort
            pass
        try:
            self.audio.terminate()
        except (OSError, AttributeError):  # pragma: no cover
            pass
        logger.info("✅ Orchestrátor ukončen")
