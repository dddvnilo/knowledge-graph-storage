"""What an analysis is and what running one produces."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from ..runners import Runner


#: The question a user is answering with an analysis. Several packages can
#: offer the same category; the interface groups analyses by it so the user
#: picks a question first and a package second.
CATEGORIES = {
    "derive_structure": "Derive a structure from response data",
    "build_structure": "Build or transform a structure",
    "structure_properties": "Inspect properties of a structure",
    "data_fit": "Check how well a structure fits response data",
    "assessment": "Assess respondents",
    "simulation": "Simulate data",
}


@dataclass(frozen=True)
class Analysis:
    """One function of one package, made available on the platform.

    `inputs` maps each input name to the input kind it accepts, e.g.
    {"responses": "responses"} or {"relation": "prerequisite_relation"}.
    `output_kind` names what the result is, so later steps (display,
    export to the knowledge graph, chaining) can rely on it.
    """

    id: str
    category: str
    package: str
    function: str
    description: str
    runner: Runner
    inputs: dict[str, str]
    output_kind: str
    default_params: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.category not in CATEGORIES:
            raise ValueError(f"{self.id}: unknown category '{self.category}'. Known: {', '.join(CATEGORIES)}")


@dataclass
class AnalysisRun:
    """The result of a run plus everything needed to reproduce it."""

    analysis_id: str
    package: str
    function: str
    output_kind: str
    params: dict
    #: input name -> content hash of the exact input used
    input_hashes: dict[str, str]
    started_at: str
    finished_at: str
    environment: dict
    result: dict

    def to_dict(self) -> dict:
        return asdict(self)
