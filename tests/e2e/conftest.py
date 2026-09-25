import subprocess
import sys
from pathlib import Path

import pytest

from dada_generator.chunker import tokenize
from dada_generator.pronounce import Pronouncer

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures"
EXAMPLES = ROOT / "examples"
DADA = Path(sys.executable).parent / "dada"


@pytest.fixture
def run_dada():
    """Run the installed `dada` console script as a user would."""

    def run(*args, stdout=None):
        return subprocess.run(
            [str(DADA), *map(str, args)],
            cwd=ROOT,
            text=True,
            stdout=stdout if stdout is not None else subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    return run


def parse_sheet(text: str) -> list[tuple[str, list[str]]]:
    """Split a lyric sheet into (header, lines) blocks."""
    sections = []
    for block in text.strip().split("\n\n"):
        header, *lines = block.split("\n")
        sections.append((header, lines))
    return sections


def line_syllables(line: str, overrides: dict[str, str] | None = None) -> int:
    pronouncer = Pronouncer(overrides)
    return sum(len(pronouncer.stress(word)) for word in tokenize(line))
