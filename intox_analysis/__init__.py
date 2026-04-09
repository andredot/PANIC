"""
Intox Analysis Package
======================

Analysis tools for investigating drug intoxication trends in Lombardy EDs.

This package provides:
- Data loading and validation (intox_analysis.data)
- Statistical analysis functions (intox_analysis.analysis) [TBD]
- Visualisation utilities (intox_analysis.viz) [TBD]

Quick Start:
    from intox_analysis.data import pharmaceutical as pharma
    from intox_analysis.data import schemas
    
    # Classify an ATC code
    result = pharma.classify_atc_code("N05BA12")
    
    # Check if ICD code is a drug intoxication
    is_intox = schemas.is_drug_intoxication_icd9("9694")
"""

__version__ = "0.1.0"
