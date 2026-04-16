# -*- coding: utf-8 -*-
"""
07_prescription_linkage.py
==========================

Analyse the relationship between prescribing patterns and 
drug intoxication presentations (Research Question 5).

Key analyses:
1. DDD trends over time (by drug class)
2. Prescribing rates: DDD per 1000 population per day
3. Linkage: Were intoxication patients receiving prescriptions?
4. Chronic vs sporadic users among intoxication cases

REQUIRES:
- Pharmaceutical data with DDD column
- ED intoxication data
- Patient ID linkage between datasets

OUTPUTS:
- Prescribing trend tables and charts
- Chronic/sporadic user breakdown among intoxication cases

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
    DATA_DIR, OUTPUT_DIR, FIGURES_DIR, TABLES_DIR,
    PROCESSED_DIR, ED_DATA_FILE, PHARMA_SYNTHETIC_FILE,
    LOMBARDY_POPULATION, PRIMARY_DRUG_CLASSES,
    PRESCRIPTION_LOOKBACK_DAYS,
    CHRONIC_USER_MIN_PRESCRIPTIONS, CHRONIC_USER_MAX_GAP_DAYS,
    get_pharma_files,
)

# Check for Polars
try:
    import polars as pl
    HAS_POLARS = True
    print(f"[OK] Polars v{pl.__version__} available")
except ImportError:
    HAS_POLARS = False
    print("[--] Polars not installed - using pandas")

# =============================================================================
# CONFIGURATION
# =============================================================================

# Lookback period for prescription linkage (days before ED presentation)
LOOKBACK_DAYS = PRESCRIPTION_LOOKBACK_DAYS


# =============================================================================
# DDD CALCULATIONS
# =============================================================================

def compute_ddd_per_1000_per_day(
    total_ddd: float,
    population: int,
    days: int,
) -> float:
    """
    Compute DDD per 1000 population per day.
    
    This is the standard metric for comparing prescribing rates
    across populations and time periods.
    
    Formula: (Total DDD / Days) / (Population / 1000)
    
    Parameters
    ----------
    total_ddd : float
        Sum of DDDs dispensed.
    population : int
        Population size.
    days : int
        Number of days in the period.
        
    Returns
    -------
    float
        DDD per 1000 inhabitants per day.
    """
    if days == 0 or population == 0:
        return 0
    return (total_ddd / days) / (population / 1000)


def compute_monthly_ddd_rates(
    df: pd.DataFrame,
    ddd_col: str = "ddd",
    date_col: str = "dispensing_date",
    drug_class_col: str = "drug_class",
    population: int = LOMBARDY_POPULATION,
) -> pd.DataFrame:
    """
    Compute monthly DDD rates by drug class.
    
    Parameters
    ----------
    df : pd.DataFrame
        Pharmaceutical data with DDD column.
    ddd_col : str
        Column containing DDD values.
    date_col : str
        Date column.
    drug_class_col : str
        Drug class column.
    population : int
        Population for rate denominator.
        
    Returns
    -------
    pd.DataFrame
        Monthly DDD rates by drug class.
    """
    df = df.copy()
    
    # Extract year-month
    df["year_month"] = pd.to_datetime(df[date_col]).dt.to_period("M")
    
    # Aggregate DDD by month and drug class
    monthly = df.groupby(["year_month", drug_class_col])[ddd_col].sum().reset_index()
    monthly.columns = ["year_month", "drug_class", "total_ddd"]
    
    # Compute rate (assuming ~30 days per month)
    monthly["ddd_per_1000_day"] = monthly["total_ddd"].apply(
        lambda x: compute_ddd_per_1000_per_day(x, population, 30)
    )
    
    return monthly


def compute_annual_ddd_summary(
    df: pd.DataFrame,
    ddd_col: str = "ddd",
    year_col: str = "year",
    drug_class_col: str = "drug_class",
    population: int = LOMBARDY_POPULATION,
) -> pd.DataFrame:
    """
    Compute annual DDD summary by drug class.
    """
    annual = df.groupby([year_col, drug_class_col]).agg({
        ddd_col: "sum",
        "patient_id": "nunique",
    }).reset_index()
    annual.columns = ["year", "drug_class", "total_ddd", "n_patients"]
    
    # Compute rate (365 days)
    annual["ddd_per_1000_day"] = annual["total_ddd"].apply(
        lambda x: compute_ddd_per_1000_per_day(x, population, 365)
    )
    
    # DDD per patient (average treatment intensity)
    annual["ddd_per_patient"] = annual["total_ddd"] / annual["n_patients"]
    
    return annual


# =============================================================================
# PRESCRIPTION LINKAGE
# =============================================================================

def link_intoxications_to_prescriptions(
    ed_df: pd.DataFrame,
    pharma_df: pd.DataFrame,
    patient_id_col: str = "patient_id",
    ed_date_col: str = "presentation_date",
    pharma_date_col: str = "dispensing_date",
    lookback_days: int = 365,
) -> pd.DataFrame:
    """
    Link ED intoxication presentations to prior prescriptions.
    
    For each intoxication case, check if the patient had any relevant
    prescriptions in the lookback period.
    
    Parameters
    ----------
    ed_df : pd.DataFrame
        ED intoxication cases.
    pharma_df : pd.DataFrame
        Pharmaceutical data.
    patient_id_col : str
        Patient ID column (must match in both datasets).
    ed_date_col : str
        ED presentation date column.
    pharma_date_col : str
        Dispensing date column.
    lookback_days : int
        Days before presentation to look for prescriptions.
        
    Returns
    -------
    pd.DataFrame
        Intoxication cases enriched with prescription history.
    """
    print(f"Linking {len(ed_df):,} intoxication cases to prescription history...")
    
    ed_df = ed_df.copy()
    pharma_df = pharma_df.copy()
    
    # Ensure dates are datetime
    ed_df[ed_date_col] = pd.to_datetime(ed_df[ed_date_col])
    pharma_df[pharma_date_col] = pd.to_datetime(pharma_df[pharma_date_col])
    
    # Get unique intoxication patient IDs
    intox_patients = set(ed_df[patient_id_col].unique())
    
    # Filter pharma to only these patients (memory efficiency)
    pharma_relevant = pharma_df[pharma_df[patient_id_col].isin(intox_patients)].copy()
    print(f"Found {len(pharma_relevant):,} prescription records for intoxication patients")
    
    # For each intoxication case, check for prior prescriptions
    results = []
    
    for idx, row in ed_df.iterrows():
        patient = row[patient_id_col]
        ed_date = row[ed_date_col]
        
        # Find prescriptions in lookback window
        patient_rx = pharma_relevant[
            (pharma_relevant[patient_id_col] == patient) &
            (pharma_relevant[pharma_date_col] >= ed_date - pd.Timedelta(days=lookback_days)) &
            (pharma_relevant[pharma_date_col] < ed_date)
        ]
        
        had_rx = len(patient_rx) > 0
        n_rx = len(patient_rx)
        
        # Check drug classes
        if had_rx and "drug_class" in patient_rx.columns:
            drug_classes = patient_rx["drug_class"].unique().tolist()
            had_benzo_rx = "benzodiazepine" in drug_classes or "z_drug" in drug_classes
            had_opioid_rx = "opioid" in drug_classes
            total_ddd = patient_rx["ddd"].sum() if "ddd" in patient_rx.columns else np.nan
        else:
            drug_classes = []
            had_benzo_rx = False
            had_opioid_rx = False
            total_ddd = 0
        
        results.append({
            "idx": idx,
            "had_prior_rx": had_rx,
            "n_prior_rx": n_rx,
            "rx_drug_classes": drug_classes,
            "had_benzo_rx": had_benzo_rx,
            "had_opioid_rx": had_opioid_rx,
            "prior_ddd": total_ddd,
        })
    
    linkage_df = pd.DataFrame(results).set_index("idx")
    
    # Join results back to original ED data using index
    ed_enriched = ed_df.join(linkage_df)
    
    return ed_enriched


def classify_user_type(
    pharma_df: pd.DataFrame,
    patient_id_col: str = "patient_id",
    drug_class_col: str = "drug_class",
    date_col: str = "dispensing_date",
    min_rx_for_chronic: int = 4,
    min_duration_days: int = 90,
) -> pd.DataFrame:
    """
    Classify patients as chronic or sporadic users.
    
    Chronic: ≥4 prescriptions over ≥90 days
    Sporadic: <4 prescriptions or <90 days of use
    
    Parameters
    ----------
    pharma_df : pd.DataFrame
        Pharmaceutical data.
    patient_id_col : str
        Patient ID column.
    drug_class_col : str
        Drug class column.
    date_col : str
        Dispensing date column.
    min_rx_for_chronic : int
        Minimum prescriptions for chronic classification.
    min_duration_days : int
        Minimum duration of use for chronic classification.
        
    Returns
    -------
    pd.DataFrame
        Patient-level user type classification.
    """
    pharma_df = pharma_df.copy()
    pharma_df[date_col] = pd.to_datetime(pharma_df[date_col])
    
    # Aggregate by patient and drug class
    patient_stats = pharma_df.groupby([patient_id_col, drug_class_col]).agg({
        date_col: ["min", "max", "count"],
        "ddd": "sum" if "ddd" in pharma_df.columns else "count",
    }).reset_index()
    
    patient_stats.columns = [
        patient_id_col, drug_class_col, 
        "first_rx", "last_rx", "n_prescriptions", "total_ddd"
    ]
    
    # Calculate duration
    patient_stats["duration_days"] = (
        patient_stats["last_rx"] - patient_stats["first_rx"]
    ).dt.days
    
    # Classify
    patient_stats["user_type"] = np.where(
        (patient_stats["n_prescriptions"] >= min_rx_for_chronic) & 
        (patient_stats["duration_days"] >= min_duration_days),
        "Chronic",
        "Sporadic"
    )
    
    return patient_stats


# =============================================================================
# VISUALISATION
# =============================================================================

def plot_ddd_trends(
    annual_ddd: pd.DataFrame,
    drug_classes: list = None,
    title: str = "Prescribing Trends: DDD per 1000 population per day",
    figsize: tuple = (12, 6),
) -> plt.Figure:
    """
    Plot DDD trends over time by drug class.
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    if drug_classes is None:
        drug_classes = annual_ddd["drug_class"].unique()
    
    for dc in drug_classes:
        dc_data = annual_ddd[annual_ddd["drug_class"] == dc].sort_values("year")
        ax.plot(dc_data["year"], dc_data["ddd_per_1000_day"], 
                marker="o", linewidth=2, label=dc)
    
    ax.axvline(2020, color="red", linestyle="--", alpha=0.5, label="COVID-19")
    ax.set_xlabel("Year")
    ax.set_ylabel("DDD per 1000 inhabitants per day")
    ax.set_title(title, fontweight="bold")
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    
    return fig


