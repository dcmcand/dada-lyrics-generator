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
