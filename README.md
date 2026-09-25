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
uses a whole phrase when one fits and joins phrases only when needed, so with
a single short source song the same phrase can come back often. Add more
lyric files, or use `--mode word`, for more variety.

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
uv run ruff check && uv run ruff format --check
```
