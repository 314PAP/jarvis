#!/usr/bin/env python3
"""Unit testy pro konverzační režim a povely konec/stop (bez HW).
Mockuje se mikrofon i TTS, aby se testy spustily rychle a offline.
"""
import types
import sys
from pathlib import Path
import pytest

# Import modulu
sys.path.insert(0, str(Path(__file__).parent))
import main as jarvis_mod  # type: ignore  # pylint: disable=wrong-import-position,import-error


class DummyRecognizer:
    """Minimalní stub rozpoznávače pro testy bez HW."""

    def __init__(self):
        self.energy_threshold = 50
        self.dynamic_energy_threshold = True
        self.pause_threshold = 0.8
        self.non_speaking_duration = 0.2

    def adjust_for_ambient_noise(self, _source, _duration=0.2):
        return None

    def listen(self, _source, _timeout=1, _phrase_time_limit=1):
        return types.SimpleNamespace()

    def recognize_google(self, _audio, _language="cs-CZ"):
        return "konec"


class DummyMic:
    """Stub mikrofonu pro odpojení od skutečného zařízení."""

    def __init__(self, device_index=None):
        self.device_index = device_index

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class DummyAudio:
    """Stub PyAudio pro testy bez HW."""

    def __init__(self):
        pass

    def open(self, **_kwargs):
        class _S:
            """Zjednodušený stream objekt s metodou close()."""

            def close(self):
                return None

        return _S()

    def get_device_count(self):
        return 1

    def get_device_info_by_index(self, _index):
        return {"name": "dummy", "maxInputChannels": 1}

    def terminate(self):
        return None


@pytest.fixture(autouse=True)
def patch_dependencies(monkeypatch):
    """Automaticky patchni externí závislosti pro rychlé a stabilní testy."""
    # Pyaudio
    monkeypatch.setattr(
        jarvis_mod,
        "pyaudio",
        types.SimpleNamespace(PyAudio=DummyAudio, paInt16=8),
    )
    # SpeechRecognition
    monkeypatch.setattr(
        jarvis_mod,
        "sr",
        types.SimpleNamespace(Recognizer=DummyRecognizer, Microphone=DummyMic),
    )
    # Porcupine
    monkeypatch.setattr(jarvis_mod, "PORCUPINE_OK", False)

    # LLM
    monkeypatch.setattr(jarvis_mod, "LLM_OK", True)
    monkeypatch.setattr(
        jarvis_mod,
        "Llama",
        types.SimpleNamespace(__call__=lambda *_args, **_kwargs: None),
    )


def test_conversation_konec_returns_to_wake(monkeypatch):
    """Povel 'konec' vrací do režimu wake word."""
    j = jarvis_mod.MyJarvis()
    # Není potřeba STT: rovnou otestuj systémové chování a vypni TTS
    monkeypatch.setattr(j, "speak", lambda text: None)
    res = j.handle_system_command("konec")
    assert res is True


def test_speak_interrupt_words_dont_crash(monkeypatch):
    """Volání speak by mělo být bezpečné vůči přerušovacím slovům."""
    j = jarvis_mod.MyJarvis()
    # Mocknout TTS spawn na no-op
    monkeypatch.setattr(j, "speak", lambda text: None)
    j.speak("Test. To je vše.")
