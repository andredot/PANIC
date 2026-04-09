"""
Synthetic data generators for Lombardy Emergency Department data.

This module provides functions to generate realistic synthetic data that
mirrors the structure of actual Lombardy ED data. Use this for:
- Developing and testing analysis code outside the secure VDI
- Unit testing with known data characteristics
- Demonstrating analysis workflows

The generators create data with realistic distributions based on known
epidemiological patterns from the literature, including:
- Seasonal variation in ED presentations
- Age and sex distributions typical of drug intoxications
- ICD code distributions reflecting benzodiazepine predominance
- COVID-19 pandemic effects (level and trend changes from March 2020)

IMPORTANT: Generated data is entirely synthetic and contains no real
patient information. The patterns are illustrative and should not be
used for epidemiological inference.
"""

from __future__ import annotations

import hashlib
import random
from datetime import date
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from numpy.random import Generator


# =============================================================================
# CONSTANTS FOR DATA GENERATION
# =============================================================================

# Study period
STUDY_START_YEAR = 2017
STUDY_END_YEAR = 2025
COVID_START_YEARMONTH = "202003"  # March 2020

# Age distribution parameters (mixture of normals for drug intoxication)
# Based on literature showing peaks in young adults (18-30) and older adults (50-70)
AGE_DISTRIBUTION_PARAMS = {
    "young_adult": {"mean": 25, "std": 8, "weight": 0.35},
    "middle_adult": {"mean": 45, "std": 12, "weight": 0.30},
    "older_adult": {"mean": 65, "std": 15, "weight": 0.25},
    "adolescent": {"mean": 16, "std": 2, "weight": 0.10},
}

# Sex distribution (females slightly overrepresented in drug intoxication)
FEMALE_PROPORTION = 0.55

# Drug class distribution for intoxication cases
DRUG_CLASS_DISTRIBUTION = {
    "benzodiazepine": 0.40,  # Most common in Lombardy observation
    "antidepressant": 0.20,
    "stimulant": 0.08,
    "opioid": 0.07,
    "cardiovascular": 0.05,
    "other": 0.20,
}

# ICD-10-CM codes by drug class (with intent distribution)
ICD10_CODES_BY_CLASS = {
    "benzodiazepine": ["T424X1A", "T424X2A", "T424X4A"],  # Accidental, self-harm, undetermined
    "antidepressant": ["T430X1A", "T430X2A", "T431X1A", "T432X1A", "T432X2A"],
    "stimulant": ["T436X1A", "T436X2A"],
    "opioid": ["T400X1A", "T400X2A", "T401X1A", "T402X1A"],
    "cardiovascular": ["T460X1A", "T461X1A", "T462X1A"],
    "other": ["T509X1A", "T509X2A", "T509X4A"],
}

# Intent distribution (for randomly selecting among codes)
INTENT_DISTRIBUTION = {
    "accidental": 0.45,
    "self_harm": 0.40,
    "undetermined": 0.15,
}

# ICD-9-CM codes (for pre-transition data, roughly before 2019)
ICD9_CODES_BY_CLASS = {
    "benzodiazepine": ["9694"],
    "antidepressant": ["9690", "9691"],
    "stimulant": ["9697", "9700"],
    "opioid": ["9650", "9651"],
    "cardiovascular": ["9720", "9721"],
    "other": ["9770", "9779"],
}

# Non-intoxication diagnosis codes (for generating background ED presentations)
NON_INTOX_ICD10_CODES = [
    "J069",   # Acute upper respiratory infection
    "R104",   # Abdominal pain
    "R51",    # Headache
    "S0190",  # Unspecified head injury
    "I10",    # Essential hypertension
    "K529",   # Noninfective gastroenteritis
    "F329",   # Major depressive disorder (for psychiatric comorbidity)
    "F411",   # Generalized anxiety disorder
]

