"""
01 - Getting Started with the Lombardy Drug Intoxication Analysis
==================================================================

This script will help you verify your setup and understand the data structure.
Run each section (between #%% markers) separately using Ctrl+Enter in Spyder.

The #%% markers create "cells" like in Jupyter notebooks, so you can run
the code step by step and see the output before moving on.

Author: Generated for VDI environment
Date: April 2026
"""

#%% SECTION 1: Setup and Imports
# ==============================
# Run this cell first to load all required libraries.
# If any import fails, run setup_environment.py first.

import sys
from pathlib import Path

# Add project source to Python path
project_root = Path(__file__).parent.parent.resolve()
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Core libraries
import polars as pl
import pandas as pd
import numpy as np

# Plotting
import matplotlib.pyplot as plt
import seaborn as sns

# Set plot style
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")

# Project modules
from intox_analysis.data.pharmaceutical import (
    classify_atc_code,
    scan_pharmaceutical_data,
    add_derived_columns,
    monthly_prescription_counts,
    generate_synthetic_pharmaceutical_data,
    ATC_BENZODIAZEPINES,
    ATC_Z_DRUGS,
)

print("All imports successful!")
print(f"Polars version: {pl.__version__}")
print(f"Project root: {project_root}")


#%% SECTION 2: Understanding the ATC Classification
# ==================================================
# Before looking at the data, let's understand how drug classification works.
# This is essential for Research Question 5 (prescribing patterns).

print("=" * 60)
print("ATC CODE CLASSIFICATION DEMO")
print("=" * 60)
print()

# Test with drugs observed in your VDI data
test_drugs = [
    ("N05BA12", "ALPRAZOLAM"),     # Benzodiazepine anxiolytic
    ("N05CF01", "ZOPICLONE"),      # Z-drug hypnotic
    ("N05AL07", "LEVOSULPIRIDE"),  # Antipsychotic
    ("N06AB06", "SERTRALINE"),     # SSRI antidepressant
    ("N02AX02", "TRAMADOL"),       # Opioid analgesic
    ("A02BC01", "OMEPRAZOLE"),     # PPI (not psychotropic)
]

for atc_code, drug_name in test_drugs:
    result = classify_atc_code(atc_code)
    print(f"{atc_code} ({drug_name}):")
    print(f"  Psychotropic: {result['is_psychotropic']}")
    print(f"  Drug class: {result['drug_class']}")
    if result.get('drug_name'):
        print(f"  Verified name: {result['drug_name']}")
    print()

# Show all benzodiazepines we track
print("Benzodiazepines in our classification:")
for code, name in sorted(ATC_BENZODIAZEPINES.items()):
    print(f"  {code}: {name}")


#%% SECTION 3: Generate Synthetic Data for Testing
# =================================================
# Before loading real data, let's work with synthetic data to understand
# the structure and test our analysis pipeline.

print("=" * 60)
print("GENERATING SYNTHETIC PHARMACEUTICAL DATA")
print("=" * 60)
print()

# Generate a small synthetic dataset (fast)
# In the real analysis, you'll load from CSV files
synthetic_df = generate_synthetic_pharmaceutical_data(
    n_records=50_000,      # 50k records for testing
    n_patients=5_000,      # 5k unique patients
    start_year=2017,
    end_year=2025,
    seed=42                # For reproducibility
)

print(f"Generated {len(synthetic_df):,} prescription records")
print(f"Unique patients: {synthetic_df['patient_id'].n_unique():,}")
print(f"Date range: {synthetic_df['dispensing_date'].min()} to {synthetic_df['dispensing_date'].max()}")
print()
print("Columns:")
for col in synthetic_df.columns:
    print(f"  - {col}: {synthetic_df[col].dtype}")
print()
print("Sample rows:")
print(synthetic_df.head(5))


#%% SECTION 4: Add Derived Columns Using Lazy Evaluation
# =======================================================
# This demonstrates the lazy evaluation approach you'll use for 1GB+ files.
# With lazy evaluation, Polars builds a query plan but doesn't execute until
# you call .collect(). This is crucial for memory efficiency.

print("=" * 60)
print("LAZY EVALUATION DEMONSTRATION")
print("=" * 60)
print()

# Convert to lazy frame (simulating scan_pharmaceutical_data)
lf = synthetic_df.lazy()

# Add derived columns - still lazy, no computation yet!
lf_with_derived = add_derived_columns(lf)

# Show the query plan (what Polars WILL do, not what it HAS done)
print("Query plan (optimised by Polars):")
print(lf_with_derived.explain())
print()

