from conftest import FIXTURES, parse_sheet


def test_unreachable_count_warns_and_continues(run_dada):
    result = run_dada(
        "generate", FIXTURES / "fallback.yaml", FIXTURES / "two_syllable.txt", "--seed", 1
    )
    assert result.returncode == 0
    assert "warning: verse line 1 wanted 5 syllables, used 4" in result.stderr
    [(header, lines)] = parse_sheet(result.stdout)
    assert header == "[Verse]"
    assert len(lines) == 1 and len(lines[0].split()) == 2
