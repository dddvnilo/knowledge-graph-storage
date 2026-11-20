import shutil
from pathlib import Path

import pytest

from ksplatform import ResponseDataset

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "data"

requires_r = pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript is not installed")


@pytest.fixture(scope="session")
def chain_dataset():
    # Simulated data: a is a prerequisite of b, b of c; d is independent.
    return ResponseDataset.from_csv_file(EXAMPLES / "chain_example.csv")
