# -*- coding: utf-8 -*-
"""
02_load_pharma_data.py
======================

This script demonstrates how to load and process pharmaceutical (Flusso F)
data using Polars for memory efficiency. The pharmaceutical data is large
(~1GB per year), so we use lazy evaluation to process it without loading
everything into memory at once.

This script shows:
1. How to scan large CSV files with Polars lazy evaluation
2. How to classify drugs by ATC code
3. How to compute monthly prescription counts
4. How to identify chronic users

BEFORE RUNNING: Place your pharmaceutical CSVs in the data/raw/ folder.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# =============================================================================
# CHECK POLARS INSTALLATION
# =============================================================================

try:
    import polars as pl
    print(f"✓ Polars version {pl.__version__} installed")
except ImportError:
    print("✗ Polars not installed!")
    print("\nTo install, run in Anaconda Prompt:")
    print("  pip install polars")
    print("\nOr with conda:")
    print("  conda install polars -c conda-forge")
    sys.exit(1)

# Import our pharmaceutical module
from intox_analysis.data.pharmaceutical import (
    classify_atc_code,
    scan_pharmaceutical_data,
    add_derived_columns,
    monthly_prescription_counts,
    identify_chronic_users,
    generate_synthetic_pharmaceutical_data,
    ATC_BENZODIAZEPINES,
    ATC_Z_DRUGS,
)

# =============================================================================
# CONFIGURATION - UPDATE THESE FOR YOUR DATA
# =============================================================================

DATA_DIR = project_root / "data" / "raw"

# List your pharmaceutical CSV files here (one per year)
# Update these filenames to match your actual files!
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

# Only keep files that actually exist
PHARMA_FILES = [f for f in PHARMA_FILES if f.exists()]

# =============================================================================
# STEP 1: EXPLORE ATC CODE CLASSIFICATION
# =============================================================================

print("\n" + "=" * 70)
print("STEP 1: ATC Code Classification")
print("=" * 70)

# Test with drugs confirmed in your VDI data
test_drugs = [
    ("N05BA12", "ALPRAZOLAM"),
    ("N05BA06", "LORAZEPAM"),
    ("N05CF01", "ZOPICLONE"),
    ("N05CF02", "ZOLPIDEM"),
    ("N05AL07", "LEVOSULPIRIDE"),
    ("N06AB06", "SERTRALINE"),
    ("N02AX02", "TRAMADOL"),
    ("A02BC01", "OMEPRAZOLE"),  # Not psychotropic (control)
]

print("\nDrug Classification Results:")
print("-" * 50)
for atc, name in test_drugs:
    result = classify_atc_code(atc)
    is_psych = "✓ Psychotropic" if result["is_psychotropic"] else "✗ Not psychotropic"
    print(f"{atc} ({name})")
    print(f"  {is_psych} | Class: {result['drug_class']}")

# Show known drug lists
print(f"\nKnown benzodiazepines in database: {len(ATC_BENZODIAZEPINES)}")
print(f"Known Z-drugs in database: {len(ATC_Z_DRUGS)}")

# =============================================================================
# STEP 2: LOAD PHARMACEUTICAL DATA
# =============================================================================

print("\n" + "=" * 70)
print("STEP 2: Loading Pharmaceutical Data")
print("=" * 70)

if not PHARMA_FILES:
    print("\n⚠ No pharmaceutical data files found!")
    print(f"  Looking in: {DATA_DIR}")
    print("\nTo proceed with your actual data:")
    print("1. Export pharmaceutical data from VDI as CSV files")
    print("2. Place them in:", DATA_DIR)
    print("3. Update PHARMA_FILES list above with correct filenames")
    print("4. Re-run this script")
    
    print("\n" + "-" * 40)
    print("Using SYNTHETIC DATA for demonstration...")
    print("-" * 40)
    
    # Generate synthetic data for demonstration
    print("Generating 50,000 synthetic prescription records...")
    df = generate_synthetic_pharmaceutical_data(
        n_records=50_000,
        n_patients=5_000,
        start_year=2017,
        end_year=2025,
        seed=42,
    )
    print(f"Generated {len(df):,} records for {df['patient_id'].n_unique():,} patients")
    
    # Convert to lazy frame for consistent API
    lf = df.lazy()
    USE_SYNTHETIC = True

else:
    print(f"\nFound {len(PHARMA_FILES)} pharmaceutical data files:")
    for f in PHARMA_FILES:
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"  • {f.name} ({size_mb:.1f} MB)")
    
    # Scan files lazily - this does NOT load data into memory yet!
    print("\nCreating lazy scan (no memory used yet)...")
    lf = scan_pharmaceutical_data(PHARMA_FILES)
    USE_SYNTHETIC = False
    print("✓ Lazy frame created")

# =============================================================================
# STEP 3: ADD DERIVED COLUMNS
# =============================================================================

print("\n" + "=" * 70)
print("STEP 3: Adding Derived Columns")
print("=" * 70)

# This adds drug class flags, year_month, etc.
# Still lazy - no computation happens yet!
lf_enriched = add_derived_columns(lf)

print("Added columns:")
print("  • year_month (YYYYMM)")
print("  • year, month")
print("  • is_benzodiazepine (bool)")
print("  • is_z_drug (bool)")
print("  • is_opioid (bool)")
print("  • is_antidepressant (bool)")
print("  • is_psychotropic (bool)")
print("  • drug_class (categorical)")
print("  • days_to_dispense")

# =============================================================================
# STEP 4: COMPUTE MONTHLY COUNTS (This is where computation happens!)
# =============================================================================

print("\n" + "=" * 70)
print("STEP 4: Monthly Prescription Counts")
print("=" * 70)

# This builds a query but still doesn't execute it
query = monthly_prescription_counts(
    lf_enriched,
    drug_classes=["benzodiazepine", "z_drug"],  # Focus on sedatives
    by_drug_class=True,
)

# NOW we execute the query with .collect()
# For large files, this is where you'll see memory usage
print("\nExecuting query (this loads and processes data)...")
monthly_df = query.collect()
print(f"✓ Query complete: {len(monthly_df):,} rows")

# Show results
print("\nMonthly prescription counts (first 20 rows):")
print(monthly_df.head(20))

# =============================================================================
# STEP 5: OVERALL STATISTICS
# =============================================================================

print("\n" + "=" * 70)
print("STEP 5: Summary Statistics")
print("=" * 70)

# Quick overall stats (collect a small summary)
summary = (
    lf_enriched
    .select([
        pl.len().alias("total_prescriptions"),
        pl.col("patient_id").n_unique().alias("unique_patients"),
        pl.col("is_benzodiazepine").sum().alias("n_benzodiazepine"),
        pl.col("is_z_drug").sum().alias("n_z_drug"),
        pl.col("is_opioid").sum().alias("n_opioid"),
        pl.col("is_antidepressant").sum().alias("n_antidepressant"),
        pl.col("is_psychotropic").sum().alias("n_psychotropic_total"),
        pl.col("age_years").mean().alias("mean_age"),
        (pl.col("sex") == "F").mean().alias("prop_female"),
    ])
    .collect()
)

print("\nOverall Summary:")
print(f"  Total prescriptions: {summary['total_prescriptions'][0]:,}")
print(f"  Unique patients: {summary['unique_patients'][0]:,}")
print(f"  Mean age: {summary['mean_age'][0]:.1f} years")
print(f"  % Female: {100*summary['prop_female'][0]:.1f}%")
print()
print("Psychotropic Drug Prescriptions:")
print(f"  Benzodiazepines: {summary['n_benzodiazepine'][0]:,}")
print(f"  Z-drugs: {summary['n_z_drug'][0]:,}")
print(f"  Opioids: {summary['n_opioid'][0]:,}")
print(f"  Antidepressants: {summary['n_antidepressant'][0]:,}")
print(f"  Total psychotropic: {summary['n_psychotropic_total'][0]:,}")

# =============================================================================
# STEP 6: IDENTIFY CHRONIC USERS
# =============================================================================

print("\n" + "=" * 70)
print("STEP 6: Identifying Chronic Users")
print("=" * 70)

print("\nDefinition: ≥4 prescriptions/year over ≥90 days")
print("(This helps distinguish therapeutic use from sporadic/misuse)")

# Identify chronic benzodiazepine users
chronic = identify_chronic_users(
    lf_enriched,
    drug_classes=["benzodiazepine", "z_drug"],
    min_prescriptions_per_year=4,
).collect()

n_chronic = chronic["is_chronic"].sum()
n_total = len(chronic)
print(f"\nPatients with benzo/Z-drug prescriptions: {n_total:,}")
print(f"Chronic users (≥4 Rx/year): {n_chronic:,} ({100*n_chronic/n_total:.1f}%)")
print(f"Sporadic users (<4 Rx/year): {n_total - n_chronic:,} ({100*(n_total-n_chronic)/n_total:.1f}%)")

# Distribution of prescriptions among chronic users
chronic_stats = chronic.filter(pl.col("is_chronic")).select([
    pl.col("n_prescriptions").mean().alias("mean_rx"),
    pl.col("n_prescriptions").median().alias("median_rx"),
    pl.col("duration_days").mean().alias("mean_duration"),
])
print(f"\nAmong chronic users:")
print(f"  Mean prescriptions: {chronic_stats['mean_rx'][0]:.1f}")
print(f"  Median prescriptions: {chronic_stats['median_rx'][0]:.1f}")
print(f"  Mean duration of use: {chronic_stats['mean_duration'][0]:.0f} days")

# =============================================================================
# STEP 7: TIME TREND VISUALISATION (if matplotlib available)
# =============================================================================

print("\n" + "=" * 70)
print("STEP 7: Visualisation (Optional)")
print("=" * 70)

try:
    import matplotlib.pyplot as plt
    
    # Prepare data for plotting
    plot_data = (
        monthly_df
        .group_by("year_month")
        .agg(pl.col("n_prescriptions").sum())
        .sort("year_month")
        .to_pandas()
    )
    
    # Create figure
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(range(len(plot_data)), plot_data["n_prescriptions"], marker="o", markersize=3)
    ax.set_xlabel("Month (from Jan 2017)")
    ax.set_ylabel("Total Benzo + Z-drug Prescriptions")
    ax.set_title("Monthly Benzodiazepine and Z-drug Prescriptions")
    
    # Add COVID line if in range
    covid_month = (2020 - 2017) * 12 + 2  # March 2020
    if covid_month < len(plot_data):
        ax.axvline(covid_month, color="red", linestyle="--", alpha=0.7, label="COVID-19 (Mar 2020)")
        ax.legend()
    
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    
    # Save figure
    output_dir = project_root / "outputs" / "figures"
    output_dir.mkdir(parents=True, exist_ok=True)
    fig_path = output_dir / "pharma_monthly_trend.png"
    plt.savefig(fig_path, dpi=150)
    print(f"✓ Figure saved: {fig_path}")
    
    # Show in Spyder
    plt.show()
    
except ImportError:
    print("matplotlib not available - skipping visualisation")
    print("Install with: pip install matplotlib")

# =============================================================================
# DONE
# =============================================================================

print("\n" + "=" * 70)
print("DONE!")
print("=" * 70)

print("\nVariables available in Variable Explorer:")
print("  • lf_enriched: Polars LazyFrame with all data (use .collect() to load)")
print("  • monthly_df: Monthly prescription counts")
print("  • chronic: Patient-level chronic user identification")
print("  • summary: Overall statistics")

if USE_SYNTHETIC:
    print("\n⚠ Note: Results above are based on SYNTHETIC data.")
    print("   Replace with your actual VDI data for real analysis.")
