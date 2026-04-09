"""
Project Configuration
=====================

Central configuration for the PANIC (Drug Intoxication Analysis) project.
Update the paths below to match your VDI environment.

Usage:
    from config import DATA_DIR, OUTPUT_DIR, STUDY_PERIOD
"""

from pathlib import Path

# =============================================================================
# DIRECTORY PATHS
# =============================================================================

# Project root (this folder)
PROJECT_DIR = Path(__file__).parent

# Data directories
DATA_DIR = PROJECT_DIR / "data" / "raw"
LOOKUPS_DIR = PROJECT_DIR / "data" / "lookups"
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"

# Output directories
OUTPUT_DIR = PROJECT_DIR / "outputs"
FIGURES_DIR = OUTPUT_DIR / "figures"
TABLES_DIR = OUTPUT_DIR / "tables"


# =============================================================================
# DATA FILE PATHS
# =============================================================================

# ED presentation data
ED_DATA_FILE = DATA_DIR / "ed_presentations.csv"

# Pharmaceutical data
# Option 1: Single synthetic file (from generator)
PHARMA_SYNTHETIC_FILE = DATA_DIR / "pharma_synthetic.csv"

# Option 2: One file per year (from VDI)
PHARMA_FILES = [
    DATA_DIR / "pharma_2017.csv",
    DATA_DIR / "pharma_2018.csv",
    DATA_DIR / "pharma_2019.csv",
    DATA_DIR / "pharma_2020.csv",
    DATA_DIR / "pharma_2021.csv",
    DATA_DIR / "pharma_2022.csv",
    DATA_DIR / "pharma_2023.csv",
    DATA_DIR / "pharma_2024.csv",
    DATA_DIR / "pharma_2025.csv",
]

# Only include files that exist
PHARMA_FILES_EXISTING = [f for f in PHARMA_FILES if f.exists()]

# FUA lookup for urban/rural classification (ISTAT public data)
FUA_LOOKUP_FILE = LOOKUPS_DIR / "istat_fua_comuni.csv"


# =============================================================================
# STUDY PARAMETERS
# =============================================================================

# Study period
STUDY_START_YEAR = 2017
STUDY_END_YEAR = 2025
STUDY_PERIOD = (STUDY_START_YEAR, STUDY_END_YEAR)

# COVID-19 interruption point for segmented regression
# March 2020 = first lockdown in Italy
COVID_INTERRUPTION_DATE = "2020-03"
COVID_INTERRUPTION_MONTH = 39  # Months since Jan 2017 (0-indexed: March 2020 = month 38)

# Age groups for stratified analysis
AGE_GROUPS = {
    "0-17": (0, 17),
    "18-34": (18, 34),
    "35-54": (35, 54),
    "55-74": (55, 74),
    "75+": (75, 150),
}

# Drug classes of primary interest
PRIMARY_DRUG_CLASSES = [
    "benzodiazepine",
    "z_drug",
    "opioid",
    "antidepressant",
    "stimulant",
]


# =============================================================================
# COLUMN NAME MAPPINGS (from VDI to standardised names)
# =============================================================================

# ED data column mapping (Italian VDI names → English analysis names)
ED_COLUMN_MAPPING = {
    "Codice Fiscale Assistito MICROBIO": "patient_id",
    "Annomese_INGR": "year_month",
    "Eta(calcolata)": "age_years",
    "Eta (flusso)": "age_flow",  # Don't use this - encoding unclear
    "Sesso (anag ass.to)": "sex_registry",
    "Sesso (flusso)": "sex_flow",
    "Cod Diagnosi": "diagnosis_code_primary",
    "Diagnosi": "diagnosis_desc_primary",
    "Cod Diagnosi Secondaria": "diagnosis_code_secondary",
    "Diagnosi Secondaria": "diagnosis_desc_secondary",
    "Codice Esito": "disposition_code",
    "Descrizione Esito": "disposition_desc",
    "Codice Nazione(flusso)": "nationality_code",
    "Conteggio Persone fisiche": "count",
    # New fields (added in updated extract)
    "facility_id": "facility_id",
    "residence": "residence",
}

# Pharmaceutical data column mapping
PHARMA_COLUMN_MAPPING = {
    "Codice Fiscale Assistito MICROBIO": "patient_id",
    "Eta Anni": "age_years",
    "Sesso": "sex",
    "Data Prescrizione.Data": "prescription_date",
    "Data Erogazione.Data": "dispensing_date",
    "Cod Atc": "atc_code",
    "Desc Atc": "drug_name",
    "Cod Tipo Medico": "prescriber_type_code",
    "Desc Tipo Medico": "prescriber_type_desc",
    "DDD": "ddd",
}


# =============================================================================
# HELPER FUNCTION
# =============================================================================

def check_setup():
    """Print setup status for debugging."""
    print("=" * 60)
    print("PANIC - CONFIGURATION STATUS")
    print("=" * 60)
    
    print(f"\nProject: {PROJECT_DIR}")
    print(f"  Exists: {'✓' if PROJECT_DIR.exists() else '✗'}")
    
    print(f"\nData directory: {DATA_DIR}")
    if DATA_DIR.exists():
        files = list(DATA_DIR.glob("*.csv"))
        print(f"  CSV files: {len(files)}")
        for f in files[:5]:
            size_mb = f.stat().st_size / (1024 * 1024)
            print(f"    • {f.name} ({size_mb:.1f} MB)")
        if len(files) > 5:
            print(f"    ... and {len(files) - 5} more")
    else:
        print("  (not created yet)")
    
    print(f"\nLookups directory: {LOOKUPS_DIR}")
    if LOOKUPS_DIR.exists():
        files = list(LOOKUPS_DIR.glob("*.csv"))
        print(f"  CSV files: {len(files)}")
        for f in files:
            print(f"    • {f.name}")
    else:
        print("  (not created yet)")
    
    print(f"\nKey files:")
    print(f"  ED data:        {'✓' if ED_DATA_FILE.exists() else '✗'} {ED_DATA_FILE.name}")
    print(f"  Pharma synth:   {'✓' if PHARMA_SYNTHETIC_FILE.exists() else '✗'} {PHARMA_SYNTHETIC_FILE.name}")
    print(f"  FUA lookup:     {'✓' if FUA_LOOKUP_FILE.exists() else '✗'} {FUA_LOOKUP_FILE.name}")
    print(f"  Pharma (VDI):   {len(PHARMA_FILES_EXISTING)} of {len(PHARMA_FILES)} files")
    
    print(f"\nOutput directory: {OUTPUT_DIR}")
    print(f"  Exists: {'✓' if OUTPUT_DIR.exists() else '✗'}")
    if FIGURES_DIR.exists():
        figs = list(FIGURES_DIR.glob("*.png"))
        print(f"  Figures: {len(figs)}")
    if TABLES_DIR.exists():
        tabs = list(TABLES_DIR.glob("*.csv"))
        print(f"  Tables: {len(tabs)}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    check_setup()