# Now collect - THIS is when computation happens
print("Executing query...")
df_with_derived = lf_with_derived.collect()
print(f"Done! Result has {len(df_with_derived):,} rows")
print()
print("New columns added:")
new_cols = [c for c in df_with_derived.columns if c not in synthetic_df.columns]
for col in new_cols:
    print(f"  - {col}")


#%% SECTION 5: Explore Drug Class Distribution
# =============================================
# Let's see the distribution of drug classes in our synthetic data.
# This mirrors what you'll do with the real data.

print("=" * 60)
print("DRUG CLASS DISTRIBUTION")
print("=" * 60)
print()

# Count by drug class
drug_class_counts = (
    df_with_derived
    .group_by("drug_class")
    .agg(pl.len().alias("n_prescriptions"))
    .sort("n_prescriptions", descending=True)
)

print(drug_class_counts)
print()

# Plot
fig, ax = plt.subplots(figsize=(10, 6))
data = drug_class_counts.to_pandas()
colors = sns.color_palette("husl", len(data))
bars = ax.barh(data["drug_class"], data["n_prescriptions"], color=colors)
ax.set_xlabel("Number of Prescriptions")
ax.set_title("Distribution of Drug Classes (Synthetic Data)")
ax.invert_yaxis()  # Largest at top

# Add value labels
for bar, val in zip(bars, data["n_prescriptions"]):
    ax.text(val + 100, bar.get_y() + bar.get_height()/2, 
            f'{val:,}', va='center', fontsize=9)

plt.tight_layout()
plt.savefig(project_root / "outputs" / "figures" / "drug_class_distribution.png", dpi=150)
plt.show()
print("Figure saved to outputs/figures/drug_class_distribution.png")


#%% SECTION 6: Monthly Prescription Trends
# ========================================
# This is the core analysis: tracking prescriptions over time.
# We'll use the pre-built aggregation function.

print("=" * 60)
print("MONTHLY PRESCRIPTION TRENDS")
print("=" * 60)
print()

# Get monthly counts for benzodiazepines and Z-drugs
monthly_benzo = monthly_prescription_counts(
    lf_with_derived,
    drug_classes=["benzodiazepine", "z_drug"],
    by_drug_class=True,
).collect()

print("Monthly benzodiazepine/Z-drug prescriptions:")
print(monthly_benzo.head(10))
print()

# Plot trends
fig, ax = plt.subplots(figsize=(12, 6))

for drug_class in ["benzodiazepine", "z_drug"]:
    data = monthly_benzo.filter(pl.col("drug_class") == drug_class).to_pandas()
    data["date"] = pd.to_datetime(data["year_month"], format="%Y%m")
    ax.plot(data["date"], data["n_prescriptions"], 
            label=drug_class.replace("_", " ").title(), linewidth=2)

# Add COVID marker
covid_date = pd.Timestamp("2020-03-01")
ax.axvline(covid_date, color="red", linestyle="--", alpha=0.7, label="COVID-19 onset")

ax.set_xlabel("Date")
ax.set_ylabel("Number of Prescriptions")
ax.set_title("Monthly Prescriptions of Benzodiazepines and Z-drugs (Synthetic Data)")
ax.legend()

plt.tight_layout()
plt.savefig(project_root / "outputs" / "figures" / "monthly_trends_benzo.png", dpi=150)
plt.show()
print("Figure saved to outputs/figures/monthly_trends_benzo.png")


#%% SECTION 7: Stratified Analysis by Age Group
# ==============================================
# Research Question 3 asks about trends by demographics.
# Let's stratify by age group.

print("=" * 60)
print("STRATIFIED ANALYSIS BY AGE GROUP")
print("=" * 60)
print()

# Get monthly counts stratified by age group
monthly_by_age = monthly_prescription_counts(
    lf_with_derived,
    drug_classes=["benzodiazepine"],
    by_age_group=True,
).collect()

print("Monthly benzodiazepine prescriptions by age group:")
print(monthly_by_age.head(15))
print()

# Plot as small multiples
age_groups = ["0-17", "18-34", "35-54", "55-74", "75+"]

fig, axes = plt.subplots(2, 3, figsize=(14, 8), sharex=True, sharey=True)
axes = axes.flatten()

for i, age_group in enumerate(age_groups):
    ax = axes[i]
    data = monthly_by_age.filter(pl.col("age_group") == age_group).to_pandas()
    data["date"] = pd.to_datetime(data["year_month"], format="%Y%m")
    
    ax.plot(data["date"], data["n_prescriptions"], linewidth=1.5, color=f"C{i}")
    ax.axvline(pd.Timestamp("2020-03-01"), color="red", linestyle="--", alpha=0.5)
    ax.set_title(f"Age {age_group}")
    ax.tick_params(axis='x', rotation=45)

