import re
from collections.abc import Iterable
from dataclasses import dataclass

from dada_generator.source import SourceLine

MODES = ("phrase", "word")

CONJUNCTIONS = frozenset(
    {"and", "but", "or", "so", "when", "because", "while", "if", "though", "until", "then"}
)

# Phrase breaks: sentence/clause punctuation, brackets, quotes, en/em dashes,
# a spaced hyphen, or a run of two or more hyphens. A hyphen inside a word
# ("well-known") is not a break.
_BREAK_RE = re.compile(r"[,.;:!?()\[\]{}\"“”–—]|\s-+\s|-{2,}")

# A word is letters/digits with optional internal apostrophes. A trailing
# apostrophe is kept only after "in" (dropped-g spellings like "runnin'").
_WORD_RE = re.compile(r"[^\W_]+(?:'[^\W_]+)*(?:(?<=[iI][nN])')?")


@dataclass(frozen=True)
class Chunk:
    words: tuple[str, ...]
    source: str


def tokenize(text: str) -> list[str]:
    normalized = text.replace("’", "'").replace("‘", "'")
    return _WORD_RE.findall(normalized)


def chunk(lines: Iterable[SourceLine], mode: str) -> list[Chunk]:
    """Split lyric lines into phrase-level or word-level chunks."""
    if mode not in MODES:
        raise ValueError(f"unknown mode '{mode}'")
    chunks: list[Chunk] = []
    for line in lines:
        if mode == "word":
            chunks.extend(Chunk((word,), line.source) for word in tokenize(line.text))
            continue
        for fragment in _BREAK_RE.split(line.text):
            current: list[str] = []
            for word in tokenize(fragment):
                if current and word.lower() in CONJUNCTIONS:
                    chunks.append(Chunk(tuple(current), line.source))
                    current = []
                current.append(word)
            if current:
                chunks.append(Chunk(tuple(current), line.source))
    return chunks