def plot_prescription_intoxication_comparison(
    prescribing_rates: pd.DataFrame,
    intoxication_rates: pd.DataFrame,
    drug_class: str = "benzodiazepine",
    figsize: tuple = (12, 5),
) -> plt.Figure:
    """
    Plot prescribing rate vs intoxication rate over time (dual axis).
    """
    fig, ax1 = plt.subplots(figsize=figsize)
    
    # Filter to drug class
    rx_data = prescribing_rates[prescribing_rates["drug_class"] == drug_class].sort_values("year")
    
    # Plot prescribing on left axis
    color1 = "tab:blue"
    ax1.set_xlabel("Year")
    ax1.set_ylabel("DDD per 1000/day (Prescribing)", color=color1)
    ax1.plot(rx_data["year"], rx_data["ddd_per_1000_day"], 
             color=color1, marker="o", linewidth=2, label="Prescribing")
    ax1.tick_params(axis="y", labelcolor=color1)
    
    # Plot intoxications on right axis
    ax2 = ax1.twinx()
    color2 = "tab:red"
    ax2.set_ylabel("Intoxication cases", color=color2)
    if "year" in intoxication_rates.columns and drug_class in intoxication_rates.columns:
        intox_data = intoxication_rates.sort_values("year")
        ax2.plot(intox_data["year"], intox_data[drug_class],
                 color=color2, marker="s", linewidth=2, label="Intoxications")
    ax2.tick_params(axis="y", labelcolor=color2)
    
    ax1.axvline(2020, color="gray", linestyle="--", alpha=0.5)
    
    fig.suptitle(f"{drug_class.title()}: Prescribing vs Intoxications", fontweight="bold")
    plt.tight_layout()
    
    return fig


