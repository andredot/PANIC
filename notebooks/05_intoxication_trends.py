# -*- coding: utf-8 -*-
"""
05_intoxication_trends.py
=========================

Analyse drug intoxication trends by drug class to identify
which drugs are driving the upward trend in ED presentations.

Outputs:
1. Summary table: Average annual cases and YoY growth rates by drug class
2. Bubble chart: Drug classes by volume vs growth rate
3. Line chart: Annual trends for top drug classes
4. Comparison: All ED presentations vs admitted patients only

The same analysis is then repeated for mental health diagnoses.

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
    DATA_DIR, OUTPUT_DIR, FIGURES_DIR, TABLES_DIR,
    ED_DATA_FILE, PROCESSED_DIR,
    ED_COLUMN_MAPPING,
)

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

# Column names (update if your export uses different names)
COL_CONFIG = {
    "diagnosis_col_primary": "diagnosis_code_primary",
    "diagnosis_col_secondary": "diagnosis_code_secondary",
    "date_col": "year_month",
    "esito_col": "disposition_code",
}

# Esito codes that indicate hospital admission
ADMISSION_CODES = ["2", "3", "4"]

# Number of recent years for trend analysis
LAST_N_YEARS = 3  # 2023, 2024, 2025

# =============================================================================
# STEP 1: LOAD DATA
# =============================================================================

print("=" * 70)
print("DRUG INTOXICATION & MENTAL HEALTH TREND ANALYSIS")
print("=" * 70)

# Try processed file first, then raw file
processed_file = PROCESSED_DIR / "ed_processed.csv"

if processed_file.exists():
    print(f"\nLoading processed data: {processed_file.name}")
    df = pd.read_csv(processed_file)
    print(f"Loaded {len(df):,} records")
    USE_SYNTHETIC = False

elif ED_DATA_FILE.exists():
    print(f"\nLoading: {ED_DATA_FILE}")
    df = pd.read_csv(ED_DATA_FILE)
    print(f"Loaded {len(df):,} records")
    USE_SYNTHETIC = False
    
    # Rename columns if needed
    cols_to_rename = {k: v for k, v in ED_COLUMN_MAPPING.items() if k in df.columns}
    if cols_to_rename:
        print(f"Renaming {len(cols_to_rename)} columns...")
        df = df.rename(columns=cols_to_rename)

else:
    print(f"\nData file not found: {ED_DATA_FILE}")
    print("Generating SYNTHETIC DATA for testing...")
    
    from intox_analysis.data.generators import generate_ed_data
    from config import STUDY_YEARS
    
    df = generate_ed_data(n_records=50000, years=STUDY_YEARS)
    print(f"Generated {len(df):,} synthetic records")
    USE_SYNTHETIC = True

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