# Esito (disposition) distribution
ESITO_DISTRIBUTION = {
    "1": 0.70,  # Discharged home
    "2": 0.10,  # Admitted to ordinary ward (this is our ~10% admission rate)
    "4": 0.02,  # ICU
    "7": 0.08,  # Left AMA
    "8": 0.10,  # Left without being seen
}

# Seasonal pattern (relative rates by month, 1.0 = average)
SEASONAL_PATTERN = {
    1: 1.05,   # January - slightly elevated (post-holiday)
    2: 0.95,
    3: 1.00,
    4: 0.98,
    5: 1.02,
    6: 1.05,   # June - slightly elevated
    7: 1.08,   # July - summer peak
    8: 1.10,   # August - summer peak
    9: 1.00,
    10: 0.98,
    11: 0.95,
    12: 1.05,  # December - holiday period
}

# COVID effect parameters
COVID_IMMEDIATE_EFFECT = -0.15  # 15% drop in March 2020
COVID_TREND_CHANGE = 0.01       # 1% additional monthly increase post-COVID


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def generate_pseudonymised_id(seed: int | str) -> str:
    """
    Generate a deterministic pseudonymised ID in the MB-{hash} format.
    
    Parameters
    ----------
    seed : int or str
        Seed value for generating the hash. Same seed produces same ID.
        
    Returns
    -------
    str
        Pseudonymised ID in format "MB-" followed by 64 hex characters.
        
    Examples
    --------
    >>> generate_pseudonymised_id(12345)
    'MB-5994471ABB01112AFCC18159F6CC74B4F511B99806DA59B3CAF5A9C173CACFC5'
    """
    # Create a deterministic hash from the seed
    seed_str = str(seed).encode('utf-8')
    hash_bytes = hashlib.sha256(seed_str).hexdigest().upper()
    return f"MB-{hash_bytes}"


def generate_yearmonth_range(
    start_year: int = STUDY_START_YEAR,
    end_year: int = STUDY_END_YEAR,
) -> list[str]:
    """
    Generate list of YYYYMM strings for the study period.
    
    Parameters
    ----------
    start_year : int
        First year of study period.
    end_year : int
        Last year of study period.
        
    Returns
    -------
    list[str]
        List of year-month strings in YYYYMM format.
        
    Examples
    --------
    >>> yearmonths = generate_yearmonth_range(2017, 2018)
    >>> len(yearmonths)
    24
    >>> yearmonths[0]
    '201701'
    """
    yearmonths = []
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            yearmonths.append(f"{year}{month:02d}")
    return yearmonths


def sample_age(rng: Generator, n: int = 1) -> np.ndarray:
    """
    Sample ages from a mixture distribution typical of drug intoxication patients.
    
    The distribution is a mixture of four normal distributions representing:
    - Adolescents (10-18)
    - Young adults (18-35)
    - Middle-aged adults (35-55)
    - Older adults (55+)
    
    Parameters
    ----------
    rng : numpy.random.Generator
        Random number generator for reproducibility.
    n : int
        Number of ages to sample.
        
    Returns
    -------
    np.ndarray
        Array of integer ages, clipped to [0, 110].
    """
    ages = np.zeros(n)
    
    # Sample from mixture
    for i in range(n):
        # Choose component
        r = rng.random()
        cumulative = 0.0
        
        for params in AGE_DISTRIBUTION_PARAMS.values():
            cumulative += params["weight"]
            if r < cumulative:
                age = rng.normal(params["mean"], params["std"])
                break
        
        ages[i] = age
    
    # Clip to valid range and convert to int
    return np.clip(ages, 0, 110).astype(int)


def sample_drug_class(rng: Generator, n: int = 1) -> list[str]:
    """
    Sample drug classes according to the observed distribution.
    
    Parameters
    ----------
    rng : numpy.random.Generator
        Random number generator.
    n : int
        Number of samples.
        
    Returns
    -------
    list[str]
        List of drug class names.
    """
    classes = list(DRUG_CLASS_DISTRIBUTION.keys())
    probs = list(DRUG_CLASS_DISTRIBUTION.values())
    return list(rng.choice(classes, size=n, p=probs))


