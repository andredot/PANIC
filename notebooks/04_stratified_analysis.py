# -*- coding: utf-8 -*-
"""
04_stratified_analysis.py
=========================

This script performs stratified trend analysis to answer:

Q3: Who are the patients? How do trends vary by sex, age, and residence (urban/rural)?
Q5: Is the trend linked to prescribing changes (chronic vs sporadic users)?

NEW DATA FIELDS USED:
- ED facility identifier (for heterogeneity analysis)
- Residence (town/comune) → classified as urban/rural using ISTAT FUA lookup
- DDD (Defined Daily Dose) in pharmaceutical data

OUTPUTS:
- Stratified trend tables (by sex, age group, residence type)
- Facility heterogeneity analysis
- Prescription-intoxication linkage analysis
- Forest plots and stratified line charts
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

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
)

# =============================================================================
# CONFIGURATION
# =============================================================================

DATA_DIR = project_root / "data" / "raw"
LOOKUP_DIR = project_root / "data" / "lookups"
OUTPUT_DIR = project_root / "outputs"

# File paths (UPDATE THESE)
ED_FILE = DATA_DIR / "ed_presentations.csv"
FUA_LOOKUP_FILE = LOOKUP_DIR / "istat_fua_comuni.csv"

# Column names for new fields (UPDATE if different in your extract)
RESIDENCE_COLUMN = "residence"      # Town/comune name
FACILITY_COLUMN = "facility_id"     # ED facility identifier

# Age group definitions
AGE_GROUPS = {
    "0-17": (0, 17),
    "18-34": (18, 34),
    "35-54": (35, 54),
    "55-74": (55, 74),
    "75+": (75, 150),
}

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

if not ED_FILE.exists():
    print(f"\n⚠ Data file not found: {ED_FILE}")
    print("\nCreating SYNTHETIC DATA for demonstration...")
    
    # Generate synthetic data with new fields
    np.random.seed(42)
    n_records = 30000
    
    years = np.random.choice([2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025], 
                              n_records, p=[0.08, 0.09, 0.10, 0.11, 0.12, 0.12, 0.13, 0.13, 0.12])
    
    # Drug codes with more benzos in recent years
    def get_diagnosis(year):
        if year >= 2023:
            weights = [0.35, 0.15, 0.10, 0.08, 0.05, 0.27]  # More benzos
        elif year >= 2020:
            weights = [0.25, 0.15, 0.10, 0.08, 0.05, 0.37]
        else:
            weights = [0.15, 0.12, 0.10, 0.08, 0.05, 0.50]
        codes = ["T424X2A", "T400X1A", "T391X1A", "T436X2A", "9694", "J189"]
        return np.random.choice(codes, p=weights)
    
    diagnoses = [get_diagnosis(y) for y in years]
    
    # Residence (mix of urban and rural comuni in Lombardy)
    urban_comuni = ["Milano", "Bergamo", "Brescia", "Monza", "Como", "Varese", "Pavia"]
    rural_comuni = ["Sondrio", "Morbegno", "Chiavenna", "Bormio", "Livigno", "Tirano"]
    all_comuni = urban_comuni + rural_comuni
    residence_weights = [0.25, 0.12, 0.12, 0.08, 0.06, 0.05, 0.05] + [0.04, 0.03, 0.03, 0.03, 0.02, 0.02]
    
    # Facilities
    facilities = ["OSP_MI_01", "OSP_MI_02", "OSP_BG_01", "OSP_BS_01", "OSP_CO_01"]
    
    df = pd.DataFrame({
        "patient_id": [f"MB-{''.join(np.random.choice(list('0123456789ABCDEF'), 64))}" for _ in range(n_records)],
        "year_month": [f"{y}{np.random.randint(1,13):02d}" for y in years],
        "age_years": np.random.normal(42, 20, n_records).astype(int).clip(5, 95),
        "sex_registry": np.random.choice(["M", "F"], n_records, p=[0.42, 0.58]),
        "diagnosis_code_primary": diagnoses,
        "diagnosis_code_secondary": ["_"] * n_records,
        "disposition_code": np.random.choice(["1", "2", "3"], n_records, p=[0.78, 0.17, 0.05]),
        "residence": np.random.choice(all_comuni, n_records, p=residence_weights),
        "facility_id": np.random.choice(facilities, n_records, p=[0.35, 0.25, 0.20, 0.12, 0.08]),
    })
    
    print(f"Generated {len(df):,} synthetic records")
    USE_SYNTHETIC = True

else:
    df = pd.read_csv(ED_FILE)
    print(f"Loaded {len(df):,} records")
    USE_SYNTHETIC = False
    
    # Rename columns if needed
    if "Cod Diagnosi" in df.columns:
        column_mapping = {
            "Codice Fiscale Assistito MICROBIO": "patient_id",
            "Annomese_INGR": "year_month",
            "Eta(calcolata)": "age_years",
            "Sesso (anag ass.to)": "sex_registry",
            "Cod Diagnosi": "diagnosis_code_primary",
            "Cod Diagnosi Secondaria": "diagnosis_code_secondary",
            "Codice Esito": "disposition_code",
            # Add your actual column names for new fields:
            # "YOUR_RESIDENCE_COL": "residence",
            # "YOUR_FACILITY_COL": "facility_id",
        }
        df = df.rename(columns=column_mapping)

# -----------------------------------------------------------------------------
# STEP 2: PROCESS DATA
# -----------------------------------------------------------------------------

print("\n--- Step 2: Processing Data ---")

# Process ED data (adds intoxication classification)
df = process_ed_data(
    df,
    diagnosis_col_primary="diagnosis_code_primary",
    diagnosis_col_secondary="diagnosis_code_secondary",
    date_col="year_month",
    esito_col="disposition_code",
)

# Add age groups
df["age_group"] = df["age_years"].apply(assign_age_group)

# Standardise sex column
if "sex_registry" in df.columns:
    df["sex"] = df["sex_registry"]
elif "sex" not in df.columns:
    df["sex"] = "Unknown"

# -----------------------------------------------------------------------------
# STEP 3: URBAN/RURAL CLASSIFICATION
# -----------------------------------------------------------------------------

print("\n--- Step 3: Urban/Rural Classification ---")

if "residence" in df.columns:
    if FUA_LOOKUP_FILE.exists():
        try:
            mapping, lookup_df = setup_urban_rural_classification(FUA_LOOKUP_FILE)
            df = add_urban_rural_column(df, "residence", mapping, "residence_type")
            print(f"Classified {df['residence_type'].notna().sum():,} residence records")
            print(df["residence_type"].value_counts())
        except Exception as e:
            print(f"Warning: Could not load FUA lookup: {e}")
            df["residence_type"] = "Unknown"
    else:
        print(f"FUA lookup not found at {FUA_LOOKUP_FILE}")
        print("Creating synthetic urban/rural classification...")
        # For synthetic data, classify based on our known lists
        urban_comuni = ["Milano", "Bergamo", "Brescia", "Monza", "Como", "Varese", "Pavia"]
        df["residence_type"] = df["residence"].apply(
            lambda x: "Urban" if x in urban_comuni else "Rural"
        )
        print(df["residence_type"].value_counts())
else:
    print("No residence column found - skipping urban/rural classification")
    df["residence_type"] = "Unknown"

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
