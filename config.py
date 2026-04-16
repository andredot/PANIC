# -*- coding: utf-8 -*-
"""
Project Configuration
=====================

CENTRAL CONFIGURATION for the PANIC project.
Change settings HERE and they propagate to all notebooks and modules.

Usage:
    from config import *
    # or
    from config import DATA_DIR, STUDY_PERIOD, ICD10_INTOX_CODES
"""

from pathlib import Path

# =============================================================================
# DIRECTORY PATHS
# =============================================================================

PROJECT_DIR = Path(__file__).parent
DATA_DIR = PROJECT_DIR / "data" / "raw"
LOOKUPS_DIR = PROJECT_DIR / "data" / "lookups"
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"
OUTPUT_DIR = PROJECT_DIR / "outputs"
FIGURES_DIR = OUTPUT_DIR / "figures"
TABLES_DIR = OUTPUT_DIR / "tables"


# =============================================================================
# DATA FILE PATHS
# =============================================================================

# ED presentation data
ED_DATA_FILE = DATA_DIR / "ed_presentations.csv"

# Pharmaceutical data - single synthetic file
PHARMA_SYNTHETIC_FILE = DATA_DIR / "pharma_synthetic.csv"

# Pharmaceutical data - yearly files from VDI (if available)
PHARMA_YEARLY_PATTERN = "pharma_{year}.csv"

# FUA lookup for urban/rural classification (OPTIONAL - privacy restrictions)
FUA_LOOKUP_FILE = LOOKUPS_DIR / "istat_fua_comuni.csv"
FUA_LOOKUP_AVAILABLE = FUA_LOOKUP_FILE.exists()


# =============================================================================
# STUDY PARAMETERS
# =============================================================================

STUDY_START_YEAR = 2017
STUDY_END_YEAR = 2025
STUDY_PERIOD = (STUDY_START_YEAR, STUDY_END_YEAR)
STUDY_YEARS = list(range(STUDY_START_YEAR, STUDY_END_YEAR + 1))

# COVID-19 interruption point for segmented regression
COVID_INTERRUPTION_DATE = "2020-03"
COVID_INTERRUPTION_YEAR = 2020
COVID_INTERRUPTION_MONTH = 3

# Lombardy population (approximate, for rate calculations)
LOMBARDY_POPULATION = 10_000_000


# =============================================================================
# AGE GROUPS FOR STRATIFICATION
# =============================================================================

AGE_GROUPS = {
    "0-17": (0, 17),
    "18-34": (18, 34),
    "35-54": (35, 54),
    "55-74": (55, 74),
    "75+": (75, 150),
}

AGE_GROUP_ORDER = ["0-17", "18-34", "35-54", "55-74", "75+"]


# =============================================================================
# ICD CODE DEFINITIONS - DRUG INTOXICATION
# =============================================================================

# ICD-10 codes for drug intoxication (T36-T50)
ICD10_INTOX_PREFIXES = [
    "T36",  # Systemic antibiotics
    "T37",  # Other systemic anti-infectives
    "T38",  # Hormones
    "T39",  # Nonopioid analgesics
    "T40",  # Narcotics and psychodysleptics
    "T41",  # Anaesthetics
    "T42",  # Antiepileptics, sedative-hypnotics, antiparkinsonism
    "T43",  # Psychotropic drugs
    "T44",  # Drugs affecting autonomic nervous system
    "T45",  # Systemic and haematological agents
    "T46",  # Cardiovascular drugs
    "T47",  # Gastrointestinal drugs
    "T48",  # Smooth/skeletal muscle and respiratory drugs
    "T49",  # Topical agents
    "T50",  # Diuretics and other unspecified drugs
]

# ICD-9 codes for drug intoxication (960-979)
ICD9_INTOX_RANGE = (960, 979)

# Mental health ICD-10 codes (F-codes)
ICD10_MENTAL_HEALTH_PREFIXES = ["F0", "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9"]

# Specific drug class codes - ICD-10
ICD10_BENZODIAZEPINE = "T424"
ICD10_OPIOID_PREFIXES = ["T400", "T401", "T402", "T403", "T404"]
ICD10_ANTIDEPRESSANT_PREFIXES = ["T430", "T431", "T432"]
ICD10_STIMULANT = "T436"
ICD10_COCAINE = "T405"

# Specific drug class codes - ICD-9
ICD9_BENZODIAZEPINE = "9694"
ICD9_OPIOID = "9650"
ICD9_ANTIDEPRESSANT = "9690"
ICD9_STIMULANT = "9697"


# =============================================================================
# ATC CODE DEFINITIONS - PHARMACEUTICAL
# =============================================================================

# Benzodiazepines
ATC_BENZODIAZEPINES = ["N05BA", "N05CD"]  # Anxiolytics + Hypnotics

# Z-drugs (non-benzodiazepine hypnotics)
ATC_Z_DRUGS = ["N05CF"]

# Opioids
ATC_OPIOIDS = ["N02A"]

