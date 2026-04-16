# -*- coding: utf-8 -*-
"""
06_stratified_analysis.py
=========================

Stratified trend analysis to answer:

Q3: Who are the patients? How do trends vary by sex, age, and residence (urban/rural)?

Analyses stratified by:
- Sex (M/F)
- Age group (0-17, 18-34, 35-54, 55-74, 75+)
- Residence (urban/rural) - OPTIONAL, requires FUA lookup
- ED facility

OUTPUTS:
- Stratified trend tables (CSV)
- Forest plots and stratified line charts (PNG)

All configuration comes from config.py
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Import configuration
from config import (
    DATA_DIR, LOOKUPS_DIR, OUTPUT_DIR, FIGURES_DIR, TABLES_DIR,
    PROCESSED_DIR, ED_DATA_FILE, FUA_LOOKUP_FILE,
    AGE_GROUPS, AGE_GROUP_ORDER,
)

# Import our modules
from intox_analysis.analysis.trends import (
    process_ed_data,
    classify_drug_intoxication_detailed,
    compute_annual_counts,
    compute_trend_metrics,
    create_trend_summary_table,
)
from intox_analysis.data.residence import (
    setup_urban_rural_classification,
    classify_residence,
    add_urban_rural_column,
    is_fua_available,
)

# =============================================================================
# CONFIGURATION
# =============================================================================

# Column names for new fields (UPDATE if different in your extract)
RESIDENCE_COLUMN = "residence"      # Town/comune name
FACILITY_COLUMN = "facility_id"     # ED facility identifier

LAST_N_YEARS = 3  # For trend calculations


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def assign_age_group(age: int) -> str:
    """Assign age to age group."""
    if pd.isna(age):
        return "Unknown"
    age = int(age)
    for group_name, (min_age, max_age) in AGE_GROUPS.items():
        if min_age <= age <= max_age:
            return group_name
    return "Unknown"


def compute_stratified_trends(
    df: pd.DataFrame,
    stratify_by: str,
    outcome_col: str = "is_intoxication",
    year_col: str = "year",
    last_n_years: int = 3,
) -> pd.DataFrame:
    """
    Compute trend metrics stratified by a categorical variable.
    
    Parameters
    ----------
    df : pd.DataFrame
        Processed ED data.
    stratify_by : str
        Column to stratify by (e.g., "sex", "age_group", "residence_type").
    outcome_col : str
        Column indicating outcome (True/False).
    year_col : str
        Year column.
    last_n_years : int
        Number of years for trend calculation.
        
    Returns
    -------
    pd.DataFrame
        Trend metrics for each stratum.
    """
    results = []
    
    for stratum in df[stratify_by].dropna().unique():
        stratum_df = df[df[stratify_by] == stratum]
        
        # Get annual counts
        annual = stratum_df[stratum_df[outcome_col]].groupby(year_col).size()
        years = sorted(annual.index)
        recent_years = years[-last_n_years:] if len(years) >= last_n_years else years
        
        counts = [annual.get(y, 0) for y in recent_years]
        
        # Compute metrics
        avg_annual = np.mean(counts)
        total = sum(counts)
        
        # YoY growth
        yoy_rates = []
        for i in range(1, len(counts)):
            if counts[i-1] > 0:
                growth = (counts[i] - counts[i-1]) / counts[i-1] * 100
                yoy_rates.append(growth)
        avg_yoy = np.nanmean(yoy_rates) if yoy_rates else 0
        
        results.append({
            "Stratum": stratum,
            "Avg Annual Cases": round(avg_annual, 1),
            "Total (3yr)": total,
            "Avg YoY Growth (%)": round(avg_yoy, 1),
        })
    
    return pd.DataFrame(results).sort_values("Avg Annual Cases", ascending=False)


def plot_stratified_trends(
    df: pd.DataFrame,
    stratify_by: str,
    title: str,
    figsize: tuple = (12, 6),
) -> plt.Figure:
    """
    Plot annual trends stratified by a variable.
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    df_intox = df[df["is_intoxication"]]
    
    for stratum in df_intox[stratify_by].dropna().unique():
        stratum_df = df_intox[df_intox[stratify_by] == stratum]
        annual = stratum_df.groupby("year").size()
        ax.plot(annual.index, annual.values, marker="o", label=stratum, linewidth=2)
    
    ax.axvline(2020, color="red", linestyle="--", alpha=0.5, label="COVID-19")
    ax.set_xlabel("Year")
    ax.set_ylabel("Number of Intoxication Cases")
    ax.set_title(title, fontweight="bold")
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    
    return fig