def get_icd_code(drug_class: str, use_icd10: bool, rng: Generator) -> str:
    """
    Get an ICD code for a given drug class.
    
    Parameters
    ----------
    drug_class : str
        Drug class name (e.g., "benzodiazepine").
    use_icd10 : bool
        If True, return ICD-10-CM code; otherwise ICD-9-CM.
    rng : numpy.random.Generator
        Random number generator.
        
    Returns
    -------
    str
        ICD diagnosis code.
    """
    if use_icd10:
        codes = ICD10_CODES_BY_CLASS.get(drug_class, ICD10_CODES_BY_CLASS["other"])
    else:
        codes = ICD9_CODES_BY_CLASS.get(drug_class, ICD9_CODES_BY_CLASS["other"])
    
    return rng.choice(codes)


def calculate_expected_count(
    yearmonth: str,
    baseline_monthly_count: float,
    pre_covid_trend: float = 0.005,  # 0.5% monthly increase pre-COVID
    include_covid_effect: bool = True,
) -> float:
    """
    Calculate expected count for a given month including trend and seasonality.
    
    Parameters
    ----------
    yearmonth : str
        Year-month in YYYYMM format.
    baseline_monthly_count : float
        Baseline count at study start (January 2017).
    pre_covid_trend : float
        Monthly trend (proportional change) before COVID.
    include_covid_effect : bool
        Whether to include COVID-related level and trend changes.
        
    Returns
    -------
    float
        Expected count for the month.
    """
    year = int(yearmonth[:4])
    month = int(yearmonth[4:6])
    
    # Calculate months since study start
    months_since_start = (year - STUDY_START_YEAR) * 12 + (month - 1)
    
    # Apply pre-COVID trend
    expected = baseline_monthly_count * (1 + pre_covid_trend) ** months_since_start
    
    # Apply seasonal pattern
    expected *= SEASONAL_PATTERN.get(month, 1.0)
    
    # Apply COVID effects if applicable
    if include_covid_effect and yearmonth >= COVID_START_YEARMONTH:
        # Immediate level change
        expected *= (1 + COVID_IMMEDIATE_EFFECT)
        
        # Additional trend change post-COVID
        covid_year = int(COVID_START_YEARMONTH[:4])
        covid_month = int(COVID_START_YEARMONTH[4:6])
        months_since_covid = (year - covid_year) * 12 + (month - covid_month)
        expected *= (1 + COVID_TREND_CHANGE) ** months_since_covid
    
    return max(expected, 0)


# =============================================================================
# MAIN DATA GENERATION FUNCTIONS
# =============================================================================

