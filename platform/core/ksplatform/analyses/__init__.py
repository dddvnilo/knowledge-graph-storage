"""Available analyses: one module per analysis, discovered automatically.

See docs/adding-an-analysis.md.
"""

from ._base import CATEGORIES, Analysis, AnalysisRun
from ._registry import get_analysis, list_analyses, run_analysis

__all__ = ["CATEGORIES", "Analysis", "AnalysisRun", "get_analysis", "list_analyses", "run_analysis"]
