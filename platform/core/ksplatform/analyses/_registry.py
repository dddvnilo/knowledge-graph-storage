"""Discovers analyses and runs them.

Every module in this package whose name does not start with "_" and that
defines a module-level `ANALYSIS` is registered automatically. Adding an
analysis means adding a module; no existing file is edited.
"""

from __future__ import annotations

import importlib
import pkgutil
import platform
from datetime import datetime, timezone
from functools import cache

from ..inputs import AnalysisInput
from ._base import Analysis, AnalysisRun


@cache
def _discover() -> dict[str, Analysis]:
    package = importlib.import_module(__package__)
    found: dict[str, Analysis] = {}
    for module_info in pkgutil.iter_modules(package.__path__):
        if module_info.name.startswith("_"):
            continue
        module = importlib.import_module(f"{__package__}.{module_info.name}")
        analysis = getattr(module, "ANALYSIS", None)
        if not isinstance(analysis, Analysis):
            continue
        if analysis.id in found:
            raise RuntimeError(f"Duplicate analysis id: {analysis.id}")
        found[analysis.id] = analysis
    return found


def list_analyses(category: str | None = None) -> list[Analysis]:
    """All analyses, or only those answering one category of question."""
    analyses = sorted(_discover().values(), key=lambda analysis: analysis.id)
    if category is not None:
        analyses = [analysis for analysis in analyses if analysis.category == category]
    return analyses


def get_analysis(analysis_id: str) -> Analysis:
    try:
        return _discover()[analysis_id]
    except KeyError:
        available = ", ".join(sorted(_discover()))
        raise ValueError(f"Unknown analysis: {analysis_id}. Available: {available}") from None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_analysis(analysis_id: str, inputs: dict[str, AnalysisInput], params: dict | None = None) -> AnalysisRun:
    """Run an analysis on named inputs, e.g. {"responses": dataset}."""
    analysis = get_analysis(analysis_id)

    if set(inputs) != set(analysis.inputs):
        raise ValueError(f"{analysis.id} expects inputs {sorted(analysis.inputs)}, got {sorted(inputs)}.")
    for name, expected_kind in analysis.inputs.items():
        if inputs[name].kind != expected_kind:
            raise ValueError(f"Input '{name}' must be of kind '{expected_kind}', got '{inputs[name].kind}'.")

    effective_params = {**analysis.default_params, **(params or {})}
    payload = {name: value.to_payload() for name, value in inputs.items()}
    payload["params"] = effective_params

    started_at = _now()
    output = analysis.runner.run(payload)
    finished_at = _now()

    return AnalysisRun(
        analysis_id=analysis.id,
        package=analysis.package,
        function=analysis.function,
        output_kind=analysis.output_kind,
        params=effective_params,
        input_hashes={name: value.content_hash for name, value in inputs.items()},
        started_at=started_at,
        finished_at=finished_at,
        environment={"platform_python": platform.python_version(), **output.environment},
        result=output.result,
    )
