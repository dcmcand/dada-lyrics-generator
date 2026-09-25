import re
import unicodedata
from collections.abc import Mapping

import pronouncing
import pyphen

_VOWEL_GROUP_RE = re.compile(r"[aeiouy]+")


def normalize(word: str) -> str:
    return unicodedata.normalize("NFC", word).lower().replace("\u2019", "'").replace("\u2018", "'")


class Pronouncer:
    """Look up a word's stress pattern: overrides, then CMU, then a guess."""

    def __init__(self, overrides: Mapping[str, str] | None = None) -> None:
        self._overrides = {normalize(k): v for k, v in (overrides or {}).items()}
        self._hyphenator = pyphen.Pyphen(lang="en_US")
        self._guessed: set[str] = set()

    @property
    def guessed(self) -> list[str]:
        return sorted(self._guessed)

    def stress(self, word: str) -> str:
        key = normalize(word)
        if key in self._overrides:
            return self._overrides[key]
        cmu = _cmu_stress(key)
        if cmu is not None:
            return "?" if len(cmu) == 1 else cmu
        self._guessed.add(key)
        count = self._guess_syllables(key)
        return "?" if count == 1 else "1" + "0" * (count - 1)

    def _guess_syllables(self, key: str) -> int:
        vowel_groups = len(_VOWEL_GROUP_RE.findall(_syllable_letters(key)))
        if key.endswith("e") and not key.endswith("le") and vowel_groups > 1:
            vowel_groups -= 1
        hyphen_parts = len(self._hyphenator.positions(key)) + 1
        return max(vowel_groups, hyphen_parts, 1)


def _strip_accents(key: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", key) if not unicodedata.combining(c))


def _syllable_letters(key: str) -> str:
    """Accent-stripped letters, with a break before a vowel carrying a diaeresis (noël)."""
    letters: list[str] = []
    for char in unicodedata.normalize("NFD", key):
        if char == "\u0308" and letters:
            letters.insert(len(letters) - 1, "-")
        elif not unicodedata.combining(char):
            letters.append(char)
    return "".join(letters)


def _cmu_stress(key: str) -> str | None:
    candidates = [key]
    if _strip_accents(key) != key:
        candidates.append(_strip_accents(key))
    if key.endswith("'"):
        candidates.append(key[:-1])
    if key.endswith("in'"):
        candidates.append(key[:-1] + "g")
    for candidate in candidates:
        phones = pronouncing.phones_for_word(candidate)
        if phones:
            stress = pronouncing.stresses(phones[0]).replace("2", "1")
            if stress:
                return stress
    return None
