<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# MyJarvis - Pokyny pro GitHub Copilot

Tento projekt je lokální hlasový asistent pro Kubuntu/KDE Plasma napsaný v Pythonu.

## Technologický stack

- **Python 3.10+** s async/await
- **Porcupine** pro wake word detection
- **OpenAI Whisper** (transformers) pro STT
- **Meta-Llama-3-8B-Instruct GGUF** přes llama-cpp-python pro LLM
- **Piper TTS** pro převod textu na řeč
- **KDE Plasma integrace** přes qdbus

## Coding guidelines

- Používej async/await pro všechny I/O operace
- Logování pomocí structured logging
- Type hints pro všechny funkce
- Docstrings v českém jazyce
- Error handling s specific exceptions
- Konfigurace přes dataclasses

## Architektura

- Modulární design s jasně oddělenými komponentami
- Dependency injection pro konfiguraci
- Event-driven audio processing
- JSON-based function calling pro LLM

## AMD GPU optimalizace

- Používej ROCm pro GPU akceleraci
- Optimalizuj n_gpu_layers pro Llama model
- Memory management pro velké modely

## KDE Plasma integrace

- qdbus pro systémové akce
- xdg-open pro otevírání souborů
- systemctl pro power management