def plot_user_type_breakdown(
    linkage_df: pd.DataFrame,
    figsize: tuple = (10, 5),
) -> plt.Figure:
    """
    Plot breakdown of intoxication cases by user type and prior prescription status.
    """
    fig, axes = plt.subplots(1, 2, figsize=figsize)
    
    # Left: Had prior prescription?
    ax1 = axes[0]
    prior_rx_counts = linkage_df["had_prior_rx"].value_counts()
    labels = ["Had prior Rx", "No prior Rx"]
    colors = ["#2ca02c", "#d62728"]
    ax1.pie(prior_rx_counts.values, labels=labels, colors=colors, autopct="%1.1f%%")
    ax1.set_title("Prior Prescription Status\namong Intoxication Cases")
    
    # Right: User type (if available)
    ax2 = axes[1]
    if "user_type" in linkage_df.columns:
        user_counts = linkage_df["user_type"].value_counts()
        ax2.pie(user_counts.values, labels=user_counts.index, autopct="%1.1f%%")
        ax2.set_title("Chronic vs Sporadic Users\namong Intoxication Cases")
    else:
        ax2.text(0.5, 0.5, "User type data\nnot available", 
                 ha="center", va="center", fontsize=12)
        ax2.set_title("User Type Breakdown")
    
    plt.tight_layout()
    return fig


