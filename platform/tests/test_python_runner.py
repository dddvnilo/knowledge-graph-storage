import pytest

from ksplatform.runners import AnalysisError, PythonRunner


def count_items(payload):
    return {"n_items": len(payload["responses"]["items"])}


def test_runs_function_and_records_versions():
    output = PythonRunner(count_items, packages=("pytest",)).run({"responses": {"items": ["a", "b"]}})
    assert output.result == {"n_items": 2}
    assert output.environment["packages"]["pytest"]
    assert output.environment["python_version"]


def test_errors_are_reported_as_analysis_errors():
    with pytest.raises(AnalysisError, match="count_items"):
        PythonRunner(count_items).run({})
