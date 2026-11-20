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
