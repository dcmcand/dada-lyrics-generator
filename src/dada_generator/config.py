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
        text = Path(path).read_text(encoding="utf-8-sig")
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
        if not isinstance(word, str):
            raise DadaError(
                f'{path}: override key {word!r} is not a word; quote the word, e.g. "no": "1"'
            )
        if not isinstance(stress, str) or not _OVERRIDE_RE.fullmatch(stress):
            raise DadaError(
                f"{path}: '{word}' must map to a quoted stress string of 0/1, "
                f'e.g. "10" (got {stress!r})'
            )
        overrides[str(word)] = stress
    return overrides
