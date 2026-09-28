# -*- coding: utf-8 -*-
"""
03_intoxication_trends.py
=========================

This script analyses drug intoxication trends by drug class to identify
which drugs are driving the upward trend in ED presentations.

Outputs:
1. Summary table: Average annual cases and YoY growth rates by drug class
2. Bubble chart: Drug classes by volume vs growth rate
3. Line chart: Annual trends for top drug classes
4. Comparison: All ED presentations vs admitted patients only

The same analysis is then repeated for mental health diagnoses to explore
whether mental health trends might explain prescribing (and thus intoxication) increases.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np

# Import our analysis module
from intox_analysis.analysis.trends import (
    process_ed_data,
    run_intoxication_trend_analysis,
    run_mental_health_trend_analysis,
    classify_drug_intoxication_detailed,
    classify_mental_health,
)

# =============================================================================
# CONFIGURATION
# =============================================================================

DATA_DIR = project_root / "data" / "raw"
OUTPUT_DIR = project_root / "outputs"

# Update this to your actual ED data file!
ED_FILE = DATA_DIR / "ed_presentations.csv"

# Column names (update if your export uses different names)
# These should match after loading - check your CSV headers
COL_CONFIG = {
    "diagnosis_col_primary": "diagnosis_code_primary",     # or "Cod Diagnosi"
    "diagnosis_col_secondary": "diagnosis_code_secondary", # or "Cod Diagnosi Secondaria"  
    "date_col": "year_month",                              # or "Annomese_INGR"
    "esito_col": "disposition_code",                       # or "Codice Esito"
}

# Esito codes that indicate hospital admission (verify against your codebook!)
ADMISSION_CODES = ["2", "3", "4"]

# Number of recent years for trend analysis
LAST_N_YEARS = 3  # 2023, 2024, 2025

# =============================================================================
# STEP 1: LOAD DATA
# =============================================================================

print("=" * 70)
print("DRUG INTOXICATION & MENTAL HEALTH TREND ANALYSIS")
print("=" * 70)

if not ED_FILE.exists():
    print(f"\n⚠ Data file not found: {ED_FILE}")
    print("\nCreating SYNTHETIC DATA for demonstration...")
    print("(Replace with your actual data for real analysis)")
    
    # Generate synthetic data
    np.random.seed(42)
    n_records = 50000
    
    years = np.random.choice([2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025], 
                              n_records, p=[0.08, 0.09, 0.10, 0.11, 0.12, 0.12, 0.13, 0.13, 0.12])
    months = np.random.randint(1, 13, n_records)
    
    # Mix of drug intoxication and other diagnoses
    # Higher proportion of benzos in recent years to simulate the trend
    drug_codes_icd10 = ["T424X2A", "T424X1A", "T400X1A", "T391X1A", "T436X2A", "T510X1A", "T426X2A"]
    drug_codes_icd9 = ["9694", "96509", "9650", "9697"]
    mh_codes_icd10 = ["F329", "F411", "F500", "F431", "F320", "F412"]
    mh_codes_icd9 = ["3004", "311", "30750", "309"]
    other_codes = ["J189", "K529", "R104", "S0100", "R55"]  # Random non-relevant codes
    
    # Create diagnosis distribution that changes over time
    diagnoses = []
    for i, year in enumerate(years):
        if year >= 2023:
            # More benzos in recent years
            weights = [0.20, 0.10, 0.05, 0.05, 0.03, 0.02, 0.02,  # ICD-10 drugs
                       0.05, 0.03, 0.02, 0.02,  # ICD-9 drugs
                       0.08, 0.05, 0.03, 0.03, 0.02, 0.02,  # Mental health
                       0.05, 0.03, 0.02, 0.02, 0.06]  # Other
        elif year >= 2020:
            weights = [0.15, 0.08, 0.05, 0.05, 0.03, 0.02, 0.02,
                       0.05, 0.03, 0.02, 0.02,
                       0.10, 0.06, 0.04, 0.04, 0.03, 0.02,
                       0.05, 0.04, 0.03, 0.03, 0.04]
        else:
            weights = [0.10, 0.06, 0.05, 0.04, 0.03, 0.02, 0.02,
                       0.06, 0.04, 0.03, 0.02,
                       0.08, 0.05, 0.03, 0.03, 0.02, 0.02,
                       0.08, 0.06, 0.05, 0.05, 0.06]
        
        all_codes = drug_codes_icd10 + drug_codes_icd9 + mh_codes_icd10 + mh_codes_icd9 + other_codes
        diagnoses.append(np.random.choice(all_codes, p=weights))
    
    df = pd.DataFrame({
        "patient_id": [f"MB-{''.join(np.random.choice(list('0123456789ABCDEF'), 64))}" for _ in range(n_records)],
        "year_month": [f"{y}{m:02d}" for y, m in zip(years, months)],
        "age_years": np.random.normal(45, 18, n_records).astype(int).clip(10, 95),
        "sex_registry": np.random.choice(["M", "F"], n_records, p=[0.45, 0.55]),
        "diagnosis_code_primary": diagnoses,
        "diagnosis_desc_primary": ["Synthetic diagnosis"] * n_records,
        "diagnosis_code_secondary": np.random.choice(["_", "F329", "F411", ""], n_records, p=[0.6, 0.15, 0.15, 0.1]),
        "diagnosis_desc_secondary": ["_"] * n_records,
        "disposition_code": np.random.choice(["1", "2", "3", "4"], n_records, p=[0.75, 0.15, 0.07, 0.03]),
        "disposition_desc": ["Synthetic"] * n_records,
    })
    
    print(f"Generated {len(df):,} synthetic records")
    USE_SYNTHETIC = True

else:
    print(f"\nLoading: {ED_FILE}")
    df = pd.read_csv(ED_FILE)
    print(f"Loaded {len(df):,} records")
    USE_SYNTHETIC = False
    
    # Check if column renaming is needed
    if "Cod Diagnosi" in df.columns:
        print("\nRenaming Italian columns to English...")
        column_mapping = {
            "Codice Fiscale Assistito MICROBIO": "patient_id",
            "Annomese_INGR": "year_month",
            "Eta(calcolata)": "age_years",
            "Sesso (anag ass.to)": "sex_registry",
            "Cod Diagnosi": "diagnosis_code_primary",
            "Diagnosi": "diagnosis_desc_primary",
            "Cod Diagnosi Secondaria": "diagnosis_code_secondary",
            "Diagnosi Secondaria": "diagnosis_desc_secondary",
            "Codice Esito": "disposition_code",
            "Descrizione Esito": "disposition_desc",
        }
        df = df.rename(columns=column_mapping)

print(f"\nColumns: {list(df.columns)}")

# =============================================================================
# STEP 2: PROCESS DATA (add classifications)
# =============================================================================

print("\n" + "=" * 70)
print("STEP 2: Processing Data")
print("=" * 70)

df_processed = process_ed_data(
    df,
    diagnosis_col_primary="diagnosis_code_primary",
    diagnosis_col_secondary="diagnosis_code_secondary",
    date_col="year_month",
    esito_col="disposition_code",
    admission_codes=ADMISSION_CODES,
)

# Summary
n_intox = df_processed["is_intoxication"].sum()
n_mh = df_processed["is_mental_health"].sum()
n_admitted = df_processed["is_admitted"].sum()

print(f"\nData summary:")
print(f"  Total records: {len(df_processed):,}")
print(f"  Drug intoxications: {n_intox:,} ({100*n_intox/len(df_processed):.1f}%)")
print(f"  Mental health diagnoses: {n_mh:,} ({100*n_mh/len(df_processed):.1f}%)")
print(f"  Admitted patients: {n_admitted:,} ({100*n_admitted/len(df_processed):.1f}%)")

# Year distribution
print(f"\nRecords by year:")
year_counts = df_processed.groupby("year").size()
for year, count in year_counts.items():
    print(f"  {year}: {count:,}")

# =============================================================================
# STEP 3: DRUG INTOXICATION TREND ANALYSIS
# =============================================================================

print("\n" + "=" * 70)
print("STEP 3: Drug Intoxication Trend Analysis")
print("=" * 70)

intox_results = run_intoxication_trend_analysis(
    df_processed,
    output_dir=str(OUTPUT_DIR / "figures"),
    last_n_years=LAST_N_YEARS,
)

# =============================================================================
# STEP 4: MENTAL HEALTH TREND ANALYSIS
# =============================================================================

print("\n" + "=" * 70)
print("STEP 4: Mental Health Trend Analysis")
print("=" * 70)

mh_results = run_mental_health_trend_analysis(
    df_processed,
    output_dir=str(OUTPUT_DIR / "figures"),
    last_n_years=LAST_N_YEARS,
)

# =============================================================================
# STEP 5: SUMMARY AND KEY FINDINGS
# =============================================================================

print("\n" + "=" * 70)
print("KEY FINDINGS")
print("=" * 70)

# Find top growing drug class
top_intox_all = intox_results["table_all"].iloc[0]
top_intox_admitted = intox_results["table_admitted"].iloc[0]

print(f"""
DRUG INTOXICATIONS:
  
  All ED Presentations:
    - Fastest growing class: {top_intox_all['Category']}
    - Average YoY growth: {top_intox_all['Avg YoY Growth (%)']:.1f}%
    - Average annual cases: {top_intox_all['Avg Annual Cases']:.0f}
  
  Admitted Patients Only:
    - Fastest growing class: {top_intox_admitted['Category']}
    - Average YoY growth: {top_intox_admitted['Avg YoY Growth (%)']:.1f}%
    - Average annual cases: {top_intox_admitted['Avg Annual Cases']:.0f}
