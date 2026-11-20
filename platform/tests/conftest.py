import shutil
from pathlib import Path

import pytest

from ksplatform import KnowledgeStructure, PrerequisiteRelation, ResponseDataset

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "data"

requires_r = pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript is not installed")


@pytest.fixture(scope="session")
def chain_dataset():
    # Simulated data: a is a prerequisite of b, b of c; d is independent.
    return ResponseDataset.from_csv_file(EXAMPLES / "chain_example.csv")


def chain_states(order):
    """States of a chain over `order` (first item easiest) with an independent d."""
    rows = []
    for length in range(len(order) + 1):
        for d in (0, 1):
            solved = set(order[:length]) | ({"d"} if d else set())
            rows.append([int(item in solved) for item in ["a", "b", "c", "d"]])
    return rows


@pytest.fixture(scope="session")
def true_structure():
    """The structure the example data was simulated from: a -> b -> c, d independent."""
    return KnowledgeStructure(["a", "b", "c", "d"], chain_states(["a", "b", "c"]))


@pytest.fixture(scope="session")
def reversed_structure():
    """A deliberately wrong structure: c -> b -> a."""
    return KnowledgeStructure(["a", "b", "c", "d"], chain_states(["c", "b", "a"]))


@pytest.fixture(scope="session")
def chain_relation():
    return PrerequisiteRelation(["a", "b", "c", "d"], [("a", "b"), ("b", "c")])