# =============================================================================
# MAIN ANALYSIS
# =============================================================================

print("=" * 70)
print("PRESCRIPTION-INTOXICATION LINKAGE ANALYSIS (Q5)")
print("=" * 70)

# -----------------------------------------------------------------------------
# CHECK DATA AVAILABILITY
# -----------------------------------------------------------------------------

print("\n--- Checking Data Availability ---")

if not HAS_POLARS:
    print("[--] Polars not available - pharmaceutical analysis will use pandas")

# Find available data files
pharma_files = get_pharma_files()
processed_ed = PROCESSED_DIR / "ed_processed.csv"
processed_pharma = PROCESSED_DIR / "pharma_processed.csv"

# Determine what data to use
if processed_ed.exists() and processed_pharma.exists():
    print(f"[OK] Found processed data files")
    USE_SYNTHETIC = False
    USE_PROCESSED = True
elif ED_DATA_FILE.exists() and pharma_files:
    print(f"[OK] Found raw data files")
    USE_SYNTHETIC = False
    USE_PROCESSED = False
else:
    print(f"[--] Data files not found - will generate synthetic data")
    USE_SYNTHETIC = True
    USE_PROCESSED = False

if USE_SYNTHETIC:
    print("\n--- Creating SYNTHETIC DATA for demonstration ---")
    
    from intox_analysis.data.generators import generate_ed_data, generate_pharma_data
    from config import STUDY_YEARS
    
    # Generate pharma data
    pharma_df = generate_pharma_data(n_records=100000, years=STUDY_YEARS)
    print(f"Generated {len(pharma_df):,} synthetic prescription records")
    
    # Generate ED data
    ed_df = generate_ed_data(n_records=50000, years=STUDY_YEARS)
    
    # Filter to intoxications only and add required columns
    from intox_analysis.data.schemas import classify_drug_intoxication
    
    diag_col = "diagnosis_code" if "diagnosis_code" in ed_df.columns else "diagnosis_code_primary"
    ed_df["_class"] = ed_df[diag_col].apply(lambda x: classify_drug_intoxication(str(x)))
    ed_df["is_intoxication"] = ed_df["_class"].apply(lambda x: x["is_intoxication"])
    ed_df["drug_class"] = ed_df["_class"].apply(lambda x: x["drug_class"])
    ed_df = ed_df.drop(columns=["_class"])
    
    # Filter to intoxications
    ed_df = ed_df[ed_df["is_intoxication"]].copy()
    
    # Create presentation_date from year_month
    if "presentation_date" not in ed_df.columns:
        ed_df["year_month"] = ed_df["year_month"].astype(str)
        ed_df["presentation_date"] = pd.to_datetime(
            ed_df["year_month"].str[:4] + "-" + ed_df["year_month"].str[4:6] + "-15"
        )
    ed_df["year"] = ed_df["presentation_date"].dt.year
    
    print(f"Generated {len(ed_df):,} synthetic intoxication cases")

