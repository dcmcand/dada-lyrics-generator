import pytest
from conftest import FIXTURES


def _song(tmp_path, text):
    path = tmp_path / "song.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def _lyrics(tmp_path, content: bytes):
    path = tmp_path / "lyrics.txt"
    path.write_bytes(content)
    return path


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        ("missing_lyrics", "error: cannot read"),
        ("malformed_yaml", "invalid YAML"),
        ("unknown_section", "outline references unknown section 'bridge'"),
        ("bad_meter", "section 'verse' line 1: invalid meter"),
        ("punctuation_only_lyrics", "no usable words"),
        ("latin1_lyrics", "not valid UTF-8"),
        ("bad_overrides", "must map to a quoted stress string"),
    ],
)
def test_bad_input_is_one_line_error(run_dada, tmp_path, case, expected):
    song = FIXTURES / "simple.yaml"
    lyrics = FIXTURES / "mixed.txt"
    extra = []
    if case == "missing_lyrics":
        lyrics = tmp_path / "nope.txt"
    elif case == "malformed_yaml":
        song = _song(tmp_path, "sections: [unclosed\n")
    elif case == "unknown_section":
        song = _song(tmp_path, "sections: {verse: [iambic 2]}\noutline: [verse, bridge]\n")
    elif case == "bad_meter":
        song = _song(tmp_path, "sections: {verse: ['01a1']}\noutline: [verse]\n")
    elif case == "punctuation_only_lyrics":
        lyrics = _lyrics(tmp_path, b"[Chorus]\n...\n!!\n")
    elif case == "latin1_lyrics":
        lyrics = _lyrics(tmp_path, "caf\xe9\n".encode("latin-1"))
    elif case == "bad_overrides":
        overrides = tmp_path / "p.yaml"
        overrides.write_text("zorp: 10\n", encoding="utf-8")
        extra = ["--pronunciations", overrides]

    result = run_dada("generate", song, lyrics, *extra)
    assert result.returncode == 2
    assert result.stdout == ""
    assert "Traceback" not in result.stderr
    lines = result.stderr.strip().splitlines()
    assert len(lines) == 1
    assert lines[0].startswith("error: ")
    assert expected in lines[0]


def test_unknown_mode_is_usage_error(run_dada):
    result = run_dada(
        "generate", FIXTURES / "simple.yaml", FIXTURES / "mixed.txt", "--mode", "letter"
    )
    assert result.returncode == 2
    assert "Traceback" not in result.stderr
