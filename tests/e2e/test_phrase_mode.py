from conftest import EXAMPLES, line_syllables, parse_sheet

from dada_generator.config import load_song


def expected_sections(song_path):
    config = load_song(song_path)
    return [(f"[{name.title()}]", config.sections[name].templates) for name in config.outline]


def assert_sheet_matches(stdout, song_path):
    sheet = parse_sheet(stdout)
    expected = expected_sections(song_path)
    assert [header for header, _ in sheet] == [header for header, _ in expected]
    for (_, lines), (_, templates) in zip(sheet, expected, strict=True):
        assert [line_syllables(line) for line in lines] == [len(t) for t in templates]


def test_phrase_mode_full_sheet(run_dada):
    song = EXAMPLES / "pop-song.yaml"
    result = run_dada("generate", song, EXAMPLES / "sample-lyrics.txt", "--seed", 1)
    assert result.returncode == 0
    assert "warning:" not in result.stderr
    assert_sheet_matches(result.stdout, song)
