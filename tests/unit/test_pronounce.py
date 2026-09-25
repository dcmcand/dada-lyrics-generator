import pytest

from dada_generator.pronounce import Pronouncer


@pytest.mark.parametrize(
    ("word", "expected"),
    [
        ("river", "10"),
        ("River", "10"),
        ("hello", "01"),
        ("the", "?"),
        ("love", "?"),
        ("skyline", "11"),  # CMU secondary stress 2 maps to 1
        ("runnin'", "10"),  # in CMU directly
        ("dreamin'", "10"),  # retried as "dreaming"
        ("caf\u00e9", "01"),  # retried without accents as "cafe"
        ("cafe\u0301", "01"),  # NFD input
        ("Z\u00fcrich", "10"),
    ],
)
def test_cmu_words(word, expected):
    p = Pronouncer()
    assert p.stress(word) == expected
    assert p.guessed == []


@pytest.mark.parametrize(
    ("word", "expected"),
    [
        ("zorp", "?"),
        ("xyzzy", "10"),
        ("zorbflak", "10"),
        ("glimmerous", "100"),
        ("zo\u00ebla", "100"),  # diaeresis starts a new syllable
        ("br\u00e9zin", "10"),  # accented vowel counts as a vowel
    ],
)
def test_guessed_words(word, expected):
    p = Pronouncer()
    assert p.stress(word) == expected
    assert p.guessed == [word]


def test_guessed_is_sorted_and_unique():
    p = Pronouncer()
    for word in ["zorp", "Xyzzy", "zorp"]:
        p.stress(word)
    assert p.guessed == ["xyzzy", "zorp"]


@pytest.mark.parametrize(
    ("overrides", "word", "expected"),
    [
        ({"zorp": "01"}, "zorp", "01"),
        ({"Zorp": "01"}, "ZORP", "01"),
        ({"river": "01"}, "river", "01"),  # override beats CMU
        ({"the": "0"}, "the", "0"),  # override may pin a monosyllable
        ({"dreamin\u2019": "11"}, "dreamin'", "11"),
    ],
)
def test_overrides(overrides, word, expected):
    p = Pronouncer(overrides)
    assert p.stress(word) == expected
    assert p.guessed == []
