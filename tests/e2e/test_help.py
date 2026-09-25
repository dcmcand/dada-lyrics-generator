import pytest


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        (["--help"], ["generate"]),
        (["generate", "--help"], ["--mode", "--seed", "--pronunciations", "SONG_YAML", "LYRICS"]),
    ],
)
def test_help(run_dada, args, expected):
    result = run_dada(*args)
    assert result.returncode == 0
    for text in expected:
        assert text in result.stdout
