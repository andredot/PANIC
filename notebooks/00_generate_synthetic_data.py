# -*- coding: utf-8 -*-
"""
00_generate_synthetic_data.py
=============================

Run this script FIRST to generate synthetic data for testing all analyses
without needing access to the VDI.

This creates:
- data/raw/ed_presentations.csv (ED syndromic surveillance)
- data/raw/pharma_synthetic.csv (Pharmaceutical dispensing with DDD)
- data/lookups/istat_fua_comuni.csv (Urban/rural classification)

After running this, you can run all other scripts (01-05) with realistic
synthetic data that mimics the actual Lombardy health data structure.

The synthetic data includes:
- Increasing benzodiazepine intoxications over time (the trend we're studying)
- Patient overlap between ED and pharma (for linkage analysis)
- Urban/rural residence distribution
- Multiple ED facilities
- Realistic age/sex distributions
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from intox_analysis.data.generators import generate_all_synthetic_data

# =============================================================================
# CONFIGURATION
# =============================================================================

# Output directory (relative to project root)
DATA_DIR = project_root / "data"

# Sample sizes (adjust based on your testing needs)
# Smaller = faster, larger = more realistic distributions
N_ED_RECORDS = 50000        # ED presentations
N_PHARMA_RECORDS = 100000   # Pharmaceutical prescriptions

# Random seed for reproducibility
SEED = 42

# =============================================================================
# GENERATE DATA
# =============================================================================

print("=" * 70)
print("SYNTHETIC DATA GENERATOR")
print("=" * 70)
print()
print("This script creates realistic synthetic data for testing the")
print("analysis pipeline without access to the VDI.")
print()
print(f"Output directory: {DATA_DIR}")
print(f"ED records: {N_ED_RECORDS:,}")
print(f"Pharma records: {N_PHARMA_RECORDS:,}")
print()

# Generate all data
data = generate_all_synthetic_data(
    output_dir=DATA_DIR,
    n_ed_records=N_ED_RECORDS,
    n_pharma_records=N_PHARMA_RECORDS,
    seed=SEED,
    save_files=True,
)

# =============================================================================
# SUMMARY
# =============================================================================

print()
print("=" * 70)
print("DATA SUMMARY")
print("=" * 70)

# ED summary
ed_df = data["ed"]
print(f"\nED Presentations ({len(ed_df):,} records):")
print(f"  Date range: {ed_df['Annomese_INGR'].min()} to {ed_df['Annomese_INGR'].max()}")
print(f"  Unique patients: {ed_df['Codice Fiscale Assistito MICROBIO'].nunique():,}")
print(f"  Facilities: {ed_df['facility_id'].nunique()}")

# Count intoxications
intox_codes = ed_df["Cod Diagnosi"].str.startswith(("T4", "96"))
print(f"  Drug intoxications: {intox_codes.sum():,} ({100*intox_codes.mean():.1f}%)")

# Pharma summary
pharma_df = data["pharma"]
print(f"\nPharmaceutical Data ({len(pharma_df):,} records):")
print(f"  Unique patients: {pharma_df['Codice Fiscale Assistito MICROBIO'].nunique():,}")
print(f"  Total DDD: {pharma_df['DDD'].sum():,.0f}")

# Benzodiazepine count
benzo_codes = pharma_df["Cod Atc"].str.startswith("N05B")
print(f"  Benzodiazepine Rx: {benzo_codes.sum():,} ({100*benzo_codes.mean():.1f}%)")

# FUA summary
fua_df = data["fua"]
print(f"\nFUA Lookup ({len(fua_df)} municipalities):")
urban = (fua_df["Città (City/Greater City) 2021"] != "No City/Città").sum()
rural = len(fua_df) - urban
print(f"  Urban: {urban}")
print(f"  Rural: {rural}")

# =============================================================================
# NEXT STEPS
# =============================================================================

print()
print("=" * 70)
print("NEXT STEPS")
print("=" * 70)
print("""
Synthetic data has been generated! You can now run:

  1. 01_load_ed_data.py      - Explore ED data structure
  2. 02_load_pharma_data.py  - Explore pharmaceutical data (needs Polars)
  3. 03_intoxication_trends.py - Drug class trend analysis
  4. 04_stratified_analysis.py - Sex/age/residence stratification
  5. 05_prescription_linkage.py - Prescription-intoxication linkage

The synthetic data includes realistic features:
  ✓ Increasing benzodiazepine intoxications over time
  ✓ Patient overlap for linkage analysis (~60% of intox patients have Rx)
  ✓ Urban/rural residence distribution
  ✓ Multiple ED facilities with varying volumes
  ✓ Chronic vs sporadic prescription users
  ✓ DDD values for prescribing rate calculations

When you have real data from the VDI, simply replace the CSV files
in data/raw/ and re-run the analysis scripts.
""")
