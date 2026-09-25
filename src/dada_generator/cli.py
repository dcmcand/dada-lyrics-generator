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
        help='YAML file of word: stress overrides, e.g. runnin\': "10"',
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
