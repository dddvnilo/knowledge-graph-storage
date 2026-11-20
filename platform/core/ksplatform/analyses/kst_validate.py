from ..runners import RScriptRunner
from ._base import Analysis

ANALYSIS = Analysis(
    id="kst.validate",
    category="data_fit",
    package="kst",
    function="kvalidate",
    description=(
        "How well a knowledge structure fits response data: gamma index and violational "
        "coefficient (for its prerequisite relation), discrepancy index and distance agreement."
    ),
    runner=RScriptRunner("kst_validate.R"),
    inputs={"structure": "knowledge_structure", "responses": "responses"},
    output_kind="fit_measures",
)