def generate_ed_presentations(
    n_presentations: int = 10000,
    intoxication_rate: float = 0.03,  # 3% of ED presentations are drug intox
    seed: int = 42,
    start_year: int = STUDY_START_YEAR,
    end_year: int = STUDY_END_YEAR,
    include_covid_effect: bool = True,
    icd10_transition_yearmonth: str = "201901",  # When ICD-10 coding begins
) -> pd.DataFrame:
    """
    Generate a synthetic dataset of ED presentations.
    
    This function creates a realistic dataset with:
    - Appropriate temporal distribution (trend + seasonality + COVID effect)
    - Realistic age and sex distributions
    - ICD-9 to ICD-10 coding transition
    - Drug class distribution matching Lombardy observations
    
    Parameters
    ----------
    n_presentations : int
        Total number of ED presentations to generate.
    intoxication_rate : float
        Proportion of presentations that are drug intoxications.
    seed : int
        Random seed for reproducibility.
    start_year : int
        First year of data.
    end_year : int
        Last year of data.
    include_covid_effect : bool
        Whether to include COVID-related changes.
    icd10_transition_yearmonth : str
        Year-month when ICD-10 coding began.
        
    Returns
    -------
    pd.DataFrame
        Synthetic ED presentation data with columns matching the Lombardy schema.
        
    Examples
    --------
    >>> df = generate_ed_presentations(n_presentations=1000, seed=42)
    >>> df.shape
    (1000, 14)
    >>> df['annomese_ingr'].nunique()  # Multiple months represented
    > 1
    """
    rng = np.random.default_rng(seed)
    
    # Generate year-month distribution
    yearmonths = generate_yearmonth_range(start_year, end_year)
    
    # Calculate expected counts per month
    baseline = n_presentations / len(yearmonths)
    expected_counts = [
        calculate_expected_count(ym, baseline, include_covid_effect=include_covid_effect)
        for ym in yearmonths
    ]
    
    # Normalise to sum to n_presentations
    total_expected = sum(expected_counts)
    normalised_probs = [c / total_expected for c in expected_counts]
    
    # Sample year-months according to expected distribution
    sampled_yearmonths = rng.choice(yearmonths, size=n_presentations, p=normalised_probs)
    
    # Determine which presentations are drug intoxications
    is_intoxication = rng.random(n_presentations) < intoxication_rate
    n_intox = is_intoxication.sum()
    
    # Generate ages
    ages = sample_age(rng, n_presentations)
    
    # Generate sex
    sexes = np.where(rng.random(n_presentations) < FEMALE_PROPORTION, "F", "M")
    
    # Generate drug classes for intoxication cases
    drug_classes = [""] * n_presentations
    for i in np.where(is_intoxication)[0]:
        drug_classes[i] = sample_drug_class(rng, 1)[0]
    
    # Generate diagnosis codes
    cod_diagnosi = []
    diagnosi_desc = []
    cod_diagnosi_secondaria = []
    diagnosi_secondaria_desc = []
    
    for i in range(n_presentations):
        ym = sampled_yearmonths[i]
        use_icd10 = ym >= icd10_transition_yearmonth
        
        if is_intoxication[i]:
            # Drug intoxication case
            code = get_icd_code(drug_classes[i], use_icd10, rng)
            cod_diagnosi.append(code)
            diagnosi_desc.append(f"INTOSSICAZIONE DA {drug_classes[i].upper()}")
            
            # Occasionally add psychiatric comorbidity as secondary
            if rng.random() < 0.3:
                cod_diagnosi_secondaria.append("F329" if use_icd10 else "2962")
                diagnosi_secondaria_desc.append("DISTURBO DEPRESSIVO")
            else:
                cod_diagnosi_secondaria.append("_")
                diagnosi_secondaria_desc.append("DATO NON APPLICABILE")
        else:
            # Non-intoxication case
            if use_icd10:
                code = rng.choice(NON_INTOX_ICD10_CODES)
            else:
                # Simplified ICD-9 codes for non-intox
                code = rng.choice(["4659", "7890", "7840", "4019"])
            
            cod_diagnosi.append(code)
            diagnosi_desc.append("ALTRA DIAGNOSI")
            cod_diagnosi_secondaria.append("_")
            diagnosi_secondaria_desc.append("DATO NON APPLICABILE")
    
    # Generate esito (disposition)
    esito_codes = list(ESITO_DISTRIBUTION.keys())
    esito_probs = list(ESITO_DISTRIBUTION.values())
    esiti = rng.choice(esito_codes, size=n_presentations, p=esito_probs)
    
    esito_descriptions = {
        "1": "DIMISSIONE A DOMICILIO",
        "2": "RICOVERO IN REPARTO",
        "4": "RICOVERO IN TERAPIA INTENSIVA",
        "7": "RIFIUTO RICOVERO",
        "8": "ABBANDONO",
    }
    esiti_desc = [esito_descriptions.get(e, "ALTRO") for e in esiti]
    
    # Build DataFrame
    df = pd.DataFrame({
        "codice_fiscale_assistito_microbio": [
            generate_pseudonymised_id(seed * 1000000 + i) for i in range(n_presentations)
        ],
        "annomese_ingr": sampled_yearmonths,
        "eta_calcolata": ages,
        "eta_flusso": [str(a * 100 + rng.integers(0, 100)) for a in ages],  # Simulated flow encoding
        "sesso_anag_ass_to": sexes,
        "sesso_flusso": sexes,  # Same as registry for simplicity
        "cod_diagnosi": cod_diagnosi,
        "diagnosi": diagnosi_desc,
        "cod_diagnosi_secondaria": cod_diagnosi_secondaria,
        "diagnosi_secondaria": diagnosi_secondaria_desc,
        "codice_esito": esiti,
        "descrizione_esito": esiti_desc,
        "codice_nazione_flusso": ["100"] * n_presentations,  # Italy
        "conteggio_persone_fisiche": [1] * n_presentations,
    })
    
    return df


