from collections.abc import Iterable
from dataclasses import dataclass

from dada_generator.chunker import Chunk
from dada_generator.pronounce import Pronouncer


@dataclass(frozen=True)
class Unit:
    text: str
    stress: str
    source: str
    mode: str

    @property
    def syllables(self) -> int:
        return len(self.stress)


def tag(chunks: Iterable[Chunk], pronouncer: Pronouncer, mode: str) -> list[Unit]:
    """Attach stress patterns to chunks; a phrase's stress is its words' stresses joined."""
    return [
        Unit(
            text=" ".join(c.words),
            stress="".join(pronouncer.stress(w) for w in c.words),
            source=c.source,
            mode=mode,
        )
        for c in chunks
        if c.words
    ]
