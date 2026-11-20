import pytest

from conftest import requires_r
from ksplatform import AnalysisError, ResponseDataset, run_analysis

pytestmark = requires_r


@pytest.fixture(scope="module")
def chain_run(chain_dataset):
    return run_analysis("daks.iita", {"responses": chain_dataset})


def test_finds_chain_in_platform_direction(chain_run):
    pairs = {tuple(pair) for pair in chain_run.result["pairs"]}
    assert pairs == {("a", "b"), ("b", "c"), ("a", "c")}


def test_result_keeps_all_items(chain_run):
    assert chain_run.result["items"] == ["a", "b", "c", "d"]
    assert chain_run.result["relation_form"] == "transitive_closure"


def test_run_records_provenance(chain_run, chain_dataset):
    assert chain_run.package == "DAKS"
    assert chain_run.output_kind == "prerequisite_relation"
    assert chain_run.params == {"version": 2}
    assert chain_run.environment["packages"]["DAKS"]
    assert chain_run.environment["r_version"]
    assert chain_run.input_hashes == {"responses": chain_dataset.content_hash}


def test_invalid_version_is_reported():
    dataset = ResponseDataset.from_csv_bytes(b"a,b\n1,0\n1,1\n0,0\n")
    with pytest.raises(AnalysisError, match="version"):
        run_analysis("daks.iita", {"responses": dataset}, {"version": 7})
