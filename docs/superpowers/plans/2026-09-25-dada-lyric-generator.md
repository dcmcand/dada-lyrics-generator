# Dada Lyric Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `dada` CLI that cuts up lyric files into phrases or words, tags syllables and stress, and reassembles them into a song that follows a user-defined meter and outline.

**Architecture:** A linear pipeline of small modules (source -> chunker -> pronounce/units -> assembler -> render) wired by `cli.py`. The assembler fills each line left to right using a syllable-reachability DP so it never dead-ends, choosing the lowest stress-mismatch unit at random. All randomness flows through an explicit `random.Random(seed)`.

**Tech Stack:** Python 3.12+, uv, hatchling, pronouncing (CMU dict), pyphen, PyYAML, pytest, ruff, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-25-dada-lyric-generator-design.md`

## Journeys

| # | Item | Proof | Check method | Evidence |
|---|------|-------|--------------|----------|
| 1 | I can install the tool and run `dada` from my shell | `uv tool install .` (or `uv sync` then `uv run dada --help`) succeeds; `dada --help` and `dada generate --help` print usage listing `--mode`, `--seed`, `--pronunciations`; exit 0 | narrated: install + help transcript | 2026-09-25 @6531d7d: `uv sync && uv run dada --help` exit 0 (lists `generate`); `uv run dada generate --help` exit 0, lists `--mode {phrase,word}`, `--seed SEED`, `--pronunciations FILE`, `SONG_YAML LYRICS`. `uv tool install` not run (avoids global install; journey allows either). |
| 2 | Phrase mode, one lyric file + example song YAML, produces a complete sheet: every section in outline order, every line exactly the template's syllable count | `dada generate examples/pop-song.yaml examples/sample-lyrics.txt --seed 1` exits 0; headers appear in outline order; each line re-tagged by the pronouncer equals its template length | automated: `tests/e2e/test_phrase_mode.py` + narrated: transcript of the run | Re-verified after the 2026-09-25 selection revision: test_phrase_mode_full_sheet PASSED (e2e 54/54). Narrated `--seed 1` exit 0, headers in outline order, no warnings; verse 1 begins `hold on hold on the pickup coughed`. |
| 3 | Word mode, same inputs, produces a visibly more fragmented sheet, still exact syllable counts | Same command with `--mode word` exits 0, exact per-line counts; mean units per line is higher than phrase mode for the same seed and inputs | automated: `tests/e2e/test_word_mode.py` + narrated: side-by-side transcript | Re-verified after revision: test_word_mode_full_sheet, test_word_mode_is_more_fragmented PASSED; word mode distinct-line ratio 1.00 over seeds 1-20 for both examples. |
| 4 | Multiple lyric files are pooled and output draws from more than one | With two sample files and a fixed seed, generated lines contain units originating from both sources (checked via a test hook on the assembled song, not text guessing) | automated: `tests/unit/test_assembler.py::test_multi_source_pool` + `tests/e2e/test_multi_source.py` (exit 0, output produced) | test_multi_source_pool, test_multi_source_draws_from_both (sources == both example files), test_multi_source_cli_run PASSED. |
| 5 | Same seed -> identical output; different seed -> different output | Two runs with `--seed 7` are byte-identical; runs with `--seed 7` and `--seed 8` differ | automated: `tests/e2e/test_seed.py` | test_same_seed_is_identical, test_different_seed_differs PASSED. |
| 6 | Stress matching measurably steers selection | Fixture pool with same-length units of different stresses; for template `0101`, chosen units have total mismatch 0 across 100 seeded fills while a stress-blind baseline over the same pool averages > 0 | automated: `tests/unit/test_assembler.py::test_stress_steering` | test_stress_steering PASSED (chosen total mismatch 0 over 100 fills; stress-blind baseline mean > 0). |
| 7 | Unreachable syllable count still yields a song plus a stderr warning naming section and line | Fixture lyrics with only 2-syllable units and a template of length 5: exit 0, lyrics on stdout, stderr contains `warning: verse line 1 wanted 5 syllables, used 4` | automated: `tests/e2e/test_fallback.py` | test_unreachable_count_warns_and_continues PASSED; narrated run stderr: `warning: verse line 1 wanted 5 syllables, used 4`, exit 0. |
| 8 | Unknown words are guessed and reported; overrides change tagging | Fixture with a non-CMU word: stderr lists it under `guessed pronunciations:`; with `--pronunciations` mapping it, it is no longer listed and its stress/syllables follow the override | automated: `tests/e2e/test_pronunciations.py` + `tests/unit/test_pronounce.py` | test_unknown_word_is_guessed_and_reported, test_override_changes_tagging, tests/unit/test_pronounce.py (all) PASSED. |
| 9 | Bad input yields a one-line error, no traceback, exit 2 | Cases: missing lyric file, malformed YAML, undefined outline section, invalid meter string. Each: exit 2, stderr single line starting `error:`, no `Traceback` | automated: `tests/e2e/test_errors.py` (parametrized) | test_bad_input_is_one_line_error x7 (missing lyrics, malformed YAML, unknown section, bad meter, punctuation-only, latin-1, bad overrides) + test_unknown_mode_is_usage_error PASSED. |
| 10 | `dada generate ... > song.txt` saves only lyrics | Run that triggers both a fallback warning and guessed words, redirecting stdout to a file: file contains no `warning:` or `guessed pronunciations:` lines; stderr contains them | automated: `tests/e2e/test_streams.py` + narrated: shell transcript with `cat song.txt` | test_redirected_stdout_holds_only_lyrics PASSED. Narrated: `> song.txt` exit 0; stderr had `warning: verse line 1 wanted 5 syllables, used 4` and `guessed pronunciations: zorbflak`; `cat song.txt` = `[Verse]` / `window zorbflak` only. |
| 11 | I can copy an example, edit it per the README, and run it | Copy `examples/ballad.yaml`, change the outline and one template following README syntax, run it: exit 0, new structure reflected in output | narrated: transcript of copy, edit, run | Re-verified after revision: my-song.yaml (ballad + `bridge: [trochaic 3]`, outline [verse, chorus, bridge, chorus], verse line 4 "x1010") run exit 0 with `[Bridge]`; verse lines now vary (`Maybe it's the static` / `hold on the pickup coughed` / ... / `maybe it's the rain`) instead of one phrase on every line. |
| 12 | CI runs lint + tests on push/PR and passes | Workflow file runs ruff check, ruff format --check, pytest on push and pull_request; locally, the same steps pass (via `act` if available, otherwise running the exact workflow commands). Full verification requires a GitHub remote and is expected to be user-waived until then | narrated: local run transcript of the workflow steps; GitHub run URL once pushed | Local workflow steps (`act` not installed): `uv sync --locked`, `ruff check` (All checks passed), `ruff format --check` (32 files already formatted), `pytest` (161 passed), exit 0. GitHub Actions run https://github.com/dcmcand/dada-lyrics-generator/actions/runs/36134830465 on push of e607f2e: job `test` succeeded in 18s; `ruff check` All checks passed!, `ruff format --check` 33 files already formatted, `pytest` 166 passed. (Earlier waiver superseded.) |
| 13 | Repeated phrases do not dominate the song | With `examples/ballad.yaml` and `examples/pop-song.yaml` against `examples/sample-lyrics.txt`, seeds 1-20: phrase mode mean distinct-line ratio over generated sections >= 0.6 (was 0.20 / 0.33 before the revision); word mode most-common-word share never exceeds 30% of words (was up to 39%) | automated: `tests/e2e/test_variety.py` + narrated: ballad run transcript | test_variety.py 4/4 PASSED. Seeds 1-20: phrase distinct-line ratio mean ballad 0.77 (was 0.20), pop 0.79 (was 0.33); word mode top-word share max ballad 0.25 (was 0.39), pop 0.17. Narrated ballad run above (row 11). |

## Global Constraints

- Python `>=3.12`; ruff `target-version = "py312"`, `line-length = 100`.
- Runtime dependencies are exactly `pronouncing`, `pyphen`, `pyyaml`. CLI uses stdlib `argparse`.
- Console script name: `dada`; subcommand `generate SONG_YAML LYRICS [LYRICS ...]` with `--mode phrase|word` (default `phrase`), `--seed INT`, `--pronunciations FILE`.
- Lyrics go to stdout only. Warnings, the guessed-pronunciations summary, and errors go to stderr only.
- All user-input errors raise `DadaError`, printed by the CLI as `error: <message>` (one line) with exit code 2. Unexpected exceptions are not caught.
- Never use the global `random` module state; always pass a `random.Random`.
- Tests are table-driven (`pytest.mark.parametrize`) wherever there is more than one case.
- Never use em dashes in code, docs, or messages.
- `CLAUDE.md` is gitignored and never committed. Commit messages carry no AI attribution.
- Stress alphabet: templates use `0 1 x`; unit stresses use `0 1 ?`; override values use `0 1`.

## Review Focus

1. Unquoted stress strings in YAML (`- 0101` parses as the integer 65): user expects a clear error telling them to quote it, not a crash or silent wrong meter. Pinned in Task 6.
2. Lyric files whose lines are only punctuation or labels (e.g. `...`, `[Chorus]`): user expects `error:` + exit 2, not a traceback from an empty pool. Pinned in Task 7 (`Pool`) and Task 8 (e2e).
3. Curly apostrophes and non-ASCII letters (`don't` typed with a curly apostrophe, `cafe` with an accented e, `dreamin'` with a curly apostrophe): user expects whole words, not fragments like `caf`. Pinned in Task 3.
4. A lyric file that is not UTF-8 (e.g. exported as Latin-1): user expects `error: cannot read ...`, exit 2. Pinned in Task 2.
5. A template shorter than every unit in the pool (e.g. `"1"` when phrase mode has no one-syllable chunk): user expects the nearest longer fill plus a warning, not a hang or crash. Pinned in Task 7.

---

## File Structure

```
pyproject.toml                         project metadata, deps, ruff/pytest config
README.md                              usage docs (stub in Task 1, full in Task 9)
.github/workflows/ci.yml               lint + tests
src/dada_generator/__init__.py         __version__
src/dada_generator/errors.py           DadaError
src/dada_generator/meter.py            template parsing + mismatch scoring
src/dada_generator/source.py           read lyric files -> SourceLine records
src/dada_generator/chunker.py          tokenize + phrase/word chunking
src/dada_generator/pronounce.py        Pronouncer (overrides, CMU, guess)
src/dada_generator/units.py            Unit + tag()
src/dada_generator/config.py           song YAML + overrides YAML loading/validation
src/dada_generator/assembler.py        Pool, fill_line, build_song, Line/Section/Song
src/dada_generator/render.py           plain-text lyric sheet
src/dada_generator/cli.py              argparse + wiring + exit codes
tests/unit/test_*.py                   one file per module
tests/e2e/conftest.py                  run_dada fixture + sheet parsing helpers
tests/e2e/test_*.py                    user-journey tests via the installed `dada`
tests/fixtures/*                       small lyric and song files
examples/*                             templates for users
```

---

### Task 1: Project scaffold, error type, CI

Advances journeys: 12

**Files:**
- Create: `pyproject.toml`, `README.md` (stub), `src/dada_generator/__init__.py`, `src/dada_generator/errors.py`, `.github/workflows/ci.yml`
- Test: `tests/unit/test_package.py`

**Interfaces:**
- Consumes: nothing
- Produces: `dada_generator.__version__: str == "0.1.0"`; `dada_generator.errors.DadaError(Exception)`

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "dada-generator"
version = "0.1.0"
description = "Dadaist cut-up lyric generator"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "pronouncing>=0.3",
    "pyphen>=0.17",
    "pyyaml>=6.0",
]

[project.scripts]
dada = "dada_generator.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[dependency-groups]
dev = [
    "pytest>=8",
    "ruff>=0.6",
]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Write stub `README.md`** (hatchling requires the readme file to exist)

```markdown
# dada-generator

Dadaist cut-up lyric generator. Full usage docs arrive with the examples.
```

- [ ] **Step 3: Write the failing test** `tests/unit/test_package.py`

```python
import dada_generator
from dada_generator.errors import DadaError


def test_version():
    assert dada_generator.__version__ == "0.1.0"


def test_dada_error_carries_message():
    err = DadaError("bad input")
    assert isinstance(err, Exception)
    assert str(err) == "bad input"
```

- [ ] **Step 4: Run to verify it fails**

Run: `uv sync && uv run pytest tests/unit/test_package.py -v`
Expected: FAIL / collection error, `ModuleNotFoundError: No module named 'dada_generator'` (or build error because the package dir is missing).

- [ ] **Step 5: Implement**

`src/dada_generator/__init__.py`:

```python
"""Dadaist cut-up lyric generator."""

__version__ = "0.1.0"
```

`src/dada_generator/errors.py`:

```python
class DadaError(Exception):
    """A user-facing input problem. The CLI prints it and exits with code 2."""
```

- [ ] **Step 6: Run to verify it passes**

Run: `uv sync && uv run pytest tests/unit/test_package.py -v`
Expected: 2 passed.

- [ ] **Step 7: Write `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
  pull_request:

permissions:
  contents: read

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      - uses: astral-sh/setup-uv@c18668ad3cf93ea998bef934396af7bb5c839dc7 # v10.2.0
        with:
          python-version: "3.12"
      - run: uv sync --locked
      - run: uv run ruff check
      - run: uv run ruff format --check
      - run: uv run pytest
```

- [ ] **Step 8: Run the CI steps locally**

Run: `uv sync --locked && uv run ruff check && uv run ruff format --check && uv run pytest`
Expected: all succeed.

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml uv.lock README.md src/ tests/ .github/
git commit -m "Scaffold package, error type, and CI workflow"
```

---

### Task 2: Lyric source reading

Advances journeys: 9

**Files:**
- Create: `src/dada_generator/source.py`
- Test: `tests/unit/test_source.py`

**Interfaces:**
- Consumes: `DadaError`
- Produces: `SourceLine(text: str, source: str)` frozen dataclass; `read_sources(paths: Sequence[Path]) -> list[SourceLine]`. `source` is `str(path)` as given.

- [ ] **Step 1: Write the failing tests** `tests/unit/test_source.py`

```python
import pytest

from dada_generator.errors import DadaError
from dada_generator.source import SourceLine, read_sources


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("hello world\n", ["hello world"]),
        ("  padded line  \n\n\n", ["padded line"]),
        ("[Chorus]\nsing it\n  [Verse 2]  \nagain\n", ["sing it", "again"]),
        ("line one\r\nline two\r\n", ["line one", "line two"]),
        ("not [a label] here\n", ["not [a label] here"]),
    ],
)
def test_read_sources_cleans_lines(tmp_path, content, expected):
    path = tmp_path / "song.txt"
    path.write_text(content, encoding="utf-8")
    assert read_sources([path]) == [SourceLine(text, str(path)) for text in expected]


def test_read_sources_tags_each_file(tmp_path):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("from a\n", encoding="utf-8")
    b.write_text("from b\n", encoding="utf-8")
    assert read_sources([a, b]) == [SourceLine("from a", str(a)), SourceLine("from b", str(b))]


@pytest.mark.parametrize(
    ("setup", "message"),
    [
        ("missing", "cannot read"),
        ("directory", "cannot read"),
        ("latin1", "not valid UTF-8"),
        ("empty", "no lyric text found"),
        ("labels_only", "no lyric text found"),
    ],
)
def test_read_sources_errors(tmp_path, setup, message):
    path = tmp_path / "song.txt"
    if setup == "directory":
        path.mkdir()
    elif setup == "latin1":
        path.write_bytes("caf\xe9 au lait\n".encode("latin-1"))
    elif setup == "empty":
        path.write_text("\n\n", encoding="utf-8")
    elif setup == "labels_only":
        path.write_text("[Verse]\n[Chorus]\n", encoding="utf-8")
    with pytest.raises(DadaError, match=message):
        read_sources([path])
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/unit/test_source.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'dada_generator.source'`.

- [ ] **Step 3: Implement** `src/dada_generator/source.py`

```python
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
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/unit/test_source.py -v`
Expected: all passed.

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check --fix && uv run ruff format && uv run ruff check && uv run ruff format --check
git add src/dada_generator/source.py tests/unit/test_source.py
git commit -m "Add lyric source reader"
```

---

### Task 3: Tokenizing and chunking

Advances journeys: 2, 3

**Files:**
- Create: `src/dada_generator/chunker.py`
- Test: `tests/unit/test_chunker.py`

**Interfaces:**
- Consumes: `SourceLine`
- Produces: `MODES = ("phrase", "word")`; `CONJUNCTIONS: frozenset[str]`; `Chunk(words: tuple[str, ...], source: str)` frozen dataclass; `tokenize(text: str) -> list[str]`; `chunk(lines: Iterable[SourceLine], mode: str) -> list[Chunk]` (raises `ValueError` on unknown mode).

- [ ] **Step 1: Write the failing tests** `tests/unit/test_chunker.py`

```python
import pytest

from dada_generator.chunker import Chunk, chunk, tokenize
from dada_generator.source import SourceLine


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("the river hums", ["the", "river", "hums"]),
        ("don't stop", ["don't", "stop"]),
        ("don\u2019t stop", ["don't", "stop"]),
        ("runnin' late", ["runnin'", "late"]),
        ("dreamin\u2019 on", ["dreamin'", "on"]),
        ("'quoted' word", ["quoted", "word"]),
        ("caf\u00e9 society", ["caf\u00e9", "society"]),
        ("well-known road", ["well", "known", "road"]),
        ("...!?", []),
    ],
)
def test_tokenize(text, expected):
    assert tokenize(text) == expected


def _words(chunks):
    return [" ".join(c.words) for c in chunks]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("I walked home, the streetlights hummed", ["I walked home", "the streetlights hummed"]),
        ("stop. go! why? now; here: there", ["stop", "go", "why", "now", "here", "there"]),
        ("left \u2014 right \u2013 center", ["left", "right", "center"]),
        ("up - down -- around", ["up", "down", "around"]),
        ("well-known road", ["well known road"]),
        ("I ran and she hid", ["I ran", "and she hid"]),
        ("and then we left", ["and", "then we left"]),
        ("but I stayed until dawn", ["but I stayed", "until dawn"]),
        ("rock AND roll", ["rock", "AND roll"]),
        ("...", []),
    ],
)
def test_phrase_chunking(text, expected):
    assert _words(chunk([SourceLine(text, "s.txt")], "phrase")) == expected


def test_word_chunking_keeps_source():
    chunks = chunk([SourceLine("Hello, big world", "a.txt")], "word")
    assert chunks == [
        Chunk(("Hello",), "a.txt"),
        Chunk(("big",), "a.txt"),
        Chunk(("world",), "a.txt"),
    ]


def test_phrase_chunks_never_cross_lines():
    lines = [SourceLine("one two", "a.txt"), SourceLine("three four", "b.txt")]
    assert chunk(lines, "phrase") == [
        Chunk(("one", "two"), "a.txt"),
        Chunk(("three", "four"), "b.txt"),
    ]


def test_unknown_mode():
    with pytest.raises(ValueError, match="unknown mode"):
        chunk([SourceLine("x", "a.txt")], "letter")
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/unit/test_chunker.py -v`
Expected: FAIL, `ModuleNotFoundError`.

- [ ] **Step 3: Implement** `src/dada_generator/chunker.py`

```python
import re
from collections.abc import Iterable
from dataclasses import dataclass

from dada_generator.source import SourceLine

MODES = ("phrase", "word")

CONJUNCTIONS = frozenset(
    {"and", "but", "or", "so", "when", "because", "while", "if", "though", "until", "then"}
)

# Phrase breaks: sentence/clause punctuation, brackets, quotes, en/em dashes,
# a spaced hyphen, or a run of two or more hyphens. A hyphen inside a word
# ("well-known") is not a break.
_BREAK_RE = re.compile(r"[,.;:!?()\[\]{}\"\u201c\u201d\u2013\u2014]|\s-+\s|-{2,}")

# A word is letters/digits with optional internal apostrophes. A trailing
# apostrophe is kept only after "in" (dropped-g spellings like "runnin'").
_WORD_RE = re.compile(r"[^\W_]+(?:'[^\W_]+)*(?:(?<=[iI][nN])')?")


@dataclass(frozen=True)
class Chunk:
    words: tuple[str, ...]
    source: str


def tokenize(text: str) -> list[str]:
    normalized = text.replace("\u2019", "'").replace("\u2018", "'")
    return _WORD_RE.findall(normalized)


def chunk(lines: Iterable[SourceLine], mode: str) -> list[Chunk]:
    """Split lyric lines into phrase-level or word-level chunks."""
    if mode not in MODES:
        raise ValueError(f"unknown mode '{mode}'")
    chunks: list[Chunk] = []
    for line in lines:
        if mode == "word":
            chunks.extend(Chunk((word,), line.source) for word in tokenize(line.text))
            continue
        for fragment in _BREAK_RE.split(line.text):
            current: list[str] = []
            for word in tokenize(fragment):
                if current and word.lower() in CONJUNCTIONS:
                    chunks.append(Chunk(tuple(current), line.source))
                    current = []
                current.append(word)
            if current:
                chunks.append(Chunk(tuple(current), line.source))
    return chunks
```

Note on `"and then we left"`: "and" is first so no split before it; "then" is a conjunction not in first position so it splits, giving `["and", "then we left"]`. The test encodes this.

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/unit/test_chunker.py -v`
Expected: all passed.

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check --fix && uv run ruff format && uv run ruff check && uv run ruff format --check
git add src/dada_generator/chunker.py tests/unit/test_chunker.py
git commit -m "Add tokenizer and phrase/word chunker"
```

---

### Task 4: Meter templates and stress scoring

Advances journeys: 2, 6

**Files:**
- Create: `src/dada_generator/meter.py`
- Test: `tests/unit/test_meter.py`

**Interfaces:**
- Consumes: nothing
- Produces: `FEET: dict[str, str]`; `parse_template(text: str) -> str` (returns a string over `0 1 x`; raises `ValueError` with a human message); `mismatch(template: str, stress: str) -> int` (equal-length strings).

- [ ] **Step 1: Write the failing tests** `tests/unit/test_meter.py`

```python
import pytest

from dada_generator.meter import mismatch, parse_template


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("01010101", "01010101"),
        ("x1010101", "x1010101"),
        ("  0101  ", "0101"),
        ("X101", "x101"),
        ("iambic 4", "01010101"),
        ("trochaic 3", "101010"),
        ("anapestic 2", "001001"),
        ("dactylic 2", "100100"),
        ("Iambic  2", "0101"),
    ],
)
def test_parse_template_valid(text, expected):
    assert parse_template(text) == expected


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("", "invalid meter"),
        ("01a1", "invalid meter"),
        ("iambic", "invalid meter"),
        ("iambic zero", "invalid meter"),
        ("iambic 0", "at least 1"),
        ("spondaic 2", "unknown foot 'spondaic'"),
    ],
)
def test_parse_template_invalid(text, message):
    with pytest.raises(ValueError, match=message):
        parse_template(text)


@pytest.mark.parametrize(
    ("template", "stress", "expected"),
    [
        ("0101", "0101", 0),
        ("0101", "1010", 4),
        ("0101", "0111", 1),
        ("0101", "????", 0),
        ("xxxx", "1010", 0),
        ("x1", "?0", 1),
        ("01", "?1", 0),
    ],
)
def test_mismatch(template, stress, expected):
    assert mismatch(template, stress) == expected


def test_mismatch_requires_equal_length():
    with pytest.raises(ValueError):
        mismatch("010", "01")
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/unit/test_meter.py -v`
Expected: FAIL, `ModuleNotFoundError`.

- [ ] **Step 3: Implement** `src/dada_generator/meter.py`

```python
import re

FEET = {"iambic": "01", "trochaic": "10", "anapestic": "001", "dactylic": "100"}

_STRESS_RE = re.compile(r"[01x]+")
_SHORTHAND_RE = re.compile(r"([a-z]+)\s+(\d+)")


def parse_template(text: str) -> str:
    """Turn a stress string ("x101") or foot shorthand ("iambic 4") into a stress string."""
    spec = text.strip().lower()
    if _STRESS_RE.fullmatch(spec):
        return spec
    match = _SHORTHAND_RE.fullmatch(spec)
    if match:
        foot, count = match.group(1), int(match.group(2))
        if foot not in FEET:
            raise ValueError(f"unknown foot '{foot}' (expected one of: {', '.join(FEET)})")
        if count < 1:
            raise ValueError("foot count must be at least 1")
        return FEET[foot] * count
    raise ValueError(
        f"invalid meter '{text}': use a stress string of 0/1/x or '<foot> <count>'"
    )


def mismatch(template: str, stress: str) -> int:
    """Count positions where both sides are definite (0/1) and disagree."""
    return sum(
        1
        for want, have in zip(template, stress, strict=True)
        if want in "01" and have in "01" and want != have
    )
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/unit/test_meter.py -v`
Expected: all passed.

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check --fix && uv run ruff format && uv run ruff check && uv run ruff format --check
git add src/dada_generator/meter.py tests/unit/test_meter.py
git commit -m "Add meter template parsing and stress mismatch scoring"
```

---

### Task 5: Pronouncer and unit tagging

Advances journeys: 2, 3, 8

**Files:**
- Create: `src/dada_generator/pronounce.py`, `src/dada_generator/units.py`
- Test: `tests/unit/test_pronounce.py`, `tests/unit/test_units.py`

**Interfaces:**
- Consumes: `Chunk` (Task 3)
- Produces:
  - `Pronouncer(overrides: Mapping[str, str] | None = None)`; `Pronouncer.stress(word: str) -> str` (over `0 1 ?`, length = syllables); `Pronouncer.guessed -> list[str]` (sorted, normalized words).
  - `Unit(text: str, stress: str, source: str, mode: str)` frozen dataclass with property `syllables -> int`.
  - `tag(chunks: Iterable[Chunk], pronouncer: Pronouncer, mode: str) -> list[Unit]`.

Reference (verified against pronouncing 0.3.0 docs and a local probe): `pronouncing.phones_for_word(word)` returns a list of pronunciations (lowercase lookup); `pronouncing.stresses(phones)` returns digits where `1` primary, `2` secondary, `0` unstressed. `pyphen.Pyphen(lang="en_US").positions(word)` returns hyphenation offsets; it undercounts short endings (`dreamin` -> no break), hence the vowel-group max.

- [ ] **Step 1: Write the failing tests** `tests/unit/test_pronounce.py`

```python
import pytest

from dada_generator.pronounce import Pronouncer


@pytest.mark.parametrize(
    ("word", "expected"),
    [
        ("river", "10"),
        ("River", "10"),
        ("hello", "01"),
        ("the", "?"),
        ("love", "?"),
        ("skyline", "11"),  # CMU secondary stress 2 maps to 1
        ("runnin'", "10"),  # in CMU directly
        ("dreamin'", "10"),  # retried as "dreaming"
    ],
)
def test_cmu_words(word, expected):
    p = Pronouncer()
    assert p.stress(word) == expected
    assert p.guessed == []


@pytest.mark.parametrize(
    ("word", "expected"),
    [
        ("zorp", "?"),
        ("xyzzy", "10"),
        ("zorbflak", "10"),
        ("glimmerous", "100"),
    ],
)
def test_guessed_words(word, expected):
    p = Pronouncer()
    assert p.stress(word) == expected
    assert p.guessed == [word]


def test_guessed_is_sorted_and_unique():
    p = Pronouncer()
    for word in ["zorp", "Xyzzy", "zorp"]:
        p.stress(word)
    assert p.guessed == ["xyzzy", "zorp"]


@pytest.mark.parametrize(
    ("overrides", "word", "expected"),
    [
        ({"zorp": "01"}, "zorp", "01"),
        ({"Zorp": "01"}, "ZORP", "01"),
        ({"river": "01"}, "river", "01"),  # override beats CMU
        ({"the": "0"}, "the", "0"),  # override may pin a monosyllable
        ({"dreamin\u2019": "11"}, "dreamin'", "11"),
    ],
)
def test_overrides(overrides, word, expected):
    p = Pronouncer(overrides)
    assert p.stress(word) == expected
    assert p.guessed == []
```

`tests/unit/test_units.py`:

```python
from dada_generator.chunker import Chunk
from dada_generator.pronounce import Pronouncer
from dada_generator.units import Unit, tag


def test_tag_builds_phrase_stress():
    units = tag([Chunk(("the", "river", "hums"), "a.txt")], Pronouncer(), "phrase")
    assert units == [Unit(text="the river hums", stress="?10?", source="a.txt", mode="phrase")]
    assert units[0].syllables == 4


def test_tag_skips_empty_chunks():
    assert tag([Chunk((), "a.txt")], Pronouncer(), "word") == []
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/unit/test_pronounce.py tests/unit/test_units.py -v`
Expected: FAIL, `ModuleNotFoundError`.

- [ ] **Step 3: Implement** `src/dada_generator/pronounce.py`

```python
import re
from collections.abc import Mapping

import pronouncing
import pyphen

_VOWEL_GROUP_RE = re.compile(r"[aeiouy]+")


def normalize(word: str) -> str:
    return word.lower().replace("\u2019", "'").replace("\u2018", "'")


class Pronouncer:
    """Look up a word's stress pattern: overrides, then CMU, then a guess."""

    def __init__(self, overrides: Mapping[str, str] | None = None) -> None:
        self._overrides = {normalize(k): v for k, v in (overrides or {}).items()}
        self._hyphenator = pyphen.Pyphen(lang="en_US")
        self._guessed: set[str] = set()

    @property
    def guessed(self) -> list[str]:
        return sorted(self._guessed)

    def stress(self, word: str) -> str:
        key = normalize(word)
        if key in self._overrides:
            return self._overrides[key]
        cmu = _cmu_stress(key)
        if cmu is not None:
            return "?" if len(cmu) == 1 else cmu
        self._guessed.add(key)
        count = self._guess_syllables(key)
        return "?" if count == 1 else "1" + "0" * (count - 1)

    def _guess_syllables(self, key: str) -> int:
        vowel_groups = len(_VOWEL_GROUP_RE.findall(key))
        if key.endswith("e") and not key.endswith("le") and vowel_groups > 1:
            vowel_groups -= 1
        hyphen_parts = len(self._hyphenator.positions(key)) + 1
        return max(vowel_groups, hyphen_parts, 1)


def _cmu_stress(key: str) -> str | None:
    candidates = [key]
    if key.endswith("'"):
        candidates.append(key[:-1])
    if key.endswith("in'"):
        candidates.append(key[:-1] + "g")
    for candidate in candidates:
        phones = pronouncing.phones_for_word(candidate)
        if phones:
            stress = pronouncing.stresses(phones[0]).replace("2", "1")
            if stress:
                return stress
    return None
```

`src/dada_generator/units.py`:

```python
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
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/unit/test_pronounce.py tests/unit/test_units.py -v`
Expected: all passed. If a CMU expectation differs (dictionary version drift), check the actual value with `uv run python -c "import pronouncing; print(pronouncing.phones_for_word('WORD'))"` and report it rather than silently editing the expectation; the guessed-word expectations are derived from the algorithm above and must hold.

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check --fix && uv run ruff format && uv run ruff check && uv run ruff format --check
git add src/dada_generator/pronounce.py src/dada_generator/units.py tests/unit/test_pronounce.py tests/unit/test_units.py
git commit -m "Add pronouncer with CMU lookup, overrides, and guessing; add unit tagging"
```

---

### Task 6: Song and override config loading

Advances journeys: 2, 8, 9

**Files:**
- Create: `src/dada_generator/config.py`
- Test: `tests/unit/test_config.py`

**Interfaces:**
- Consumes: `DadaError`, `parse_template`
- Produces: `SectionSpec(templates: tuple[str, ...], repeat: bool = False)`; `SongConfig(sections: dict[str, SectionSpec], outline: tuple[str, ...])`; `load_song(path: Path) -> SongConfig`; `load_overrides(path: Path) -> dict[str, str]`. All errors are `DadaError` with single-line messages.

- [ ] **Step 1: Write the failing tests** `tests/unit/test_config.py`

```python
import pytest

from dada_generator.config import SectionSpec, SongConfig, load_overrides, load_song
from dada_generator.errors import DadaError


def _write(tmp_path, text, name="song.yaml"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_load_song_list_and_mapping_forms(tmp_path):
    path = _write(
        tmp_path,
        """
sections:
  verse:
    - iambic 2
    - "x101"
  chorus:
    repeat: true
    lines: [trochaic 1]
outline: [verse, chorus, verse]
""",
    )
    assert load_song(path) == SongConfig(
        sections={
            "verse": SectionSpec(("0101", "x101"), repeat=False),
            "chorus": SectionSpec(("10",), repeat=True),
        },
        outline=("verse", "chorus", "verse"),
    )


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("sections: [unclosed", "invalid YAML"),
        ("", "expected a mapping"),
        ("- just a list", "expected a mapping"),
        ("outline: [verse]", "missing 'sections'"),
        ("sections: {verse: [iambic 1]}", "missing 'outline'"),
        ("sections: {}\noutline: [verse]", "'sections' must be a non-empty mapping"),
        ("sections: {verse: []}\noutline: [verse]", "section 'verse': expected a non-empty list"),
        ("sections: {verse: {lines: []}}\noutline: [verse]", "section 'verse': expected a non-empty"),
        (
            "sections: {verse: {lines: [iambic 1], repeat: maybe}}\noutline: [verse]",
            "'repeat' must be true or false",
        ),
        (
            "sections: {verse: {lines: [iambic 1], loop: true}}\noutline: [verse]",
            "unknown key",
        ),
        ("sections: {verse: [iambic 1]}\noutline: []", "'outline' must be a non-empty list"),
        ("sections: {verse: [iambic 1]}\noutline: verse", "'outline' must be a non-empty list"),
        (
            "sections: {verse: [iambic 1]}\noutline: [verse, bridge]",
            "outline references unknown section 'bridge'",
        ),
        (
            "sections: {verse: [iambic 1, '01a1']}\noutline: [verse]",
            "section 'verse' line 2: invalid meter",
        ),
        # Review Focus 1: unquoted stress strings are parsed by YAML as integers.
        (
            "sections: {verse: [0101]}\noutline: [verse]",
            "section 'verse' line 1: meter must be a quoted string",
        ),
    ],
)
def test_load_song_errors(tmp_path, text, message):
    path = _write(tmp_path, text)
    with pytest.raises(DadaError, match=message) as info:
        load_song(path)
    assert "\n" not in str(info.value)


def test_load_song_missing_file(tmp_path):
    with pytest.raises(DadaError, match="cannot read"):
        load_song(tmp_path / "nope.yaml")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("zorp: '01'\nrunnin': \"10\"", {"zorp": "01", "runnin'": "10"}),
        ("", {}),
    ],
)
def test_load_overrides(tmp_path, text, expected):
    assert load_overrides(_write(tmp_path, text, "p.yaml")) == expected


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("- zorp", "expected a mapping"),
        ("zorp: 10", "must map to a quoted stress string"),
        ("zorp: '1x'", "must map to a quoted stress string"),
        ("zorp: ''", "must map to a quoted stress string"),
        ("zorp: [1]", "invalid YAML|must map to a quoted stress string"),
    ],
)
def test_load_overrides_errors(tmp_path, text, message):
    with pytest.raises(DadaError, match=message):
        load_overrides(_write(tmp_path, text, "p.yaml"))
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/unit/test_config.py -v`
Expected: FAIL, `ModuleNotFoundError`.

- [ ] **Step 3: Implement** `src/dada_generator/config.py`

```python
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from dada_generator.errors import DadaError
from dada_generator.meter import parse_template

_OVERRIDE_RE = re.compile(r"[01]+")


@dataclass(frozen=True)
class SectionSpec:
    templates: tuple[str, ...]
    repeat: bool = False


@dataclass(frozen=True)
class SongConfig:
    sections: dict[str, SectionSpec]
    outline: tuple[str, ...]


def _one_line(text: str) -> str:
    return " ".join(str(text).split())


def _load_yaml(path: Path) -> Any:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise DadaError(f"{path}: cannot read: not valid UTF-8 text") from exc
    except OSError as exc:
        raise DadaError(f"{path}: cannot read: {exc.strerror or exc}") from exc
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise DadaError(f"{path}: invalid YAML: {_one_line(exc)}") from exc


def load_song(path: Path) -> SongConfig:
    data = _load_yaml(path)
    if not isinstance(data, dict):
        raise DadaError(f"{path}: expected a mapping with 'sections' and 'outline'")
    for key in ("sections", "outline"):
        if key not in data:
            raise DadaError(f"{path}: missing '{key}'")

    raw_sections = data["sections"]
    if not isinstance(raw_sections, dict) or not raw_sections:
        raise DadaError(f"{path}: 'sections' must be a non-empty mapping")
    sections = {str(name): _parse_section(str(name), body) for name, body in raw_sections.items()}

    raw_outline = data["outline"]
    if not isinstance(raw_outline, list) or not raw_outline:
        raise DadaError(f"{path}: 'outline' must be a non-empty list of section names")
    outline = tuple(str(item) for item in raw_outline)
    for name in outline:
        if name not in sections:
            raise DadaError(f"outline references unknown section '{name}'")
    return SongConfig(sections=sections, outline=outline)


def _parse_section(name: str, body: Any) -> SectionSpec:
    lines = body
    repeat = False
    if isinstance(body, dict):
        unknown = sorted(str(k) for k in body if k not in ("lines", "repeat"))
        if unknown:
            raise DadaError(f"section '{name}': unknown key(s) {', '.join(unknown)}")
        lines = body.get("lines")
        repeat = body.get("repeat", False)
        if not isinstance(repeat, bool):
            raise DadaError(f"section '{name}': 'repeat' must be true or false")
    if not isinstance(lines, list) or not lines:
        raise DadaError(f"section '{name}': expected a non-empty list of meter lines")

    templates = []
    for index, item in enumerate(lines, start=1):
        if not isinstance(item, str):
            raise DadaError(
                f"section '{name}' line {index}: meter must be a quoted string, "
                f'e.g. "0101" (got {item!r})'
            )
        try:
            templates.append(parse_template(item))
        except ValueError as exc:
            raise DadaError(f"section '{name}' line {index}: {exc}") from exc
    return SectionSpec(templates=tuple(templates), repeat=repeat)


def load_overrides(path: Path) -> dict[str, str]:
    data = _load_yaml(path)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise DadaError(f"{path}: expected a mapping of word: stress string")
    overrides = {}
    for word, stress in data.items():
        if not isinstance(stress, str) or not _OVERRIDE_RE.fullmatch(stress):
            raise DadaError(
                f"{path}: '{word}' must map to a quoted stress string of 0/1, "
                f'e.g. "10" (got {stress!r})'
            )
        overrides[str(word)] = stress
    return overrides
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/unit/test_config.py -v`
Expected: all passed.

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check --fix && uv run ruff format && uv run ruff check && uv run ruff format --check
git add src/dada_generator/config.py tests/unit/test_config.py
git commit -m "Add song and pronunciation override config loading"
```

---

### Task 7: Assembler

Advances journeys: 2, 3, 4, 5, 6, 7

**Files:**
- Create: `src/dada_generator/assembler.py`
- Test: `tests/unit/test_assembler.py`

**Interfaces:**
- Consumes: `Unit` (Task 5), `mismatch` (Task 4), `SongConfig`/`SectionSpec` (Task 6), `DadaError`
- Produces:
  - `Line(units: tuple[Unit, ...])` with properties `text -> str`, `syllables -> int`
  - `Section(name: str, lines: tuple[Line, ...])`
  - `Song(sections: tuple[Section, ...], warnings: tuple[str, ...])`
  - `Pool(units: Sequence[Unit])` with `by_length: dict[int, list[Unit]]`, `lengths: list[int]` (sorted); raises `DadaError("no usable words found in the lyric files")` when empty
  - `fill_line(template: str, pool: Pool, mode: str, rng: random.Random) -> Line`
  - `build_song(config: SongConfig, pool: Pool, mode: str, rng: random.Random) -> Song`

- [ ] **Step 1: Write the failing tests** `tests/unit/test_assembler.py`

```python
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
        line = fill_line(template, pool, meta.choice(["phrase", "word"]), random.Random(meta.random()))
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/unit/test_assembler.py -v`
Expected: FAIL, `ModuleNotFoundError`.

- [ ] **Step 3: Implement** `src/dada_generator/assembler.py`

```python
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
        allowed = [
            n
            for n in pool.lengths
            if n <= remaining
            and best[remaining - n] is not None
            and (mode != "phrase" or best[remaining - n] == best[remaining] - 1)
        ]
        length = rng.choice(allowed)
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
```

Why `allowed` is never empty: `best[remaining]` is not None, so some length `n` achieved it with `best[remaining - n] == best[remaining] - 1`; that `n` passes both filters.

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/unit/test_assembler.py -v`
Expected: all passed.

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check --fix && uv run ruff format && uv run ruff check && uv run ruff format --check
git add src/dada_generator/assembler.py tests/unit/test_assembler.py
git commit -m "Add reachability-guided line assembler and song builder"
```

---

### Task 8: Rendering, CLI, and user-journey tests on fixtures

Advances journeys: 1, 5, 7, 8, 9, 10

**Files:**
- Create: `src/dada_generator/render.py`, `src/dada_generator/cli.py`
- Create: `tests/e2e/conftest.py`, `tests/e2e/test_seed.py`, `tests/e2e/test_fallback.py`, `tests/e2e/test_pronunciations.py`, `tests/e2e/test_errors.py`, `tests/e2e/test_streams.py`, `tests/e2e/test_help.py`
- Create fixtures: `tests/fixtures/two_syllable.txt`, `tests/fixtures/zorbflak.txt`, `tests/fixtures/streams.txt`, `tests/fixtures/mixed.txt`, `tests/fixtures/fallback.yaml`, `tests/fixtures/zorbflak.yaml`, `tests/fixtures/simple.yaml`
- Test: `tests/unit/test_render.py`

**Interfaces:**
- Consumes: everything above
- Produces: `render(song: Song) -> str`; `cli.main(argv: Sequence[str] | None = None) -> int`; `cli.build_parser() -> argparse.ArgumentParser`. E2E helpers in `tests/e2e/conftest.py`: fixture `run_dada` (callable `(*args, stdout=None) -> subprocess.CompletedProcess[str]`), module-level `parse_sheet(text: str) -> list[tuple[str, list[str]]]`, `line_syllables(line: str, overrides: dict[str, str] | None = None) -> int`, constants `ROOT`, `FIXTURES`, `EXAMPLES`.

- [ ] **Step 1: Write fixtures**

`tests/fixtures/two_syllable.txt`:
```
river, window, candle, yellow
```

`tests/fixtures/zorbflak.txt`:
```
zorbflak
```

`tests/fixtures/streams.txt`:
```
river, zorbflak, window
```

`tests/fixtures/mixed.txt`:
```
[Verse]
Oh, the river hums and every door is open
I left a light on, just in case you wandered home
we were paper boats until the morning came
```

`tests/fixtures/fallback.yaml`:
```yaml
sections:
  verse:
    - "01010"
outline: [verse]
```

`tests/fixtures/zorbflak.yaml`:
```yaml
sections:
  verse:
    - "0101"
outline: [verse]
```

`tests/fixtures/simple.yaml`:
```yaml
sections:
  verse:
    - iambic 3
    - iambic 3
  chorus:
    repeat: true
    lines:
      - trochaic 2
outline: [verse, chorus, verse, chorus]
```

- [ ] **Step 2: Write the failing render test** `tests/unit/test_render.py`

```python
from dada_generator.assembler import Line, Section, Song
from dada_generator.render import render
from dada_generator.units import Unit


def test_render_sheet():
    def line(*texts):
        return Line(tuple(Unit(t, "10", "a.txt", "phrase") for t in texts))

    song = Song(
        sections=(
            Section("verse", (line("the river", "hums"), line("open"))),
            Section("pre-chorus", (line("hold on"),)),
        ),
        warnings=(),
    )
    assert render(song) == "[Verse]\nthe river hums\nopen\n\n[Pre-Chorus]\nhold on\n"
```

- [ ] **Step 3: Write the e2e harness** `tests/e2e/conftest.py`

```python
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
```

- [ ] **Step 4: Write the failing e2e tests**

`tests/e2e/test_help.py` (Journey 1):
```python
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
```

`tests/e2e/test_seed.py` (Journey 5):
```python
from conftest import FIXTURES


def _run(run_dada, seed):
    return run_dada("generate", FIXTURES / "simple.yaml", FIXTURES / "mixed.txt", "--seed", seed)


def test_same_seed_is_identical(run_dada):
    first, second = _run(run_dada, 7), _run(run_dada, 7)
    assert first.returncode == second.returncode == 0
    assert first.stdout == second.stdout


def test_different_seed_differs(run_dada):
    assert _run(run_dada, 7).stdout != _run(run_dada, 8).stdout
```

`tests/e2e/test_fallback.py` (Journey 7):
```python
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
```

`tests/e2e/test_pronunciations.py` (Journey 8):
```python
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
```

`tests/e2e/test_errors.py` (Journey 9, Review Focus 2 and 4):
```python
import pytest

from conftest import FIXTURES


def _song(tmp_path, text):
    path = tmp_path / "song.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def _lyrics(tmp_path, content: bytes):
    path = tmp_path / "lyrics.txt"
    path.write_bytes(content)
    return path


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        ("missing_lyrics", "error: cannot read"),
        ("malformed_yaml", "invalid YAML"),
        ("unknown_section", "outline references unknown section 'bridge'"),
        ("bad_meter", "section 'verse' line 1: invalid meter"),
        ("punctuation_only_lyrics", "no usable words"),
        ("latin1_lyrics", "not valid UTF-8"),
        ("bad_overrides", "must map to a quoted stress string"),
    ],
)
def test_bad_input_is_one_line_error(run_dada, tmp_path, case, expected):
    song = FIXTURES / "simple.yaml"
    lyrics = FIXTURES / "mixed.txt"
    extra = []
    if case == "missing_lyrics":
        lyrics = tmp_path / "nope.txt"
    elif case == "malformed_yaml":
        song = _song(tmp_path, "sections: [unclosed\n")
    elif case == "unknown_section":
        song = _song(tmp_path, "sections: {verse: [iambic 2]}\noutline: [verse, bridge]\n")
    elif case == "bad_meter":
        song = _song(tmp_path, "sections: {verse: ['01a1']}\noutline: [verse]\n")
    elif case == "punctuation_only_lyrics":
        lyrics = _lyrics(tmp_path, b"[Chorus]\n...\n!!\n")
    elif case == "latin1_lyrics":
        lyrics = _lyrics(tmp_path, "caf\xe9\n".encode("latin-1"))
    elif case == "bad_overrides":
        overrides = tmp_path / "p.yaml"
        overrides.write_text("zorp: 10\n", encoding="utf-8")
        extra = ["--pronunciations", overrides]

    result = run_dada("generate", song, lyrics, *extra)
    assert result.returncode == 2
    assert result.stdout == ""
    assert "Traceback" not in result.stderr
    lines = result.stderr.strip().splitlines()
    assert len(lines) == 1
    assert lines[0].startswith("error: ")
    assert expected in lines[0]


def test_unknown_mode_is_usage_error(run_dada):
    result = run_dada(
        "generate", FIXTURES / "simple.yaml", FIXTURES / "mixed.txt", "--mode", "letter"
    )
    assert result.returncode == 2
    assert "Traceback" not in result.stderr
```

`tests/e2e/test_streams.py` (Journey 10):
```python
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
```

Note: `from conftest import ...` works because pytest's default `rootdir`-relative import mode puts `tests/e2e` on `sys.path` for test modules there. If collection fails on that import, add `pythonpath = ["tests/e2e"]` under `[tool.pytest.ini_options]` in `pyproject.toml`.

- [ ] **Step 5: Run to verify they fail**

Run: `uv run pytest tests/unit/test_render.py tests/e2e -v`
Expected: FAIL (`ModuleNotFoundError: dada_generator.render`; e2e fail because `dada` script entry point `dada_generator.cli:main` does not exist).

- [ ] **Step 6: Implement** `src/dada_generator/render.py`

```python
from dada_generator.assembler import Song


def render(song: Song) -> str:
    """Format a song as a plain-text lyric sheet."""
    blocks = []
    for section in song.sections:
        header = f"[{section.name.title()}]"
        blocks.append("\n".join([header, *(line.text for line in section.lines)]))
    return "\n\n".join(blocks) + "\n"
```

`src/dada_generator/cli.py`:

```python
import argparse
import random
import sys
from collections.abc import Sequence
from pathlib import Path

from dada_generator.assembler import Pool, build_song
from dada_generator.chunker import MODES, chunk
from dada_generator.config import load_overrides, load_song
from dada_generator.errors import DadaError
from dada_generator.pronounce import Pronouncer
from dada_generator.render import render
from dada_generator.source import read_sources
from dada_generator.units import tag


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dada",
        description="Dadaist cut-up lyric generator: recombine lyrics into a new song "
        "that follows your meter and structure.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    generate = commands.add_parser(
        "generate",
        help="generate a song from lyric files",
        description="Generate a song. Lyrics go to stdout; warnings go to stderr.",
    )
    generate.add_argument(
        "song", type=Path, metavar="SONG_YAML", help="song file with sections and outline"
    )
    generate.add_argument(
        "lyrics", type=Path, nargs="+", metavar="LYRICS", help="one or more source lyric files"
    )
    generate.add_argument(
        "--mode",
        choices=MODES,
        default="phrase",
        help="cut lyrics into phrases (default) or single words",
    )
    generate.add_argument("--seed", type=int, default=None, help="seed for reproducible output")
    generate.add_argument(
        "--pronunciations",
        type=Path,
        default=None,
        metavar="FILE",
        help="YAML file of word: stress overrides, e.g. runnin': \"10\"",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return _generate(args)
    except DadaError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def _generate(args: argparse.Namespace) -> int:
    config = load_song(args.song)
    overrides = load_overrides(args.pronunciations) if args.pronunciations else {}
    pronouncer = Pronouncer(overrides)
    units = tag(chunk(read_sources(args.lyrics), args.mode), pronouncer, args.mode)
    song = build_song(config, Pool(units), args.mode, random.Random(args.seed))
    sys.stdout.write(render(song))
    for warning in song.warnings:
        print(warning, file=sys.stderr)
    if pronouncer.guessed:
        print(f"guessed pronunciations: {', '.join(pronouncer.guessed)}", file=sys.stderr)
    return 0
```

- [ ] **Step 7: Reinstall and run to verify they pass**

Run: `uv sync && uv run pytest tests/unit/test_render.py tests/e2e -v`
Expected: all passed.

- [ ] **Step 8: Full suite, lint, commit**

```bash
uv run ruff check --fix && uv run ruff format && uv run pytest && uv run ruff check && uv run ruff format --check
git add src/dada_generator/render.py src/dada_generator/cli.py tests/unit/test_render.py tests/e2e tests/fixtures
git commit -m "Add CLI, lyric sheet rendering, and user-journey tests"
```

---

### Task 9: Examples, README, and example-driven journey tests

Advances journeys: 1, 2, 3, 4, 11

**Files:**
- Create: `examples/pop-song.yaml`, `examples/ballad.yaml`, `examples/pronunciations.yaml`, `examples/sample-lyrics.txt`, `examples/sample-lyrics-2.txt`
- Modify: `README.md` (replace stub)
- Create: `tests/e2e/test_phrase_mode.py`, `tests/e2e/test_word_mode.py`, `tests/e2e/test_multi_source.py`, `tests/e2e/test_examples.py`

**Interfaces:**
- Consumes: `run_dada`, `parse_sheet`, `line_syllables`, `EXAMPLES` from `tests/e2e/conftest.py`; `load_song`, `read_sources`, `chunk`, `tag`, `Pool`, `build_song`, `Pronouncer`.
- Produces: user-facing examples and docs.

- [ ] **Step 1: Write the example files**

`examples/sample-lyrics.txt` (original demo text written for this repo):
```
[Verse 1]
I left the porch light burning, just in case
the kitchen radio was humming something old
you said the river never keeps a single face
and every window in this town is painted gold

[Chorus]
Oh, hold on, hold on
we were paper boats in a summer storm
hold on, hold on
until the morning finds us warm

[Verse 2]
the pickup coughed and rattled down the county road
my father's jacket hanging heavy on the door
I counted every mile marker, every load
but never figured what I was counting for

[Bridge]
Maybe it's the static, maybe it's the rain
maybe I'm still dreamin' on the eastbound train
```

`examples/sample-lyrics-2.txt`:
```
[Verse]
Streetlights blinking in a language no one speaks
the diner coffee tastes like Sunday afternoon
we traded secrets for a handful of old keys
while somebody whistled half a borrowed tune

[Chorus]
Carry me, carry me, over the water
carry me home when the evening is gone
the lanterns are low and the night's getting shorter
so carry me, carry me on
```

`examples/pop-song.yaml`:
```yaml
# A full pop structure for `dada generate`.
#
# Each line is a meter template:
#   - a quoted stress string: 0 = unstressed, 1 = stressed, x = either.
#     Its length is the line's syllable count. Always quote it ("0101"),
#     because YAML reads unquoted digits as a number.
#   - or shorthand "<foot> <count>": iambic (01), trochaic (10),
#     anapestic (001), dactylic (100).
#
# A section is either a plain list of lines, or a mapping with `lines`
# and `repeat: true` to reuse the same lyrics every time it appears.
sections:
  verse:
    - iambic 4
    - iambic 4
    - "x1010101"
    - iambic 3
  pre-chorus:
    - trochaic 2
    - trochaic 2
  chorus:
    repeat: true
    lines:
      - "1011"
      - anapestic 3
      - "1011"
      - iambic 4
  bridge:
    - trochaic 3
    - trochaic 3

outline: [verse, pre-chorus, chorus, verse, pre-chorus, chorus, bridge, chorus]
```

`examples/ballad.yaml`:
```yaml
# A short ballad using only shorthand meter.
sections:
  verse:
    - iambic 3
    - iambic 3
    - iambic 3
    - iambic 2
  chorus:
    repeat: true
    lines:
      - dactylic 2
      - dactylic 2

outline: [verse, chorus, verse, chorus]
```

`examples/pronunciations.yaml`:
```yaml
# Pronunciation overrides: word -> quoted stress string (0/1).
# The string's length is the word's syllable count.
# Use these for slang, names, or words the tool guesses wrong
# (they are listed on stderr as "guessed pronunciations").
streetlights: "11"
dreamin': "10"
```

- [ ] **Step 2: Write the failing e2e tests**

`tests/e2e/test_phrase_mode.py` (Journey 2):
```python
from conftest import EXAMPLES, line_syllables, parse_sheet

from dada_generator.config import load_song


def expected_sections(song_path):
    config = load_song(song_path)
    return [(f"[{name.title()}]", config.sections[name].templates) for name in config.outline]


def assert_sheet_matches(stdout, song_path):
    sheet = parse_sheet(stdout)
    expected = expected_sections(song_path)
    assert [header for header, _ in sheet] == [header for header, _ in expected]
    for (_, lines), (_, templates) in zip(sheet, expected, strict=True):
        assert [line_syllables(line) for line in lines] == [len(t) for t in templates]


def test_phrase_mode_full_sheet(run_dada):
    song = EXAMPLES / "pop-song.yaml"
    result = run_dada("generate", song, EXAMPLES / "sample-lyrics.txt", "--seed", 1)
    assert result.returncode == 0
    assert "warning:" not in result.stderr
    assert_sheet_matches(result.stdout, song)
```

`tests/e2e/test_word_mode.py` (Journey 3):
```python
import random
from statistics import mean

from conftest import EXAMPLES
from test_phrase_mode import assert_sheet_matches

from dada_generator.assembler import Pool, build_song
from dada_generator.chunker import chunk
from dada_generator.config import load_song
from dada_generator.pronounce import Pronouncer
from dada_generator.source import read_sources
from dada_generator.units import tag

SONG = EXAMPLES / "pop-song.yaml"
LYRICS = EXAMPLES / "sample-lyrics.txt"


def test_word_mode_full_sheet(run_dada):
    result = run_dada("generate", SONG, LYRICS, "--mode", "word", "--seed", 1)
    assert result.returncode == 0
    assert "warning:" not in result.stderr
    assert_sheet_matches(result.stdout, SONG)


def _mean_units(mode):
    units = tag(chunk(read_sources([LYRICS]), mode), Pronouncer(), mode)
    song = build_song(load_song(SONG), Pool(units), mode, random.Random(1))
    return mean(len(line.units) for s in song.sections for line in s.lines)


def test_word_mode_is_more_fragmented():
    assert _mean_units("word") > _mean_units("phrase")
```

`tests/e2e/test_multi_source.py` (Journey 4):
```python
import random

from conftest import EXAMPLES

from dada_generator.assembler import Pool, build_song
from dada_generator.chunker import chunk
from dada_generator.config import load_song
from dada_generator.pronounce import Pronouncer
from dada_generator.source import read_sources
from dada_generator.units import tag

FILES = [EXAMPLES / "sample-lyrics.txt", EXAMPLES / "sample-lyrics-2.txt"]


def test_multi_source_cli_run(run_dada):
    result = run_dada("generate", EXAMPLES / "pop-song.yaml", *FILES, "--seed", 1)
    assert result.returncode == 0
    assert result.stdout.startswith("[Verse]\n")


def test_multi_source_draws_from_both():
    units = tag(chunk(read_sources(FILES), "phrase"), Pronouncer(), "phrase")
    song = build_song(load_song(EXAMPLES / "pop-song.yaml"), Pool(units), "phrase", random.Random(1))
    sources = {u.source for s in song.sections for line in s.lines for u in line.units}
    assert sources == {str(f) for f in FILES}
```

`tests/e2e/test_examples.py` (every example runs cleanly; Journey 11 automated part):
```python
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
```

Note: `test_multi_source_draws_from_both` is seed-dependent. If seed 1 happens to draw only one file, try seeds 1..20 inside the test and assert that at least one seed draws from both, and that seed 1 output is non-empty. Do not delete the assertion.

- [ ] **Step 3: Run to verify they fail**

Run: `uv run pytest tests/e2e/test_phrase_mode.py tests/e2e/test_word_mode.py tests/e2e/test_multi_source.py tests/e2e/test_examples.py -v`
Expected before Step 1 files exist: FAIL on missing files. If Step 1 was done first, these may pass immediately; that is acceptable here because the behavior was implemented in Tasks 2-8 and these tests pin it against the shipped examples.

- [ ] **Step 4: Write `README.md`**

````markdown
# dada-generator

A Dadaist cut-up lyric generator. It takes lyrics you wrote, cuts them into
phrases or single words, and reassembles them at random into a new song that
follows a verse/chorus structure and a meter you define. The structure sounds
confident and familiar; the words are chance. (Tristan Tzara's cut-up method,
mechanized.)

## Install

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv tool install .          # puts `dada` on your PATH
# or, for development:
uv sync
uv run dada --help
```

## Usage

```
dada generate SONG_YAML LYRICS [LYRICS ...] [--mode phrase|word] [--seed INT] [--pronunciations FILE]
```

| Option | Meaning |
|--------|---------|
| `SONG_YAML` | Song file: section meters and the outline (see below) |
| `LYRICS` | One or more plain-text lyric files. More files = a bigger pool |
| `--mode phrase` | Default. Cut at line breaks, punctuation, and before conjunctions (and, but, when, ...). More singable |
| `--mode word` | Cut into single words. More fragmented, closer to word salad |
| `--seed INT` | Same seed + same inputs = same song |
| `--pronunciations FILE` | Override how specific words are stressed (see below) |

Lyrics print to stdout. Warnings print to stderr, so redirecting saves only
the lyrics:

```bash
dada generate examples/pop-song.yaml examples/sample-lyrics.txt --seed 1
dada generate examples/pop-song.yaml my-song.txt another-song.txt --mode word > new-song.txt
```

In lyric files, blank lines and section labels like `[Chorus]` are ignored.

## Song files

```yaml
sections:
  verse:
    - iambic 4          # shorthand: 4 iambic feet = "01010101"
    - "x1010101"        # stress string: x = either
  chorus:
    repeat: true        # generate once, reuse every time the chorus appears
    lines:
      - trochaic 3
      - "10101010"
outline: [verse, chorus, verse, chorus]
```

- **Stress strings:** `0` unstressed, `1` stressed, `x` either. The length is
  the line's syllable count. **Always quote them**: YAML reads `0101` as a
  number and the tool will tell you to add quotes.
- **Shorthand:** `<foot> <count>` where foot is `iambic` (01), `trochaic` (10),
  `anapestic` (001), or `dactylic` (100).
- **Sections** are either a plain list of lines, or `{lines: [...], repeat: true}`.
  Repeated sections reuse the same lyrics (a hook); other sections are
  regenerated every time they appear.
- **Outline** is the order of sections; every name must be defined.

To make your own, copy an example and edit it:

```bash
cp examples/ballad.yaml my-song.yaml
```

## How matching works

Every line gets exactly its template's syllable count when the pool allows.
Among units that fit, the tool prefers those whose stress best matches the
template; one-syllable words count as matching either way. In phrase mode it
uses a whole phrase when one fits and joins phrases only when needed.

If a line's syllable count cannot be reached (for example, every phrase is
2 syllables and the line needs 5), it uses the nearest count and warns:

```
warning: verse line 1 wanted 5 syllables, used 4
```

Add more lyric files or adjust the meter to avoid this.

## Pronunciations

Stress comes from the CMU Pronouncing Dictionary. Words it does not know are
guessed and listed on stderr:

```
guessed pronunciations: streetlights, zorbflak
```

Fix them with an overrides file (quoted `0`/`1` strings; length = syllables):

```yaml
streetlights: "11"
dreamin': "10"
```

```bash
dada generate my-song.yaml lyrics.txt --pronunciations examples/pronunciations.yaml
```

## Errors

Bad input (missing file, broken YAML, unknown section, bad meter) prints one
`error: ...` line to stderr and exits with code 2.

## Development

```bash
uv sync
uv run pytest
uv run ruff check --fix && uv run ruff format && uv run ruff check && uv run ruff format --check
```
````

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest -v && uv run ruff check && uv run ruff format --check`
Expected: all passed. If `test_phrase_mode_full_sheet` reports a `warning:` for the example, the sample lyrics lack a needed unit length; confirm `Oh` (1 syllable) survives chunking with `uv run python -c "..."` and fix the example content, not the test.

- [ ] **Step 6: Commit**

```bash
git add examples README.md tests/e2e
git commit -m "Add examples, README, and example-driven journey tests"
```

---

### Task 10: Journey verification gate

Advances journeys: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12

**Files:**
- Modify: this plan's `## Journeys` table (Evidence column)

- [ ] **Step 1:** Run `bash ~/.claude/skills/definition-of-done-journeys/lint-journeys-block.sh docs/superpowers/specs/2026-09-25-dada-lyric-generator-design.md docs/superpowers/plans/2026-09-25-dada-lyric-generator.md` and diff the two Journeys tables; surface any drift.
- [ ] **Step 2:** Journey 1: `uv tool install --force . && dada --help && dada generate --help`; paste the transcript.
- [ ] **Step 3:** Journeys 2, 3: run the automated tests, then paste the transcript of `dada generate examples/pop-song.yaml examples/sample-lyrics.txt --seed 1` and the same with `--mode word`.
- [ ] **Step 4:** Journeys 4-9: run each named test file with `uv run pytest <file> -v`; paste pass lines.
- [ ] **Step 5:** Journey 10: run the test, then in a shell `dada generate tests/fixtures/fallback.yaml tests/fixtures/streams.txt --seed 1 > /tmp/song.txt; cat /tmp/song.txt`; paste both streams.
- [ ] **Step 6:** Journey 11: `cp examples/ballad.yaml <scratch>/my-song.yaml`, add a `bridge: [trochaic 3]` section and put it in the outline, run it; paste the transcript showing `[Bridge]`.
- [ ] **Step 7:** Journey 12: run the workflow commands locally (`uv sync --locked && uv run ruff check && uv run ruff format --check && uv run pytest`), or `act` if installed; paste the transcript. Record a user waiver for the GitHub run until a remote exists.
- [ ] **Step 8:** Paste all evidence into the Evidence column. Any failure: paste it, stop, report.
````
