"""Core of the KST platform: inputs, analyses and the runners that execute them.

This package does not depend on any web framework, so the same code can sit
behind Django, FastAPI or a command line.
"""

from .analyses import CATEGORIES, Analysis, AnalysisRun, get_analysis, list_analyses, run_analysis
from .datasets import DatasetError, ResponseDataset
from .runners import AnalysisError
from .structures import KnowledgeStructure, PrerequisiteRelation, StructureError

__all__ = [
    "CATEGORIES",
    "Analysis",
    "AnalysisError",
    "AnalysisRun",
    "DatasetError",
    "KnowledgeStructure",
    "PrerequisiteRelation",
    "ResponseDataset",
    "StructureError",
    "get_analysis",
    "list_analyses",
    "run_analysis",
]
