import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from dada_generator.errors import DadaError

_LABEL_RE = re.compile(r"^\s*\[.*\]\s*$")


@dataclass(frozen=True)
class SourceLine:
    text: str
    source: str


def read_sources(paths: Sequence[Path]) -> list[SourceLine]:
    """Read lyric files, dropping blank lines and [Section] labels."""
    lines: list[SourceLine] = []
    for path in paths:
        try:
            content = Path(path).read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise DadaError(f"cannot read {path}: not valid UTF-8 text") from exc
        except OSError as exc:
            raise DadaError(f"cannot read {path}: {exc.strerror or exc}") from exc
        for raw in content.splitlines():
            text = raw.strip()
            if text and not _LABEL_RE.match(text):
                lines.append(SourceLine(text=text, source=str(path)))
    if not lines:
        names = ", ".join(str(p) for p in paths)
        raise DadaError(f"no lyric text found in {names}")
    return lines
