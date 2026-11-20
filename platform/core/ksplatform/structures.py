"""Knowledge structures used as analysis inputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from .inputs import canonical_hash


class StructureError(ValueError):
    """Raised when a structure is inconsistent."""


@dataclass(frozen=True)
class PrerequisiteRelation:
    """A prerequisite relation between items.

    A pair (a, b) means *a is a prerequisite of b*: whoever masters b also
    masters a. `items` lists every item, including isolated ones that appear
    in no pair. Reflexive pairs (a, a) are not stored.
    """

    kind: ClassVar[str] = "prerequisite_relation"

    items: list[str]
    pairs: list[tuple[str, str]] = field(default_factory=list)
    #: "as_given", "transitive_closure" or "transitive_reduction"
    relation_form: str = "as_given"

    def __post_init__(self) -> None:
        if len(set(self.items)) != len(self.items):
            raise StructureError("Item ids must be unique.")
        known = set(self.items)
        for a, b in self.pairs:
            if a not in known or b not in known:
                raise StructureError(f"Pair ({a}, {b}) refers to an unknown item.")
            if a == b:
                raise StructureError(f"Reflexive pair ({a}, {a}) is not allowed.")

    @property
    def content_hash(self) -> str:
        return canonical_hash({"items": sorted(self.items), "pairs": sorted(map(list, self.pairs))})

    def to_payload(self) -> dict:
        return {"items": self.items, "pairs": [list(pair) for pair in self.pairs], "relation_form": self.relation_form}

    @classmethod
    def from_payload(cls, payload: dict) -> "PrerequisiteRelation":
        """Build from an analysis result or an export with items, pairs and relation_form."""
        return cls(
            items=list(payload["items"]),
            pairs=[(a, b) for a, b in payload.get("pairs", [])],
            relation_form=payload.get("relation_form", "as_given"),
        )


@dataclass(frozen=True)
class KnowledgeStructure:
    """A knowledge structure: the family of admissible knowledge states.

    Each state is a 0/1 row over `items` (1 = the item is in the state). By
    definition a structure contains the empty state and the full state.
    A knowledge space is a knowledge structure, so it uses this class too.
    """

    kind: ClassVar[str] = "knowledge_structure"

    items: list[str]
    states: list[list[int]]

    def __post_init__(self) -> None:
        if len(set(self.items)) != len(self.items):
            raise StructureError("Item ids must be unique.")
        for row in self.states:
            if len(row) != len(self.items):
                raise StructureError(f"State {row} does not have one value per item.")
            if any(value not in (0, 1) for value in row):
                raise StructureError(f"State {row} must contain only 0 and 1.")
        rows = {tuple(row) for row in self.states}
        if len(rows) != len(self.states):
            raise StructureError("States must be unique.")
        if (0,) * len(self.items) not in rows or (1,) * len(self.items) not in rows:
            raise StructureError("A knowledge structure must contain the empty and the full state.")

    @property
    def content_hash(self) -> str:
        order = sorted(range(len(self.items)), key=lambda i: self.items[i])
        states = sorted("".join(str(row[i]) for i in order) for row in self.states)
        return canonical_hash({"items": sorted(self.items), "states": states})

    def to_payload(self) -> dict:
        return {"items": self.items, "states": self.states}

    @classmethod
    def from_payload(cls, payload: dict) -> "KnowledgeStructure":
        """Build from an analysis result or an export with items and states."""
        return cls(items=list(payload["items"]), states=[list(row) for row in payload["states"]])