elif USE_PROCESSED:
    print("\n--- Loading Processed Data ---")
    
    ed_df = pd.read_csv(processed_ed)
    
    # Filter to intoxications
    if "is_intoxication" in ed_df.columns:
        ed_df = ed_df[ed_df["is_intoxication"]].copy()
    
    # Create presentation_date from year_month if needed
    if "presentation_date" not in ed_df.columns and "year_month" in ed_df.columns:
        ed_df["year_month"] = ed_df["year_month"].astype(str)
        ed_df["presentation_date"] = pd.to_datetime(
            ed_df["year_month"].str[:4] + "-" + ed_df["year_month"].str[4:6] + "-15"
        )
    if "year" not in ed_df.columns:
        ed_df["year"] = ed_df["presentation_date"].dt.year
    
    print(f"  Loaded {len(ed_df):,} intoxication cases")
    
    pharma_df = pd.read_csv(processed_pharma)
    print(f"  Loaded {len(pharma_df):,} prescription records")

else:
    # Load raw data
    print("\n--- Loading Raw Data ---")
    
    ed_df = pd.read_csv(ED_DATA_FILE)
    
    # Rename columns
    from config import ED_COLUMN_MAPPING
    ed_df = ed_df.rename(columns={k: v for k, v in ED_COLUMN_MAPPING.items() if k in ed_df.columns})
    
    # Classify intoxications
    from intox_analysis.data.schemas import classify_drug_intoxication
    diag_col = "diagnosis_code_primary" if "diagnosis_code_primary" in ed_df.columns else "diagnosis_code"
    ed_df["_class"] = ed_df[diag_col].apply(lambda x: classify_drug_intoxication(str(x)))
    ed_df["is_intoxication"] = ed_df["_class"].apply(lambda x: x["is_intoxication"])
    ed_df["drug_class"] = ed_df["_class"].apply(lambda x: x["drug_class"])
    ed_df = ed_df.drop(columns=["_class"])
    ed_df = ed_df[ed_df["is_intoxication"]].copy()
    
    # Create presentation_date from year_month
    if "year_month" in ed_df.columns and "presentation_date" not in ed_df.columns:
        ed_df["year_month"] = ed_df["year_month"].astype(str)
        ed_df["presentation_date"] = pd.to_datetime(
            ed_df["year_month"].str[:4] + "-" + ed_df["year_month"].str[4:6] + "-15"
        )
    ed_df["year"] = ed_df["presentation_date"].dt.year
    
    print(f"  Loaded {len(ed_df):,} intoxication cases")
    
    # Load pharma data
    if HAS_POLARS and any(f.stat().st_size > 100_000_000 for f in pharma_files):
        from intox_analysis.data.pharmaceutical import scan_pharmaceutical_data, add_derived_columns
        lf = scan_pharmaceutical_data([str(f) for f in pharma_files])
        lf = add_derived_columns(lf)
        pharma_df = lf.collect().to_pandas()
    else:
        pharma_df = pd.concat([pd.read_csv(f) for f in pharma_files])
    
    # Rename pharma columns
    from config import PHARMA_COLUMN_MAPPING
    pharma_df = pharma_df.rename(columns={k: v for k, v in PHARMA_COLUMN_MAPPING.items() if k in pharma_df.columns})
    
    print(f"  Loaded {len(pharma_df):,} prescription records")

# Ensure required columns exist
if "dispensing_date" in pharma_df.columns:
    pharma_df["dispensing_date"] = pd.to_datetime(pharma_df["dispensing_date"], errors="coerce")

# Add drug_class from ATC code if needed
if "atc_code" in pharma_df.columns and "drug_class" not in pharma_df.columns:
    from intox_analysis.data.pharmaceutical import classify_atc_code
    pharma_df["drug_class"] = pharma_df["atc_code"].apply(
        lambda x: classify_atc_code(str(x))["drug_class"] if pd.notna(x) else "other"
    )

if "year" not in pharma_df.columns and "dispensing_date" in pharma_df.columns:
    pharma_df["year"] = pharma_df["dispensing_date"].dt.year

# -----------------------------------------------------------------------------
# STEP 1: DDD TRENDS
# -----------------------------------------------------------------------------

print("\n" + "=" * 70)
print("STEP 1: PRESCRIBING TRENDS (DDD)")
print("=" * 70)

