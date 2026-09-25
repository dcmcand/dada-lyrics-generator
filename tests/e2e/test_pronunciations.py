from conftest import FIXTURES, parse_sheet


def _run(run_dada, *extra):
    return run_dada(
        "generate", FIXTURES / "zorbflak.yaml", FIXTURES / "zorbflak.txt", "--seed", 1, *extra
    )


def test_unknown_word_is_guessed_and_reported(run_dada):
    result = _run(run_dada)
    assert result.returncode == 0
    assert "guessed pronunciations: zorbflak" in result.stderr
    # Guess is 2 syllables, so a 4-syllable line needs two copies.
    assert parse_sheet(result.stdout) == [("[Verse]", ["zorbflak zorbflak"])]


def test_override_changes_tagging(run_dada, tmp_path):
    overrides = tmp_path / "p.yaml"
    overrides.write_text('zorbflak: "0101"\n', encoding="utf-8")
    result = _run(run_dada, "--pronunciations", overrides)
    assert result.returncode == 0
    assert "guessed pronunciations" not in result.stderr
    # Override makes it 4 syllables, so one copy fills the line.
    assert parse_sheet(result.stdout) == [("[Verse]", ["zorbflak"])]
