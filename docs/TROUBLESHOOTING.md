# Troubleshooting

## Zasekne se po „Ano, poslouchám“
- Zkontrolujte, že `stt.service` je `whisper` a `model: tiny` (na CPU nejrychlejší)
- V `src/core/jarvis.py` je pauza 0.2s před STT a 0.05s po — lze doladit
- Ověřte, že wake stream se opravdu pozastaví (`detector.stop_stream`) a obnoví

## Ticho / nerozpozná řeč
- Zvyšte `stt.timeout` (8–10) a `phrase_timeout` (8–10)
- Snižte `energy_threshold` (např. 100–150) nebo zapněte dynamic
- Otestujte mikrofon skriptem `test_simple_audio.py`

## TTS nemluví
- Zkuste `espeak -v cs "test"`
- Přepněte na `spd-say` nebo nastavte Piper model (`tts.service: piper`, `tts.model: <cesta>.onnx`)

## Wake word nefunguje
- Ověřte Porcupine access_key a cestu k `.ppn`
- Zvyšte `wake_word.threshold` (méně falešných), snižte pro citlivost

## Hlas se sám přerušuje
- Nastavte `tts.interrupt_enabled: false`
- Případně změňte `interrupt_words`

## LLM pomalý
- Zkraťte `max_tokens` a `n_ctx`, snižte `n_threads` podle CPU
- Zvažte rychlejší kvantizaci modelu v `models/`
