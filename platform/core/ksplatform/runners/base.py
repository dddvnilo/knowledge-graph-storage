"""The contract between analyses and the code that executes them."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class AnalysisError(RuntimeError):
    """Raised when an analysis fails or reports an error."""


@dataclass(frozen=True)
class RunnerOutput:
    result: dict
    #: Language and package versions, recorded as provenance,
    #: e.g. {"r_version": "4.4.2", "packages": {"DAKS": "2.1.3"}}.
    environment: dict


class Runner(ABC):
    """Executes one analysis on a JSON-serialisable payload.

    Each language or execution style (Rscript, an in-process Python function,
    later perhaps an R service) is one subclass. Analyses only hold a runner;
    adding a new way of running code never touches existing analyses.
    """

    @abstractmethod
    def run(self, payload: dict) -> RunnerOutput: ...
