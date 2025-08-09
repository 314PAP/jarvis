#!/usr/bin/env python3
"""Základní sanity testy pro audio, TTS a prompt."""
from pathlib import Path
import shutil

ROOT = Path(__file__).parent


def test_prompt_exists():
    """Ověř, že existuje systémový prompt soubor."""
    assert (ROOT / "prompt" / "system_prompt_cs.txt").exists()


def test_tts_binaries_present():
    """Ověř, že je dostupná alespoň jedna TTS binárka."""
    assert (
        shutil.which("espeak-ng") or shutil.which("espeak") or shutil.which("spd-say")
    )
