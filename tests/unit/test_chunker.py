import pytest

from dada_generator.chunker import Chunk, chunk, tokenize
from dada_generator.source import SourceLine


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("the river hums", ["the", "river", "hums"]),
        ("don't stop", ["don't", "stop"]),
        ("don\u2019t stop", ["don't", "stop"]),
        ("runnin' late", ["runnin'", "late"]),
        ("dreamin\u2019 on", ["dreamin'", "on"]),
        ("'quoted' word", ["quoted", "word"]),
        ("caf\u00e9 society", ["caf\u00e9", "society"]),
        ("nai\u0308ve cafe\u0301", ["na\u00efve", "caf\u00e9"]),  # NFD input
        ("well-known road", ["well", "known", "road"]),
        ("...!?", []),
    ],
)
def test_tokenize(text, expected):
    assert tokenize(text) == expected


def _words(chunks):
    return [" ".join(c.words) for c in chunks]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("I walked home, the streetlights hummed", ["I walked home", "the streetlights hummed"]),
        ("stop. go! why? now; here: there", ["stop", "go", "why", "now", "here", "there"]),
        ("left \u2014 right \u2013 center", ["left", "right", "center"]),
        ("up - down -- around", ["up", "down", "around"]),
        ("well-known road", ["well known road"]),
        ("I ran and she hid", ["I ran", "and she hid"]),
        ("and then we left", ["and", "then we left"]),
        ("but I stayed until dawn", ["but I stayed", "until dawn"]),
        ("rock AND roll", ["rock", "AND roll"]),
        ("...", []),
    ],
)
def test_phrase_chunking(text, expected):
    assert _words(chunk([SourceLine(text, "s.txt")], "phrase")) == expected


def test_word_chunking_keeps_source():
    chunks = chunk([SourceLine("Hello, big world", "a.txt")], "word")
    assert chunks == [
        Chunk(("Hello",), "a.txt"),
        Chunk(("big",), "a.txt"),
        Chunk(("world",), "a.txt"),
    ]


def test_phrase_chunks_never_cross_lines():
    lines = [SourceLine("one two", "a.txt"), SourceLine("three four", "b.txt")]
    assert chunk(lines, "phrase") == [
        Chunk(("one", "two"), "a.txt"),
        Chunk(("three", "four"), "b.txt"),
    ]


def test_unknown_mode():
    with pytest.raises(ValueError, match="unknown mode"):
        chunk([SourceLine("x", "a.txt")], "letter")
