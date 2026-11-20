import pytest

from ksplatform import KnowledgeStructure, PrerequisiteRelation, StructureError


def test_hash_ignores_order():
    one = PrerequisiteRelation(["a", "b", "c"], [("a", "b"), ("b", "c")])
    two = PrerequisiteRelation(["c", "a", "b"], [("b", "c"), ("a", "b")])
    assert one.content_hash == two.content_hash


def test_isolated_items_are_kept():
    relation = PrerequisiteRelation(["a", "b", "z"], [("a", "b")])
    assert relation.to_payload()["items"] == ["a", "b", "z"]


def test_structure_hash_ignores_order():
    one = KnowledgeStructure(["a", "b"], [[0, 0], [1, 0], [1, 1]])
    two = KnowledgeStructure(["b", "a"], [[1, 1], [0, 0], [0, 1]])
    assert one.content_hash == two.content_hash


@pytest.mark.parametrize(
    "states, message",
    [
        ([[0, 0], [1, 1], [1, 2]], "only 0 and 1"),
        ([[0, 0], [1, 1], [1]], "one value per item"),
        ([[0, 0], [1, 1], [1, 1]], "unique"),
        ([[1, 0], [1, 1]], "empty and the full state"),
    ],
)
def test_rejects_invalid_structures(states, message):
    with pytest.raises(StructureError, match=message):
        KnowledgeStructure(["a", "b"], states)


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
