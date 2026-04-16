# -*- coding: utf-8 -*-
"""
01_load_ed_data.py
==================

Load and explore ED (Emergency Department) presentation data.

This script:
1. Loads ED data from CSV (or generates synthetic data if not available)
2. Renames columns to standardised names  
3. Classifies drug intoxication cases
4. Creates basic exploratory summaries

All configuration comes from config.py - change settings there.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np

# Import configuration
from config import (
    DATA_DIR, PROCESSED_DIR, OUTPUT_DIR,
    ED_DATA_FILE, ED_COLUMN_MAPPING, MISSING_VALUES,
    STUDY_YEARS, AGE_GROUPS, AGE_GROUP_ORDER,
)

# Import classification functions
from intox_analysis.data.schemas import (
    classify_drug_intoxication,
    is_missing,
)

# =============================================================================
# CONFIGURATION
# =============================================================================

# Set to True to generate synthetic data if file not found
GENERATE_SYNTHETIC_IF_MISSING = True

# CSV parameters (adjust if your file uses different format)
CSV_PARAMS = {
    "sep": ",",
    "encoding": "utf-8",
    "na_values": MISSING_VALUES,
}

# =============================================================================
# STEP 1: LOAD DATA
# =============================================================================

print("=" * 70)
print("STEP 1: Loading ED Data")
print("=" * 70)

if ED_DATA_FILE.exists():
    print(f"\nLoading: {ED_DATA_FILE}")
    df = pd.read_csv(ED_DATA_FILE, **CSV_PARAMS)
    print(f"Loaded {len(df):,} rows, {len(df.columns)} columns")
    USE_SYNTHETIC = False

elif GENERATE_SYNTHETIC_IF_MISSING:
    print(f"\nFile not found: {ED_DATA_FILE}")
    print("Generating synthetic data for testing...")
    
    # Import generator
    from intox_analysis.data.generators import generate_ed_data
    
    # Generate synthetic ED data
    df = generate_ed_data(n_records=50000, years=STUDY_YEARS)
    
    # Save for future use
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(ED_DATA_FILE, index=False)
    print(f"Saved synthetic data to: {ED_DATA_FILE}")
    print(f"Generated {len(df):,} rows")
    USE_SYNTHETIC = True

else:
    print(f"\nFile not found: {ED_DATA_FILE}")
    print("\nTo proceed:")
    print("1. Export ED data from VDI as CSV")
    print(f"2. Save to: {DATA_DIR}")
    print("3. Update ED_DATA_FILE in config.py if filename differs")
    print("4. Re-run this script")
    raise FileNotFoundError(f"ED data not found: {ED_DATA_FILE}")

# Show columns
print(f"\nColumns in dataset:")
for col in df.columns[:15]:
    print(f"  - {col}")
if len(df.columns) > 15:
    print(f"  ... and {len(df.columns) - 15} more")

# =============================================================================
# STEP 2: STANDARDISE COLUMN NAMES
# =============================================================================

print("\n" + "=" * 70)
print("STEP 2: Standardising Column Names")
print("=" * 70)

# Rename columns that exist in the mapping
cols_to_rename = {k: v for k, v in ED_COLUMN_MAPPING.items() if k in df.columns}
df_std = df.rename(columns=cols_to_rename)

print(f"\nRenamed {len(cols_to_rename)} columns:")
for old, new in list(cols_to_rename.items())[:10]:
    print(f"  {old} -> {new}")

# =============================================================================
# STEP 3: DATA EXPLORATION
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
    print(f"  Mean:   {age.mean():.1f} years")
    print(f"  Median: {age.median():.1f} years")
    print(f"  Range:  {age.min():.0f} to {age.max():.0f}")
    print(f"  Missing: {age.isna().sum():,}")

# Sex distribution
sex_col = "sex" if "sex" in df_std.columns else "sex_registry"
if sex_col in df_std.columns:
    print(f"\nSex distribution:")
    sex_counts = df_std[sex_col].value_counts()
    for sex, count in sex_counts.items():
        print(f"  {sex}: {count:,} ({100*count/len(df_std):.1f}%)")

# Disposition distribution
if "disposition_code" in df_std.columns:
    print(f"\nDisposition (top 5):")
    disp_counts = df_std["disposition_code"].value_counts()
    for code, count in disp_counts.head(5).items():
        pct = 100 * count / len(df_std)
        print(f"  {code}: {count:,} ({pct:.1f}%)")

# =============================================================================
# STEP 4: IDENTIFY DRUG INTOXICATION CASES
# =============================================================================

print("\n" + "=" * 70)
print("STEP 4: Classifying Drug Intoxications")
print("=" * 70)

# Determine diagnosis column name
diag_col = "diagnosis_code" if "diagnosis_code" in df_std.columns else "diagnosis_code_primary"
if diag_col not in df_std.columns:
    # Try to find it
    diag_cols = [c for c in df_std.columns if "diag" in c.lower() and "code" in c.lower()]
    diag_col = diag_cols[0] if diag_cols else None

if diag_col:
    print(f"\nUsing diagnosis column: {diag_col}")
    
    # Classify each diagnosis
    print("Classifying diagnoses...", end=" ", flush=True)
    
    def classify_row(code):
        if pd.isna(code) or is_missing(str(code)):
            return {"is_intoxication": False, "drug_class": None, "intent": None}
        return classify_drug_intoxication(str(code))
    
    classifications = df_std[diag_col].apply(classify_row).apply(pd.Series)
    print("Done!")
    
    # Add to dataframe
    df_std["is_intoxication"] = classifications["is_intoxication"]
    df_std["drug_class"] = classifications["drug_class"]
    df_std["intent"] = classifications["intent"]
    
    # Summary
    n_intox = df_std["is_intoxication"].sum()
    print(f"\nDrug intoxications found: {n_intox:,} ({100*n_intox/len(df_std):.2f}%)")
    
    if n_intox > 0:
        print(f"\nDrug class distribution:")
        class_counts = df_std[df_std["is_intoxication"]]["drug_class"].value_counts()
        for drug_class, count in class_counts.head(10).items():
            print(f"  {drug_class}: {count:,} ({100*count/n_intox:.1f}%)")
else:
    print("\nNo diagnosis column found - skipping classification")
    n_intox = 0

# =============================================================================
# STEP 5: ADD AGE GROUPS
# =============================================================================

print("\n" + "=" * 70)
print("STEP 5: Adding Age Groups")
print("=" * 70)

if "age_years" in df_std.columns:
    age = pd.to_numeric(df_std["age_years"], errors="coerce")
    
    def assign_age_group(a):
        if pd.isna(a):
            return "Unknown"
        for group, (low, high) in AGE_GROUPS.items():
            if low <= a <= high:
                return group
        return "Unknown"
    
    df_std["age_group"] = age.apply(assign_age_group)
    
    print(f"\nAge group distribution:")
    for group in AGE_GROUP_ORDER:
        count = (df_std["age_group"] == group).sum()
        print(f"  {group}: {count:,} ({100*count/len(df_std):.1f}%)")

# =============================================================================
# STEP 6: CREATE INTOXICATION SUBSET
# =============================================================================

print("\n" + "=" * 70)
print("STEP 6: Intoxication Subset")
print("=" * 70)

if n_intox > 0:
    df_intox = df_std[df_std["is_intoxication"]].copy()
    
    # Monthly counts
    if "year_month" in df_intox.columns:
        monthly = df_intox.groupby("year_month").size()
        print(f"\nMonthly intoxications:")
        print(f"  Total months: {len(monthly)}")
        print(f"  Monthly mean: {monthly.mean():.1f}")
        print(f"  Monthly range: {monthly.min()} to {monthly.max()}")
else:
    df_intox = pd.DataFrame()
    print("\nNo intoxication cases to subset")

# =============================================================================
# STEP 7: SAVE OUTPUTS
# =============================================================================

print("\n" + "=" * 70)
print("STEP 7: Saving Outputs")
print("=" * 70)

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# Save processed ED data
output_file = PROCESSED_DIR / "ed_processed.csv"
df_std.to_csv(output_file, index=False)
print(f"\nSaved: {output_file}")

# Save intoxication cases
if len(df_intox) > 0:
    intox_file = PROCESSED_DIR / "ed_intoxications.csv"
    df_intox.to_csv(intox_file, index=False)
    print(f"Saved: {intox_file}")

# =============================================================================
# SUMMARY
# =============================================================================

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

print(f"""
Data source: {'Synthetic' if USE_SYNTHETIC else 'Real VDI data'}
Total records: {len(df_std):,}
Intoxications: {n_intox:,} ({100*n_intox/len(df_std):.2f}%)

Variables available in Spyder:
  df_std   - Full dataset with standardised columns
  df_intox - Intoxication cases only

Next step: Run 02_load_pharma_data.py
""")
print("=" * 70)
