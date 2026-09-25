# Dada Lyric Generator - Design

Date: 2026-09-25
Source brief: `dadaist-lyric-generator-spec.md` (user-provided)

## Purpose

A CLI that cuts up the user's own song lyrics into phrases or words, tags each
unit with syllable count and stress, and reassembles them at random into a new
song that follows a user-defined structure and meter. The conventional
structure and confident meter are the misdirection; the words are chance
(Tzara's cut-up method, mechanized). Repetition is acceptable and even
desirable.

Success: the user runs the CLI on one of their songs with a song config and
gets a complete, on-meter lyric sheet on stdout, in either phrase or word mode.

## Decisions

| Topic | Decision |
|-------|----------|
| Language / tooling | Python 3.12+, `uv`, `pyproject.toml`, `ruff`, `pytest` |
| Stress strictness | Syllable count exact; stress scored (lowest mismatch wins); monosyllables are stress-flexible |
| Fallback | Combine units to reach the exact count; if the count is unreachable, use nearest reachable count and warn |
| Phrase boundaries | Line breaks + punctuation + split before conjunctions |
| Out-of-dictionary words | User override file -> CMU (`pronouncing`, with `in'` -> `ing` retry) -> guess: syllables = max(Pyphen, vowel-group count), first-syllable stress; guessed words reported on stderr |
| Repeated sections | A section marked `repeat: true` is generated once and reused on every outline occurrence (hook-style chorus); other sections regenerate each time |
| Output | Plain-text lyric sheet on stdout; warnings/errors on stderr; no file export, no JSON |
| Meter notation | Stress strings (`"01010101"`) or foot shorthand (`iambic 4`); `x` wildcard |
| Config layout | One song YAML containing `sections` and `outline` |
| Repo | Local git now; no GitHub repo or push until the user asks |
| Assembly algorithm | Randomized left-to-right fill guided by a syllable-reachability DP (no backtracking needed) |

## CLI

```
dada generate SONG_YAML LYRICS [LYRICS ...]
    --mode phrase|word      default: phrase
    --seed INT              reproducible output
    --pronunciations FILE   optional pronunciation overrides
```

`argparse` (stdlib). Runtime dependencies: `pronouncing`, `pyphen`, `pyyaml`.

## Input formats

### Lyric files

Plain text. Blank lines and bracketed section labels (lines matching
`^\s*\[.*\]\s*$`, e.g. `[Chorus]`) are ignored. Each remaining line is a lyric
line tagged with its source filename.

### Song YAML

```yaml
sections:
  verse:
    - iambic 4
    - "x1010101"
    - "01010101"
    - iambic 3
  chorus:
    repeat: true
    lines:
      - trochaic 3
      - trochaic 3
      - "10101010"
outline: [verse, chorus, verse, chorus, chorus]
```

- `sections`: mapping of section name -> either a non-empty list of line
  templates, or a mapping `{lines: <non-empty list>, repeat: <bool, default false>}`.
  With `repeat: true` the section is generated on its first outline occurrence
  and the same lyrics are reused for every later occurrence.
- A line template is either a stress string over the alphabet `0`, `1`, `x`
  (length = syllable count) or `<foot> <n>` where foot is one of `iambic`
  (`01`), `trochaic` (`10`), `anapestic` (`001`), `dactylic` (`100`) and `n`
  is a positive integer.
- `outline`: non-empty list of section names, each defined in `sections`.
- Stress strings must be quoted in YAML: an unquoted `0101` is parsed by YAML
  as an integer, and the loader rejects non-string templates with a hint to quote them.

### Pronunciation overrides YAML

```yaml
runnin': "10"
gonna: "10"
```

Keys are words (matched case-insensitively, after the same normalization used
for lookup); values are stress strings over `0`/`1`. Length = syllable count.

## Components

Package `dada_generator` under `src/`, console script `dada`.

| Module | Responsibility | Depends on |
|--------|----------------|------------|
| `source.py` | Read lyric files; drop blank lines and `[Section]` labels; return `(line, source)` records | - |
| `chunker.py` | `chunk(lines, mode)` -> text units. Phrase: split on line breaks, punctuation (`, . ; : ! ? -` and em/en dashes), and before conjunctions. Word: split into words, strip surrounding punctuation (keep internal apostrophes) | - |
| `pronounce.py` | `Pronouncer.stress(word)` -> stress string (length = syllables). Order: override file, CMU via `pronouncing` (lowercased; then without trailing `'`; then `in'` -> `ing`), guess. Records guessed words | `pronouncing`, `pyphen` |
| `units.py` | `Unit` dataclass (`text`, `syllables`, `stress`, `source`, `mode`); `tag(chunks, pronouncer)` builds unit stress from word stresses | `pronounce` |
| `meter.py` | Parse templates (string / shorthand) into stress strings; `mismatch(template_slice, unit_stress)` scoring | - |
| `config.py` | Load and validate song YAML and overrides YAML into dataclasses | `pyyaml`, `meter` |
| `assembler.py` | `fill_line(template, pool, mode, rng)`; `build_song(config, pool, mode, rng)` walks the outline | `meter`, `units` |
| `render.py` | Format song as plain-text lyric sheet | - |
| `cli.py` | Parse args, wire modules, route lyrics to stdout and warnings/errors to stderr, map errors to exit codes | all |

The random generator is always an explicit `random.Random(seed)` passed down;
no module uses the global `random` state.

The conjunction list lives in one constant in `chunker.py`:
`and, but, or, so, when, because, while, if, though, until, then`.
Splitting happens only before a conjunction that is not the first word of the
fragment, and a split never produces an empty chunk.

## Stress representation and scoring

- Unit stress is a string over `0`, `1`, `?`.
- CMU primary (`1`) and secondary (`2`) stress both map to `1`; `0` stays `0`.
- Every syllable of a monosyllabic word becomes `?` (flexible).
- Phrase stress is the concatenation of its words' stresses. Example:
  "the river hums" -> `?10?`.
- Guessed words: syllables = max(Pyphen hyphenation parts, vowel-group count
  with a silent-final-`e` adjustment, minimum 1). Pyphen alone undercounts
  because it is a hyphenator (it will not split short word endings, e.g.
  `dreamin` -> 1). Polysyllabic guesses: first syllable `1`, rest `0`;
  monosyllabic guesses: `?`.
- Override values are used exactly as given (a user may pin a monosyllable to `0`).
- `mismatch(template, stress)` = number of positions where both characters are
  definite (`0`/`1`) and differ. `?` and `x` never mismatch.

## Assembly algorithm

For a line template `T` of length `N`, with the pool's available syllable
lengths `L = {unit.syllables}`:

1. Compute `reach[r]` for `r = 0..N`: whether `r` syllables can be composed
   from lengths in `L` (unbounded reuse, since repetition is allowed), and
   `min_units[r]`: the fewest units that compose `r`.
2. If `reach[N]` is false, choose the nearest reachable `N'` (smallest
   `|N - N'|`, ties go to the shorter), adjust `T` by truncating or padding
   with `x` to length `N'`, and emit a warning:
   `warning: <section> line <i> wanted <N> syllables, used <N'>`.
   If no length in `1..2N` is reachable (empty pool), raise `DadaError`.
3. Fill left to right with `r` remaining:
   - Allowed lengths: `l` in `L` with `l <= r` and `reach[r - l]`.
   - Choose a length at random, weighted by `count(l) * w(l)`, where
     `count(l)` is the number of pool units of that length (so a rare length
     is not over-used) and `w(l)` is 1 in word mode. In phrase mode
     `w(l) = 0.5 ** extra(l)` with `extra(l) = min_units[r - l] + 1 - min_units[r]`
     (the extra units that choice forces): fewer, longer phrases are
     preferred but not required, so one phrase cannot fill every line.
   - Among units of that length, compute `mismatch` against the matching
     slice of `T`; choose uniformly at random among those with the lowest
     score.

   (Revised 2026-09-25: the original rule, "phrase mode must stay on a
   fewest-units path; length chosen uniformly", made output degenerate on a
   single short source, e.g. every 6-syllable line was the only 6-syllable
   phrase.)
4. Join chosen unit texts with single spaces to form the line.

Because every step keeps the remainder reachable, the fill always terminates
without backtracking.

`build_song` walks the outline. For a section with `repeat: true` it caches the
first generated section and reuses it on later occurrences (warnings are
emitted only when a section is actually generated). Other sections are
generated fresh on every occurrence.

## Output

```
[Verse]
the river hums and every door
...

[Chorus]
...
```

Section header is the section name title-cased in brackets; one blank line
between sections. Lyrics go to stdout only.

After generation, if any words were guessed, one line is written to stderr:
`guessed pronunciations: <comma-separated sorted unique words>`.

## Error handling

All user-input problems raise `DadaError`, caught in `cli.py`, printed as
`error: <message>` on stderr, exit code 2. Validation lives at boundaries
(`source.py`, `config.py`); inner modules assume valid input. Unexpected
exceptions are not caught.

| Situation | Message shape | Exit |
|-----------|---------------|------|
| Lyric file missing or unreadable | `error: cannot read <file>: <reason>` | 2 |
| No usable lyric lines across all files | `error: no lyric text found in <files>` | 2 |
| Song YAML missing, malformed, or lacking `sections` / `outline` | `error: <file>: <problem>` | 2 |
| Outline references undefined section | `error: outline references unknown section '<name>'` | 2 |
| Invalid meter template | `error: section '<name>' line <i>: <problem>` | 2 |
| Malformed overrides file | `error: <file>: <problem>` | 2 |
| Line needs nearest-count fallback | stderr warning, run continues | 0 |
| Guessed pronunciations | stderr summary, run continues | 0 |

## Testing

- TDD throughout; `pytest`; table-driven tests (`pytest.mark.parametrize`).
- Unit tests per module: chunker splits and label stripping; pronouncer CMU,
  override, and fallback paths plus guess tracking; meter shorthand, `x`,
  scoring with `?`, invalid templates; config every error row; assembler exact
  fit, phrase-mode fewest-units preference, word mode, fallback warning, seed
  determinism.
- Property-style test: for random templates and random pools, every filled line
  has exactly `N` syllables whenever `N` is reachable.
- User-journey tests in `tests/e2e/` invoke the installed `dada` command via
  `subprocess` against fixture lyrics and the example song files, asserting
  exit codes, section headers, per-line syllable counts (re-tagged with the
  same pronouncer), seed determinism, stdout/stderr separation, and error exit
  codes.

## CI

`.github/workflows/ci.yml`, on push and pull_request: checkout, `astral-sh/setup-uv`,
Python 3.12, `uv sync`, `uv run ruff check`, `uv run ruff format --check`,
`uv run pytest`.

## Docs and examples

- `README.md`: install (`uv sync`, `uv tool install .`), command syntax, all
  flags, phrase vs word mode, meter notation (strings, shorthand, `x`),
  overrides file, sample invocations including shell redirection.
- `examples/pop-song.yaml` (verse, pre-chorus, chorus, bridge; mix of strings
  and shorthand), `examples/ballad.yaml` (short, shorthand only),
  `examples/pronunciations.yaml`, `examples/sample-lyrics.txt` and
  `examples/sample-lyrics-2.txt` (original demo text written for this repo).

## Layout

```
pyproject.toml
README.md
.gitignore            # includes CLAUDE.md
src/dada_generator/{__init__,cli,source,chunker,pronounce,units,meter,config,assembler,render}.py
tests/unit/
tests/e2e/
tests/fixtures/
examples/
.github/workflows/ci.yml
docs/superpowers/specs/
```

## Out of scope (v1)

JSON or annotated output, GUI, file export, weighted/looseness selection,
POS-based clause detection, neural G2P, GitHub repo creation.

## Journeys

| # | Item | Proof | Check method | Evidence |
|---|------|-------|--------------|----------|
| 1 | I can install the tool and run `dada` from my shell | `uv tool install .` (or `uv sync` then `uv run dada --help`) succeeds; `dada --help` and `dada generate --help` print usage listing `--mode`, `--seed`, `--pronunciations`; exit 0 | narrated: install + help transcript | |
| 2 | Phrase mode, one lyric file + example song YAML, produces a complete sheet: every section in outline order, every line exactly the template's syllable count | `dada generate examples/pop-song.yaml examples/sample-lyrics.txt --seed 1` exits 0; headers appear in outline order; each line re-tagged by the pronouncer equals its template length | automated: `tests/e2e/test_phrase_mode.py` + narrated: transcript of the run | |
| 3 | Word mode, same inputs, produces a visibly more fragmented sheet, still exact syllable counts | Same command with `--mode word` exits 0, exact per-line counts; mean units per line is higher than phrase mode for the same seed and inputs | automated: `tests/e2e/test_word_mode.py` + narrated: side-by-side transcript | |
| 4 | Multiple lyric files are pooled and output draws from more than one | With two sample files and a fixed seed, generated lines contain units originating from both sources (checked via a test hook on the assembled song, not text guessing) | automated: `tests/unit/test_assembler.py::test_multi_source_pool` + `tests/e2e/test_multi_source.py` (exit 0, output produced) | |
| 5 | Same seed -> identical output; different seed -> different output | Two runs with `--seed 7` are byte-identical; runs with `--seed 7` and `--seed 8` differ | automated: `tests/e2e/test_seed.py` | |
| 6 | Stress matching measurably steers selection | Fixture pool with same-length units of different stresses; for template `0101`, chosen units have total mismatch 0 across 100 seeded fills while a stress-blind baseline over the same pool averages > 0 | automated: `tests/unit/test_assembler.py::test_stress_steering` | |
| 7 | Unreachable syllable count still yields a song plus a stderr warning naming section and line | Fixture lyrics with only 2-syllable units and a template of length 5: exit 0, lyrics on stdout, stderr contains `warning: verse line 1 wanted 5 syllables, used 4` | automated: `tests/e2e/test_fallback.py` | |
| 8 | Unknown words are guessed and reported; overrides change tagging | Fixture with a non-CMU word: stderr lists it under `guessed pronunciations:`; with `--pronunciations` mapping it, it is no longer listed and its stress/syllables follow the override | automated: `tests/e2e/test_pronunciations.py` + `tests/unit/test_pronounce.py` | |
| 9 | Bad input yields a one-line error, no traceback, exit 2 | Cases: missing lyric file, malformed YAML, undefined outline section, invalid meter string. Each: exit 2, stderr single line starting `error:`, no `Traceback` | automated: `tests/e2e/test_errors.py` (parametrized) | |
| 10 | `dada generate ... > song.txt` saves only lyrics | Run that triggers both a fallback warning and guessed words, redirecting stdout to a file: file contains no `warning:` or `guessed pronunciations:` lines; stderr contains them | automated: `tests/e2e/test_streams.py` + narrated: shell transcript with `cat song.txt` | |
| 11 | I can copy an example, edit it per the README, and run it | Copy `examples/ballad.yaml`, change the outline and one template following README syntax, run it: exit 0, new structure reflected in output | narrated: transcript of copy, edit, run | |
| 12 | CI runs lint + tests on push/PR and passes | Workflow file runs ruff check, ruff format --check, pytest on push and pull_request; locally, the same steps pass (via `act` if available, otherwise running the exact workflow commands). Full verification requires a GitHub remote and is expected to be user-waived until then | narrated: local run transcript of the workflow steps; GitHub run URL once pushed | |
| 13 | Repeated phrases do not dominate the song | With `examples/ballad.yaml` and `examples/pop-song.yaml` against `examples/sample-lyrics.txt`, seeds 1-20: phrase mode mean distinct-line ratio over generated sections >= 0.6 (was 0.20 / 0.33 before the revision); word mode most-common-word share never exceeds 30% of words (was up to 39%) | automated: `tests/e2e/test_variety.py` + narrated: ballad run transcript | |
