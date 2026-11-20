"""The contract every analysis input fulfils.

An input is anything an analysis consumes: a response dataset, a prerequisite
relation, a knowledge space... Analyses do not care about the concrete class,
only about this contract. A new kind of input is a new class that fulfils it;
nothing existing has to change.
"""

from __future__ import annotations

import hashlib
import json
from typing import Protocol, runtime_checkable


@runtime_checkable
class AnalysisInput(Protocol):
    #: Short name of the input type, e.g. "responses" or "prerequisite_relation".
    #: Analyses declare which kinds they accept.
    kind: str

    @property
    def content_hash(self) -> str:
        """SHA-256 identifying the exact content, recorded as provenance."""

    def to_payload(self) -> dict:
        """JSON-serialisable form passed to the analysis script."""


def canonical_hash(value: object) -> str:
    """SHA-256 of a value serialised as canonical JSON (sorted keys, no spaces)."""
    text = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
