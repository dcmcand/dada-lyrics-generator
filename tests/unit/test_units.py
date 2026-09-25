from dada_generator.chunker import Chunk
from dada_generator.pronounce import Pronouncer
from dada_generator.units import Unit, tag


def test_tag_builds_phrase_stress():
    units = tag([Chunk(("the", "river", "hums"), "a.txt")], Pronouncer(), "phrase")
    assert units == [Unit(text="the river hums", stress="?10?", source="a.txt", mode="phrase")]
    assert units[0].syllables == 4


def test_tag_skips_empty_chunks():
    assert tag([Chunk((), "a.txt")], Pronouncer(), "word") == []
