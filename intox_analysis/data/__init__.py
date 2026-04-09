"""
Data handling subpackage.

This subpackage contains:
- schemas: ICD code classification and data validation
- pharmaceutical: Polars-based pharmaceutical data processing
- residence: Urban/rural classification using ISTAT FUA
- generators: Synthetic data generation for testing
"""

# Import modules that don't have heavy dependencies
from intox_analysis.data import schemas
from intox_analysis.data import residence
from intox_analysis.data import generators

# Try to import pharmaceutical (requires Polars)
try:
    from intox_analysis.data import pharmaceutical
    __all__ = ["schemas", "pharmaceutical", "residence", "generators"]
except ImportError:
    # Polars not installed - pharmaceutical module unavailable
    __all__ = ["schemas", "residence", "generators"]
