# Architektura MyJarvis

Modulární asistent s jasně oddělenými vrstvami. Cílem je jednoduchá údržba a snadná rozšiřitelnost.

## Přehled komponent

- src/core/jarvis.py – orchestrátor, řídí stavy a tok dat (wake → STT → akce/LLM → TTS)
- src/audio/
  - wake_word_detector.py – Porcupine wrapper (start/stop, stream detect)
  - speech_to_text.py – STT (Whisper/OpenAI + HF fallback, Google jako záloha)
  - text_to_speech.py – TTS (Piper → espeak → spd-say), volitelné přerušení
- src/llm/
  - engine.py – Llama.cpp wrapper (lokální inference)
- src/system/action_executor.py – bezpečné systémové akce (KDE/qdbus, xdg-open, systemctl)
- src/utils/logger.py – strukturované logování

## Datové toky

1) Wake stream (Porcupine) běží v loopu a signalizuje „wake“.
2) Po wake orchestrátor pozastaví wake stream, spustí STT poslech, po dokončení obnoví.
3) Text se pošle do ActionExecutor (příkazy) nebo LLM.
4) Odpověď jde do TTS (s volitelným přerušením) a poté se obnoví wake stream.

## Důležité volby a latence

- STT: Na CPU preferujeme Whisper tiny pro nízkou latenci. HF pipeline je fallback.
- TTS: Piper je preferovaný pro kvalitu, jinak espeak/spd-say. Přerušení je defaultně vypnuté.
- Wake: Stream se pozastavuje před STT/TTS a po skončení obnovuje s malou prodlevou, aby se uvolnila zařízení.

## Konfigurace (config.yaml)

- wake_word: Porcupine klíč, cesta k .ppn, práh
- stt: service, language, model, device, timeouty
- tts: service, hlas/parametry, pause, interrupt_* klíče
- llm: model_path, n_ctx, tokeny, teplota atd.

## Testy a kvalita

- pytest sanity testy v repu (test_improvements.py, test_simple_audio.py)
- Lint/syntax check je součástí CI (doporučeno)

## Rozšíření

- Přidání nové akce: implementujte v ActionExecutor a doplňte do mapy příkazů
- Nový TTS/STT backend: přidejte modul a zapojte do orchestrátoru přes DI
- Pluginy: možné zapojit přes registr funkcí v ActionExecutor