if "ddd" in pharma_df.columns:
    annual_ddd = compute_annual_ddd_summary(
        pharma_df, 
        ddd_col="ddd", 
        year_col="year",
        drug_class_col="drug_class",
    )
    
    print("\nAnnual DDD Summary (psychotropic drugs):")
    psych_ddd = annual_ddd[annual_ddd["drug_class"].isin(DRUG_CLASSES_OF_INTEREST)]
    print(psych_ddd.pivot(index="year", columns="drug_class", values="ddd_per_1000_day").round(2))
    
else:
    print("⚠ No DDD column found in pharmaceutical data")
    annual_ddd = None

# -----------------------------------------------------------------------------
# STEP 2: USER TYPE CLASSIFICATION
# -----------------------------------------------------------------------------

print("\n" + "=" * 70)
print("STEP 2: CHRONIC VS SPORADIC USERS")
print("=" * 70)

user_types = classify_user_type(
    pharma_df,
    drug_class_col="drug_class",
    date_col="dispensing_date",
)

# Summary by drug class
user_summary = user_types.groupby(["drug_class", "user_type"]).size().unstack(fill_value=0)
user_summary["% Chronic"] = (user_summary["Chronic"] / user_summary.sum(axis=1) * 100).round(1)

print("\nUser Type Distribution by Drug Class:")
print(user_summary[user_summary.index.isin(DRUG_CLASSES_OF_INTEREST)])

# -----------------------------------------------------------------------------
# STEP 3: LINKAGE ANALYSIS
# -----------------------------------------------------------------------------

print("\n" + "=" * 70)
print("STEP 3: INTOXICATION-PRESCRIPTION LINKAGE")
print("=" * 70)

# Filter to intoxication cases only (not all 50k ED presentations)
# Check if we have diagnosis info to filter
if "diagnosis_code_primary" in ed_df.columns:
    intox_mask = ed_df["diagnosis_code_primary"].astype(str).str.startswith(("T4", "96"))
    ed_intox = ed_df[intox_mask].copy()
    print(f"Filtered to {len(ed_intox):,} intoxication cases (from {len(ed_df):,} total ED)")
else:
    # If no diagnosis column, assume all are intoxications (synthetic data case)
    ed_intox = ed_df.copy()
    print(f"Processing {len(ed_intox):,} records")

# Skip linkage if too many records (would be slow) or no pharma data
if len(ed_intox) > 10000:
    print(f"\n⚠ Too many records ({len(ed_intox):,}) for row-by-row linkage.")
    print("  Performing simplified aggregate analysis instead...")
    
    # Simplified linkage: just check if patient IDs overlap
    ed_patients = set(ed_intox["patient_id"].unique())
    pharma_patients = set(pharma_df["patient_id"].unique())
    overlap_patients = ed_patients & pharma_patients
    
    n_with_rx = len(overlap_patients)
    n_total = len(ed_patients)
    pct_with_rx = 100 * n_with_rx / n_total if n_total > 0 else 0
    
    print(f"\nIntoxication patients with ANY prescription history:")
    print(f"  With prior Rx: {n_with_rx:,} ({pct_with_rx:.1f}%)")
    print(f"  Without prior Rx: {n_total - n_with_rx:,} ({100-pct_with_rx:.1f}%)")
    
    linkage_df = None
    
else:
    linkage_df = link_intoxications_to_prescriptions(
        ed_intox,
        pharma_df,
        ed_date_col="presentation_date",
        pharma_date_col="dispensing_date",
        lookback_days=LOOKBACK_DAYS,
    )
    
    # Summary statistics
    n_with_rx = linkage_df["had_prior_rx"].sum()
    n_total = len(linkage_df)
    pct_with_rx = n_with_rx / n_total * 100

    print(f"\nIntoxication cases with prior prescription ({LOOKBACK_DAYS}-day lookback):")
    print(f"  With prior Rx: {n_with_rx:,} ({pct_with_rx:.1f}%)")
    print(f"  Without prior Rx: {n_total - n_with_rx:,} ({100-pct_with_rx:.1f}%)")

    # Among those with prior Rx
    if n_with_rx > 0:
        with_rx = linkage_df[linkage_df["had_prior_rx"]]
        print(f"\nAmong those with prior prescriptions:")
        print(f"  Had benzo/Z-drug Rx: {with_rx['had_benzo_rx'].sum():,} ({100*with_rx['had_benzo_rx'].mean():.1f}%)")
        print(f"  Had opioid Rx: {with_rx['had_opioid_rx'].sum():,} ({100*with_rx['had_opioid_rx'].mean():.1f}%)")
        print(f"  Mean prior prescriptions: {with_rx['n_prior_rx'].mean():.1f}")

