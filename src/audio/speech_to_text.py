"""Speech-to-Text (STT) modul.

Primárně používá OpenAI Whisper (lokálně přes balíček whisper) nebo
transformers ASR. Pokud nic z toho není k dispozici nebo výsledek je
nekvalitní, padá na Google SpeechRecognition jako zálohu.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import os
import tempfile

import numpy as np
import speech_recognition as sr


try:
    import whisper  # type: ignore
except ImportError:
    whisper = None  # type: ignore

try:
    from transformers import pipeline  # type: ignore
except ImportError:  # pragma: no cover - volitelná závislost
    pipeline = None  # type: ignore


@dataclass
class STTConfig:
    language: str = "cs"  # "cs" or locale like "cs-CZ" for Google
    service: str = "google"  # "google" | "whisper" | "whisper_openai" | "whisper_hf"
    whisper_model: str = "small"  # openai-whisper
    hf_model: str = "openai/whisper-small"  # transformers
    device: str = "auto"  # "auto" | "cuda" | "cpu"
    energy_threshold: int = 300
    pause_threshold: float = 0.8
    dynamic_energy: bool = True


class SpeechToText:
    """STT wrapper s více backendy a automatickou degradací.

    - Pokud je preferován Whisper a není dostupný, zkusí transformers ASR.
    - Pokud výsledek není text nebo je prázdný, zkusí Google jako fallback.
    """

    def __init__(self, cfg: Optional[STTConfig] = None):
        self.cfg = cfg or STTConfig()
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = self.cfg.energy_threshold
        self.recognizer.pause_threshold = self.cfg.pause_threshold
        self.recognizer.dynamic_energy_threshold = self.cfg.dynamic_energy
        # Nepovinná metrika (není vždy dostupná ve starších verzích SR)
        try:
            self.recognizer.non_speaking_duration = float(  # type: ignore[attr-defined]
                getattr(self.cfg, "non_speaking_duration", 0.2)
            )
        except (AttributeError, ValueError, TypeError):  # pragma: no cover
            pass
        self._whisper_model = None
        self._hf_pipe = None

        # Init backend according to service preference (prefer faster models on CPU)
        service = (self.cfg.service or "google").lower()
        use_cuda = self.cfg.device == "cuda"

        if service in ("whisper", "whisper_openai") and whisper is not None:
            try:
                # On CPU prefer a smaller model for latency
                selected_whisper_model = self.cfg.whisper_model
                if not use_cuda and selected_whisper_model in (
                    "small",
                    "medium",
                    "large",
                ):
                    selected_whisper_model = "tiny"  # fastest for CPU
                device = "cuda" if use_cuda else None
                self._whisper_model = whisper.load_model(
                    selected_whisper_model, device=device
                )  # type: ignore[arg-type]
            except (RuntimeError, OSError, ValueError):
                self._whisper_model = None
                # If generic "whisper" requested, try HF as next
                if service == "whisper":
                    service = "whisper_hf"

        if service in ("whisper", "whisper_hf") and pipeline is not None:
            try:
                dev = 0 if use_cuda else -1
                selected_hf_model = self.cfg.hf_model
                if not use_cuda and selected_hf_model.endswith("whisper-small"):
                    selected_hf_model = "openai/whisper-tiny"  # much faster on CPU
                self._hf_pipe = pipeline(
                    "automatic-speech-recognition",
                    model=selected_hf_model,
                    device=dev,
                )
            except (OSError, ValueError, ImportError):
                self._hf_pipe = None

    def recognize_once(
        self,
        device_index: Optional[int] = None,
        timeout: Optional[float] = None,
        phrase_time_limit: Optional[float] = None,
    ) -> Optional[str]:
        """Počkej na řeč z mikrofonu a vrať text (nebo None)."""
        mic = sr.Microphone(device_index=device_index)
        try:
            with mic as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
                audio = self.recognizer.listen(
                    source, timeout=timeout, phrase_time_limit=phrase_time_limit
                )
        except sr.WaitTimeoutError:
            return None

        # 1) openai-whisper lokálně (preferováno kvůli rychlosti na CPU)
        if self._whisper_model is not None:
            try:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    f.write(audio.get_wav_data())
                    tmp_path = f.name
                try:
                    # Whisper očekává ISO kód jazyka, pro cs-CZ mapuj na cs
                    lang = self.cfg.language
                    if lang.lower() in ("cs-cz", "cs_cz"):
                        lang = "cs"
                    result = self._whisper_model.transcribe(tmp_path, language=lang)
                    text = (result or {}).get("text", "").strip()
                    if text:
                        return text
                finally:
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass
            except (RuntimeError, OSError, ValueError):
                pass

        # 2) HF transformers Whisper
        if self._hf_pipe is not None:
            try:
                wav_bytes = audio.get_wav_data(convert_rate=16000, convert_width=2)
                np_audio = (
                    np.frombuffer(wav_bytes, dtype=np.int16).astype(np.float32)
                    / 32768.0
                )
                res = self._hf_pipe(
                    {"array": np_audio, "sampling_rate": 16000},
                    generate_kwargs={"language": "cs", "task": "transcribe"},
                )
                text = (res.get("text") if isinstance(res, dict) else str(res)).strip()
                if text:
                    return text
            except (RuntimeError, OSError, ValueError):
                pass

        # 3) Fallback: Google online API
        try:
            lang = self.cfg.language
            if lang == "cs":
                lang = "cs-CZ"
            return self.recognizer.recognize_google(audio, language=lang)
        except sr.UnknownValueError:
            return None
        except sr.RequestError:
            return None
