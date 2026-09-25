# AGENTS.md

Guidance for coding agents (and humans) working in this repository.

## Project

`dada` is a Python CLI that cuts a user's own lyrics into phrases or words,
tags each unit with syllable count and stress, and reassembles them at random
into a song that follows a user-defined meter and outline. The design spec is
`docs/superpowers/specs/2026-09-25-dada-lyric-generator-design.md`. It is the
authority for behavior; read it before changing how assembly, chunking, or
pronunciation works.

## Setup and commands

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync                          # create .venv and install the package + dev tools
uv run pytest                    # full suite (unit + end-to-end)
uv run pytest tests/unit         # fast unit tests only
uv run ruff check --fix          # lint (auto-fix import order etc.)
uv run ruff format               # format
uv run dada generate examples/pop-song.yaml examples/sample-lyrics.txt --seed 1
```

Before every commit, all of these must pass. CI (`.github/workflows/ci.yml`)
runs exactly:

```bash
uv sync --locked && uv run ruff check && uv run ruff format --check && uv run pytest
```

If you change dependencies, run `uv lock` and commit `uv.lock`; CI uses
`--locked`.

## Layout

Each module has one job. The pipeline is
`source -> chunker -> pronounce/units -> assembler -> render`, wired by `cli`.

| Path | Responsibility |
|------|----------------|
| `src/dada_generator/source.py` | Read lyric files (UTF-8, BOM ok); drop blank lines and `[Section]` labels |
| `src/dada_generator/chunker.py` | `tokenize` and `chunk(lines, mode)`: phrase splits at punctuation and before conjunctions; word splits |
| `src/dada_generator/pronounce.py` | `Pronouncer.stress(word)`: overrides, then CMU (with `in'`->`ing` and accent-stripped retries), then a guess |
| `src/dada_generator/units.py` | `Unit` dataclass and `tag()` |
| `src/dada_generator/meter.py` | Meter template parsing (`"x101"`, `iambic 4`) and stress `mismatch` scoring |
| `src/dada_generator/config.py` | Load and validate the song YAML and the pronunciation overrides YAML |
| `src/dada_generator/assembler.py` | `Pool`, `fill_line`, `build_song` (reachability DP + weighted random fill) |
| `src/dada_generator/render.py` | Plain-text lyric sheet |
| `src/dada_generator/cli.py` | argparse, wiring, stdout/stderr routing, exit codes |
| `tests/unit/` | One test file per module |
| `tests/e2e/` | User-journey tests that run the installed `dada` script via subprocess |
| `tests/fixtures/` | Small lyric and song files for tests |
| `examples/` | User-facing templates; the e2e tests run against them, so keep them valid |
| `docs/superpowers/` | Design spec and implementation plan (including the Journeys definition-of-done table) |

## Behavior contracts (do not break)

- **Streams:** lyrics go to stdout only. Warnings, the
  `guessed pronunciations:` summary, and errors go to stderr only. Users rely
  on `dada generate ... > song.txt` saving only lyrics.
- **Errors:** every user-input problem raises `DadaError` with a single-line
  message. Only `cli.py` catches it, prints `error: <message>`, and exits 2.
  Validate at the boundaries (`source.py`, `config.py`); inner modules assume
  valid input. Do not catch unexpected exceptions.
- **Randomness:** always pass an explicit `random.Random`; never use the
  global `random` state. Same seed and same inputs must give identical output.
- **Syllable counts:** a filled line must hit the template's exact syllable
  count whenever the pool can reach it. Otherwise it uses the nearest reachable
  count (ties go shorter) and emits
  `warning: <section> line <i> wanted <N> syllables, used <M>`.
- **Stress alphabets:** templates use `0 1 x`; unit stresses use `0 1 ?`
  (`?` = one-syllable word, matches anything); override values use `0 1`.
- **Repeat sections:** a section with `repeat: true` is generated once and
  reused; others regenerate on every outline occurrence.

## Conventions

- **Test-driven:** write the failing test first, watch it fail, then implement.
  Bug fixes start with a test that reproduces the bug.
- **Table-driven tests:** use `pytest.mark.parametrize` whenever there is more
  than one case.
- **Never disable, skip, or weaken a test to make it pass.** If a test encodes
  behavior the spec has deliberately changed, update the spec first and say so.
- **End-to-end tests** call the real console script (`run_dada` fixture in
  `tests/e2e/conftest.py`), not internal functions, unless they need to inspect
  unit provenance.
- **ASCII-only source:** write non-ASCII characters in code and tests as `\u`
  escapes (e.g. `"\u2014"`).
- **No em dashes** in code, docs, comments, messages, or commit messages. Use
  `-`, a colon, or rewrite the sentence.
- **Style:** ruff with `line-length = 100`, `target-version = "py312"`, rules
  `E, F, I, B, UP`. `docs/` is excluded from ruff.
- **Dependencies:** runtime deps are `pronouncing`, `pyphen`, `pyyaml`, and
  nothing else without a good reason. The CLI uses stdlib `argparse`.
- **Commits:** small and focused, imperative subject line, no AI attribution
  lines. `CLAUDE.md` is gitignored and must never be committed.

## Where to start for common changes

- **New meter shorthand:** add it to `FEET` in `meter.py`, add a parametrize
  case in `tests/unit/test_meter.py`, and document it in `README.md` and the
  example YAML comments.
- **Different phrase-splitting rules:** `_BREAK_RE` and `CONJUNCTIONS` in
  `chunker.py`, with cases in `tests/unit/test_chunker.py`.
- **Selection behavior:** `fill_line` and `_length_weight` in `assembler.py`.
  Keep `tests/unit/test_assembler.py` (exact counts, property test, stress
  steering) and `tests/e2e/test_variety.py` green.
- **New CLI flag:** `build_parser` in `cli.py`, a test in `tests/e2e/`, and the
  Usage table in `README.md`.
