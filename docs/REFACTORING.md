# Refaktoring: Modularizace Jarvis

Cíl: 100% zachování chování. Pouze změna struktury, lepší čitelnost a údržba.

## Kroková strategie
1) Extrakce TTS do `src/audio/text_to_speech.py`
2) Extrakce STT do `src/audio/speech_to_text.py`
3) Extrakce wake-word do `src/audio/wake_word_detector.py`
4) Akce systému do `src/system/action_executor.py` (již existuje)
5) LLM do `src/llm/engine.py` (alias k existujícímu `llama_brain_fast.py`)
6) Orchestrátor do `src/core/jarvis.py`
7) Ztenčení `main.py` na bootstrap

Každý krok: běžící testy (pytest) a beze změny chování.

## Rozhraní (kontrakty)
- TextToSpeech.speak(text: str) -> None
- SpeechToText.adjust(source) -> None; listen(source, timeout, limit) -> AudioData; transcribe(audio) -> str|None
- WakeWordDetector.start/stop/detect -> bool
- ActionExecutor.handle(text: str) -> bool|False|None
- LlmEngine.generate(text: str) -> str

## Mapování symbolů
- main.MyJarvis.speak -> src/audio/text_to_speech.TextToSpeech.speak
- main.MyJarvis.listen_for_command + init_stt -> src/audio/speech_to_text.SpeechToText
- main.MyJarvis.detect_wake_word + init_porcupine -> src/audio/wake_word_detector.WakeWordDetector
- main.MyJarvis.handle_system_command -> src/system/action_executor.ActionExecutor
- main.MyJarvis.generate_ai_response + init_llm -> src/llm/engine.LlmEngine
- main.MyJarvis.main_loop -> src/core/jarvis.JarvisOrchestrator

## Ověření
- `tools/checks.sh` + `pytest -q` po každém kroku.
