#!/usr/bin/env python3
"""Bootstrap pro modulární Jarvis: spustí orchestrátor.

Zachovává kompatibilitu pro testy: exportuje pyaudio, sr, LLM_OK/PORCUPINE_OK
a poskytuje thin-compat třídu MyJarvis se stejným rozhraním pro testy.
"""

import asyncio
import logging
import traceback

# Třetí strany nejdřív (kvůli lintu)
import pyaudio  # pylint: disable=unused-import
import speech_recognition as sr  # pylint: disable=unused-import

from src.core.jarvis import JarvisOrchestrator
from src.system.action_executor import ActionExecutor

# Stavové příznaky (testy je přepisují monkeypatchem)
PORCUPINE_OK = False
try:  # LLM indikátor a placeholder
    from llama_cpp import Llama as _RealLlama  # type: ignore

    Llama = _RealLlama  # type: ignore
    LLM_OK = True
except ImportError:  # pragma: no cover - pokud balík není k dispozici

    class Llama:  # type: ignore
        pass

    LLM_OK = False


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger("MyJarvis")


class MyJarvis:
    """Thin kompatibilní vrstva pro stávající testy.

    Používá ActionExecutor pro systémové příkazy a noop speak.
    Reálný běh aplikace zajišťuje Orchestrator přes main().
    """

    def __init__(self):
        self.actions = ActionExecutor(
            speak=self.speak,
            listen=lambda: None,
            config={},
        )

    def speak(self, text: str) -> None:  # testy si tento atribut monkeypatchují
        _ = text
        return None

    def handle_system_command(self, text: str):
        """Deleguj na ActionExecutor.handle a vrať jeho výsledek."""
        return self.actions.handle(text)


def main() -> None:
    print("🤖 MyJarvis - Český Hlasový Asistent")
    print("=" * 50)
    print("📖 Řekněte: 'hello bitch' pro aktivaci")
    print("🗣️ Pak libovolný příkaz česky")
    print("🛑 'konec' = návrat do wake word režimu")
    print("=" * 50)
    try:
        jarvis = JarvisOrchestrator()
        asyncio.run(jarvis.run())
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error("Kritická chyba: %s", e)
        traceback.print_exc()


if __name__ == "__main__":
    main()
