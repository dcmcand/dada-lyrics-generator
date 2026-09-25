"""Journey 13: repeated phrases do not dominate the song."""

import random
from collections import Counter
from statistics import mean

import pytest
from conftest import EXAMPLES

from dada_generator.assembler import Pool, build_song
from dada_generator.chunker import chunk
from dada_generator.config import load_song
from dada_generator.pronounce import Pronouncer
from dada_generator.source import read_sources
from dada_generator.units import tag

LYRICS = EXAMPLES / "sample-lyrics.txt"
SEEDS = range(1, 21)


def _generated_lines(song):
    """Lines from sections actually generated (a repeat: true section counts once)."""
    seen, lines = set(), []
    for section in song.sections:
        if id(section) not in seen:
            seen.add(id(section))
            lines.extend(line.text for line in section.lines)
    return lines


def _songs(song_file, mode):
    units = tag(chunk(read_sources([LYRICS]), mode), Pronouncer(), mode)
    pool, config = Pool(units), load_song(EXAMPLES / song_file)
    return [build_song(config, pool, mode, random.Random(seed)) for seed in SEEDS]


@pytest.mark.parametrize("song_file", ["ballad.yaml", "pop-song.yaml"])
def test_phrase_mode_lines_are_mostly_distinct(song_file):
    ratios = []
    for song in _songs(song_file, "phrase"):
        lines = _generated_lines(song)
        ratios.append(len(set(lines)) / len(lines))
    assert mean(ratios) >= 0.6


@pytest.mark.parametrize("song_file", ["ballad.yaml", "pop-song.yaml"])
def test_word_mode_no_word_dominates(song_file):
    for song in _songs(song_file, "word"):
        words = [w.lower() for line in _generated_lines(song) for w in line.split()]
        assert Counter(words).most_common(1)[0][1] / len(words) <= 0.3
