import pytest
from conftest import EXAMPLES


@pytest.mark.parametrize("song", ["pop-song.yaml", "ballad.yaml"])
@pytest.mark.parametrize("mode", ["phrase", "word"])
def test_examples_run(run_dada, song, mode):
    result = run_dada(
        "generate",
        EXAMPLES / song,
        EXAMPLES / "sample-lyrics.txt",
        EXAMPLES / "sample-lyrics-2.txt",
        "--mode",
        mode,
        "--pronunciations",
        EXAMPLES / "pronunciations.yaml",
        "--seed",
        3,
    )
    assert result.returncode == 0
    assert result.stdout.strip()
    assert "warning:" not in result.stderr
