import random

import pytest

from dada_generator.assembler import Pool, build_song, fill_line
from dada_generator.config import SectionSpec, SongConfig
from dada_generator.errors import DadaError
from dada_generator.meter import mismatch
from dada_generator.units import Unit


def u(text, stress, source="a.txt", mode="phrase"):
    return Unit(text=text, stress=stress, source=source, mode=mode)


def test_pool_rejects_empty():
    with pytest.raises(DadaError, match="no usable words"):
        Pool([])


def test_pool_indexes_by_length():
    pool = Pool([u("a", "?"), u("bb", "10"), u("cc", "01")])
    assert pool.lengths == [1, 2]
    assert [x.text for x in pool.by_length[2]] == ["bb", "cc"]


@pytest.mark.parametrize("mode", ["phrase", "word"])
@pytest.mark.parametrize("template", ["1", "01", "010", "0101010", "x1010101010"])
def test_exact_syllables_when_reachable(mode, template):
    pool = Pool([u("a", "?"), u("bb", "10"), u("ccc", "010")])
    for seed in range(25):
        line = fill_line(template, pool, mode, random.Random(seed))
        assert line.syllables == len(template)


def test_property_random_pools_hit_target():
    meta = random.Random(1234)
    for _ in range(200):
        lengths = meta.sample(range(1, 7), meta.randint(1, 3))
        pool = Pool([u("w" * n, "".join(meta.choice("01?") for _ in range(n))) for n in lengths])
        template = "".join(meta.choice("01x") for _ in range(meta.randint(1, 14)))
        line = fill_line(
            template, pool, meta.choice(["phrase", "word"]), random.Random(meta.random())
        )
        reachable = _reachable(lengths, len(template))
        if reachable:
            assert line.syllables == len(template)


def _reachable(lengths, target):
    ok = [True] + [False] * target
    for r in range(1, target + 1):
        ok[r] = any(n <= r and ok[r - n] for n in lengths)
    return ok[target]


def test_phrase_mode_prefers_fewest_units():
    pool = Pool([u("a", "?"), u("bbbb", "1010"), u("cccccccc", "10101010")])
    for seed in range(50):
        line = fill_line("10101010", pool, "phrase", random.Random(seed))
        assert [x.text for x in line.units] == ["cccccccc"]


def test_word_mode_mixes_lengths():
    pool = Pool([u("a", "?", mode="word"), u("bb", "10", mode="word")])
    counts = {len(fill_line("1010", pool, "word", random.Random(s)).units) for s in range(50)}
    assert len(counts) > 1


def test_stress_steering():
    """Journey 6: stress matching measurably steers selection."""
    pool_units = [u("good", "0101"), u("flip", "1010"), u("front", "1100"), u("back", "0011")]
    pool = Pool(pool_units)
    chosen_total = sum(
        mismatch("0101", fill_line("0101", pool, "phrase", random.Random(s)).units[0].stress)
        for s in range(100)
    )
    baseline_rng = random.Random(0)
    baseline_total = sum(
        mismatch("0101", baseline_rng.choice(pool_units).stress) for _ in range(100)
    )
    assert chosen_total == 0
    assert baseline_total / 100 > 0


@pytest.mark.parametrize(
    ("lengths", "template", "expected"),
    [
        ([2], "01010", 4),  # tie between 4 and 6 goes to the shorter
        ([2], "0", 2),  # Review Focus 5: shorter than every unit
        ([3], "0101", 3),
        ([3, 5], "0101010", 6),
    ],
)
def test_fallback_uses_nearest_reachable(lengths, template, expected):
    pool = Pool([u("w" * n, "0" * n) for n in lengths])
    line = fill_line(template, pool, "phrase", random.Random(0))
    assert line.syllables == expected


def _config(sections, outline):
    return SongConfig(sections=sections, outline=tuple(outline))


def test_build_song_outline_order_and_warning():
    pool = Pool([u("river", "10")])
    config = _config(
        {"verse": SectionSpec(("01010",)), "chorus": SectionSpec(("10",))},
        ["verse", "chorus", "verse"],
    )
    song = build_song(config, pool, "phrase", random.Random(0))
    assert [s.name for s in song.sections] == ["verse", "chorus", "verse"]
    assert song.warnings == (
        "warning: verse line 1 wanted 5 syllables, used 4",
        "warning: verse line 1 wanted 5 syllables, used 4",
    )


def test_repeat_sections_reuse_first_generation():
    pool = Pool([u(f"w{i}", "10") for i in range(30)])
    config = _config(
        {
            "verse": SectionSpec(("1010", "1010")),
            "chorus": SectionSpec(("1010", "1010"), repeat=True),
        },
        ["chorus", "verse", "chorus", "verse", "chorus"],
    )
    song = build_song(config, pool, "phrase", random.Random(3))
    choruses = [s for s in song.sections if s.name == "chorus"]
    verses = [s for s in song.sections if s.name == "verse"]
    assert choruses[0] == choruses[1] == choruses[2]
    assert verses[0] != verses[1]


def test_multi_source_pool():
    """Journey 4: output draws from more than one source file."""
    units = [u(f"a{i}", "10", source="a.txt") for i in range(5)]
    units += [u(f"b{i}", "10", source="b.txt") for i in range(5)]
    config = _config({"verse": SectionSpec(("1010",) * 6)}, ["verse"])
    song = build_song(config, Pool(units), "phrase", random.Random(1))
    sources = {unit.source for s in song.sections for line in s.lines for unit in line.units}
    assert sources == {"a.txt", "b.txt"}


def test_same_seed_same_song():
    pool = Pool([u(f"w{i}", s) for i, s in enumerate(["?", "10", "01", "100", "?"])])
    config = _config({"verse": SectionSpec(("01010101", "10101010"))}, ["verse", "verse"])
    first = build_song(config, pool, "word", random.Random(42))
    second = build_song(config, pool, "word", random.Random(42))
    assert first == second