# Antidepressants
ATC_ANTIDEPRESSANTS = ["N06A"]

# Antipsychotics
ATC_ANTIPSYCHOTICS = ["N05A"]

# Stimulants (ADHD medications)
ATC_STIMULANTS = ["N06BA"]

# All psychotropic ATC codes
ATC_PSYCHOTROPIC = ATC_BENZODIAZEPINES + ATC_Z_DRUGS + ATC_OPIOIDS + ATC_ANTIDEPRESSANTS + ATC_ANTIPSYCHOTICS + ATC_STIMULANTS

# Drug classes of primary interest
PRIMARY_DRUG_CLASSES = [
    "benzodiazepine",
    "z_drug",
    "opioid",
    "antidepressant",
    "antipsychotic",
    "stimulant",
]


# =============================================================================
# CHRONIC USER DEFINITION
# =============================================================================

# Minimum prescriptions per year to be considered chronic user
CHRONIC_USER_MIN_PRESCRIPTIONS = 4

# Maximum gap between prescriptions (days) for chronic user
CHRONIC_USER_MAX_GAP_DAYS = 90

# Lookback period for prescription-intoxication linkage (days)
PRESCRIPTION_LOOKBACK_DAYS = 365


# =============================================================================
# COLUMN NAME MAPPINGS (VDI Italian -> English)
# =============================================================================

# ED data column mapping
ED_COLUMN_MAPPING = {
    "Codice Fiscale Assistito MICROBIO": "patient_id",
    "Annomese_INGR": "year_month",
    "Eta(calcolata)": "age_years",
    "Eta (flusso)": "age_flow",
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

# Missing value conventions in VDI data
MISSING_VALUES = ["_", "DATO NON APPLICABILE", "", "NA", "N/A"]


# =============================================================================
# URBAN/RURAL CLASSIFICATION (OPTIONAL)
# =============================================================================

# Column name in FUA lookup containing municipality name
FUA_MUNICIPALITY_COLUMN = "Comune"

# Column name in FUA lookup containing city classification
FUA_CITY_COLUMN = "City (City/Greater City) 2021"

# Value indicating "no city" (rural)
FUA_NO_CITY_VALUE = "No City"


# =============================================================================
# PLOTTING SETTINGS
# =============================================================================

FIGURE_DPI = 150
FIGURE_FORMAT = "png"

# Color palette for drug classes
DRUG_CLASS_COLORS = {
    "benzodiazepine": "#1f77b4",
    "z_drug": "#ff7f0e",
    "opioid": "#d62728",
    "antidepressant": "#2ca02c",
    "antipsychotic": "#9467bd",
    "stimulant": "#8c564b",
    "other": "#7f7f7f",
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_pharma_files():
    """Get list of available pharmaceutical files."""
    files = []
    
    # Check for synthetic file first
    if PHARMA_SYNTHETIC_FILE.exists():
        files.append(PHARMA_SYNTHETIC_FILE)
    
    # Check for yearly files
    for year in STUDY_YEARS:
        yearly_file = DATA_DIR / PHARMA_YEARLY_PATTERN.format(year=year)
        if yearly_file.exists():
            files.append(yearly_file)
    
    return files


def ensure_directories():
    """Create all required directories if they don't exist."""
    for d in [DATA_DIR, LOOKUPS_DIR, PROCESSED_DIR, FIGURES_DIR, TABLES_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def check_setup():
    """Print setup status for debugging."""
    print("=" * 60)
    print("PANIC - CONFIGURATION STATUS")
    print("=" * 60)
    
    print(f"\nProject: {PROJECT_DIR}")
    
    print(f"\nData directory: {DATA_DIR}")
    if DATA_DIR.exists():
        files = list(DATA_DIR.glob("*.csv"))
        print(f"  CSV files: {len(files)}")
        for f in files[:5]:
            size_mb = f.stat().st_size / (1024 * 1024)
            print(f"    - {f.name} ({size_mb:.1f} MB)")
        if len(files) > 5:
            print(f"    ... and {len(files) - 5} more")
    else:
        print("  (not created yet)")
    
    print(f"\nLookups: {LOOKUPS_DIR}")
    print(f"  FUA lookup available: {FUA_LOOKUP_AVAILABLE}")
    
    print(f"\nKey files:")
    print(f"  ED data:      {'[OK]' if ED_DATA_FILE.exists() else '[--]'} {ED_DATA_FILE.name}")
    print(f"  Pharma:       {'[OK]' if PHARMA_SYNTHETIC_FILE.exists() else '[--]'} {PHARMA_SYNTHETIC_FILE.name}")
    
    pharma_files = get_pharma_files()
    print(f"  Pharma files: {len(pharma_files)} available")
    
    print(f"\nStudy period: {STUDY_START_YEAR}-{STUDY_END_YEAR}")
    print(f"COVID interruption: {COVID_INTERRUPTION_DATE}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    check_setup()
