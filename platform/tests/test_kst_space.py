from conftest import requires_r
from ksplatform import PrerequisiteRelation, run_analysis

pytestmark = requires_r


def states_of(run):
    items = run.result["items"]
    return {frozenset(item for item, bit in zip(items, row) if bit) for row in run.result["states"]}


def test_chain_with_isolated_item():
    relation = PrerequisiteRelation(items=["a", "b", "c", "d"], pairs=[("a", "b"), ("b", "c")])
    run = run_analysis("kst.space", {"relation": relation})

    chain = [set(), {"a"}, {"a", "b"}, {"a", "b", "c"}]
    expected = {frozenset(state | extra) for state in chain for extra in (set(), {"d"})}
    assert states_of(run) == expected
    assert run.result["items"] == ["a", "b", "c", "d"]


def test_hasse_and_closure_give_the_same_space():
    items = ["a", "b", "c"]
    hasse = PrerequisiteRelation(items, [("a", "b"), ("b", "c")], "transitive_reduction")
    closure = PrerequisiteRelation(items, [("a", "b"), ("b", "c"), ("a", "c")], "transitive_closure")
    assert states_of(run_analysis("kst.space", {"relation": hasse})) == states_of(
        run_analysis("kst.space", {"relation": closure})
    )


def test_iita_result_chains_into_kst(chain_dataset):
    iita = run_analysis("daks.iita", {"responses": chain_dataset})
    space = run_analysis("kst.space", {"relation": PrerequisiteRelation.from_payload(iita.result)})
    assert len(space.result["states"]) == 8