def generate_intoxication_only_dataset(
    n_intoxications: int = 1000,
    seed: int = 42,
    start_year: int = STUDY_START_YEAR,
    end_year: int = STUDY_END_YEAR,
    include_covid_effect: bool = True,
) -> pd.DataFrame:
    """
    Generate a dataset containing only drug intoxication cases.
    
    This is useful for testing analysis code that operates on
    pre-filtered intoxication data.
    
    Parameters
    ----------
    n_intoxications : int
        Number of intoxication cases to generate.
    seed : int
        Random seed.
    start_year : int
        First year.
    end_year : int
        Last year.
    include_covid_effect : bool
        Whether to include COVID effects.
        
    Returns
    -------
    pd.DataFrame
        Dataset with only drug intoxication cases.
    """
    # Generate with 100% intoxication rate
    return generate_ed_presentations(
        n_presentations=n_intoxications,
        intoxication_rate=1.0,
        seed=seed,
        start_year=start_year,
        end_year=end_year,
        include_covid_effect=include_covid_effect,
    )


def generate_monthly_aggregated_data(
    seed: int = 42,
    start_year: int = STUDY_START_YEAR,
    end_year: int = STUDY_END_YEAR,
    baseline_intox_count: int = 150,
    baseline_total_ed: int = 5000,
    include_covid_effect: bool = True,
) -> pd.DataFrame:
    """
    Generate monthly aggregated counts for trend analysis.
    
    This creates data in the format needed for segmented regression,
    with counts rather than individual records.
    
    Parameters
    ----------
    seed : int
        Random seed.
    start_year : int
        First year.
    end_year : int
        Last year.
    baseline_intox_count : int
        Baseline monthly intoxication count (January 2017).
    baseline_total_ed : int
        Baseline monthly total ED presentations.
    include_covid_effect : bool
        Whether to include COVID effects.
        
    Returns
    -------
    pd.DataFrame
        Monthly aggregated data with columns:
        - yearmonth: YYYYMM string
        - year: int
        - month: int
        - intoxication_count: int
        - total_ed_count: int
        - admission_count: int (among intoxications)
        - intoxication_rate: float (per 1000 ED presentations)
        - covid_period: bool
        - months_since_start: int
        - months_since_covid: int (0 before COVID)
    """
    rng = np.random.default_rng(seed)
    
    yearmonths = generate_yearmonth_range(start_year, end_year)
    
    records = []
    for i, ym in enumerate(yearmonths):
        year = int(ym[:4])
        month = int(ym[4:6])
        
        # Calculate expected counts
        expected_intox = calculate_expected_count(
            ym, baseline_intox_count, 
            pre_covid_trend=0.008,  # 0.8% monthly increase
            include_covid_effect=include_covid_effect
        )
        expected_total = calculate_expected_count(
            ym, baseline_total_ed,
            pre_covid_trend=0.002,  # Slower growth in total ED
            include_covid_effect=include_covid_effect
        )
        
        # Add Poisson noise
        intox_count = rng.poisson(expected_intox)
        total_count = rng.poisson(expected_total)
        
        # Admissions (~10% of intoxications)
        admission_count = rng.binomial(intox_count, 0.10)
        
        # COVID indicator
        is_covid = ym >= COVID_START_YEARMONTH
        
        # Months since COVID (0 if before)
        if is_covid:
            covid_year = int(COVID_START_YEARMONTH[:4])
            covid_month = int(COVID_START_YEARMONTH[4:6])
            months_since_covid = (year - covid_year) * 12 + (month - covid_month)
        else:
            months_since_covid = 0
        
        records.append({
            "yearmonth": ym,
            "year": year,
            "month": month,
            "intoxication_count": intox_count,
            "total_ed_count": total_count,
            "admission_count": admission_count,
            "intoxication_rate": (intox_count / total_count * 1000) if total_count > 0 else 0,
            "covid_period": is_covid,
            "months_since_start": i,
            "months_since_covid": months_since_covid,
        })
    
    return pd.DataFrame(records)