# Hide empty subplot
axes[5].set_visible(False)

fig.suptitle("Benzodiazepine Prescriptions by Age Group (Synthetic Data)", fontsize=14)
fig.supxlabel("Date")
fig.supylabel("Number of Prescriptions")

plt.tight_layout()
plt.savefig(project_root / "outputs" / "figures" / "trends_by_age_group.png", dpi=150)
plt.show()
print("Figure saved to outputs/figures/trends_by_age_group.png")


#%% SECTION 8: Loading Real Data (Template)
# =========================================
# This section shows how to load your actual VDI data.
# Modify the file paths to match your data location.

print("=" * 60)
print("LOADING REAL DATA - TEMPLATE")
print("=" * 60)
print()

# Define your data paths - MODIFY THESE!
DATA_DIR = project_root / "data" / "raw"

# Example: List available CSV files
csv_files = list(DATA_DIR.glob("*.csv"))
print(f"CSV files found in {DATA_DIR}:")
for f in csv_files:
    size_mb = f.stat().st_size / (1024 * 1024) if f.exists() else 0
    print(f"  - {f.name} ({size_mb:.1f} MB)")

if not csv_files:
    print("  (No CSV files found - add your data extracts here)")
    print()
    print("When you have data, uncomment the code below:")
    print("""
# UNCOMMENT AND MODIFY THIS CODE:
# --------------------------------
# pharma_files = [
#     DATA_DIR / "pharma_2017.csv",
#     DATA_DIR / "pharma_2018.csv",
#     DATA_DIR / "pharma_2019.csv",
#     DATA_DIR / "pharma_2020.csv",
#     DATA_DIR / "pharma_2021.csv",
#     DATA_DIR / "pharma_2022.csv",
#     DATA_DIR / "pharma_2023.csv",
#     DATA_DIR / "pharma_2024.csv",
#     DATA_DIR / "pharma_2025.csv",
# ]
# 
# # Lazy load all files (memory efficient!)
# lf_real = scan_pharmaceutical_data(pharma_files)
# lf_real = add_derived_columns(lf_real)
# 
# # Now run your analyses...
# monthly_counts = monthly_prescription_counts(lf_real).collect()
""")


#%% SECTION 9: Summary Statistics Function
# ========================================
# A helper function to compute summary stats for any dataset.

def summarise_pharmaceutical_data(df: pl.DataFrame) -> None:
    """Print summary statistics for pharmaceutical data."""
    
    print("=" * 60)
    print("DATA SUMMARY")
    print("=" * 60)
    print()
    
    print(f"Total prescriptions: {len(df):,}")
    print(f"Unique patients: {df['patient_id'].n_unique():,}")
    print(f"Date range: {df['dispensing_date'].min()} to {df['dispensing_date'].max()}")
    print()
    
    print("Prescriptions by drug class:")
    class_counts = df.group_by("drug_class").agg(
        pl.len().alias("n"),
        pl.col("patient_id").n_unique().alias("n_patients")
    ).sort("n", descending=True)
    print(class_counts)
    print()
    
    print("Age distribution:")
    print(f"  Mean: {df['age_years'].mean():.1f} years")
    print(f"  Median: {df['age_years'].median():.1f} years")
    print(f"  Range: {df['age_years'].min()} - {df['age_years'].max()}")
    print()
    
    print("Sex distribution:")
    sex_counts = df.group_by("sex").agg(pl.len().alias("n"))
    total = len(df)
    for row in sex_counts.iter_rows(named=True):
        pct = 100 * row["n"] / total
        print(f"  {row['sex']}: {row['n']:,} ({pct:.1f}%)")

# Run on synthetic data
summarise_pharmaceutical_data(df_with_derived)


#%% SECTION 10: Next Steps
# ========================
print("""
=" * 60
NEXT STEPS
=" * 60

You've completed the getting started guide! Here's what to do next:

1. ADD YOUR DATA
   Place your VDI extracts in: data/raw/
   
2. RUN THE ED ANALYSIS
   Open: notebooks/02_ed_exploration.py
   This will analyse ED presentation trends.
   
3. RUN THE PHARMACEUTICAL ANALYSIS
   Open: notebooks/03_pharma_analysis.py
   This will analyse prescribing patterns and link to ED data.

4. CUSTOMISE
   The code in src/intox_analysis/ can be modified to suit your needs.
   Key files:
   - data/pharmaceutical.py : Drug classification and processing
   - data/schemas.py : ED data validation
   - analysis/trends.py : Segmented regression (to be created)

5. ASK FOR HELP
   If you get stuck, copy the error message and ask Claude!

Good luck with your analysis!
""")