""")

# Find top growing mental health diagnosis
top_mh = mh_results["table_all"].iloc[0]

print(f"""MENTAL HEALTH DIAGNOSES:
  
  - Fastest growing diagnosis: {top_mh['Category']}
  - Average YoY growth: {top_mh['Avg YoY Growth (%)']:.1f}%
  - Average annual cases: {top_mh['Avg Annual Cases']:.0f}
""")

# =============================================================================
# STEP 6: SAVE RESULTS
# =============================================================================

print("\n" + "=" * 70)
print("OUTPUTS SAVED")
print("=" * 70)

output_files = [
    OUTPUT_DIR / "figures" / "intox_growth_drivers_all.png",
    OUTPUT_DIR / "figures" / "intox_growth_drivers_admitted.png",
    OUTPUT_DIR / "figures" / "intox_annual_trends.png",
    OUTPUT_DIR / "figures" / "intox_comparison.png",
    OUTPUT_DIR / "figures" / "mental_health_annual_trends.png",
    OUTPUT_DIR / "figures" / "mental_health_growth_drivers.png",
    OUTPUT_DIR / "figures" / "intox_trends_all_presentations.csv",
    OUTPUT_DIR / "figures" / "intox_trends_admitted_only.csv",
    OUTPUT_DIR / "figures" / "mental_health_trends_all.csv",
]

print("\nFigures and tables saved to:")
for f in output_files:
    if f.exists():
        print(f"  ✓ {f.name}")
    else:
        print(f"  • {f.name} (will be created)")

if USE_SYNTHETIC:
    print("\n⚠ NOTE: Results above are based on SYNTHETIC data.")
    print("   Replace with your actual VDI data for real analysis.")

print("\n" + "=" * 70)
print("ANALYSIS COMPLETE")
print("=" * 70)

# =============================================================================
# AVAILABLE VARIABLES FOR EXPLORATION
# =============================================================================

print("""
Variables available for further exploration in Spyder:

  df_processed     : Full dataset with classifications
  intox_results    : Dictionary with intoxication analysis results
  mh_results       : Dictionary with mental health analysis results

Example queries:

  # View intoxication cases only
  df_intox = df_processed[df_processed['is_intoxication']]
  
  # View benzos specifically
  df_benzos = df_processed[df_processed['drug_class'] == 'Benzodiazepines']
  
  # Cross-tabulate drug class by year
  pd.crosstab(df_processed['drug_class'], df_processed['year'])
  
  # View annual counts table
  intox_results['counts_all']
""")
