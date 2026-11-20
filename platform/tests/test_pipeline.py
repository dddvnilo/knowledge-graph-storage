"""The full path a user takes: data -> structure -> fit, across packages."""

from conftest import requires_r
from ksplatform import KnowledgeStructure, PrerequisiteRelation, run_analysis

pytestmark = requires_r


def test_derive_build_and_check_fit(chain_dataset):
    iita = run_analysis("daks.iita", {"responses": chain_dataset})
    relation = PrerequisiteRelation.from_payload(iita.result)

    space = run_analysis("kst.space", {"relation": relation})
    structure = KnowledgeStructure.from_payload(space.result)
    assert len(structure.states) == 8

    validation = run_analysis("kst.validate", {"structure": structure, "responses": chain_dataset})
    blim = run_analysis("pks.blim", {"structure": structure, "responses": chain_dataset})

    assert validation.result["gamma"] > 0.8
    assert sum(blim.result["state_probabilities"]) > 0.99
    # each step records the exact input it used, so the chain can be traced back
    assert validation.input_hashes["structure"] == structure.content_hash
    assert blim.input_hashes["responses"] == chain_dataset.content_hash
