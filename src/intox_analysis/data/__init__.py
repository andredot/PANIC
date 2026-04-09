"""
Data handling subpackage for intox_analysis.

This subpackage contains:
- pharmaceutical: Polars-based processing for large pharmaceutical datasets
- schemas: Data validation schemas and ICD code classification (requires pandera)
- generators: Synthetic data generation for testing

For large pharmaceutical files (1GB+), use the pharmaceutical module with
lazy evaluation to avoid memory issues.
"""

# Import pharmaceutical module (Polars only, no pandera dependency)
from intox_analysis.data.pharmaceutical import (
    # ATC classification
    classify_atc_code,
    ATC_BENZODIAZEPINES,
    ATC_Z_DRUGS,
    ATC_OPIOIDS,
    ATC_ANTIDEPRESSANTS,
    ATC_STIMULANTS,
    ATC_PSYCHOTROPIC_GROUPS,
    
    # Data loading (lazy/memory-efficient)
    scan_pharmaceutical_data,
    add_derived_columns,
    PHARMA_COLUMN_MAPPING,
    
    # Pre-built queries
    monthly_prescription_counts,
    identify_chronic_users,
    compute_prescribing_summary,
    
    # Synthetic data
    generate_synthetic_pharmaceutical_data,
)

__all__ = [
    # ATC classification
    "classify_atc_code",
    "ATC_BENZODIAZEPINES",
    "ATC_Z_DRUGS",
    "ATC_OPIOIDS",
    "ATC_ANTIDEPRESSANTS",
    "ATC_STIMULANTS",
    "ATC_PSYCHOTROPIC_GROUPS",
    
    # Data loading
    "scan_pharmaceutical_data",
    "add_derived_columns",
    "PHARMA_COLUMN_MAPPING",
    
    # Pre-built queries
    "monthly_prescription_counts",
    "identify_chronic_users",
    "compute_prescribing_summary",
    
    # Synthetic data
    "generate_synthetic_pharmaceutical_data",
]

# Optional imports (require additional dependencies)
try:
    from intox_analysis.data.schemas import (
        classify_drug_intoxication,
        is_drug_intoxication_icd9,
        is_drug_intoxication_icd10,
        is_missing,
        MISSING_VALUE_MARKERS,
        EDPresentation,
        EsitoED,
        Sex,
        ADMISSION_ESITO_CODES,
        COLUMN_NAME_MAPPING,
        standardise_column_names,
    )
    __all__.extend([
        "classify_drug_intoxication",
        "is_drug_intoxication_icd9",
        "is_drug_intoxication_icd10",
        "is_missing",
        "MISSING_VALUE_MARKERS",
        "EDPresentation",
        "EsitoED",
        "Sex",
        "ADMISSION_ESITO_CODES",
        "COLUMN_NAME_MAPPING",
        "standardise_column_names",
    ])
except ImportError:
    # pandera/pydantic not installed - skip schema imports
    pass
