"""
Analysis subpackage.

This subpackage contains:
- trends: Trend analysis for drug intoxications and mental health diagnoses
"""

from intox_analysis.analysis.trends import (
    process_ed_data,
    run_intoxication_trend_analysis,
    run_mental_health_trend_analysis,
    classify_drug_intoxication_detailed,
    classify_mental_health,
    compute_annual_counts,
    compute_trend_metrics,
    create_trend_summary_table,
)

__all__ = [
    "process_ed_data",
    "run_intoxication_trend_analysis",
    "run_mental_health_trend_analysis",
    "classify_drug_intoxication_detailed",
    "classify_mental_health",
    "compute_annual_counts",
    "compute_trend_metrics",
    "create_trend_summary_table",
]
