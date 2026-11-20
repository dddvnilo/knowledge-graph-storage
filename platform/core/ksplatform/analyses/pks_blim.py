from ..runners import RScriptRunner
from ._base import Analysis

ANALYSIS = Analysis(
    id="pks.blim",
    category="data_fit",
    package="pks",
    function="blim",
    description=(
        "Fits a basic local independence model: careless error and lucky guess "
        "probabilities per item, state probabilities, and model fit (G2, AIC, BIC)."
    ),
    runner=RScriptRunner("pks_blim.R"),
    inputs={"structure": "knowledge_structure", "responses": "responses"},
    output_kind="blim_fit",
    # method: "ML" (maximum likelihood), "MD" (minimum discrepancy) or "MDML"
    default_params={"method": "ML"},
)
