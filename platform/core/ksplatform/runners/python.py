"""Runs analyses implemented as Python functions (e.g. on top of learning_spaces)."""

from __future__ import annotations

import platform
from collections.abc import Callable
from importlib.metadata import PackageNotFoundError, version

from .base import AnalysisError, Runner, RunnerOutput


class PythonRunner(Runner):
    """Calls `function(payload) -> result dict` in-process.

    `packages` are the distributions whose versions belong to the provenance
    of the result.
    """

    def __init__(self, function: Callable[[dict], dict], packages: tuple[str, ...] = ()) -> None:
        self.function = function
        self.packages = packages

    def run(self, payload: dict) -> RunnerOutput:
        try:
            result = self.function(payload)
        except Exception as error:  # report any failure the same way as R scripts do
            raise AnalysisError(f"{self.function.__name__}: {error}") from error
        return RunnerOutput(result=result, environment=self._environment())

    def _environment(self) -> dict:
        packages = {}
        for name in self.packages:
            try:
                packages[name] = version(name)
            except PackageNotFoundError:
                packages[name] = None
        return {"python_version": platform.python_version(), "packages": packages}
