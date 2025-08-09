#!/usr/bin/env python3
"""
Rychlý kontrolní skript: ověří klíčové komponenty bez dlouhého běhu.
"""
from __future__ import annotations
import shutil
import sys
import importlib
import importlib.util
from pathlib import Path

ROOT = Path(__file__).parent

OK = True  # Celkový úspěch kontroly

# 1) Konfig
cfg = ROOT / "config.yaml"
print(f"Config: {'OK' if cfg.exists() else 'MISSING'} -> {cfg}")
OK &= cfg.exists()

# 2) STT závislosti
print("Whisper openai:", importlib.util.find_spec("whisper") is not None)
print("Transformers:", importlib.util.find_spec("transformers") is not None)
print("SpeechRecognition:", importlib.util.find_spec("speech_recognition") is not None)

# 3) TTS binárky
print("espeak-ng:", shutil.which("espeak-ng") is not None)
print("espeak:", shutil.which("espeak") is not None)
print("spd-say:", shutil.which("spd-say") is not None)

# 4) LLM model
model = ROOT / "models" / "Llama-3.2-1B-Instruct.Q5_K_M.gguf"
print(f"LLM model: {'OK' if model.exists() else 'MISSING'} -> {model}")

# 5) Prompt soubor
prompt = ROOT / "prompt" / "system_prompt_cs.txt"
print(f"Prompt: {'OK' if prompt.exists() else 'MISSING'} -> {prompt}")

sys.exit(0 if OK else 1)
