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
        (
            "sections: {verse: {lines: []}}\noutline: [verse]",
            "section 'verse': expected a non-empty",
        ),
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
        ("no: '10'", "quote the word"),  # YAML reads bare no/yes/on/off as booleans
        ("123: '10'", "quote the word"),
    ],
)
def test_load_overrides_errors(tmp_path, text, message):
    with pytest.raises(DadaError, match=message):
        load_overrides(_write(tmp_path, text, "p.yaml"))
