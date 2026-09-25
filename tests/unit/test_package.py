import dada_generator
from dada_generator.errors import DadaError


def test_version():
    assert dada_generator.__version__ == "0.1.0"


def test_dada_error_carries_message():
    err = DadaError("bad input")
    assert isinstance(err, Exception)
    assert str(err) == "bad input"
