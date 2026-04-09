# -*- coding: utf-8 -*-
"""
01_load_ed_data.py
==================

This script demonstrates how to load and explore ED (Emergency Department)
presentation data. It shows:

1. How to load CSV data with pandas
2. How to rename columns to standardised names
3. How to filter for drug intoxication cases
4. How to explore the data structure and quality

BEFORE RUNNING: Place your ED data extract in the data/raw/ folder
and update the filename below.
"""

import sys
from pathlib import Path

# Add project root to Python path (so imports work)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np

# Import our classification functions
from intox_analysis.data.schemas import (
    classify_drug_intoxication,
    is_drug_intoxication_icd9,
    is_drug_intoxication_icd10,
    is_missing,
    ED_COLUMN_MAPPING,
)

# =============================================================================
# CONFIGURATION - UPDATE THESE FOR YOUR DATA
# =============================================================================

# Path to your ED data extract (update this filename!)
DATA_DIR = project_root / "data" / "raw"
ED_FILE = DATA_DIR / "ed_presentations.csv"  # <-- CHANGE THIS

# If your CSV uses a different delimiter or encoding, adjust here
CSV_PARAMS = {
    "sep": ",",           # Use ";" if semicolon-separated
    "encoding": "utf-8",  # Try "latin-1" or "cp1252" if utf-8 fails
}

# =============================================================================
# STEP 1: LOAD THE DATA
# =============================================================================

print("=" * 70)
print("STEP 1: Loading ED Data")
print("=" * 70)

# Check if file exists
if not ED_FILE.exists():
    print(f"\n⚠ File not found: {ED_FILE}")
    print("\nTo proceed:")
    print("1. Export your ED data from the VDI as a CSV file")
    print("2. Copy it to:", DATA_DIR)
    print("3. Update ED_FILE variable above with the correct filename")
    print("4. Re-run this script")
    
    # For demonstration, create a small sample dataset
    print("\n" + "-" * 40)
    print("Creating sample data for demonstration...")
    print("-" * 40)
    
    sample_data = {
        "Codice Fiscale Assistito MICROBIO": [
            "MB-0643EBF4C0B837E4F239756CA2C1F5C80D67FF1E0A79413D13954A56F7F03E97",
            "MB-1234567890ABCDEF1234567890ABCDEF1234567890ABCDEF1234567890ABCDEF",
            "MB-ABCDEF1234567890ABCDEF1234567890ABCDEF1234567890ABCDEF12345678",
        ],
        "Annomese_INGR": ["201907", "202003", "202106"],
        "Eta(calcolata)": [16, 45, 32],
        "Eta (flusso)": ["2856", "4521", "3890"],
        "Sesso (anag ass.to)": ["F", "M", "F"],
        "Sesso (flusso)": ["F", "M", "F"],
        "Cod Diagnosi": ["30750", "9694", "T424X2A"],
        "Diagnosi": [
            "DISTURBO DELL'ALIMENTAZIONE NON SPECIFICATO",
            "POISONING BY BENZODIAZEPINE TRANQUILIZERS",
            "POISONING BY BENZODIAZEPINES, INTENTIONAL SELF-HARM",
        ],
        "Cod Diagnosi Secondaria": ["_", "3004", "F329"],
        "Diagnosi Secondaria": ["DATO NON APPLICABILE", "ANXIETY STATE", "DEPRESSION"],
        "Codice Esito": ["1", "2", "1"],
        "Descrizione Esito": ["DIMISSIONE A DOMICILIO", "RICOVERO ORDINARIO", "DIMISSIONE A DOMICILIO"],
        "Codice Nazione(flusso)": ["100", "100", "100"],
        "Conteggio Persone fisiche": [1, 1, 1],
    }
    df = pd.DataFrame(sample_data)
    print(f"Created sample dataset with {len(df)} rows")

else:
    # Load the actual data
    print(f"\nLoading: {ED_FILE}")
    df = pd.read_csv(ED_FILE, **CSV_PARAMS)
    print(f"Loaded {len(df):,} rows and {len(df.columns)} columns")

# Show the columns
print(f"\nColumns in dataset:")
for col in df.columns:
    print(f"  • {col}")

# =============================================================================
# STEP 2: STANDARDISE COLUMN NAMES
# =============================================================================

print("\n" + "=" * 70)
print("STEP 2: Standardising Column Names")
print("=" * 70)

# Create a copy with standardised names
df_std = df.rename(columns=ED_COLUMN_MAPPING)

print("\nColumn mapping applied:")
for old, new in ED_COLUMN_MAPPING.items():
    if old in df.columns:
        print(f"  {old}  →  {new}")

# =============================================================================
# STEP 3: BASIC DATA EXPLORATION
# =============================================================================

print("\n" + "=" * 70)
print("STEP 3: Data Exploration")
print("=" * 70)

# Date range
if "year_month" in df_std.columns:
    date_col = df_std["year_month"].astype(str)
    print(f"\nDate range: {date_col.min()} to {date_col.max()}")

