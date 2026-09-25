from conftest import FIXTURES


def test_redirected_stdout_holds_only_lyrics(run_dada, tmp_path):
    out = tmp_path / "song.txt"
    with out.open("w", encoding="utf-8") as handle:
        result = run_dada(
            "generate",
            FIXTURES / "fallback.yaml",
            FIXTURES / "streams.txt",
            "--seed",
            1,
            stdout=handle,
        )
    assert result.returncode == 0
    saved = out.read_text(encoding="utf-8")
    assert saved.startswith("[Verse]\n")
    assert "warning:" not in saved
    assert "guessed pronunciations:" not in saved
    assert "warning: verse line 1 wanted 5 syllables, used 4" in result.stderr
    assert "guessed pronunciations: zorbflak" in result.stderr
