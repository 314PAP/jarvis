"""Text-to-Speech modul pro Jarvis.

Podporuje backendy: Piper (preferovaný, pokud je k dispozici model), espeak-ng/espeak
nebo spd-say. Přerušení hlasem je ve výchozím stavu vypnuté, aby se Jarvis
nepřerušoval vlastním hlasem.
"""

from __future__ import annotations

from typing import Optional, Sequence
import os
import re
import shutil
import subprocess
import tempfile
import time

import speech_recognition as sr


class TextToSpeech:
    """TTS s možností volitelného přerušení během mluvení.

    Kontrakt:
    - vstup: text (str)
    - výstup: mluvený projev (blokující), návrat None
    - chyby: chyby backendu jsou zachytávány; při selhání se použije fallback
    - úspěch: text je přehrán nebo vypsán do konzole
    """

    def __init__(self, cfg: dict, recognizer: sr.Recognizer, mic_device: Optional[int]):
        self.cfg = cfg or {}
        self.recognizer = recognizer
        self.mic_device = mic_device
        self._last_tmp_wav: Optional[str] = None
        # hooky pro pozastavení/obnovení wake streamu nastavuje orchestrátor
        self._close_wake_stream = None  # type: ignore
        self._restore_wake_stream = None  # type: ignore

    def set_wake_stream_hooks(self, close_cb, restore_cb) -> None:
        """Nastaví callbacky pro pozastavení/obnovení wake-word streamu."""
        self._close_wake_stream = close_cb
        self._restore_wake_stream = restore_cb

    # ---- vnitřní pomocné funkce -------------------------------------------------
    def _spawn_tts(self, chunk: str) -> Optional[subprocess.Popen]:
        """Spustí syntézu a vrátí Popen přehrávače, je-li k dispozici.

        U Piper se nejprve vygeneruje WAV do dočasného souboru a ten se přehraje
        paplay/aplay. U espeak/spd-say se přehrává přímo procesem.
        """
        service = (self.cfg.get("service") or "espeak").lower()

        # Preferuj Piper, pokud je nakonfigurován model a binárka je dostupná
        if service == "piper":
            model = self.cfg.get("model") or self.cfg.get("voice_path")
            voice_cfg = self.cfg.get("voice_config")
            if model and shutil.which("piper"):
                tmp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                tmp_path = tmp_wav.name
                tmp_wav.close()
                try:
                    cmd = ["piper", "--model", model, "--output_file", tmp_path]
                    if voice_cfg:
                        cmd.extend(["--config", voice_cfg])
                    p = subprocess.run(
                        cmd,
                        input=chunk.encode("utf-8"),
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False,
                    )
                    if p.returncode != 0:
                        try:
                            os.unlink(tmp_path)
                        except OSError:
                            pass
                        return None
                    # vyber přehrávač
                    if shutil.which("paplay"):
                        play_cmd = ["paplay", tmp_path]
                    elif shutil.which("aplay"):
                        play_cmd = ["aplay", "-q", tmp_path]
                    else:
                        play_cmd = ["play", "-q", tmp_path]
                    proc = subprocess.Popen(
                        play_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                    self._last_tmp_wav = tmp_path
                    return proc
                except (OSError, ValueError):
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass
                    return None
            # fallback na espeak pokud Piper nelze použít
            service = "espeak"

        if service == "espeak":
            voice = self.cfg.get("voice", "cs")
            speed = str(self.cfg.get("speed", 150))
            volume = str(self.cfg.get("volume", 90))
            pitch = str(self.cfg.get("pitch", 50))
            gap = str(self.cfg.get("gap", 10))
            for bin_name in ("espeak-ng", "espeak"):
                if shutil.which(bin_name):
                    cmd = [
                        bin_name,
                        "-v",
                        voice,
                        "-s",
                        speed,
                        "-a",
                        volume,
                        "-p",
                        pitch,
                        "-g",
                        gap,
                        chunk,
                    ]
                    try:
                        return subprocess.Popen(
                            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                        )
                    except (OSError, ValueError):
                        continue
            if shutil.which("spd-say"):
                try:
                    return subprocess.Popen(
                        ["spd-say", "-l", "cs", chunk],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                except OSError:
                    return None
            # poslední fallback – aspoň zaloguj do konzole
            print(f"🗣️ {chunk}")
            return None

        # neznámý service -> konzole
        print(f"🗣️ {chunk}")
        return None

    def _listen_for_interrupt(self, timeout_s: Optional[float]) -> bool:
        """Krátce poslouchej pro klíčová slova (stop/konec); defaultně vypnuto."""
        if not self.mic_device:
            return False
        if not self.cfg.get("interrupt_enabled", False):
            return False
        if timeout_s is None:
            timeout_s = float(self.cfg.get("interrupt_listen_timeout", 0.6))
        phrase_limit = float(self.cfg.get("interrupt_phrase_limit", 0.8))
        mic = sr.Microphone(device_index=self.mic_device)
        try:
            with mic as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.15)
                audio = self.recognizer.listen(
                    source, timeout=timeout_s, phrase_time_limit=phrase_limit
                )
                try:
                    heard = self.recognizer.recognize_google(
                        audio, language=self.cfg.get("language", "cs-CZ")
                    )
                except sr.UnknownValueError:
                    return False
                except (sr.RequestError, OSError, ValueError):
                    return False
                words: Sequence[str] = (
                    self.cfg.get("interrupt_words")
                    if isinstance(self.cfg.get("interrupt_words"), list)
                    else ["stop", "konec"]
                )
                tl = heard.lower()
                return any(w in tl for w in words)
        except sr.WaitTimeoutError:
            return False
        except (OSError, ValueError):
            return False

    # ---- veřejné API -------------------------------------------------------------
    def speak(self, text: str) -> None:
        """Řekni text po větách a případně umožni přerušení.

        Dělí text na věty, pozastaví wake stream, přehraje věty postupně a poté
        wake stream obnoví. Dočasné WAVy (Piper) se uklidí.
        """
        if not text:
            return

        # rozděl text na věty a zachovej interpunkci
        sentences = [
            s.strip() for s in re.split(r"([.!?…]+)\s+", text) if s and not s.isspace()
        ]
        chunks: list[str] = []
        i = 0
        while i < len(sentences):
            if i + 1 < len(sentences) and re.match(r"[.!?…]+", sentences[i + 1]):
                chunks.append(sentences[i] + sentences[i + 1])
                i += 2
            else:
                chunks.append(sentences[i])
                i += 1

        # pozastav wake stream (pokud je k dispozici)
        if self._close_wake_stream:
            try:
                self._close_wake_stream()
            except OSError:
                pass

        pause_ms = int(self.cfg.get("sentence_pause_ms", 300))
        for chunk in chunks:
            proc = self._spawn_tts(chunk)
            if proc is None:
                # fallback simulace – přibližná délka mluvení
                time.sleep(max(0.1, len(chunk) / 8 / 10))
            else:
                interrupted = False
                while proc.poll() is None:
                    if self._listen_for_interrupt(timeout_s=None):
                        interrupted = True
                        try:
                            proc.terminate()
                        except OSError:
                            pass
                        break
                    time.sleep(0.05)
                # úklid dočasného WAV po dohrání
                if self._last_tmp_wav:
                    try:
                        os.unlink(self._last_tmp_wav)
                    except OSError:
                        pass
                    finally:
                        self._last_tmp_wav = None
                if interrupted:
                    break

            time.sleep(pause_ms / 1000.0)
            if self._listen_for_interrupt(timeout_s=None):
                break

        # obnova wake streamu
        if self._restore_wake_stream:
            try:
                self._restore_wake_stream()
            except OSError:
                pass
        # finální úklid případného tmp souboru
        if self._last_tmp_wav:
            try:
                os.unlink(self._last_tmp_wav)
            except OSError:
                pass
            finally:
                self._last_tmp_wav = None
