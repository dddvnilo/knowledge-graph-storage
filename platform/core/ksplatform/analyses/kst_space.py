from ..runners import RScriptRunner
from ._base import Analysis

ANALYSIS = Analysis(
    id="kst.space",
    category="build_structure",
    package="kst",
    function="kspace",
    description="Builds the knowledge space spanned by a prerequisite relation.",
    runner=RScriptRunner("kst_space.R"),
    inputs={"relation": "prerequisite_relation"},
    output_kind="knowledge_structure",
)
