import pytest

from conftest import requires_r
from ksplatform import AnalysisError, KnowledgeStructure, ResponseDataset, run_analysis

pytestmark = requires_r


@pytest.fixture(scope="module")
def true_fit(true_structure, chain_dataset):
    return run_analysis("kst.validate", {"structure": true_structure, "responses": chain_dataset}).result


@pytest.fixture(scope="module")
def reversed_fit(reversed_structure, chain_dataset):
    return run_analysis("kst.validate", {"structure": reversed_structure, "responses": chain_dataset}).result


def test_true_structure_fits_well(true_fit):
    assert true_fit["gamma"] > 0.8
    assert true_fit["vc"] < 0.05
    assert true_fit["di"] < 0.1
    assert true_fit["n_respondents"] == 200


def test_true_structure_fits_better_than_reversed(true_fit, reversed_fit):
    assert true_fit["gamma"] > reversed_fit["gamma"]
    assert true_fit["vc"] < reversed_fit["vc"]
    assert true_fit["di"] < reversed_fit["di"]
    assert true_fit["da"] < reversed_fit["da"]


def test_di_distribution_counts_every_respondent(true_fit):
    assert sum(true_fit["di_distribution"].values()) == 200


def test_response_column_order_does_not_matter(true_structure, true_fit):
    shuffled = ResponseDataset.from_csv_bytes(
        b"d,c,b,a\n" + b"\n".join(b"0,0,0,1" for _ in range(5)) + b"\n"
    )
    original = ResponseDataset.from_csv_bytes(b"a,b,c,d\n" + b"\n".join(b"1,0,0,0" for _ in range(5)) + b"\n")
    assert (
        run_analysis("kst.validate", {"structure": true_structure, "responses": shuffled}).result["di"]
        == run_analysis("kst.validate", {"structure": true_structure, "responses": original}).result["di"]
    )


def test_items_must_match(true_structure):
    other = ResponseDataset.from_csv_bytes(b"a,b,c,x\n1,0,0,0\n")
    with pytest.raises(AnalysisError, match="same items"):
        run_analysis("kst.validate", {"structure": true_structure, "responses": other})
