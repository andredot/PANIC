# -*- coding: utf-8 -*-
"""
02_load_pharma_data.py
======================

Load and process pharmaceutical (Flusso F) data.

This script works in two modes:
- WITH polars: Lazy evaluation for large files (1GB+) - faster
- WITHOUT polars: Uses pandas - slower but works everywhere

This script shows:
1. How to load pharmaceutical CSVs
2. How to classify drugs by ATC code
3. How to compute monthly prescription counts
4. How to identify chronic users

All configuration comes from config.py
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
    DATA_DIR, PROCESSED_DIR,
    PHARMA_SYNTHETIC_FILE,
    PHARMA_COLUMN_MAPPING, MISSING_VALUES,
    STUDY_YEARS,
    ATC_BENZODIAZEPINES, ATC_Z_DRUGS, ATC_OPIOIDS, ATC_ANTIDEPRESSANTS,
    CHRONIC_USER_MIN_PRESCRIPTIONS, CHRONIC_USER_MAX_GAP_DAYS,
    get_pharma_files,
)

# =============================================================================
# CHECK POLARS AVAILABILITY
# =============================================================================

try:
    import polars as pl
    HAS_POLARS = True
    print(f"[OK] Polars v{pl.__version__} available - using fast processing")
except ImportError:
    HAS_POLARS = False
    print("[--] Polars not installed - using pandas (slower for large files)")

# Import pharmaceutical module
from intox_analysis.data.pharmaceutical import classify_atc_code

# =============================================================================
# CONFIGURATION
# =============================================================================

# Generate synthetic data if no files found
GENERATE_SYNTHETIC_IF_MISSING = True

# =============================================================================
# HELPER FUNCTIONS (pandas fallback)
# =============================================================================

def classify_atc_vectorized(atc_series: pd.Series) -> pd.DataFrame:
    """Classify a series of ATC codes."""
    results = atc_series.apply(lambda x: classify_atc_code(str(x)) if pd.notna(x) else {
        "drug_class": "unknown", "is_benzodiazepine": False, "is_z_drug": False,
        "is_opioid": False, "is_psychotropic": False
    })
    return pd.DataFrame(results.tolist())


def load_pharma_pandas(file_path: Path) -> pd.DataFrame:
    """Load pharmaceutical data with pandas."""
    print(f"  Loading {file_path.name}...", end=" ", flush=True)
    
    df = pd.read_csv(
        file_path,
        na_values=MISSING_VALUES,
        low_memory=False,
    )
    
    print(f"{len(df):,} rows")
    return df


def process_pharma_pandas(df: pd.DataFrame) -> pd.DataFrame:
    """Process pharmaceutical data with pandas."""
    # Rename columns
    cols_to_rename = {k: v for k, v in PHARMA_COLUMN_MAPPING.items() if k in df.columns}
    df = df.rename(columns=cols_to_rename)
    
    # Classify ATC codes
    atc_col = "atc_code" if "atc_code" in df.columns else None
    if atc_col is None:
        atc_cols = [c for c in df.columns if "atc" in c.lower()]
        atc_col = atc_cols[0] if atc_cols else None
    
    if atc_col:
        print("  Classifying ATC codes...", end=" ", flush=True)
        classifications = classify_atc_vectorized(df[atc_col])
        df["drug_class"] = classifications["drug_class"]
        df["is_benzodiazepine"] = classifications["is_benzodiazepine"]
        df["is_z_drug"] = classifications["is_z_drug"]
        df["is_opioid"] = classifications["is_opioid"]
        df["is_psychotropic"] = classifications["is_psychotropic"]
        print("Done!")
    
    # Parse dates
    date_col = "dispensing_date" if "dispensing_date" in df.columns else None
    if date_col is None:
        date_cols = [c for c in df.columns if "data" in c.lower() or "date" in c.lower()]
        date_col = date_cols[0] if date_cols else None
    
    if date_col:
        df["dispensing_date"] = pd.to_datetime(df[date_col], errors="coerce")
        df["year"] = df["dispensing_date"].dt.year
        df["year_month"] = df["dispensing_date"].dt.to_period("M").astype(str)
    
    return df


# =============================================================================
# POLARS FUNCTIONS (if available)
# =============================================================================

if HAS_POLARS:
    from intox_analysis.data.pharmaceutical import (
        scan_pharmaceutical_data,
        add_derived_columns,
    )


# =============================================================================
# STEP 1: LOAD DATA
# =============================================================================

print("\n" + "=" * 70)
print("STEP 1: Loading Pharmaceutical Data")
print("=" * 70)

# Find available files
pharma_files = get_pharma_files()

if pharma_files:
    print(f"\nFound {len(pharma_files)} pharmaceutical file(s):")
    for f in pharma_files:
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"  - {f.name} ({size_mb:.1f} MB)")
    
    USE_SYNTHETIC = False
    
    if HAS_POLARS and any(f.stat().st_size > 100_000_000 for f in pharma_files):
        # Use polars for large files
        print("\nUsing Polars for large file processing...")
        lf = scan_pharmaceutical_data([str(f) for f in pharma_files])
        lf = add_derived_columns(lf)
        
        # Collect a sample first
        print("Collecting data...", end=" ", flush=True)
        df_pharma = lf.collect()
        df_pharma = df_pharma.to_pandas()
        print(f"Done! {len(df_pharma):,} rows")
    else:
        # Use pandas
        print("\nUsing pandas for processing...")
        dfs = [load_pharma_pandas(f) for f in pharma_files]
        df_pharma = pd.concat(dfs, ignore_index=True)
        df_pharma = process_pharma_pandas(df_pharma)

elif GENERATE_SYNTHETIC_IF_MISSING:
    print("\nNo pharmaceutical files found.")
    print("Generating synthetic data for testing...")
    
    from intox_analysis.data.generators import generate_pharma_data
    
    df_pharma = generate_pharma_data(n_records=100000, years=STUDY_YEARS)
    
    # Save for future use
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df_pharma.to_csv(PHARMA_SYNTHETIC_FILE, index=False)
    print(f"Saved synthetic data to: {PHARMA_SYNTHETIC_FILE}")
    print(f"Generated {len(df_pharma):,} rows")
    
    USE_SYNTHETIC = True

else:
    print("\nNo pharmaceutical files found!")
    print(f"Place CSV files in: {DATA_DIR}")
    raise FileNotFoundError("No pharmaceutical data available")

# =============================================================================
# STEP 2: DATA EXPLORATION
# =============================================================================

print("\n" + "=" * 70)
print("STEP 2: Data Exploration")
print("=" * 70)

print(f"\nTotal records: {len(df_pharma):,}")
print(f"Columns: {len(df_pharma.columns)}")

# Date range
if "year" in df_pharma.columns:
    print(f"\nYear range: {df_pharma['year'].min()} to {df_pharma['year'].max()}")

# Patient count
patient_col = "patient_id" if "patient_id" in df_pharma.columns else None
if patient_col:
    n_patients = df_pharma[patient_col].nunique()
    print(f"Unique patients: {n_patients:,}")

# Drug class distribution
if "drug_class" in df_pharma.columns:
    print(f"\nDrug class distribution:")
    class_counts = df_pharma["drug_class"].value_counts()
    for drug_class, count in class_counts.head(10).items():
        pct = 100 * count / len(df_pharma)
        print(f"  {drug_class}: {count:,} ({pct:.1f}%)")

# Psychotropic prescriptions
if "is_psychotropic" in df_pharma.columns:
    n_psychotropic = df_pharma["is_psychotropic"].sum()
    print(f"\nPsychotropic prescriptions: {n_psychotropic:,} ({100*n_psychotropic/len(df_pharma):.1f}%)")

# =============================================================================
# STEP 3: MONTHLY PRESCRIPTION COUNTS
# =============================================================================

print("\n" + "=" * 70)
print("STEP 3: Monthly Prescription Counts")
print("=" * 70)

if "year_month" in df_pharma.columns and "drug_class" in df_pharma.columns:
    monthly = df_pharma.groupby(["year_month", "drug_class"]).size().reset_index(name="n_prescriptions")
    monthly = monthly.sort_values("year_month")
    
    print(f"\nMonthly data points: {len(monthly):,}")
    
    # Benzodiazepine trend
    benzo_monthly = monthly[monthly["drug_class"] == "benzodiazepine"]
    if len(benzo_monthly) > 0:
        print(f"\nBenzodiazepine prescriptions:")
        print(f"  Months with data: {len(benzo_monthly)}")
        print(f"  Monthly mean: {benzo_monthly['n_prescriptions'].mean():.0f}")
        print(f"  Monthly range: {benzo_monthly['n_prescriptions'].min()} to {benzo_monthly['n_prescriptions'].max()}")

# =============================================================================
# STEP 4: IDENTIFY CHRONIC USERS
# =============================================================================

print("\n" + "=" * 70)
print("STEP 4: Chronic vs Sporadic Users")
print("=" * 70)

if patient_col and "dispensing_date" in df_pharma.columns and "drug_class" in df_pharma.columns:
    
    # Focus on benzodiazepines
    df_benzo = df_pharma[df_pharma["drug_class"] == "benzodiazepine"].copy()
    
    if len(df_benzo) > 0:
        # Count prescriptions per patient per year
        df_benzo["year"] = pd.to_datetime(df_benzo["dispensing_date"]).dt.year
        patient_yearly = df_benzo.groupby([patient_col, "year"]).size().reset_index(name="n_rx")
        
        # Classify: >= CHRONIC_USER_MIN_PRESCRIPTIONS = chronic
        patient_yearly["user_type"] = np.where(
            patient_yearly["n_rx"] >= CHRONIC_USER_MIN_PRESCRIPTIONS,
            "chronic",
            "sporadic"
        )
        
        # Summary
        user_summary = patient_yearly.groupby("user_type").agg(
            n_patient_years=("n_rx", "count"),
            mean_rx_per_year=("n_rx", "mean"),
        ).round(1)
        
        print(f"\nBenzodiazepine user classification (threshold: {CHRONIC_USER_MIN_PRESCRIPTIONS}+ Rx/year):")
        print(user_summary)
        
        n_chronic = (patient_yearly["user_type"] == "chronic").sum()
        n_total = len(patient_yearly)
        print(f"\nChronic user-years: {n_chronic:,} ({100*n_chronic/n_total:.1f}%)")

# =============================================================================
# STEP 5: DDD ANALYSIS (if available)
# =============================================================================

print("\n" + "=" * 70)
print("STEP 5: DDD Analysis")
print("=" * 70)

if "ddd" in df_pharma.columns:
    ddd = pd.to_numeric(df_pharma["ddd"], errors="coerce")
    
    print(f"\nDDD statistics:")
    print(f"  Records with DDD: {ddd.notna().sum():,}")
    print(f"  Mean DDD: {ddd.mean():.2f}")
    print(f"  Total DDD: {ddd.sum():,.0f}")
    
    # By drug class
    if "drug_class" in df_pharma.columns:
        df_pharma["ddd_numeric"] = ddd
        ddd_by_class = df_pharma.groupby("drug_class")["ddd_numeric"].sum().sort_values(ascending=False)
        
        print(f"\nTotal DDD by drug class:")
        for drug_class, total in ddd_by_class.head(5).items():
            print(f"  {drug_class}: {total:,.0f}")
else:
    print("\nDDD column not available in this dataset")

# =============================================================================
# STEP 6: SAVE OUTPUTS
# =============================================================================

print("\n" + "=" * 70)
print("STEP 6: Saving Outputs")
print("=" * 70)

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# Save processed data
output_file = PROCESSED_DIR / "pharma_processed.csv"
df_pharma.to_csv(output_file, index=False)
print(f"\nSaved: {output_file}")

# Save monthly aggregates
if "year_month" in df_pharma.columns and "drug_class" in df_pharma.columns:
    monthly_file = PROCESSED_DIR / "pharma_monthly.csv"
    monthly.to_csv(monthly_file, index=False)
    print(f"Saved: {monthly_file}")

# =============================================================================
# SUMMARY
# =============================================================================

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

n_benzo = (df_pharma["drug_class"] == "benzodiazepine").sum() if "drug_class" in df_pharma.columns else 0

print(f"""
Data source: {'Synthetic' if USE_SYNTHETIC else 'Real VDI data'}
Processing: {'Polars' if HAS_POLARS else 'Pandas'}
Total records: {len(df_pharma):,}
Benzodiazepine Rx: {n_benzo:,}

Variables available in Spyder:
  df_pharma - Full pharmaceutical dataset
  monthly   - Monthly aggregates by drug class

Next step: Run 05_intoxication_trends.py
""")
print("=" * 70)
