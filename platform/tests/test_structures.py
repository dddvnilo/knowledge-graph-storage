import pytest

from ksplatform import PrerequisiteRelation, StructureError


def test_hash_ignores_order():
    one = PrerequisiteRelation(["a", "b", "c"], [("a", "b"), ("b", "c")])
    two = PrerequisiteRelation(["c", "a", "b"], [("b", "c"), ("a", "b")])
    assert one.content_hash == two.content_hash


def test_isolated_items_are_kept():
    relation = PrerequisiteRelation(["a", "b", "z"], [("a", "b")])
    assert relation.to_payload()["items"] == ["a", "b", "z"]


@pytest.mark.parametrize(
    "items, pairs, message",
    [
        (["a", "a"], [], "unique"),
        (["a", "b"], [("a", "x")], "unknown item"),
        (["a", "b"], [("a", "a")], "Reflexive"),
    ],
)
def test_rejects_inconsistent_relations(items, pairs, message):
    with pytest.raises(StructureError, match=message):
        PrerequisiteRelation(items, pairs)
