# dada-lyrics-generator

[![CI](https://github.com/dcmcand/dada-lyrics-generator/actions/workflows/ci.yml/badge.svg)](https://github.com/dcmcand/dada-lyrics-generator/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

A Dadaist cut-up lyric generator. It takes lyrics you wrote, cuts them into
phrases or single words, and reassembles them at random into a new song that
follows a verse/chorus structure and a meter you define.

The structure sounds confident and familiar; the words are chance. A listener
keeps trying to assemble a story that is not really there. This is Tristan
Tzara's cut-up method, mechanized.

```
$ dada generate examples/pop-song.yaml examples/sample-lyrics.txt examples/sample-lyrics-2.txt --seed 5
[Verse]
the lanterns are low carry me
the lanterns are low just in case
the lanterns are low hold on Oh
so carry me Oh Oh

[Pre-Chorus]
carry me on
hold on hold on
...
```

## Contents

- [Install](#install)
- [Quick start](#quick-start)
- [Usage](#usage)
- [Song files](#song-files)
- [How matching works](#how-matching-works)
- [Pronunciations](#pronunciations)
- [Errors](#errors)
- [Development](#development)
- [License](#license)

## Install

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone git@github.com:dcmcand/dada-lyrics-generator.git
cd dada-lyrics-generator
uv tool install .          # puts `dada` on your PATH
```

Or run it from a development checkout without installing:

```bash
uv sync
uv run dada --help
```

## Quick start

```bash
# 1. Generate a song from the bundled example lyrics
dada generate examples/pop-song.yaml examples/sample-lyrics.txt --seed 1

# 2. Use your own lyrics (one or more plain-text files)
dada generate examples/pop-song.yaml my-song.txt another-song.txt

# 3. Make your own structure
cp examples/ballad.yaml my-structure.yaml   # edit it, then:
dada generate my-structure.yaml my-song.txt > new-song.txt
```

## Usage

```
dada generate SONG_YAML LYRICS [LYRICS ...] [--mode phrase|word] [--seed INT] [--pronunciations FILE]
```

| Option | Meaning |
|--------|---------|
| `SONG_YAML` | Song file: section meters and the outline (see [Song files](#song-files)) |
| `LYRICS` | One or more plain-text lyric files. More files = a bigger pool |
| `--mode phrase` | Default. Cut at line breaks, punctuation, and before conjunctions (and, but, when, ...). More singable |
| `--mode word` | Cut into single words. More fragmented, closer to word salad |
| `--seed INT` | Same seed + same inputs = same song |
| `--pronunciations FILE` | Override how specific words are stressed (see [Pronunciations](#pronunciations)) |

Lyrics print to stdout. Warnings print to stderr, so redirecting saves only
the lyrics:

```bash
dada generate examples/pop-song.yaml my-song.txt --mode word > new-song.txt
```

In lyric files, blank lines and section labels like `[Chorus]` are ignored.
Files must be UTF-8 (a byte-order mark is fine).

## Song files

A song file defines each section's meter and the order the sections appear in:

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
  number, and the tool will tell you to add quotes.
- **Shorthand:** `<foot> <count>`, where foot is `iambic` (01), `trochaic` (10),
  `anapestic` (001), or `dactylic` (100).
- **Sections** are either a plain list of lines, or `{lines: [...], repeat: true}`.
  Repeated sections reuse the same lyrics, like a hook. Other sections are
  regenerated every time they appear.
- **Outline** is the order of sections. Every name must be defined in `sections`.

The [`examples/`](examples) folder has ready-to-copy templates:

| File | What it is |
|------|------------|
| `pop-song.yaml` | Verse, pre-chorus, chorus, bridge; mixes stress strings and shorthand |
| `ballad.yaml` | Short verse/chorus song using only shorthand |
| `pronunciations.yaml` | Example pronunciation overrides |
| `sample-lyrics.txt`, `sample-lyrics-2.txt` | Original demo lyrics to try the tool on |

## How matching works

1. Lyrics are cut into units: phrases (phrase mode) or words (word mode).
2. Each unit is tagged with its syllable count and stress pattern.
3. Each line is filled left to right with units that add up to exactly the
   template's syllable count.
4. Among units of a chosen length, the tool picks one whose stress best matches
   the template. One-syllable words count as matching either way.

In phrase mode it prefers a whole phrase when one fits, but still joins shorter
phrases some of the time, so a single phrase does not fill every line of its
length. With a single short source song some phrases will still come back.
Repetition is part of the effect, but you can add more lyric files, or use
`--mode word`, for more variety.

If a line's syllable count cannot be reached (for example, every phrase is
2 syllables and the line needs 5), it uses the nearest count and warns:

```
warning: verse line 1 wanted 5 syllables, used 4
```

Add more lyric files or adjust the meter to avoid this.

## Pronunciations

Stress comes from the [CMU Pronouncing Dictionary](http://www.speech.cs.cmu.edu/cgi-bin/cmudict)
(via [pronouncing](https://pronouncing.readthedocs.io/)). Dropped-g spellings
like `dreamin'` are looked up as `dreaming`, and accented words like `café` fall
back to their plain spelling. Words it still does not know are guessed and
listed on stderr:

```
guessed pronunciations: streetlights, zorbflak
```

Fix them with an overrides file of quoted `0`/`1` strings (length = syllables):

```yaml
streetlights: "11"
dreamin': "10"
```

```bash
dada generate my-song.yaml lyrics.txt --pronunciations examples/pronunciations.yaml
```

## Errors

Bad input (missing file, broken YAML, unknown section, bad meter string,
unquoted stress string) prints one `error: ...` line to stderr and exits with
code 2.

## Development

```bash
uv sync
uv run pytest                                    # unit + end-to-end tests
uv run ruff check && uv run ruff format --check  # lint + format
```

CI runs the same three steps on every push and pull request.

Design and planning docs live in [`docs/superpowers/`](docs/superpowers). If
you are a coding agent (or want the contributor conventions), read
[`AGENTS.md`](AGENTS.md).

## License

Licensed under the [Apache License, Version 2.0](LICENSE).
