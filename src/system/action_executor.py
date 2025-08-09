"""Action executor: systémové příkazy a integrace prostředí (KDE, pactl, web).

Odděluje logiku z main.py. Používá callbacky `speak(text)` a `listen()`.
"""

from __future__ import annotations

from typing import Callable, Optional
from datetime import datetime
import shutil
import subprocess
import urllib.parse
import webbrowser


class ActionExecutor:
    """Zpracuje systémové příkazy a vrací tri-state výsledek.

    Návratové hodnoty:
    - True: ukončit konverzační režim (např. „konec“)
    - False: příkaz vykonán, ale režim pokračuje
    - None: nejedná se o systémový příkaz (předej AI)

    Bezpečnost: Nikdy neprovádí mazání, přesuny či formátování disků ani
    libovolné shellové příkazy. Jakékoli „smaž/odstran“ úmysly jsou odmítnuty.
    """

    def __init__(
        self,
        speak: Callable[[str], None],
        listen: Callable[[], Optional[str]],
        config: dict,
    ):
        self.speak = speak
        self.listen = listen
        self.config = config

    def handle(self, text: str) -> Optional[bool]:
        """Zpracuj požadavek a případně proveď bezpečnou akci.

        Vrací True/False/None dle třístupňové logiky třídy.
        """
        text_lower = text.lower()

        # Tvrdý bezpečnostní filtr proti destruktivním operacím
        dangerous = [
            "smaz",
            "smaž",
            "vymaž",
            "odstran",
            "delete",
            "rm ",
            "unlink",
            "prázdni koš",
            "prázdný koš",
            "formatuj",
            "naformátuj",
            "mkfs",
            "wipefs",
            "dd if=",
            "shred",
            "truncate",
        ]
        if any(k in text_lower for k in dangerous):
            self.speak("Z bezpečnostních důvodů nemohu mazat ani upravovat soubory.")
            return False

        # Ukončení konverzace
        if any(
            word in text_lower for word in ["konec", "stop", "ukončit", "vypni jarvis"]
        ):
            self.speak("Přecházím do wake word režimu")
            return True

        # Čas
        if any(word in text_lower for word in ["čas", "hodin", "kolik je"]):
            now = datetime.now()
            self.speak(f"Je {now.hour} hodin a {now.minute:02d} minut")
            return False

        # Vypnutí počítače (s potvrzením)
        if "vypni počítač" in text_lower:
            self.speak("Opravdu chcete vypnout počítač? Řekněte ano pro potvrzení")
            confirm = self.listen()
            if confirm and "ano" in confirm.lower():
                self.speak("Vypínám počítač")
                try:
                    subprocess.run(["systemctl", "poweroff"], check=False)
                except OSError:
                    pass
            else:
                self.speak("Vypnutí zrušeno")
            return False

        # Hlasitost zvuku
        if any(w in text_lower for w in ["ztiš", "ztlum", "tišeji", "ztišit"]):
            self.speak("Ztišuji zvuk")
            try:
                subprocess.run(
                    ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "-5%"],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except OSError:
                pass
            return False

        if any(
            w in text_lower
            for w in ["zesil", "hlasiteji", "nahlas", "přidej hlasitost"]
        ):
            self.speak("Zvyšuji hlasitost")
            try:
                subprocess.run(
                    ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+5%"],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except OSError:
                pass
            return False

        if any(w in text_lower for w in ["ztlum zvuk", "mute", "umlč"]):
            self.speak("Přepínám ztlumení")
            try:
                subprocess.run(
                    ["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except OSError:
                pass
            return False

        # Zamknout obrazovku
        if any(w in text_lower for w in ["zamkni obrazovku", "uzamkni", "zamkni"]):
            self.speak("Zamykám obrazovku")
            try:
                if shutil.which("qdbus"):
                    subprocess.run(
                        [
                            "qdbus",
                            "org.freedesktop.ScreenSaver",
                            "/ScreenSaver",
                            "Lock",
                        ],
                        check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                else:
                    subprocess.run(["loginctl", "lock-session"], check=False)
            except OSError:
                pass
            return False

        # Spuštění aplikací
        if "kalkula" in text_lower:
            self.speak("Spouštím kalkulačku")
            try:
                subprocess.Popen(
                    ["kcalc"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            except OSError:
                pass
            return False

        if any(w in text_lower for w in ["editor", "kate"]):
            self.speak("Spouštím editor")
            try:
                subprocess.Popen(
                    ["kate"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            except OSError:
                pass
            return False

        # Prohlížeč
        if any(word in text_lower for word in ["firefox", "prohlížeč", "internet"]):
            self.speak("Spouštím Firefox")
            try:
                subprocess.Popen(
                    ["firefox"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            except OSError:
                pass
            return False

        # Vyhledávání
        if any(word in text_lower for word in ["najdi", "vyhledej", "hledej"]):
            query = text_lower
            for word in ["najdi", "vyhledej", "hledej", "na", "internetu"]:
                query = query.replace(word, "")
            query = query.strip()
            if query:
                self.speak(f"Vyhledávám {query}")
                url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
                try:
                    webbrowser.open(url)
                except OSError:
                    pass
                self.speak("Výsledky jsou otevřené v prohlížeči")
            else:
                self.speak("Co mám vyhledat?")
            return False

        # Not a system command
        return None