def plot_forest(
    metrics_df: pd.DataFrame,
    stratum_col: str = "Stratum",
    estimate_col: str = "Avg YoY Growth (%)",
    title: str = "Forest Plot: YoY Growth by Subgroup",
    figsize: tuple = (10, 6),
) -> plt.Figure:
    """
    Create a forest plot showing growth rates by subgroup.
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    strata = metrics_df[stratum_col].values
    estimates = metrics_df[estimate_col].values
    y_pos = np.arange(len(strata))
    
    # Color by positive/negative growth
    colors = ["#d62728" if e > 0 else "#2ca02c" for e in estimates]
    
    ax.barh(y_pos, estimates, color=colors, alpha=0.7)
    ax.axvline(0, color="black", linewidth=1)
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(strata)
    ax.set_xlabel("Average Year-on-Year Growth (%)")
    ax.set_title(title, fontweight="bold")
    ax.grid(True, axis="x", alpha=0.3)
    
    plt.tight_layout()
    return fig


def analyse_facility_heterogeneity(
    df: pd.DataFrame,
    facility_col: str = "facility_id",
    last_n_years: int = 3,
) -> pd.DataFrame:
    """
    Analyse trends by ED facility to check for heterogeneity.
    """
    df_intox = df[df["is_intoxication"]].copy()
    
    results = []
    for facility in df_intox[facility_col].dropna().unique():
        fac_df = df_intox[df_intox[facility_col] == facility]
        
        # Get annual counts
        annual = fac_df.groupby("year").size()
        years = sorted(annual.index)
        recent_years = years[-last_n_years:] if len(years) >= last_n_years else years
        
        counts = [annual.get(y, 0) for y in recent_years]
        avg_annual = np.mean(counts)
        
        # YoY growth
        yoy_rates = []
        for i in range(1, len(counts)):
            if counts[i-1] > 0:
                growth = (counts[i] - counts[i-1]) / counts[i-1] * 100
                yoy_rates.append(growth)
        avg_yoy = np.nanmean(yoy_rates) if yoy_rates else 0
        
        results.append({
            "Facility": facility,
            "Avg Annual Cases": round(avg_annual, 1),
            "Total (3yr)": sum(counts),
            "Avg YoY Growth (%)": round(avg_yoy, 1),
        })
    
    return pd.DataFrame(results).sort_values("Avg Annual Cases", ascending=False)


# =============================================================================
# MAIN ANALYSIS
# =============================================================================

print("=" * 70)
print("STRATIFIED ANALYSIS: Sex, Age, Residence, Facility")
print("=" * 70)

# -----------------------------------------------------------------------------
# STEP 1: LOAD DATA
# -----------------------------------------------------------------------------

print("\n--- Step 1: Loading Data ---")

# Try processed file first
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

else:
    print(f"\nData file not found: {ED_DATA_FILE}")
    print("Generating SYNTHETIC DATA for testing...")
    
    from intox_analysis.data.generators import generate_ed_data
    from config import STUDY_YEARS
    
    df = generate_ed_data(n_records=50000, years=STUDY_YEARS)
    print(f"Generated {len(df):,} synthetic records")
    USE_SYNTHETIC = True

# -----------------------------------------------------------------------------
# STEP 2: PROCESS DATA
# -----------------------------------------------------------------------------

print("\n--- Step 2: Processing Data ---")

# Check if already processed
if "is_intoxication" not in df.columns:
    df = process_ed_data(
        df,
        diagnosis_col_primary="diagnosis_code_primary" if "diagnosis_code_primary" in df.columns else "diagnosis_code",
        diagnosis_col_secondary="diagnosis_code_secondary" if "diagnosis_code_secondary" in df.columns else None,
        date_col="year_month",
        esito_col="disposition_code" if "disposition_code" in df.columns else None,
    )

# Add age groups
if "age_group" not in df.columns:
    age_col = "age_years" if "age_years" in df.columns else "age"
    if age_col in df.columns:
        df["age_group"] = df[age_col].apply(assign_age_group)
    else:
        df["age_group"] = "Unknown"

# Standardise sex column
if "sex" not in df.columns:
    if "sex_registry" in df.columns:
        df["sex"] = df["sex_registry"]
    else:
        df["sex"] = "Unknown"

# -----------------------------------------------------------------------------
# STEP 3: URBAN/RURAL CLASSIFICATION (OPTIONAL)
# -----------------------------------------------------------------------------

print("\n--- Step 3: Urban/Rural Classification ---")

HAS_RESIDENCE = RESIDENCE_COLUMN in df.columns

if HAS_RESIDENCE and is_fua_available(FUA_LOOKUP_FILE):
    try:
        mapping, lookup_df = setup_urban_rural_classification(FUA_LOOKUP_FILE)
        df = add_urban_rural_column(df, RESIDENCE_COLUMN, mapping, "residence_type")
        print(f"Classified {df['residence_type'].notna().sum():,} residence records")
        print(df["residence_type"].value_counts())
        HAS_RESIDENCE_TYPE = True
    except Exception as e:
        print(f"Warning: Could not load FUA lookup: {e}")
        df["residence_type"] = "Unknown"
        HAS_RESIDENCE_TYPE = False
elif HAS_RESIDENCE:
    print("FUA lookup not available - urban/rural classification skipped")
    df["residence_type"] = "Unknown"
    HAS_RESIDENCE_TYPE = False
else:
    print("Residence column not available - urban/rural classification skipped")
    df["residence_type"] = "Unknown"
    HAS_RESIDENCE_TYPE = False

# -----------------------------------------------------------------------------
# STEP 4: STRATIFIED TREND ANALYSIS
# -----------------------------------------------------------------------------

print("\n" + "=" * 70)
print("STRATIFIED TREND ANALYSIS (Q3)")
print("=" * 70)

n_intox = df["is_intoxication"].sum()
print(f"\nTotal intoxication cases: {n_intox:,}")

# --- BY SEX ---
print("\n--- Trends by Sex ---")
sex_trends = compute_stratified_trends(df, "sex", last_n_years=LAST_N_YEARS)
print(sex_trends.to_string(index=False))

# --- BY AGE GROUP ---
print("\n--- Trends by Age Group ---")
age_trends = compute_stratified_trends(df, "age_group", last_n_years=LAST_N_YEARS)
print(age_trends.to_string(index=False))

# --- BY RESIDENCE TYPE ---
print("\n--- Trends by Residence (Urban/Rural) ---")
if df["residence_type"].nunique() > 1:
    residence_trends = compute_stratified_trends(df, "residence_type", last_n_years=LAST_N_YEARS)
    print(residence_trends.to_string(index=False))
else:
    print("Insufficient residence data for stratification")
    residence_trends = None

# -----------------------------------------------------------------------------
# STEP 5: FACILITY HETEROGENEITY
# -----------------------------------------------------------------------------

print("\n" + "=" * 70)
print("FACILITY HETEROGENEITY ANALYSIS")
print("=" * 70)

if "facility_id" in df.columns and df["facility_id"].notna().sum() > 0:
    facility_trends = analyse_facility_heterogeneity(df, "facility_id", LAST_N_YEARS)
    print("\nTrends by ED Facility:")
    print(facility_trends.to_string(index=False))
    
    # Check heterogeneity
    growth_rates = facility_trends["Avg YoY Growth (%)"].values
    if len(growth_rates) > 1:
        growth_std = np.std(growth_rates)
        growth_range = np.max(growth_rates) - np.min(growth_rates)
        print(f"\nHeterogeneity check:")
        print(f"  Growth rate SD: {growth_std:.1f}%")
        print(f"  Growth rate range: {growth_range:.1f}%")
        if growth_std > 10:
            print("  ⚠ Substantial heterogeneity across facilities")
        else:
            print("  ✓ Relatively consistent trends across facilities")
else:
    print("No facility data available")
    facility_trends = None

# -----------------------------------------------------------------------------
# STEP 6: CREATE FIGURES
# -----------------------------------------------------------------------------

print("\n" + "=" * 70)
print("GENERATING FIGURES")
print("=" * 70)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
figures_dir = OUTPUT_DIR / "figures"
figures_dir.mkdir(exist_ok=True)

# Figure 1: Trends by sex
fig1 = plot_stratified_trends(df, "sex", "Drug Intoxication Trends by Sex")
fig1.savefig(figures_dir / "intox_trends_by_sex.png", dpi=150, bbox_inches="tight")
print("✓ Saved: intox_trends_by_sex.png")

# Figure 2: Trends by age group
fig2 = plot_stratified_trends(df, "age_group", "Drug Intoxication Trends by Age Group")
fig2.savefig(figures_dir / "intox_trends_by_age.png", dpi=150, bbox_inches="tight")
print("✓ Saved: intox_trends_by_age.png")

# Figure 3: Trends by residence type
if df["residence_type"].nunique() > 1:
    fig3 = plot_stratified_trends(df, "residence_type", "Drug Intoxication Trends: Urban vs Rural")
    fig3.savefig(figures_dir / "intox_trends_by_residence.png", dpi=150, bbox_inches="tight")
    print("✓ Saved: intox_trends_by_residence.png")

# Figure 4: Forest plot - Age groups
fig4 = plot_forest(age_trends, title="YoY Growth Rate by Age Group")
fig4.savefig(figures_dir / "forest_plot_age.png", dpi=150, bbox_inches="tight")
print("✓ Saved: forest_plot_age.png")

# Figure 5: Forest plot - Facilities
if facility_trends is not None and len(facility_trends) > 1:
    fig5 = plot_forest(facility_trends, stratum_col="Facility", title="YoY Growth Rate by ED Facility")
    fig5.savefig(figures_dir / "forest_plot_facilities.png", dpi=150, bbox_inches="tight")
    print("✓ Saved: forest_plot_facilities.png")

# -----------------------------------------------------------------------------
# STEP 7: SAVE TABLES
# -----------------------------------------------------------------------------

print("\n--- Saving Tables ---")

tables_dir = OUTPUT_DIR / "tables"
tables_dir.mkdir(exist_ok=True)

sex_trends.to_csv(tables_dir / "trends_by_sex.csv", index=False)
age_trends.to_csv(tables_dir / "trends_by_age_group.csv", index=False)
if residence_trends is not None:
    residence_trends.to_csv(tables_dir / "trends_by_residence.csv", index=False)
if facility_trends is not None:
    facility_trends.to_csv(tables_dir / "trends_by_facility.csv", index=False)

print("✓ Tables saved to:", tables_dir)

# -----------------------------------------------------------------------------
# STEP 8: SUMMARY
# -----------------------------------------------------------------------------

print("\n" + "=" * 70)
print("KEY FINDINGS")
print("=" * 70)

# Find highest growing groups
if len(sex_trends) > 0:
    top_sex = sex_trends.iloc[0]
    print(f"\nBy Sex: {top_sex['Stratum']} has highest growth ({top_sex['Avg YoY Growth (%)']:.1f}% YoY)")

if len(age_trends) > 0:
    top_age = age_trends.sort_values("Avg YoY Growth (%)", ascending=False).iloc[0]
    print(f"By Age: {top_age['Stratum']} has highest growth ({top_age['Avg YoY Growth (%)']:.1f}% YoY)")

if residence_trends is not None and len(residence_trends) > 0:
    top_res = residence_trends.sort_values("Avg YoY Growth (%)", ascending=False).iloc[0]
    print(f"By Residence: {top_res['Stratum']} has highest growth ({top_res['Avg YoY Growth (%)']:.1f}% YoY)")

if USE_SYNTHETIC:
    print("\n⚠ NOTE: Results above are based on SYNTHETIC data.")

plt.show()

print("\n" + "=" * 70)
print("ANALYSIS COMPLETE")
print("=" * 70)
