from conftest import FIXTURES


def _run(run_dada, seed):
    return run_dada("generate", FIXTURES / "simple.yaml", FIXTURES / "mixed.txt", "--seed", seed)


def test_same_seed_is_identical(run_dada):
    first, second = _run(run_dada, 7), _run(run_dada, 7)
    assert first.returncode == second.returncode == 0
    assert first.stdout == second.stdout


def test_different_seed_differs(run_dada):
    assert _run(run_dada, 7).stdout != _run(run_dada, 8).stdout