def generate_stratified_monthly_data(
    seed: int = 42,
    start_year: int = STUDY_START_YEAR,
    end_year: int = STUDY_END_YEAR,
) -> pd.DataFrame:
    """
    Generate monthly data stratified by sex and age group.
    
    This creates data suitable for stratified trend analyses.
    
    Parameters
    ----------
    seed : int
        Random seed.
    start_year : int
        First year.
    end_year : int
        Last year.
        
    Returns
    -------
    pd.DataFrame
        Monthly data with stratification columns.
    """
    rng = np.random.default_rng(seed)
    
    yearmonths = generate_yearmonth_range(start_year, end_year)
    age_groups = ["0-17", "18-24", "25-44", "45-64", "65+"]
    sexes = ["F", "M"]
    
    # Baseline counts by stratum (reflecting demographic distribution)
    base_counts = {
        ("F", "0-17"): 8,
        ("F", "18-24"): 25,
        ("F", "25-44"): 30,
        ("F", "45-64"): 20,
        ("F", "65+"): 12,
        ("M", "0-17"): 5,
        ("M", "18-24"): 18,
        ("M", "25-44"): 22,
        ("M", "45-64"): 15,
        ("M", "65+"): 10,
    }
    
    records = []
    for ym in yearmonths:
        year = int(ym[:4])
        month = int(ym[4:6])
        
        for sex in sexes:
            for age_group in age_groups:
                baseline = base_counts.get((sex, age_group), 10)
                
                # Apply trends (different by group)
                trend_multiplier = 1.0
                if sex == "F" and age_group in ["18-24", "25-44"]:
                    # Stronger trend in young women
                    trend_multiplier = 1.5
                
                expected = calculate_expected_count(
                    ym, baseline,
                    pre_covid_trend=0.006 * trend_multiplier,
                    include_covid_effect=True
                )
                
                count = rng.poisson(expected)
                
                records.append({
                    "yearmonth": ym,
                    "year": year,
                    "month": month,
                    "sex": sex,
                    "age_group": age_group,
                    "intoxication_count": count,
                })
    
    return pd.DataFrame(records)


# =============================================================================
# CONVENIENCE FUNCTION FOR QUICK TESTING
# =============================================================================

def get_sample_data(
    size: str = "small",
    seed: int = 42,
) -> dict[str, pd.DataFrame]:
    """
    Get a collection of sample datasets for testing.
    
    Parameters
    ----------
    size : str
        "small" (1000 records), "medium" (10000), or "large" (100000).
    seed : int
        Random seed.
        
    Returns
    -------
    dict[str, pd.DataFrame]
        Dictionary with keys:
        - "ed_presentations": Individual-level ED data
        - "monthly_aggregated": Monthly counts
        - "monthly_stratified": Monthly counts by demographics
        
    Examples
    --------
    >>> data = get_sample_data("small")
    >>> data["ed_presentations"].shape
    (1000, 14)
    >>> data["monthly_aggregated"]["yearmonth"].nunique()
    108  # 9 years * 12 months
    """
    sizes = {
        "small": 1000,
        "medium": 10000,
        "large": 100000,
    }
    n = sizes.get(size, 1000)
    
    return {
        "ed_presentations": generate_ed_presentations(n, seed=seed),
        "monthly_aggregated": generate_monthly_aggregated_data(seed=seed),
        "monthly_stratified": generate_stratified_monthly_data(seed=seed),
    }
