from ..runners import RScriptRunner
from ._base import Analysis

ANALYSIS = Analysis(
    id="daks.iita",
    category="derive_structure",
    package="DAKS",
    function="iita",
    description="Inductive item tree analysis: derives a prerequisite relation from response data.",
    runner=RScriptRunner("daks_iita.R"),
    inputs={"responses": "responses"},
    output_kind="prerequisite_relation",
    # version: 1 = minimized corrected, 2 = corrected, 3 = original
    default_params={"version": 2},
)
