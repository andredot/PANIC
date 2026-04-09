"""
Data handling subpackage.

This subpackage contains:
- schemas: ICD code classification and data validation
- pharmaceutical: Polars-based pharmaceutical data processing
"""

# Simple imports that work without external dependencies
from intox_analysis.data import schemas
from intox_analysis.data import pharmaceutical

__all__ = ["schemas", "pharmaceutical"]
