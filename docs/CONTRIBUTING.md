# Přispívání do MyJarvis

Děkujeme za zájem přispívat! Níže jsou základní pravidla a doporučení.

## Jak začít
- Forkněte repozitář a vytvořte větev z `main`
- Dbejte na modulární změny, malé PR jsou vítané
- Přidejte/aktualizujte testy, pokud měníte chování

## Kódový styl
- Python 3.10+, typové anotace
- Strukturované logování
- Docstringy v češtině
- Error handling pomocí specifických výjimek

## Testy
- Spusťte `./jarvis_env/bin/pytest -q` před PR
- Testy by měly pokrýt happy-path a 1–2 okrajové případy

## Dokumentace
- Pokud měníte veřejné chování, aktualizujte `README.md` a dokumenty v `docs/`

## Bezpečnost
- Kritické systémové akce musí vyžadovat potvrzení
- Nepřidávejte akce, které by mohly mazat soubory bez explicitní volby
