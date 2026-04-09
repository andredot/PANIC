# -*- coding: utf-8 -*-
"""
Trend Analysis Module for ED Syndromic Surveillance
====================================================

This module analyses trends in:
1. Drug intoxications by drug class (ICD-coded)
2. Mental health diagnoses (ICD-coded)

Key outputs:
- Average annual cases (last 3 years)
- Year-on-year growth rates
- Visualisations highlighting drivers of upward trends

Both analyses are stratified by:
- All ED presentations (any ESITO)
- Admitted patients only (ESITO indicating ward admission)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


# =============================================================================
# ICD CODE DEFINITIONS
# =============================================================================

# -----------------------------------------------------------------------------
# DRUG INTOXICATION CODES - Detailed by drug class
# -----------------------------------------------------------------------------

# ICD-10-CM T-codes for drug poisoning (T36-T50)
ICD10_DRUG_CLASSES = {
    "Benzodiazepines": {
        "codes": ["T424"],  # T42.4
        "description": "Benzodiazepines (anxiolytics, hypnotics)",
    },
    "Other sedatives/hypnotics": {
        "codes": ["T423", "T426", "T427"],  # T42.3, T42.6, T42.7
        "description": "Barbiturates, other sedatives, unspecified",
    },
    "Opioids": {
        "codes": ["T400", "T401", "T402", "T403", "T404", "T406"],
        "description": "Opium, heroin, other opioids, methadone, synthetics",
    },
    "Antidepressants": {
        "codes": ["T430", "T431", "T432"],  # Tricyclics, tetracyclics, other
        "description": "Tricyclic, tetracyclic, and other antidepressants",
    },
    "Antipsychotics": {
        "codes": ["T433", "T434", "T435"],
        "description": "Phenothiazines, butyrophenones, other antipsychotics",
    },
    "Stimulants": {
        "codes": ["T436"],  # Psychostimulants
        "description": "Amphetamines, methylphenidate, cocaine-related",
    },
    "Cocaine": {
        "codes": ["T405"],
        "description": "Cocaine poisoning",
    },
    "Cannabis": {
        "codes": ["T407"],
        "description": "Cannabis (marijuana) poisoning",
    },
    "Hallucinogens": {
        "codes": ["T408"],  # LSD and other hallucinogens in T40.8
        "description": "LSD, other hallucinogens",
    },
    "Anticonvulsants": {
        "codes": ["T420", "T421", "T422", "T425"],
        "description": "Hydantoins, iminostilbenes, succinimides, anticonvulsants",
    },
    "Analgesics (non-opioid)": {
        "codes": ["T390", "T391", "T392", "T393", "T394"],
        "description": "Salicylates, paracetamol, NSAIDs",
    },
    "Paracetamol": {
        "codes": ["T391"],
        "description": "Paracetamol (acetaminophen) - often in self-harm",
    },
    "Alcohol (with drugs)": {
        "codes": ["T510", "T511"],  # Ethanol, methanol
        "description": "Toxic effect of alcohol (often co-ingestion)",
    },
    "Cardiovascular drugs": {
        "codes": ["T46"],  # All T46.x
        "description": "Cardiac glycosides, antihypertensives, etc.",
    },
    "Antihistamines": {
        "codes": ["T450"],
        "description": "Antiallergic and antiemetic drugs",
    },
    "Insulin/antidiabetics": {
        "codes": ["T383"],
        "description": "Insulin and oral hypoglycaemic drugs",
    },
    "Other/unspecified": {
        "codes": ["T509", "T50"],  # Unspecified drugs
        "description": "Other and unspecified drugs",
    },
}

# ICD-9-CM codes for drug poisoning (960-979)
ICD9_DRUG_CLASSES = {
    "Benzodiazepines": {
        "codes": ["9694"],  # 969.4
        "description": "Benzodiazepine-based tranquilizers",
    },
    "Other sedatives/hypnotics": {
        "codes": ["967"],  # 967.x
        "description": "Sedatives and hypnotics",
    },
    "Opioids": {
        "codes": ["9650", "9651", "9652", "96500", "96501", "96509"],
        "description": "Opiates and related narcotics",
    },
    "Antidepressants": {
        "codes": ["9690", "9691"],
        "description": "Antidepressants",
    },
    "Antipsychotics": {
        "codes": ["9693"],  # Phenothiazine tranquilizers
        "description": "Phenothiazine-based tranquilizers",
    },
    "Stimulants": {
        "codes": ["9697", "970"],
        "description": "Psychostimulants and CNS stimulants",
    },
    "Anticonvulsants": {
        "codes": ["966"],
        "description": "Anticonvulsants and anti-parkinsonism drugs",
    },
    "Analgesics (non-opioid)": {
        "codes": ["965"],  # Excluding opioids
        "description": "Analgesics, antipyretics, antirheumatics",
    },
    "Cardiovascular drugs": {
        "codes": ["972"],
        "description": "Agents affecting cardiovascular system",
    },
    "Other/unspecified": {
        "codes": ["977", "978", "979"],
        "description": "Other and unspecified drugs",
    },
}


# -----------------------------------------------------------------------------
# MENTAL HEALTH DIAGNOSIS CODES
# -----------------------------------------------------------------------------

# ICD-10-CM Mental Health Codes (F chapter)
ICD10_MENTAL_HEALTH = {
    "Depression": {
        "codes": ["F32", "F33", "F341"],
        "description": "Depressive episodes, recurrent depression, dysthymia",
    },
    "Anxiety disorders": {
        "codes": ["F40", "F41"],
        "description": "Phobic and other anxiety disorders, panic, GAD",
    },
    "Adjustment disorders": {
        "codes": ["F43"],
        "description": "Reaction to stress, PTSD, adjustment disorders",
    },
    "Bipolar disorder": {
        "codes": ["F30", "F31"],
        "description": "Manic episodes, bipolar affective disorder",
    },
    "Schizophrenia spectrum": {
        "codes": ["F20", "F21", "F22", "F23", "F24", "F25", "F28", "F29"],
        "description": "Schizophrenia, delusional, psychotic disorders",
    },
    "Eating disorders": {
        "codes": ["F50"],
        "description": "Anorexia nervosa, bulimia, other eating disorders",
    },
    "Personality disorders": {
        "codes": ["F60", "F61"],
        "description": "Specific and mixed personality disorders",
    },
    "Substance use disorders": {
        "codes": ["F10", "F11", "F12", "F13", "F14", "F15", "F16", "F17", "F18", "F19"],
        "description": "Alcohol, opioid, cannabis, sedative, cocaine, other substance disorders",
    },
    "ADHD": {
        "codes": ["F90"],
        "description": "Attention-deficit hyperactivity disorders",
    },
    "Self-harm ideation": {
        "codes": ["R45851"],  # Suicidal ideation code
        "description": "Suicidal ideation (R-code, not F)",
    },
    "Other mood disorders": {
        "codes": ["F34", "F38", "F39"],
        "description": "Persistent mood disorders, other/unspecified",
    },
}

# ICD-9-CM Mental Health Codes (290-319)
ICD9_MENTAL_HEALTH = {
    "Depression": {
        "codes": ["296", "3004", "311"],  # Major depression, neurotic depression
        "description": "Affective psychoses, depressive disorders",
    },
    "Anxiety disorders": {
        "codes": ["3000", "3001", "3002", "3003"],  # 300.0x anxiety states
        "description": "Anxiety states, phobic disorders, OCD",
    },
    "Adjustment disorders": {
        "codes": ["309"],
        "description": "Adjustment reaction",
    },
    "Bipolar disorder": {
        "codes": ["2960", "2961", "2964", "2965", "2966"],
        "description": "Manic-depressive psychosis",
    },
    "Schizophrenia spectrum": {
        "codes": ["295", "297", "298"],
        "description": "Schizophrenic, paranoid, other psychoses",
    },
    "Eating disorders": {
        "codes": ["3071", "30750", "30751", "30752", "30753", "30754", "30759"],
        "description": "Anorexia nervosa, bulimia, other eating disorders",
    },
    "Personality disorders": {
        "codes": ["301"],
        "description": "Personality disorders",
    },
    "Substance use disorders": {
        "codes": ["303", "304", "305"],
        "description": "Alcohol dependence, drug dependence, nondependent abuse",
    },
    "ADHD": {
        "codes": ["3140"],  # 314.0x
        "description": "Attention deficit disorder",
    },
}


# =============================================================================
# CLASSIFICATION FUNCTIONS
# =============================================================================

def classify_drug_intoxication_detailed(code: str) -> Dict[str, any]:
    """
    Classify a drug intoxication code into detailed drug classes.
    
    Parameters
    ----------
    code : str
        ICD-9 or ICD-10 diagnosis code.
        
    Returns
    -------
    dict
        {
            'is_intoxication': bool,
            'drug_class': str or None,
            'coding_system': 'ICD-9' or 'ICD-10' or None,
            'description': str or None
        }
    """
    if not code or not isinstance(code, str):
        return {
            'is_intoxication': False,
            'drug_class': None,
            'coding_system': None,
            'description': None
        }
    
    clean_code = code.replace(".", "").replace(" ", "").upper()
    
    # Check ICD-10 (starts with T for poisoning, or F/R for mental health)
    if clean_code.startswith("T"):
        # Check T36-T50 range
        try:
            if len(clean_code) >= 3:
                t_num = int(clean_code[1:3])
                if 36 <= t_num <= 50:
                    # It's a drug poisoning code - find the class
                    for drug_class, info in ICD10_DRUG_CLASSES.items():
                        for prefix in info["codes"]:
                            if clean_code.startswith(prefix):
                                return {
                                    'is_intoxication': True,
                                    'drug_class': drug_class,
                                    'coding_system': 'ICD-10',
                                    'description': info["description"]
                                }
                    # T36-T50 but not in our specific list
                    return {
                        'is_intoxication': True,
                        'drug_class': 'Other/unspecified',
                        'coding_system': 'ICD-10',
                        'description': 'Other drug poisoning'
                    }
        except ValueError:
            pass
        return {
            'is_intoxication': False,
            'drug_class': None,
            'coding_system': 'ICD-10',
            'description': None
        }
    
    # Check ICD-9 (960-979 range)
    try:
        if len(clean_code) >= 3:
            prefix = int(clean_code[:3])
            if 960 <= prefix <= 979:
                # It's a drug poisoning code - find the class
                for drug_class, info in ICD9_DRUG_CLASSES.items():
                    for code_prefix in info["codes"]:
                        if clean_code.startswith(code_prefix):
                            return {
                                'is_intoxication': True,
                                'drug_class': drug_class,
                                'coding_system': 'ICD-9',
                                'description': info["description"]
                            }
                # 960-979 but not in our specific list
                return {
                    'is_intoxication': True,
                    'drug_class': 'Other/unspecified',
                    'coding_system': 'ICD-9',
                    'description': 'Other drug poisoning'
                }
    except ValueError:
        pass
    
    return {
        'is_intoxication': False,
        'drug_class': None,
        'coding_system': None,
        'description': None
    }


def classify_mental_health(code: str) -> Dict[str, any]:
    """
    Classify a mental health diagnosis code.
    
    Parameters
    ----------
    code : str
        ICD-9 or ICD-10 diagnosis code.
        
    Returns
    -------
    dict
        {
            'is_mental_health': bool,
            'diagnosis_class': str or None,
            'coding_system': 'ICD-9' or 'ICD-10' or None,
            'description': str or None
        }
    """
    if not code or not isinstance(code, str):
        return {
            'is_mental_health': False,
            'diagnosis_class': None,
            'coding_system': None,
            'description': None
        }
    
    clean_code = code.replace(".", "").replace(" ", "").upper()
    
    # Check ICD-10 (F chapter for mental health, plus R45851 for suicidal ideation)
    if clean_code.startswith("F") or clean_code.startswith("R45851"):
        for diag_class, info in ICD10_MENTAL_HEALTH.items():
            for prefix in info["codes"]:
                if clean_code.startswith(prefix):
                    return {
                        'is_mental_health': True,
                        'diagnosis_class': diag_class,
                        'coding_system': 'ICD-10',
                        'description': info["description"]
                    }
        # F-code but not in our specific list
        if clean_code.startswith("F"):
            return {
                'is_mental_health': True,
                'diagnosis_class': 'Other mental health',
                'coding_system': 'ICD-10',
                'description': 'Other mental/behavioural disorder'
            }
    
    # Check ICD-9 (290-319 range)
    try:
        if len(clean_code) >= 3:
            prefix = int(clean_code[:3])
            if 290 <= prefix <= 319:
                for diag_class, info in ICD9_MENTAL_HEALTH.items():
                    for code_prefix in info["codes"]:
                        if clean_code.startswith(code_prefix):
                            return {
                                'is_mental_health': True,
                                'diagnosis_class': diag_class,
                                'coding_system': 'ICD-9',
                                'description': info["description"]
                            }
                # 290-319 but not in our specific list
                return {
                    'is_mental_health': True,
                    'diagnosis_class': 'Other mental health',
                    'coding_system': 'ICD-9',
                    'description': 'Other mental disorder'
                }
    except ValueError:
        pass
    
    return {
        'is_mental_health': False,
        'diagnosis_class': None,
        'coding_system': None,
        'description': None
    }


# =============================================================================
# DATA PROCESSING FUNCTIONS
# =============================================================================

def process_ed_data(
    df: pd.DataFrame,
    diagnosis_col_primary: str = "diagnosis_code_primary",
    diagnosis_col_secondary: str = "diagnosis_code_secondary",
    date_col: str = "year_month",
    esito_col: str = "disposition_code",
    admission_codes: List[str] = ["2", "3", "4"],
) -> pd.DataFrame:
    """
    Process ED data to add drug class and mental health classifications.
    
    Parameters
    ----------
    df : pd.DataFrame
        ED presentation data with diagnosis codes.
    diagnosis_col_primary : str
        Column name for primary diagnosis code.
    diagnosis_col_secondary : str
        Column name for secondary diagnosis code.
    date_col : str
        Column name for year-month.
    esito_col : str
        Column name for disposition/esito code.
    admission_codes : list
        Esito codes that indicate hospital admission.
        
    Returns
    -------
    pd.DataFrame
        DataFrame with added classification columns.
    """
    df = df.copy()
    
    # Extract year from year_month (format: YYYYMM)
    df["year"] = df[date_col].astype(str).str[:4].astype(int)
    df["month"] = df[date_col].astype(str).str[4:6].astype(int)
    
    # Flag for admitted patients
    df["is_admitted"] = df[esito_col].astype(str).isin(admission_codes)
    
    # Classify drug intoxications (check both primary and secondary)
    def get_drug_class(row):
        # Check primary diagnosis first
        primary = row.get(diagnosis_col_primary, "")
        if primary and str(primary).strip() not in ["_", "DATO NON APPLICABILE", ""]:
            result = classify_drug_intoxication_detailed(str(primary))
            if result["is_intoxication"]:
                return result["drug_class"]
        
        # Check secondary diagnosis
        secondary = row.get(diagnosis_col_secondary, "")
        if secondary and str(secondary).strip() not in ["_", "DATO NON APPLICABILE", ""]:
            result = classify_drug_intoxication_detailed(str(secondary))
            if result["is_intoxication"]:
                return result["drug_class"]
        
        return None
    
    # Classify mental health diagnoses
    def get_mental_health_class(row):
        # Check primary diagnosis first
        primary = row.get(diagnosis_col_primary, "")
        if primary and str(primary).strip() not in ["_", "DATO NON APPLICABILE", ""]:
            result = classify_mental_health(str(primary))
            if result["is_mental_health"]:
                return result["diagnosis_class"]
        
        # Check secondary diagnosis
        secondary = row.get(diagnosis_col_secondary, "")
        if secondary and str(secondary).strip() not in ["_", "DATO NON APPLICABILE", ""]:
            result = classify_mental_health(str(secondary))
            if result["is_mental_health"]:
                return result["diagnosis_class"]
        
        return None
    
    print("Classifying diagnoses... ", end="", flush=True)
    df["drug_class"] = df.apply(get_drug_class, axis=1)
    df["is_intoxication"] = df["drug_class"].notna()
    df["mental_health_class"] = df.apply(get_mental_health_class, axis=1)
    df["is_mental_health"] = df["mental_health_class"].notna()
    print("Done!")
    
    return df


# =============================================================================
# TREND ANALYSIS FUNCTIONS
# =============================================================================

@dataclass
class TrendMetrics:
    """Container for trend analysis results."""
    category: str
    avg_annual_cases: float
    total_cases_3yr: int
    yoy_growth_rates: List[float]
    avg_yoy_growth: float
    cagr: float  # Compound annual growth rate


def compute_annual_counts(
    df: pd.DataFrame,
    class_col: str,
    year_col: str = "year",
    admitted_only: bool = False,
) -> pd.DataFrame:
    """
    Compute annual case counts by class.
    
    Parameters
    ----------
    df : pd.DataFrame
        Processed ED data.
    class_col : str
        Column containing the classification (drug_class or mental_health_class).
    year_col : str
        Column containing the year.
    admitted_only : bool
        If True, filter to admitted patients only.
        
    Returns
    -------
    pd.DataFrame
        Pivot table with years as columns and classes as rows.
    """
    data = df.copy()
    
    # Filter to relevant cases
    data = data[data[class_col].notna()]
    
    if admitted_only:
        data = data[data["is_admitted"]]
    
    # Count by year and class
    counts = data.groupby([year_col, class_col]).size().reset_index(name="n_cases")
    
    # Pivot to wide format
    pivot = counts.pivot(index=class_col, columns=year_col, values="n_cases").fillna(0)
    
    return pivot


def compute_trend_metrics(
    annual_counts: pd.DataFrame,
    last_n_years: int = 3,
) -> List[TrendMetrics]:
    """
    Compute trend metrics for each category.
    
    Parameters
    ----------
    annual_counts : pd.DataFrame
        Pivot table from compute_annual_counts.
    last_n_years : int
        Number of recent years to analyse.
        
    Returns
    -------
    list of TrendMetrics
        Trend metrics for each category.
    """
    # Get the last N years of columns
    years = sorted([c for c in annual_counts.columns if isinstance(c, (int, float))])
    recent_years = years[-last_n_years:] if len(years) >= last_n_years else years
    
    results = []
    
    for category in annual_counts.index:
        counts = annual_counts.loc[category, recent_years].values
        
        # Average annual cases
        avg_annual = np.mean(counts)
        total_3yr = np.sum(counts)
        
        # Year-on-year growth rates
        yoy_rates = []
        for i in range(1, len(counts)):
            if counts[i-1] > 0:
                growth = (counts[i] - counts[i-1]) / counts[i-1] * 100
                yoy_rates.append(growth)
            else:
                yoy_rates.append(np.nan)
        
        avg_yoy = np.nanmean(yoy_rates) if yoy_rates else 0
        
        # CAGR (Compound Annual Growth Rate)
        if len(counts) >= 2 and counts[0] > 0:
            cagr = ((counts[-1] / counts[0]) ** (1 / (len(counts) - 1)) - 1) * 100
        else:
            cagr = 0
        
        results.append(TrendMetrics(
            category=category,
            avg_annual_cases=avg_annual,
            total_cases_3yr=int(total_3yr),
            yoy_growth_rates=yoy_rates,
            avg_yoy_growth=avg_yoy,
            cagr=cagr,
        ))
    
    return results


def create_trend_summary_table(
    metrics: List[TrendMetrics],
    sort_by: str = "Avg YoY Growth (%)",
) -> pd.DataFrame:
    """
    Create a summary table of trend metrics.
    
    Parameters
    ----------
    metrics : list of TrendMetrics
        Output from compute_trend_metrics.
    sort_by : str
        Column to sort by (descending).
        
    Returns
    -------
    pd.DataFrame
        Summary table sorted by growth rate.
    """
    data = []
    for m in metrics:
        data.append({
            "Category": m.category,
            "Avg Annual Cases": round(m.avg_annual_cases, 1),
            "Total (3yr)": m.total_cases_3yr,
            "Avg YoY Growth (%)": round(m.avg_yoy_growth, 1),
            "CAGR (%)": round(m.cagr, 1),
        })
    
    df = pd.DataFrame(data)
    if len(df) > 0 and sort_by in df.columns:
        df = df.sort_values(sort_by, ascending=False)
    
    return df


# =============================================================================
# VISUALISATION FUNCTIONS
# =============================================================================

def plot_growth_drivers(
    metrics: List[TrendMetrics],
    title: str = "Drug Classes Driving Upward Trend",
    subtitle: str = "Average annual cases vs. Year-on-Year growth rate (last 3 years)",
    figsize: Tuple[int, int] = (12, 8),
    highlight_threshold: float = 10.0,  # Highlight classes with >10% growth
):
    """
    Create a bubble chart showing which categories are driving growth.
    
    X-axis: Average YoY growth rate
    Y-axis: Average annual cases
    Bubble size: Total cases
    Color: Growth rate (red = high growth)
    
    Parameters
    ----------
    metrics : list of TrendMetrics
        Output from compute_trend_metrics.
    title : str
        Chart title.
    subtitle : str
        Chart subtitle.
    figsize : tuple
        Figure size.
    highlight_threshold : float
        Growth rate threshold for highlighting.
        
    Returns
    -------
    matplotlib.figure.Figure
        The figure object.
    """
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    
    fig, ax = plt.subplots(figsize=figsize)
    
    # Prepare data
    categories = [m.category for m in metrics]
    x = [m.avg_yoy_growth for m in metrics]  # Growth rate
    y = [m.avg_annual_cases for m in metrics]  # Volume
    sizes = [m.total_cases_3yr for m in metrics]  # Bubble size
    
    # Normalize bubble sizes
    max_size = max(sizes) if sizes else 1
    bubble_sizes = [s / max_size * 1000 + 100 for s in sizes]  # Scale to reasonable size
    
    # Color by growth rate
    cmap = plt.cm.RdYlGn_r  # Red = high growth, Green = low/negative
    norm = plt.Normalize(vmin=min(x) - 5, vmax=max(x) + 5)
    colors = [cmap(norm(val)) for val in x]
    
    # Plot bubbles
    scatter = ax.scatter(x, y, s=bubble_sizes, c=colors, alpha=0.7, edgecolors="white", linewidth=1.5)
    
    # Add labels for significant categories
    for i, cat in enumerate(categories):
        # Label if high growth or high volume
        if x[i] > highlight_threshold or y[i] > np.percentile(y, 75):
            ax.annotate(
                cat,
                (x[i], y[i]),
                xytext=(5, 5),
                textcoords="offset points",
                fontsize=9,
                fontweight="bold" if x[i] > highlight_threshold else "normal",
            )
    
    # Add reference lines
    ax.axvline(0, color="gray", linestyle="--", alpha=0.5, linewidth=1)
    ax.axhline(np.median(y), color="gray", linestyle=":", alpha=0.5, linewidth=1)
    
    # Highlight quadrant for "high growth, high volume"
    ax.axvspan(highlight_threshold, ax.get_xlim()[1], alpha=0.1, color="red")
    
    # Labels
    ax.set_xlabel("Average Year-on-Year Growth (%)", fontsize=12)
    ax.set_ylabel("Average Annual Cases", fontsize=12)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.text(0.5, 1.02, subtitle, transform=ax.transAxes, ha="center", fontsize=10, style="italic")
    
    # Add legend for bubble size
    legend_sizes = [min(sizes), np.median(sizes), max(sizes)]
    legend_bubbles = [s / max_size * 1000 + 100 for s in legend_sizes]
    for ls, lb in zip(legend_sizes, legend_bubbles):
        ax.scatter([], [], s=lb, c="gray", alpha=0.5, label=f"{int(ls):,} cases")
    ax.legend(title="Total cases (3yr)", loc="upper left", framealpha=0.9)
    
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    
    return fig


def plot_annual_trends(
    annual_counts: pd.DataFrame,
    top_n: int = 8,
    title: str = "Annual Trends by Category",
    figsize: Tuple[int, int] = (12, 6),
):
    """
    Plot line chart showing annual trends for top categories.
    
    Parameters
    ----------
    annual_counts : pd.DataFrame
        Pivot table from compute_annual_counts.
    top_n : int
        Number of top categories to show.
    title : str
        Chart title.
    figsize : tuple
        Figure size.
        
    Returns
    -------
    matplotlib.figure.Figure
        The figure object.
    """
    import matplotlib.pyplot as plt
    
    # Get top categories by total volume
    totals = annual_counts.sum(axis=1).sort_values(ascending=False)
    top_categories = totals.head(top_n).index.tolist()
    
    fig, ax = plt.subplots(figsize=figsize)
    
    years = [c for c in annual_counts.columns if isinstance(c, (int, float))]
    
    for cat in top_categories:
        values = annual_counts.loc[cat, years].values
        ax.plot(years, values, marker="o", linewidth=2, markersize=6, label=cat)
    
    # COVID reference line
    if 2020 in years:
        ax.axvline(2020, color="red", linestyle="--", alpha=0.5, label="COVID-19")
    
    ax.set_xlabel("Year", fontsize=12)
    ax.set_ylabel("Number of Cases", fontsize=12)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left")
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    return fig


def create_comparison_chart(
    metrics_all: List[TrendMetrics],
    metrics_admitted: List[TrendMetrics],
    top_n: int = 10,
    figsize: Tuple[int, int] = (14, 6),
):
    """
    Create side-by-side comparison of all presentations vs admitted only.
    
    Parameters
    ----------
    metrics_all : list of TrendMetrics
        Metrics for all ED presentations.
    metrics_admitted : list of TrendMetrics
        Metrics for admitted patients only.
    top_n : int
        Number of top categories to show.
    figsize : tuple
        Figure size.
        
    Returns
    -------
    matplotlib.figure.Figure
        The figure object.
    """
    import matplotlib.pyplot as plt
    
    fig, axes = plt.subplots(1, 2, figsize=figsize)
    
    for ax, metrics, title in zip(
        axes,
        [metrics_all, metrics_admitted],
        ["All ED Presentations", "Admitted Patients Only"]
    ):
        # Sort by growth rate and get top N
        sorted_metrics = sorted(metrics, key=lambda m: m.avg_yoy_growth, reverse=True)[:top_n]
        
        categories = [m.category for m in sorted_metrics]
        growth_rates = [m.avg_yoy_growth for m in sorted_metrics]
        volumes = [m.avg_annual_cases for m in sorted_metrics]
        
        # Color by growth rate
        colors = ["#d62728" if g > 10 else "#2ca02c" if g < 0 else "#1f77b4" for g in growth_rates]
        
        y_pos = np.arange(len(categories))
        bars = ax.barh(y_pos, growth_rates, color=colors, alpha=0.8)
        
        # Add volume labels
        for i, (bar, vol) in enumerate(zip(bars, volumes)):
            ax.text(
                bar.get_width() + 0.5,
                bar.get_y() + bar.get_height() / 2,
                f"({vol:.0f}/yr)",
                va="center",
                fontsize=9,
                color="gray"
            )
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels(categories)
        ax.set_xlabel("Avg YoY Growth (%)")
        ax.set_title(title, fontweight="bold")
        ax.axvline(0, color="black", linewidth=0.5)
        ax.grid(True, axis="x", alpha=0.3)
    
    plt.suptitle("Drug Class Growth Rates: ED Presentations vs Hospital Admissions", fontsize=14, fontweight="bold")
    plt.tight_layout()
    
    return fig


# =============================================================================
# MAIN ANALYSIS RUNNER
# =============================================================================

def run_intoxication_trend_analysis(
    df: pd.DataFrame,
    output_dir: str = None,
    last_n_years: int = 3,
) -> Dict:
    """
    Run complete drug intoxication trend analysis.
    
    Parameters
    ----------
    df : pd.DataFrame
        Processed ED data (output of process_ed_data).
    output_dir : str, optional
        Directory to save figures. If None, figures are displayed but not saved.
    last_n_years : int
        Number of recent years to analyse for trends.
        
    Returns
    -------
    dict
        Dictionary containing all analysis results.
    """
    from pathlib import Path
    import matplotlib.pyplot as plt
    
    results = {}
    
    print("\n" + "=" * 70)
    print("DRUG INTOXICATION TREND ANALYSIS")
    print("=" * 70)
    
    # Filter to intoxication cases
    df_intox = df[df["is_intoxication"]].copy()
    print(f"\nTotal intoxication cases: {len(df_intox):,}")
    
    # Get year range
    years = sorted(df_intox["year"].unique())
    print(f"Year range: {min(years)} - {max(years)}")
    recent_years = years[-last_n_years:]
    print(f"Analysing trends for: {recent_years}")
    
    # --- ALL ED PRESENTATIONS ---
    print("\n--- All ED Presentations (any ESITO) ---")
    
    counts_all = compute_annual_counts(df_intox, "drug_class", admitted_only=False)
    metrics_all = compute_trend_metrics(counts_all, last_n_years)
    table_all = create_trend_summary_table(metrics_all)
    
    print("\nTop 10 by YoY Growth:")
    print(table_all.head(10).to_string(index=False))
    
    results["counts_all"] = counts_all
    results["metrics_all"] = metrics_all
    results["table_all"] = table_all
    
    # --- ADMITTED PATIENTS ONLY ---
    print("\n--- Admitted Patients Only ---")
    
    counts_admitted = compute_annual_counts(df_intox, "drug_class", admitted_only=True)
    metrics_admitted = compute_trend_metrics(counts_admitted, last_n_years)
    table_admitted = create_trend_summary_table(metrics_admitted)
    
    print("\nTop 10 by YoY Growth:")
    print(table_admitted.head(10).to_string(index=False))
    
    results["counts_admitted"] = counts_admitted
    results["metrics_admitted"] = metrics_admitted
    results["table_admitted"] = table_admitted
    
    # --- CREATE FIGURES ---
    print("\n--- Generating Figures ---")
    
    # Figure 1: Growth drivers (all presentations)
    fig1 = plot_growth_drivers(
        metrics_all,
        title="Drug Classes Driving ED Intoxication Trends",
        subtitle=f"Average annual cases vs. growth rate ({recent_years[0]}-{recent_years[-1]})"
    )
    results["fig_growth_drivers_all"] = fig1
    
    # Figure 2: Growth drivers (admitted only)
    fig2 = plot_growth_drivers(
        metrics_admitted,
        title="Drug Classes Driving Hospital Admissions for Intoxication",
        subtitle=f"Admitted patients only ({recent_years[0]}-{recent_years[-1]})"
    )
    results["fig_growth_drivers_admitted"] = fig2
    
    # Figure 3: Annual trends
    fig3 = plot_annual_trends(
        counts_all,
        top_n=8,
        title="Annual Drug Intoxication Cases by Class (All ED Presentations)"
    )
    results["fig_annual_trends"] = fig3
    
    # Figure 4: Comparison chart
    fig4 = create_comparison_chart(metrics_all, metrics_admitted, top_n=10)
    results["fig_comparison"] = fig4
    
    # Save figures if output_dir specified
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        fig1.savefig(output_path / "intox_growth_drivers_all.png", dpi=150, bbox_inches="tight")
        fig2.savefig(output_path / "intox_growth_drivers_admitted.png", dpi=150, bbox_inches="tight")
        fig3.savefig(output_path / "intox_annual_trends.png", dpi=150, bbox_inches="tight")
        fig4.savefig(output_path / "intox_comparison.png", dpi=150, bbox_inches="tight")
        
        # Save tables
        table_all.to_csv(output_path / "intox_trends_all_presentations.csv", index=False)
        table_admitted.to_csv(output_path / "intox_trends_admitted_only.csv", index=False)
        
        print(f"\n✓ Figures and tables saved to: {output_path}")
    
    plt.show()
    
    return results


def run_mental_health_trend_analysis(
    df: pd.DataFrame,
    output_dir: str = None,
    last_n_years: int = 3,
) -> Dict:
    """
    Run complete mental health diagnosis trend analysis.
    
    Parameters
    ----------
    df : pd.DataFrame
        Processed ED data (output of process_ed_data).
    output_dir : str, optional
        Directory to save figures.
    last_n_years : int
        Number of recent years to analyse.
        
    Returns
    -------
    dict
        Dictionary containing all analysis results.
    """
    from pathlib import Path
    import matplotlib.pyplot as plt
    
    results = {}
    
    print("\n" + "=" * 70)
    print("MENTAL HEALTH DIAGNOSIS TREND ANALYSIS")
    print("=" * 70)
    
    # Filter to mental health cases
    df_mh = df[df["is_mental_health"]].copy()
    print(f"\nTotal mental health cases: {len(df_mh):,}")
    
    # Get year range
    years = sorted(df_mh["year"].unique())
    print(f"Year range: {min(years)} - {max(years)}")
    recent_years = years[-last_n_years:]
    print(f"Analysing trends for: {recent_years}")
    
    # --- ALL ED PRESENTATIONS ---
    print("\n--- All ED Presentations ---")
    
    counts_all = compute_annual_counts(df_mh, "mental_health_class", admitted_only=False)
    metrics_all = compute_trend_metrics(counts_all, last_n_years)
    table_all = create_trend_summary_table(metrics_all)
    
    print("\nTrends by diagnosis class:")
    print(table_all.to_string(index=False))
    
    results["counts_all"] = counts_all
    results["metrics_all"] = metrics_all
    results["table_all"] = table_all
    
    # --- ADMITTED PATIENTS ONLY ---
    print("\n--- Admitted Patients Only ---")
    
    counts_admitted = compute_annual_counts(df_mh, "mental_health_class", admitted_only=True)
    metrics_admitted = compute_trend_metrics(counts_admitted, last_n_years)
    table_admitted = create_trend_summary_table(metrics_admitted)
    
    print("\nTrends by diagnosis class:")
    print(table_admitted.to_string(index=False))
    
    results["counts_admitted"] = counts_admitted
    results["metrics_admitted"] = metrics_admitted
    results["table_admitted"] = table_admitted
    
    # --- CREATE FIGURES ---
    print("\n--- Generating Figures ---")
    
    # Figure 1: Annual trends
    fig1 = plot_annual_trends(
        counts_all,
        top_n=8,
        title="Annual Mental Health ED Presentations by Diagnosis"
    )
    results["fig_annual_trends"] = fig1
    
    # Figure 2: Growth drivers
    fig2 = plot_growth_drivers(
        metrics_all,
        title="Mental Health Diagnoses Driving ED Trends",
        subtitle=f"Average annual cases vs. growth rate ({recent_years[0]}-{recent_years[-1]})",
        highlight_threshold=5.0,
    )
    results["fig_growth_drivers"] = fig2
    
    # Save if output_dir specified
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        fig1.savefig(output_path / "mental_health_annual_trends.png", dpi=150, bbox_inches="tight")
        fig2.savefig(output_path / "mental_health_growth_drivers.png", dpi=150, bbox_inches="tight")
        
        table_all.to_csv(output_path / "mental_health_trends_all.csv", index=False)
        table_admitted.to_csv(output_path / "mental_health_trends_admitted.csv", index=False)
        
        print(f"\n✓ Figures and tables saved to: {output_path}")
    
    plt.show()
    
    return results


# =============================================================================
# QUICK TEST
# =============================================================================

if __name__ == "__main__":
    # Test the classification functions
    print("=" * 60)
    print("CLASSIFICATION TESTS")
    print("=" * 60)
    
    # Test drug intoxication classification
    print("\n--- Drug Intoxication Classification ---")
    test_drugs = [
        ("T424X2A", "ICD-10 Benzodiazepine self-harm"),
        ("T400X1A", "ICD-10 Opioid accidental"),
        ("T391X1A", "ICD-10 Paracetamol"),
        ("T436X2A", "ICD-10 Stimulant"),
        ("9694", "ICD-9 Benzodiazepine"),
        ("96509", "ICD-9 Opioid"),
        ("F329", "NOT intoxication (depression)"),
    ]
    
    for code, desc in test_drugs:
        result = classify_drug_intoxication_detailed(code)
        status = f"✓ {result['drug_class']}" if result['is_intoxication'] else "✗ Not intoxication"
        print(f"  {code} ({desc}): {status}")
    
    # Test mental health classification
    print("\n--- Mental Health Classification ---")
    test_mh = [
        ("F329", "ICD-10 Depression"),
        ("F411", "ICD-10 GAD"),
        ("F500", "ICD-10 Anorexia"),
        ("F200", "ICD-10 Schizophrenia"),
        ("3004", "ICD-9 Anxiety"),
        ("311", "ICD-9 Depression"),
        ("T424X2A", "NOT mental health (drug intoxication)"),
    ]
    
    for code, desc in test_mh:
        result = classify_mental_health(code)
        status = f"✓ {result['diagnosis_class']}" if result['is_mental_health'] else "✗ Not mental health"
        print(f"  {code} ({desc}): {status}")
