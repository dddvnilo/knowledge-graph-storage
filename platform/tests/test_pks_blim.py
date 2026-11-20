import pytest

from conftest import requires_r
from ksplatform import AnalysisError, ResponseDataset, run_analysis

pytestmark = requires_r


@pytest.fixture(scope="module")
def true_fit(true_structure, chain_dataset):
    return run_analysis("pks.blim", {"structure": true_structure, "responses": chain_dataset})


def test_parameters_per_item(true_fit):
    result = true_fit.result
    assert set(result["beta"]) == set(result["eta"]) == {"a", "b", "c", "d"}
    assert all(0 <= value <= 1 for value in [*result["beta"].values(), *result["eta"].values()])


def test_state_probabilities_follow_input_states(true_fit, true_structure):
    probabilities = true_fit.result["state_probabilities"]
    assert len(probabilities) == len(true_structure.states)
    assert sum(probabilities) == pytest.approx(1, abs=1e-6)


def test_true_structure_has_small_error_rates(true_fit):
    # The data was simulated with about 5 % noise.
    assert all(value < 0.15 for value in true_fit.result["beta"].values())
    assert all(value < 0.15 for value in true_fit.result["eta"].values())


def test_wrong_structure_needs_implausible_error_rates(reversed_structure, chain_dataset):
    # With 4 items and 8 states the model is saturated, so the likelihood alone cannot
    # tell the structures apart; the wrong one shows up as a very high error rate.
    result = run_analysis("pks.blim", {"structure": reversed_structure, "responses": chain_dataset}).result
    assert max([*result["beta"].values(), *result["eta"].values()]) > 0.3


def test_fit_statistics_and_provenance(true_fit):
    result = true_fit.result
    assert result["method"] == "ML"
    assert result["n_respondents"] == 200
    assert result["aic"] == pytest.approx(-2 * result["loglik"] + 2 * result["npar"])
    assert true_fit.environment["packages"]["pks"]
    assert set(true_fit.input_hashes) == {"structure", "responses"}


def test_response_column_order_does_not_matter(true_structure, chain_dataset):
    # pks matches columns by position; the script must reorder them by name.
    items = chain_dataset.items[::-1]
    rows = [[row[chain_dataset.items.index(item)] for item in items] for row in chain_dataset.responses]
    data = ",".join(items) + "\n" + "\n".join(",".join(map(str, row)) for row in rows) + "\n"
    shuffled = ResponseDataset.from_csv_bytes(data.encode())

    original = run_analysis("pks.blim", {"structure": true_structure, "responses": chain_dataset}).result
    reordered = run_analysis("pks.blim", {"structure": true_structure, "responses": shuffled}).result
    assert reordered["beta"] == pytest.approx(original["beta"], abs=1e-4)
    assert reordered["loglik"] == pytest.approx(original["loglik"])


def test_invalid_method(true_structure, chain_dataset):
    with pytest.raises(AnalysisError, match="method"):
        run_analysis("pks.blim", {"structure": true_structure, "responses": chain_dataset}, {"method": "XYZ"})