# -----------------------------------------------------------------------------
# STEP 4: GENERATE FIGURES
# -----------------------------------------------------------------------------

print("\n" + "=" * 70)
print("GENERATING FIGURES")
print("=" * 70)

figures_dir = OUTPUT_DIR / "figures"
figures_dir.mkdir(parents=True, exist_ok=True)

# Figure 1: DDD trends
if annual_ddd is not None:
    fig1 = plot_ddd_trends(annual_ddd, DRUG_CLASSES_OF_INTEREST)
    fig1.savefig(figures_dir / "prescribing_ddd_trends.png", dpi=150, bbox_inches="tight")
    print("✓ Saved: prescribing_ddd_trends.png")

# Figure 2: User type breakdown (only if detailed linkage was performed)
if linkage_df is not None:
    fig2 = plot_user_type_breakdown(linkage_df)
    fig2.savefig(figures_dir / "intox_prescription_linkage.png", dpi=150, bbox_inches="tight")
    print("✓ Saved: intox_prescription_linkage.png")
else:
    print("⚠ Skipped linkage figure (simplified analysis mode)")

# -----------------------------------------------------------------------------
# STEP 5: SAVE RESULTS
# -----------------------------------------------------------------------------

print("\n--- Saving Tables ---")

tables_dir = OUTPUT_DIR / "tables"
tables_dir.mkdir(exist_ok=True)

if annual_ddd is not None:
    annual_ddd.to_csv(tables_dir / "prescribing_ddd_annual.csv", index=False)

user_summary.to_csv(tables_dir / "user_type_by_drug_class.csv")

# Create linkage summary
if linkage_df is not None:
    linkage_summary = pd.DataFrame({
        "Metric": [
            "Total intoxication cases",
            "With prior prescription",
            "Without prior prescription",
            "% with prior Rx",
            "With benzo/Z-drug Rx",
            "With opioid Rx",
        ],
        "Value": [
            n_total,
            n_with_rx,
            n_total - n_with_rx,
            f"{pct_with_rx:.1f}%",
            linkage_df["had_benzo_rx"].sum() if "had_benzo_rx" in linkage_df.columns else "N/A",
            linkage_df["had_opioid_rx"].sum() if "had_opioid_rx" in linkage_df.columns else "N/A",
        ]
    })
else:
    linkage_summary = pd.DataFrame({
        "Metric": [
            "Total intoxication patients",
            "With ANY prescription history",
            "Without prescription history",
            "% with prior Rx",
        ],
        "Value": [
            n_total,
            n_with_rx,
            n_total - n_with_rx,
            f"{pct_with_rx:.1f}%",
        ]
    })
linkage_summary.to_csv(tables_dir / "prescription_linkage_summary.csv", index=False)

print("✓ Tables saved to:", tables_dir)

# -----------------------------------------------------------------------------
# SUMMARY
# -----------------------------------------------------------------------------

print("\n" + "=" * 70)
print("KEY FINDINGS")
print("=" * 70)

print(f"""
PRESCRIBING TRENDS:
  - Benzodiazepine prescribing {'increasing' if USE_SYNTHETIC else 'see table'}
  
INTOXICATION-PRESCRIPTION LINKAGE:
  - {pct_with_rx:.1f}% of intoxication patients had prior prescriptions
  - This suggests {'majority are prescription-related' if pct_with_rx > 50 else 'mixed picture'}
  
IMPLICATIONS:
  - If chronic users predominate: focus on prescribing guidelines, monitoring
  - If sporadic users predominate: focus on access, diversion, misuse
""")

if USE_SYNTHETIC:
    print("⚠ NOTE: Results above are based on SYNTHETIC data.")

plt.show()

print("\n" + "=" * 70)
print("ANALYSIS COMPLETE")
print("=" * 70)
