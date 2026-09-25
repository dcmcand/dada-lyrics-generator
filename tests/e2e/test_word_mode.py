import random
from statistics import mean

from conftest import EXAMPLES
from test_phrase_mode import assert_sheet_matches

from dada_generator.assembler import Pool, build_song
from dada_generator.chunker import chunk
from dada_generator.config import load_song
from dada_generator.pronounce import Pronouncer
from dada_generator.source import read_sources
from dada_generator.units import tag

SONG = EXAMPLES / "pop-song.yaml"
LYRICS = EXAMPLES / "sample-lyrics.txt"


def test_word_mode_full_sheet(run_dada):
    result = run_dada("generate", SONG, LYRICS, "--mode", "word", "--seed", 1)
    assert result.returncode == 0
    assert "warning:" not in result.stderr
    assert_sheet_matches(result.stdout, SONG)


def _mean_units(mode):
    units = tag(chunk(read_sources([LYRICS]), mode), Pronouncer(), mode)
    song = build_song(load_song(SONG), Pool(units), mode, random.Random(1))
    return mean(len(line.units) for s in song.sections for line in s.lines)


def test_word_mode_is_more_fragmented():
    assert _mean_units("word") > _mean_units("phrase")
