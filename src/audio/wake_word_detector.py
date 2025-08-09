"""Wake word detektor (Porcupine) oddělený od main.

Poskytuje jednoduché API:
- start() / stop(): správa Porcupine a audio streamu
- detect() -> bool: přečte jeden frame a vrátí, zda bylo klíčové slovo detekováno
- stop_stream() / start_stream(): dočasné pozastavení/obnovení pouze streamu
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

try:
    import pvporcupine  # type: ignore
except ImportError:  # pragma: no cover - volitelná závislost
    pvporcupine = None  # type: ignore


@dataclass
class WakeWordConfig:
    access_key: str
    model_path: str
    keyword: str = ""
    threshold: float = 0.5


class WakeWordDetector:
    """Zapouzdření Porcupine, neřeší výběr mikrofonu ani PyAudio init.

    Očekává externě vytvořený PyAudio a zvolený `input_device_index`.
    """

    def __init__(
        self, pyaudio_instance, device_index: Optional[int], cfg: WakeWordConfig
    ):
        self._pa = pyaudio_instance
        self._device_index = device_index
        self._cfg = cfg
        self._porcupine = None
        self._stream = None

    @property
    def active(self) -> bool:
        return self._porcupine is not None and self._stream is not None

    def start(self) -> bool:
        """Inicializuj Porcupine a otevři kontinuální stream. Vrací úspěch."""
        if pvporcupine is None or self._device_index is None:
            return False
        if self._porcupine is None:
            try:
                self._porcupine = pvporcupine.create(
                    access_key=self._cfg.access_key,
                    keyword_paths=[self._cfg.model_path],
                    sensitivities=[self._cfg.threshold],
                )
            except (
                OSError,
                ValueError,
                AttributeError,
            ):  # pragma: no cover - knihovní chyby
                self._porcupine = None
                return False
        # otevři stream
        try:
            self._stream = self._pa.open(
                format=self._pa.get_format_from_width(2),
                channels=1,
                rate=16000,
                input=True,
                input_device_index=self._device_index,
                frames_per_buffer=self._porcupine.frame_length,  # type: ignore[union-attr]
            )
            return True
        except (OSError, ValueError):  # pragma: no cover - driver chyby
            self._stream = None
            return False

    def stop(self) -> None:
        """Ukonči stream i Porcupine."""
        self.stop_stream()
        if self._porcupine is not None:
            try:
                self._porcupine.delete()
            except (OSError, AttributeError):  # pragma: no cover
                pass
            self._porcupine = None

    def stop_stream(self) -> None:
        """Dočasně zavři pouze stream (např. kvůli STT/TTS)."""
        if self._stream is not None:
            try:
                self._stream.close()
            except OSError:  # pragma: no cover
                pass
            self._stream = None

    def start_stream(self) -> bool:
        """Obnov pouze stream, Porcupine musí být inicializován."""
        if self._porcupine is None or self._device_index is None:
            return False
        try:
            self._stream = self._pa.open(
                format=self._pa.get_format_from_width(2),
                channels=1,
                rate=16000,
                input=True,
                input_device_index=self._device_index,
                frames_per_buffer=self._porcupine.frame_length,  # type: ignore[union-attr]
            )
            return True
        except (OSError, ValueError):  # pragma: no cover
            self._stream = None
            return False

    def detect(self) -> bool:
        """Zpracuj jeden frame a vrať True, pokud Porcupine detekoval keyword."""
        if self._porcupine is None or self._stream is None:
            return False
        try:
            audio_data = self._stream.read(self._porcupine.frame_length, exception_on_overflow=False)  # type: ignore[union-attr]
            audio_np = np.frombuffer(audio_data, dtype=np.int16)
            idx = self._porcupine.process(audio_np)
            return idx >= 0
        except (OSError, ValueError, IOError):  # pragma: no cover
            return False