# Age distribution
if "age_years" in df_std.columns:
    age = pd.to_numeric(df_std["age_years"], errors="coerce")
    print(f"\nAge distribution:")
    print(f"  Mean: {age.mean():.1f} years")
    print(f"  Median: {age.median():.1f} years")
    print(f"  Range: {age.min():.0f} to {age.max():.0f} years")
    print(f"  Missing: {age.isna().sum():,} ({100*age.isna().mean():.1f}%)")

# Sex distribution
if "sex_registry" in df_std.columns:
    print(f"\nSex distribution:")
    sex_counts = df_std["sex_registry"].value_counts()
    for sex, count in sex_counts.items():
        print(f"  {sex}: {count:,} ({100*count/len(df_std):.1f}%)")

# Disposition (Esito) distribution
if "disposition_code" in df_std.columns:
    print(f"\nDisposition distribution:")
    esito_counts = df_std["disposition_code"].value_counts()
    for code, count in esito_counts.head(10).items():
        # Try to get description
        desc = df_std[df_std["disposition_code"] == code]["disposition_desc"].iloc[0] if "disposition_desc" in df_std.columns else ""
        print(f"  {code}: {count:,} ({100*count/len(df_std):.1f}%) - {desc[:50]}")

# =============================================================================
# STEP 4: IDENTIFY DRUG INTOXICATION CASES
# =============================================================================

print("\n" + "=" * 70)
print("STEP 4: Identifying Drug Intoxication Cases")
print("=" * 70)

# Apply classification to each row
def check_intoxication(row):
    """Check primary and secondary diagnosis for drug intoxication."""
    # Check primary diagnosis
    primary = row.get("diagnosis_code_primary", "")
    if primary and not is_missing(primary):
        result = classify_drug_intoxication(str(primary))
        if result["is_intoxication"]:
            return result
    
    # Check secondary diagnosis
    secondary = row.get("diagnosis_code_secondary", "")
    if secondary and not is_missing(secondary):
        result = classify_drug_intoxication(str(secondary))
        if result["is_intoxication"]:
            return result
    
    return {"is_intoxication": False, "drug_class": None, "intent": None}

# Apply to all rows (this may take a moment for large datasets)
print("\nClassifying diagnoses... ", end="", flush=True)
classifications = df_std.apply(check_intoxication, axis=1, result_type="expand")
print("Done!")

# Add classification columns to dataframe
df_std["is_intoxication"] = classifications["is_intoxication"]
df_std["drug_class"] = classifications["drug_class"]
df_std["intent"] = classifications["intent"]

# Summary statistics
n_intox = df_std["is_intoxication"].sum()
print(f"\nDrug intoxication cases found: {n_intox:,} ({100*n_intox/len(df_std):.2f}%)")

# Drug class breakdown
if n_intox > 0:
    print(f"\nDrug class distribution (among intoxication cases):")
    class_counts = df_std[df_std["is_intoxication"]]["drug_class"].value_counts()
    for drug_class, count in class_counts.items():
        print(f"  {drug_class}: {count:,} ({100*count/n_intox:.1f}%)")
    
    # Intent breakdown (ICD-10 only)
    print(f"\nIntent distribution (ICD-10 cases only):")
    intent_counts = df_std[df_std["is_intoxication"]]["intent"].value_counts(dropna=False)
    for intent, count in intent_counts.items():
        intent_str = intent if intent else "(not specified / ICD-9)"
        print(f"  {intent_str}: {count:,}")

# =============================================================================
# STEP 5: CREATE MONTHLY TIME SERIES
# =============================================================================

print("\n" + "=" * 70)
print("STEP 5: Monthly Intoxication Counts")
print("=" * 70)

# Filter to intoxication cases only
df_intox = df_std[df_std["is_intoxication"]].copy()

if len(df_intox) > 0 and "year_month" in df_intox.columns:
    # Monthly counts
    monthly = df_intox.groupby("year_month").size().reset_index(name="n_intoxications")
    monthly = monthly.sort_values("year_month")
    
    print(f"\nMonthly intoxication counts (first 12 months):")
    print(monthly.head(12).to_string(index=False))
    
    print(f"\n... (showing first 12 of {len(monthly)} months)")
    print(f"\nOverall: {monthly['n_intoxications'].sum():,} intoxication presentations")
    print(f"Monthly average: {monthly['n_intoxications'].mean():.1f}")
    print(f"Monthly range: {monthly['n_intoxications'].min()} to {monthly['n_intoxications'].max()}")

# =============================================================================
# STEP 6: SAVE PROCESSED DATA (optional)
# =============================================================================

print("\n" + "=" * 70)
print("STEP 6: Save Processed Data")
print("=" * 70)

output_dir = project_root / "data" / "processed"
output_dir.mkdir(parents=True, exist_ok=True)

# Save intoxication cases
output_file = output_dir / "ed_intoxications.csv"
# Uncomment the next line to save:
# df_intox.to_csv(output_file, index=False)
print(f"\nTo save intoxication cases, uncomment the save line above.")
print(f"Output would be saved to: {output_file}")

print("\n" + "=" * 70)
print("DONE! You can now explore df_std and df_intox in the Variable Explorer.")
print("=" * 70)
