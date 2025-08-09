# MyJarvis - Český Hlasový Asistent

![CI](https://github.com/314PAP/jarvis/actions/workflows/ci.yml/badge.svg)

Plně funkční český hlasový asistent inspirovaný nejlepšími GitHub projekty. Navržen pro Kubuntu/KDE Plasma s důrazem na spolehlivost a českou lokalizaci.

## 🎯 Současné funkčnosti

✅ **Kompletně funkční systém:**
- Wake word detekce s custom modelem "hello bitch"
- Česká konverzace přes Whisper STT (HF/Google jako fallback) a espeak/Piper TTS
- LLM odpovědi (Llama 3.2 1B model)
- Systémové příkazy s potvrzením
- Kontinuální naslouchání s možností přerušení
- Automatické testování a monitoring

## 🗣️ Jak používat

### Základní ovládání:
1. **Aktivace**: Řekněte "hello bitch" → asistent začne poslouchat
2. **Rozhovor**: Ptejte se česky na cokoliv
3. **Přerušení**: Řekněte "stop" během mluvení
4. **Ukončení**: Řekněte "konec" pro přechod do wake word režimu

### Příklady příkazů:
```
"Kolik je hodin?"
"Jak se máš?"
"Co je hlavní město Francie?"
"Vypni počítač" (s potvrzením)
"Otevři Firefox"
"Najdi na internetu počasí v Praze"
```

## 🚀 Instalace a spuštění

### 1. Rychlá instalace:
```bash
./setup.sh
```

### 2. Spuštění:
```bash
./jarvis.sh
```

### 3. Testy:
```bash
./test_watch.sh  # Spustí monitoring změn a testy
```

## 📂 Struktura projektu

```
myjarvis/
├── main.py              # Hlavní asistent
├── config.yaml          # Konfigurace
├── jarvis.sh            # Spouštěcí script
├── setup.sh             # Instalační script
├── test_watch.sh        # Automatické testování
├── hello-bitch/         # Wake word model
├── models/              # LLM modely
├── logs/                # Log soubory
└── docs/                # Dokumentace
  ├── ARCHITECTURE.md  # Architektura a datové toky
  ├── CONFIG.md        # Konfigurace
  └── TROUBLESHOOTING.md
```

## ⚙️ Konfigurace (základ)

Hlavní nastavení v `config.yaml`:

```yaml
# Wake word (váš custom model)
wake_word:
  service: "porcupine"
  model_path: "hello-bitch/hello-bitch_en_linux_v3_0_0.ppn"
  keyword: "hello bitch"

# Český STT/TTS
stt:
  language: "cs-CZ"
  service: "whisper"   # rychlý CPU: tiny model
  model: "tiny"

tts:
  service: "espeak"    # nebo piper (doporučeno s modelem)
  voice: "cs"
```

Více v docs/CONFIG.md

## 🔧 Systémové funkce

### Podporované akce:
- **Spouštění aplikací**: Firefox, Dolphin, Konsole
- **Systémové příkazy**: vypnutí, restart, odhlášení (s potvrzením)
- **Vyhledávání**: automatické otevírání prohlížeče
- **KDE integrace**: ovládání plochy, notifikace

### Bezpečnostní opatření:
- Potvrzení pro kritické systémové akce
- Logging všech příkazů
- Možnost přerušení během zpracování

## 📊 Testování

### Rychlé testy:
- `./jarvis_env/bin/pytest -q`

### Monitoring:
- Průběžné logování do `logs/jarvis.log`
- Performance metriky v reálném čase
- Automatické oznámení problémů

## 🛠️ Řešení problémů

### Časté problémy:

1. **Wake word nefunguje**:
   ```bash
   # Zkontrolujte Porcupine klíč
   cat config.yaml | grep access_key
   ```

2. **STT nerozumí češtině**:
   ```bash
   # Test mikrofonu
   python test_simple.py
   ```

3. **TTS nemluvý**:
   ```bash
   # Test audio výstupu
   espeak -v cs "test"
   ```

## 📈 Roadmapa
- [ ] Piper jako výchozí TTS s CZ hlasem (model a config)
- [ ] Lehčí režim LLM s menší spotřebou (n_ctx, max_tokens presety)
- [ ] Plugin systém pro rozšíření akcí

## 🤝 Přispívání

1. Všechny změny dokumentujte v `docs/CHANGELOG.md`
2. Spusťte `test_watch.sh` před commitem
3. Aktualizujte README.md podle změn
4. Udržujte zpětnou kompatibilitu konfigurace

## 📝 Změny a aktualizace

- **2024-08-08**: Verze 1.0 - kompletní funkční systém
- **2024-08-08**: Přidána Porcupine podpora s custom modelem
- **2024-08-08**: Zlepšena česká konverzace a STT timeouty

---

**Autor**: GitHub Copilot + Uživatelské požadavky  
**Licence**: MIT  
**Podpora**: Vytvořte issue pro problémy nebo návrhy
