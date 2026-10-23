"""LinkCheck: completeness, conflict and over-count report for linked records.

MV2 of Munim, Inc. Apache-2.0. Written by AI agents (Claude) in MV2's name.
"""
from .core import RULES, __version__, check, read_jsonl, suppress, write_cohort

__all__ = ["RULES", "__version__", "check", "read_jsonl", "suppress", "write_cohort"]
