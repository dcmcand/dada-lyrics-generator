import random
from collections.abc import Sequence
from dataclasses import dataclass

from dada_generator.config import SongConfig
from dada_generator.errors import DadaError
from dada_generator.meter import mismatch
from dada_generator.units import Unit


@dataclass(frozen=True)
class Line:
    units: tuple[Unit, ...]

    @property
    def text(self) -> str:
        return " ".join(unit.text for unit in self.units)

    @property
    def syllables(self) -> int:
        return sum(unit.syllables for unit in self.units)


@dataclass(frozen=True)
class Section:
    name: str
    lines: tuple[Line, ...]


@dataclass(frozen=True)
class Song:
    sections: tuple[Section, ...]
    warnings: tuple[str, ...]


class Pool:
    """Tagged units indexed by syllable count."""

    def __init__(self, units: Sequence[Unit]) -> None:
        if not units:
            raise DadaError("no usable words found in the lyric files")
        self.by_length: dict[int, list[Unit]] = {}
        for unit in units:
            self.by_length.setdefault(unit.syllables, []).append(unit)
        self.lengths = sorted(self.by_length)


def _min_units(lengths: Sequence[int], limit: int) -> list[int | None]:
    """best[r] = fewest units summing to r syllables, or None if unreachable."""
    best: list[int | None] = [None] * (limit + 1)
    best[0] = 0
    for r in range(1, limit + 1):
        options = [best[r - n] for n in lengths if n <= r and best[r - n] is not None]
        if options:
            best[r] = min(options) + 1
    return best


# In phrase mode, each extra unit a length choice forces halves its weight:
# whole phrases are preferred, but joins still happen so one phrase cannot
# fill every line that matches its length.
PHRASE_SPLIT_PENALTY = 0.5


def _length_weight(length: int, remaining: int, best: list, pool: Pool, mode: str) -> float:
    """Weight a length by how many units have it, so rare lengths are not over-used."""
    weight = float(len(pool.by_length[length]))
    if mode == "phrase":
        extra = best[remaining - length] + 1 - best[remaining]
        weight *= PHRASE_SPLIT_PENALTY**extra
    return weight


def fill_line(template: str, pool: Pool, mode: str, rng: random.Random) -> Line:
    """Fill one line to the template's syllable count, or the nearest reachable count."""
    target = len(template)
    limit = target + pool.lengths[-1]
    best = _min_units(pool.lengths, limit)
    reachable = [n for n in range(1, limit + 1) if best[n] is not None]
    actual = min(reachable, key=lambda n: (abs(n - target), n))
    pattern = template[:actual] if actual <= target else template + "x" * (actual - target)

    chosen: list[Unit] = []
    position = 0
    remaining = actual
    while remaining:
        allowed = [n for n in pool.lengths if n <= remaining and best[remaining - n] is not None]
        weights = [_length_weight(n, remaining, best, pool, mode) for n in allowed]
        length = rng.choices(allowed, weights)[0]
        candidates = pool.by_length[length]
        window = pattern[position : position + length]
        scores = [mismatch(window, unit.stress) for unit in candidates]
        lowest = min(scores)
        chosen.append(
            rng.choice([unit for unit, s in zip(candidates, scores, strict=True) if s == lowest])
        )
        position += length
        remaining -= length
    return Line(units=tuple(chosen))


def build_song(config: SongConfig, pool: Pool, mode: str, rng: random.Random) -> Song:
    """Walk the outline; sections marked repeat are generated once and reused."""
    sections: list[Section] = []
    warnings: list[str] = []
    generated: dict[str, Section] = {}
    for name in config.outline:
        spec = config.sections[name]
        if spec.repeat and name in generated:
            sections.append(generated[name])
            continue
        lines = []
        for index, template in enumerate(spec.templates, start=1):
            line = fill_line(template, pool, mode, rng)
            if line.syllables != len(template):
                warnings.append(
                    f"warning: {name} line {index} wanted {len(template)} syllables, "
                    f"used {line.syllables}"
                )
            lines.append(line)
        section = Section(name=name, lines=tuple(lines))
        generated[name] = section
        sections.append(section)
    return Song(sections=tuple(sections), warnings=tuple(warnings))
