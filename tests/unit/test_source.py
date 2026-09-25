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
        ("\ufeff[Chorus]\nsing it\n", ["sing it"]),  # UTF-8 BOM
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
