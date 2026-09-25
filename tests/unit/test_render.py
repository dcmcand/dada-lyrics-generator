from dada_generator.assembler import Line, Section, Song
from dada_generator.render import render
from dada_generator.units import Unit


def test_render_sheet():
    def line(*texts):
        return Line(tuple(Unit(t, "10", "a.txt", "phrase") for t in texts))

    song = Song(
        sections=(
            Section("verse", (line("the river", "hums"), line("open"))),
            Section("pre-chorus", (line("hold on"),)),
        ),
        warnings=(),
    )
    assert render(song) == "[Verse]\nthe river hums\nopen\n\n[Pre-Chorus]\nhold on\n"
