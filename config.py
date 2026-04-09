"""
Project Configuration
=====================

Central configuration for the Lombardy Drug Intoxication Analysis project.
Update the paths below to match your VDI environment.

Usage:
    from config import DATA_DIR, OUTPUT_DIR, STUDY_PERIOD
"""

from pathlib import Path

# =============================================================================
# DIRECTORY PATHS - UPDATE THESE FOR YOUR VDI ENVIRONMENT
# =============================================================================

# Project root (this folder)
PROJECT_DIR = Path(__file__).parent

# Where your raw data extracts are stored
DATA_DIR = PROJECT_DIR / "data" / "raw"

# Where processed/intermediate files go
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"

# Where outputs (figures, tables) are saved
OUTPUT_DIR = PROJECT_DIR / "outputs"
FIGURES_DIR = OUTPUT_DIR / "figures"
TABLES_DIR = OUTPUT_DIR / "tables"


# =============================================================================
# DATA FILE PATHS - UPDATE THESE TO MATCH YOUR FILENAMES
# =============================================================================

# ED presentation data
# (update with your actual filename from the VDI extract)
ED_DATA_FILE = DATA_DIR / "ed_presentations.csv"

# Pharmaceutical data (one file per year)
# Update these paths to match your actual files
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
    # Add DDD column when available
    # "DDD": "ddd",
}


# =============================================================================
# HELPER FUNCTION
# =============================================================================

def check_setup():
    """Print setup status for debugging."""
    print("=" * 60)
    print("PROJECT CONFIGURATION STATUS")
    print("=" * 60)
    print(f"Project directory: {PROJECT_DIR}")
    print(f"  Exists: {PROJECT_DIR.exists()}")
    print()
    print(f"Data directory: {DATA_DIR}")
    print(f"  Exists: {DATA_DIR.exists()}")
    if DATA_DIR.exists():
        files = list(DATA_DIR.glob("*"))
        print(f"  Files found: {len(files)}")
        for f in files[:5]:
            print(f"    - {f.name}")
        if len(files) > 5:
            print(f"    ... and {len(files) - 5} more")
    print()
    print(f"ED data file: {ED_DATA_FILE}")
    print(f"  Exists: {ED_DATA_FILE.exists()}")
    print()
    print(f"Pharmaceutical files configured: {len(PHARMA_FILES)}")
    print(f"Pharmaceutical files existing: {len(PHARMA_FILES_EXISTING)}")
    for f in PHARMA_FILES_EXISTING:
        print(f"  ✓ {f.name}")
    print()
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"  Exists: {OUTPUT_DIR.exists()}")
    print("=" * 60)


if __name__ == "__main__":
    check_setup()
