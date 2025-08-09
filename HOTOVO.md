Hotovo dnes:

- Přerušitelné TTS: mluvení lze zastavit slovy „stop/konec/ticho/stačí“ i uprostřed věty.
- STT ladění: přidán non_speaking_duration, zpřísněn energy_threshold v configu.
- Prompt: nový soubor `prompt/system_prompt_cs.txt` pro lepší české odpovědi.
- Verifikační skript: `verify_implementation.py` – rychlá kontrola instalace a souborů.
- Sanity testy: `test_improvements.py` (prompt existuje, TTS binárky přítomné).

Další kroky:
- Zvážit filtrování nesmyslných transkriptů (např. minimum slov/hlásek) a lepší VAD.
- Přidat parametrické nastavení citlivosti přerušení.

