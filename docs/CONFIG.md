# Konfigurace MyJarvis

Všechna nastavení jsou v `config.yaml`.

## Wake word
```yaml
audio:
  sample_rate: 16000
  chunk_size: 2048
  channels: 1

wake_word:
  service: "porcupine"
  access_key: "<váš_klíč>"
  model_path: "hello-bitch/hello-bitch_en_linux_v3_0_0.ppn"
  threshold: 0.5
```

## STT
```yaml
stt:
  service: "whisper"       # whisper | whisper_hf | google
  language: "cs-CZ"
  model: "tiny"             # preferujeme tiny na CPU pro latenci
  hf_model: "openai/whisper-tiny"
  device: "auto"            # auto|cuda|cpu
  timeout: 7
  phrase_timeout: 9
  energy_threshold: 200
  dynamic_energy_threshold: true
  pause_threshold: 0.8
  non_speaking_duration: 0.2
```

## TTS
```yaml
tts:
  service: "espeak"         # piper | espeak | spd-say
  voice: "cs"
  speed: 150
  volume: 90
  pitch: 50
  gap: 10
  sentence_pause_ms: 300
  interrupt_enabled: false   # vypnuto defaultně kvůli samopřerušení
  interrupt_words: ["stop", "konec"]
```

## LLM
```yaml
llm:
  model_path: "models/Llama-3.2-1B-Instruct.Q5_K_M.gguf"
  n_ctx: 2048
  n_threads: 4
  max_tokens: 200
  temperature: 0.2
  top_p: 0.9
  repeat_penalty: 1.1
```

## KDE / systém
- Pro otevření souborů použijeme `xdg-open`.
- Pro power management `systemctl` (s potvrzením).
- KDE akce přes `qdbus`.
