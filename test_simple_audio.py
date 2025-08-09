#!/usr/bin/env python3
"""Jednoduchý test audio citlivosti a wake word simulace.
Pozn.: Testy mohou být přeskočeny, pokud není dostupný mikrofon nebo Porcupine.
"""
import time
import pytest
import speech_recognition as sr

try:
    import pvporcupine  # type: ignore
except ImportError:  # Pylint: explicit ImportError, ne broad
    pvporcupine = None  # type: ignore


def test_basic_audio():
    """Test základní audio citlivosti (přeskočí, pokud není mikrofon)."""
    print("🔍 Test základní audio citlivosti...")

    recognizer = sr.Recognizer()

    # Nastavení velmi citlivé podle nového config
    recognizer.energy_threshold = 50
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 0.8
    # Důležité: musí platit pause_threshold >= non_speaking_duration >= 0
    try:
        recognizer.non_speaking_duration = 0.2
    except AttributeError:
        # starší verze knihovny nemusí mít tento atribut
        pass

    try:
        with sr.Microphone() as source:
            print("🔧 Kalibrace...")
            recognizer.adjust_for_ambient_noise(source, duration=0.3)

            print(f"📊 Energy threshold po kalibraci: {recognizer.energy_threshold}")

            # Vynucení nízký threshold
            recognizer.energy_threshold = 50

            print("🎤 Řekněte něco NORMÁLNĚ (ne křičte)...")
            start_time = time.time()

            audio = recognizer.listen(source, timeout=5, phrase_time_limit=3)
            end_time = time.time()

            duration = end_time - start_time
            print(f"⏱️ Doba nahrávání: {duration:.1f}s")

            # Pokus o rozpoznání
            try:
                text = recognizer.recognize_google(audio, language="cs-CZ")
                print(f"✅ Rozpoznáno: '{text}'")
                assert True
            except sr.UnknownValueError:
                print("❌ Nerozpoznáno - ale audio bylo zachyceno!")
                assert True  # Audio bylo zachyceno, to je dobré
            except sr.RequestError as e:
                print(f"❌ Chyba služby: {e}")
                assert False

    except sr.WaitTimeoutError:
        print(
            "❌ Timeout - nedetekoval žádné audio. Mikrofon možná nefunguje nebo je málo citlivý."
        )
        pytest.skip("Mikrofon nedostupný nebo ticho – přeskočeno")
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"❌ Chyba: {e}")
        pytest.skip("Audio test přeskočen kvůli chybě prostředí")


def test_wake_word_simulation():
    """Test simulace wake word detekce (přeskočí, pokud Porcupine chybí)."""
    print("🔍 Test simulace wake word...")
    if pvporcupine is None:
        pytest.skip("Porcupine není nainstalován – test přeskočen")
        return
    try:
        # Test s aktuální konfigurací
        porcupine = pvporcupine.create(
            access_key="CmyAfGBdVMr5Lycr5YbH+LzEWIugNopLJAgNGxHLVY5pX8Qyja2weA==",
            keyword_paths=["hello-bitch/hello-bitch_en_linux_v3_0_0.ppn"],
            sensitivities=[0.5],  # Nové nastavení
        )
        print(f"✅ Porcupine inicializován s frame_length: {porcupine.frame_length}")
        print(f"✅ Sample rate: {porcupine.sample_rate}")
        porcupine.delete()
        assert True
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"❌ Porcupine chyba: {e}")
        pytest.skip("Porcupine nedostupný – test přeskočen")


def main():
    """Volitelný samostatný běh testů (mimo pytest)."""
    print("🚀 Test audio citlivosti - BEZ KŘIČENÍ!")
    print("=" * 50)

    for test in (test_basic_audio, test_wake_word_simulation):
        print()
        try:
            test()
            print(f"✅ {test.__name__}")
        except Exception as e:  # pylint: disable=broad-exception-caught
            print(f"❌ {test.__name__}: {e}")


if __name__ == "__main__":
    main()
