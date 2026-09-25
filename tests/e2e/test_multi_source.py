import random

from conftest import EXAMPLES

from dada_generator.assembler import Pool, build_song
from dada_generator.chunker import chunk
from dada_generator.config import load_song
from dada_generator.pronounce import Pronouncer
from dada_generator.source import read_sources
from dada_generator.units import tag

FILES = [EXAMPLES / "sample-lyrics.txt", EXAMPLES / "sample-lyrics-2.txt"]


def test_multi_source_cli_run(run_dada):
    result = run_dada("generate", EXAMPLES / "pop-song.yaml", *FILES, "--seed", 1)
    assert result.returncode == 0
    assert result.stdout.startswith("[Verse]\n")


def test_multi_source_draws_from_both():
    units = tag(chunk(read_sources(FILES), "phrase"), Pronouncer(), "phrase")
    song = build_song(
        load_song(EXAMPLES / "pop-song.yaml"), Pool(units), "phrase", random.Random(1)
    )
    sources = {u.source for s in song.sections for line in s.lines for u in line.units}
    assert sources == {str(f) for f in FILES}
