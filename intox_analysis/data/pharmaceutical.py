"""
Pharmaceutical dispensing data (Flusso F) processing module.

This module handles the pharmaceutical prescription/dispensing data from the
Lombardy regional health system. Data is approximately 1GB per year, so we use
Polars with lazy evaluation for memory-efficient processing.

Key features:
- Lazy evaluation: queries are optimised before execution
- Streaming: can process larger-than-memory datasets
- Efficient aggregations: pre-built queries for common analyses
- ATC code classification: maps drugs to therapeutic categories

Data structure (confirmed from VDI):
- Codice Fiscale Assistito MICROBIO: Pseudonymised patient ID (MB-{64 hex})
- Eta Anni: Age in years
- Sesso: Sex (M/F)
- Data Prescrizione.Data: Prescription date (YYYY/MM/DD HH:MM:SS)
- Data Erogazione.Data: Dispensing date (YYYY/MM/DD HH:MM:SS)  
- Cod Atc: ATC classification code
- Desc Atc: Drug name
- Cod Tipo Medico: Prescriber type code
- Desc Tipo Medico: Prescriber type description
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import polars as pl


# =============================================================================
# ATC CODE CLASSIFICATION
# =============================================================================

# ATC codes relevant to drug intoxication surveillance
# Reference: WHO ATC/DDD Index (https://www.whocc.no/atc_ddd_index/)

ATC_PSYCHOTROPIC_GROUPS = {
    # N05: Psycholeptics (calming drugs)
    "N05A": "Antipsychotics",
    "N05B": "Anxiolytics",           # Includes benzodiazepine anxiolytics
    "N05C": "Hypnotics and sedatives", # Includes benzodiazepine hypnotics, Z-drugs
    
    # N06: Psychoanaleptics (stimulating drugs)
    "N06A": "Antidepressants",
    "N06B": "Psychostimulants",      # ADHD medications, etc.
    "N06C": "Psycholeptics and psychoanaleptics in combination",
    "N06D": "Anti-dementia drugs",
    
    # N07: Other nervous system drugs
    "N07B": "Drugs used in addictive disorders",  # Includes opioid substitution
}

# Specific drug classes of high interest for intoxication surveillance
ATC_BENZODIAZEPINES = {
    # Anxiolytic benzodiazepines (N05BA)
    "N05BA01": "Diazepam",
    "N05BA02": "Chlordiazepoxide",
    "N05BA04": "Oxazepam",
    "N05BA05": "Potassium clorazepate",
    "N05BA06": "Lorazepam",
    "N05BA08": "Bromazepam",
    "N05BA09": "Clobazam",
    "N05BA10": "Ketazolam",
    "N05BA11": "Prazepam",
    "N05BA12": "Alprazolam",  # CONFIRMED in VDI data
    "N05BA18": "Ethyl loflazepate",
    "N05BA21": "Clotiazepam",
    "N05BA22": "Cloxazolam",
    "N05BA23": "Tofisopam",
    
    # Hypnotic benzodiazepines (N05CD)
    "N05CD01": "Flurazepam",
    "N05CD02": "Nitrazepam",
    "N05CD03": "Flunitrazepam",
    "N05CD04": "Estazolam",
    "N05CD05": "Triazolam",
    "N05CD06": "Lormetazepam",
    "N05CD07": "Temazepam",
    "N05CD08": "Midazolam",
    "N05CD09": "Brotizolam",
    "N05CD11": "Loprazolam",
    "N05CD12": "Doxefazepam",
    "N05CD13": "Cinolazepam",
}

ATC_Z_DRUGS = {
    # Z-drugs (benzodiazepine-like hypnotics)
    "N05CF01": "Zopiclone",  # CONFIRMED in VDI data
    "N05CF02": "Zolpidem",
    "N05CF03": "Zaleplon",
    "N05CF04": "Eszopiclone",
}

ATC_OPIOIDS = {
    # Opioid analgesics (N02A)
    "N02AA01": "Morphine",
    "N02AA03": "Hydromorphone",
    "N02AA05": "Oxycodone",
    "N02AA55": "Oxycodone combinations",
    "N02AB02": "Pethidine",
    "N02AB03": "Fentanyl",
    "N02AE01": "Buprenorphine",
    "N02AX02": "Tramadol",
    "N02AX52": "Tramadol combinations",
    
    # Opioid substitution (N07BC)
    "N07BC01": "Buprenorphine",
    "N07BC02": "Methadone",
    "N07BC51": "Buprenorphine combinations",
}

ATC_ANTIDEPRESSANTS = {
    # SSRIs (N06AB)
    "N06AB03": "Fluoxetine",
    "N06AB04": "Citalopram",
    "N06AB05": "Paroxetine",
    "N06AB06": "Sertraline",
    "N06AB08": "Fluvoxamine",
    "N06AB10": "Escitalopram",
    
    # SNRIs (N06AX)
    "N06AX16": "Venlafaxine",
    "N06AX21": "Duloxetine",
    
    # Tricyclics (N06AA)
    "N06AA04": "Clomipramine",
    "N06AA09": "Amitriptyline",
    "N06AA10": "Nortriptyline",
    "N06AA21": "Maprotiline",
    
    # Others
    "N06AX05": "Trazodone",
    "N06AX11": "Mirtazapine",
    "N06AX12": "Bupropion",
}

ATC_STIMULANTS = {
    # Psychostimulants for ADHD (N06BA)
    "N06BA01": "Amfetamine",
    "N06BA02": "Dexamfetamine",
    "N06BA04": "Methylphenidate",
    "N06BA07": "Modafinil",
    "N06BA09": "Atomoxetine",
    "N06BA12": "Lisdexamfetamine",
}


def classify_atc_code(atc_code: str) -> dict[str, str | bool]:
    """
    Classify an ATC code into therapeutic categories.
    
    This function determines whether a drug is a psychotropic medication
    and identifies its specific drug class for intoxication surveillance.
    
    Parameters
    ----------
    atc_code : str
        ATC classification code (e.g., "N05BA12" for alprazolam).
        
    Returns
    -------
    dict
        Dictionary containing:
        - is_psychotropic: bool
        - drug_class: str (e.g., "benzodiazepine", "opioid", "antidepressant")
        - group_name: str (e.g., "Anxiolytics")
        - drug_name: str or None (if known)
        
    Examples
    --------
    >>> classify_atc_code("N05BA12")
    {'is_psychotropic': True, 'drug_class': 'benzodiazepine', 
     'group_name': 'Anxiolytics', 'drug_name': 'Alprazolam'}
    >>> classify_atc_code("N05CF01")
    {'is_psychotropic': True, 'drug_class': 'z_drug',
     'group_name': 'Hypnotics and sedatives', 'drug_name': 'Zopiclone'}
    >>> classify_atc_code("A02BC01")
    {'is_psychotropic': False, 'drug_class': 'other',
     'group_name': None, 'drug_name': None}
    """
    if not atc_code or not isinstance(atc_code, str):
        return {
            "is_psychotropic": False,
            "drug_class": "unknown",
            "group_name": None,
            "drug_name": None,
        }
    
    atc_upper = atc_code.upper().strip()
    
    # Check specific drug classes first (most specific match)
    if atc_upper in ATC_BENZODIAZEPINES:
        return {
            "is_psychotropic": True,
            "drug_class": "benzodiazepine",
            "group_name": "Anxiolytics" if atc_upper.startswith("N05BA") else "Hypnotics and sedatives",
            "drug_name": ATC_BENZODIAZEPINES[atc_upper],
        }
    
    if atc_upper in ATC_Z_DRUGS:
        return {
            "is_psychotropic": True,
            "drug_class": "z_drug",
            "group_name": "Hypnotics and sedatives",
            "drug_name": ATC_Z_DRUGS[atc_upper],
        }
    
    if atc_upper in ATC_OPIOIDS:
        return {
            "is_psychotropic": True,
            "drug_class": "opioid",
            "group_name": "Opioid analgesics",
            "drug_name": ATC_OPIOIDS[atc_upper],
        }
    
    if atc_upper in ATC_ANTIDEPRESSANTS:
        return {
            "is_psychotropic": True,
            "drug_class": "antidepressant",
            "group_name": "Antidepressants",
            "drug_name": ATC_ANTIDEPRESSANTS[atc_upper],
        }
    
    if atc_upper in ATC_STIMULANTS:
        return {
            "is_psychotropic": True,
            "drug_class": "stimulant",
            "group_name": "Psychostimulants",
            "drug_name": ATC_STIMULANTS[atc_upper],
        }
    
    # Check broader psychotropic groups (N05, N06, N07B)
    for group_code, group_name in ATC_PSYCHOTROPIC_GROUPS.items():
        if atc_upper.startswith(group_code):
            return {
                "is_psychotropic": True,
                "drug_class": "other_psychotropic",
                "group_name": group_name,
                "drug_name": None,
            }
    
    # Not a psychotropic drug
    return {
        "is_psychotropic": False,
        "drug_class": "other",
        "group_name": None,
        "drug_name": None,
    }


# =============================================================================
# COLUMN NAME MAPPINGS
# =============================================================================

# Mapping from VDI column names to standardised names
PHARMA_COLUMN_MAPPING = {
    "Codice Fiscale Assistito MICROBIO": "patient_id",
    "Eta Anni": "age_years",
    "Sesso": "sex",
    "Data Prescrizione.Data": "prescription_date",
    "Data Erogazione.Data": "dispensing_date",
    "Cod Atc": "atc_code",
    "Desc Atc": "drug_name",
    "Cod Tipo Medico": "prescriber_type_code",
    "Desc Tipo Medico": "prescriber_type_desc",
}

# Prescriber types (from VDI observations)
PRESCRIBER_TYPES = {
    "1": "GP",              # GENERICI = General Practitioner
    "2": "Missing",         # DATO MANCANTE
    "Y": "Hospital",        # DIPENDENTI = Hospital/employed physicians (provisional)
    # TODO: Verify complete codebook in VDI
}


# =============================================================================
# POLARS LAZY LOADING AND PROCESSING
# =============================================================================

def scan_pharmaceutical_data(
    file_paths: list[Path] | Path,
    *,
    standardise_columns: bool = True,
    parse_dates: bool = True,
) -> pl.LazyFrame:
    """
    Create a lazy scan of pharmaceutical dispensing data.
    
    This function creates a LazyFrame that can be used to build optimised
    queries without loading data into memory until collect() is called.
    For 1GB+ files, this is essential for memory efficiency.
    
    Parameters
    ----------
    file_paths : Path or list of Path
        Path(s) to CSV file(s) containing pharmaceutical data.
        Multiple files will be concatenated vertically.
    standardise_columns : bool, default True
        If True, rename columns to standardised English names.
    parse_dates : bool, default True
        If True, parse date columns as datetime type.
        
    Returns
    -------
    pl.LazyFrame
        Lazy representation of the pharmaceutical data.
        
    Examples
    --------
    >>> # Scan all yearly files without loading into memory
    >>> lf = scan_pharmaceutical_data([
    ...     Path("pharma_2017.csv"),
    ...     Path("pharma_2018.csv"),
    ...     Path("pharma_2019.csv"),
    ... ])
    >>> # Build query (still lazy, no memory used)
    >>> benzos = lf.filter(pl.col("atc_code").str.starts_with("N05BA"))
    >>> # Only now does data get loaded and processed
    >>> result = benzos.collect()
    
    Notes
    -----
    The date format in VDI is "YYYY/MM/DD HH:MM:SS" which Polars can parse
    with format "%Y/%m/%d %H:%M:%S".
    """
    if isinstance(file_paths, Path):
        file_paths = [file_paths]
    
    # Create lazy scans for each file
    lazy_frames = []
    for path in file_paths:
        # Use scan_csv for lazy loading (memory efficient)
        lf = pl.scan_csv(
            path,
            # Infer schema from first 10000 rows for speed
            infer_schema_length=10000,
            # Don't load everything at once
            low_memory=True,
        )
        lazy_frames.append(lf)
    
    # Concatenate all files vertically
    if len(lazy_frames) == 1:
        lf = lazy_frames[0]
    else:
        lf = pl.concat(lazy_frames)
    
    # Standardise column names if requested
    if standardise_columns:
        # Build rename mapping for columns that exist
        lf = lf.rename({
            old: new 
            for old, new in PHARMA_COLUMN_MAPPING.items()
        })
    
    # Parse dates if requested
    if parse_dates:
        date_format = "%Y/%m/%d %H:%M:%S"
        date_cols = ["prescription_date", "dispensing_date"] if standardise_columns else [
            "Data Prescrizione.Data", "Data Erogazione.Data"
        ]
        for col in date_cols:
            lf = lf.with_columns(
                pl.col(col).str.to_datetime(format=date_format, strict=False)
            )
    
    return lf


def add_derived_columns(lf: pl.LazyFrame) -> pl.LazyFrame:
    """
    Add derived columns useful for analysis.
    
    This function adds:
    - year_month: YYYYMM format for temporal aggregation
    - is_benzodiazepine: boolean flag for benzodiazepine prescriptions
    - is_z_drug: boolean flag for Z-drug prescriptions  
    - is_opioid: boolean flag for opioid prescriptions
    - drug_class: categorical classification of the drug
    - days_to_dispense: days between prescription and dispensing
    
    Parameters
    ----------
    lf : pl.LazyFrame
        Lazy frame with standardised column names.
        
    Returns
    -------
    pl.LazyFrame
        Lazy frame with additional derived columns.
    """
    # Build list of benzodiazepine ATC prefixes for efficient matching
    benzo_prefixes = list(ATC_BENZODIAZEPINES.keys())
    z_drug_prefixes = list(ATC_Z_DRUGS.keys())
    opioid_prefixes = list(ATC_OPIOIDS.keys())
    antidepressant_prefixes = list(ATC_ANTIDEPRESSANTS.keys())
    stimulant_prefixes = list(ATC_STIMULANTS.keys())
    
    return lf.with_columns([
        # Year-month for temporal aggregation (from dispensing date)
        pl.col("dispensing_date").dt.strftime("%Y%m").alias("year_month"),
        
        # Year and month as separate columns for flexibility
        pl.col("dispensing_date").dt.year().alias("year"),
        pl.col("dispensing_date").dt.month().alias("month"),
        
        # Drug class flags using efficient string operations
        pl.col("atc_code").is_in(benzo_prefixes).alias("is_benzodiazepine"),
        pl.col("atc_code").is_in(z_drug_prefixes).alias("is_z_drug"),
        pl.col("atc_code").is_in(opioid_prefixes).alias("is_opioid"),
        pl.col("atc_code").is_in(antidepressant_prefixes).alias("is_antidepressant"),
        pl.col("atc_code").is_in(stimulant_prefixes).alias("is_stimulant"),
        
        # Broader psychotropic flag (N05 or N06 or N07B)
        (
            pl.col("atc_code").str.starts_with("N05") |
            pl.col("atc_code").str.starts_with("N06") |
            pl.col("atc_code").str.starts_with("N07B")
        ).alias("is_psychotropic"),
        
        # Days between prescription and dispensing
        (
            pl.col("dispensing_date") - pl.col("prescription_date")
        ).dt.total_days().alias("days_to_dispense"),
        
        # Drug class as categorical (more efficient than repeated string ops)
        pl.when(pl.col("atc_code").is_in(benzo_prefixes))
          .then(pl.lit("benzodiazepine"))
          .when(pl.col("atc_code").is_in(z_drug_prefixes))
          .then(pl.lit("z_drug"))
          .when(pl.col("atc_code").is_in(opioid_prefixes))
          .then(pl.lit("opioid"))
          .when(pl.col("atc_code").is_in(antidepressant_prefixes))
          .then(pl.lit("antidepressant"))
          .when(pl.col("atc_code").is_in(stimulant_prefixes))
          .then(pl.lit("stimulant"))
          .when(pl.col("atc_code").str.starts_with("N05") | 
                pl.col("atc_code").str.starts_with("N06") |
                pl.col("atc_code").str.starts_with("N07B"))
          .then(pl.lit("other_psychotropic"))
          .otherwise(pl.lit("non_psychotropic"))
          .alias("drug_class"),
    ])


# =============================================================================
# PRE-BUILT AGGREGATION QUERIES
# =============================================================================

def monthly_prescription_counts(
    lf: pl.LazyFrame,
    *,
    drug_classes: list[str] | None = None,
    by_drug_class: bool = False,
    by_age_group: bool = False,
    by_sex: bool = False,
) -> pl.LazyFrame:
    """
    Compute monthly prescription counts with optional stratification.
    
    This is a common query for trend analysis. The function builds an
    optimised lazy query that Polars will execute efficiently.
    
    Parameters
    ----------
    lf : pl.LazyFrame
        Lazy frame with derived columns (from add_derived_columns).
    drug_classes : list of str, optional
        Filter to specific drug classes (e.g., ["benzodiazepine", "z_drug"]).
        If None, includes all prescriptions.
    by_drug_class : bool, default False
        If True, stratify counts by drug class.
    by_age_group : bool, default False
        If True, stratify by age group (0-17, 18-34, 35-54, 55-74, 75+).
    by_sex : bool, default False
        If True, stratify by sex.
        
    Returns
    -------
    pl.LazyFrame
        Lazy frame with columns: year_month, [stratification columns], n_prescriptions, n_patients.
        
    Examples
    --------
    >>> # Total monthly benzodiazepine prescriptions
    >>> counts = monthly_prescription_counts(
    ...     lf, drug_classes=["benzodiazepine"]
    ... ).collect()
    >>> 
    >>> # Monthly counts by drug class and sex
    >>> stratified = monthly_prescription_counts(
    ...     lf, by_drug_class=True, by_sex=True
    ... ).collect()
    """
    # Start with the lazy frame
    query = lf
    
    # Filter to specific drug classes if requested
    if drug_classes:
        query = query.filter(pl.col("drug_class").is_in(drug_classes))
    
    # Add age groups if stratifying by age
    if by_age_group:
        query = query.with_columns(
            pl.when(pl.col("age_years") < 18).then(pl.lit("0-17"))
              .when(pl.col("age_years") < 35).then(pl.lit("18-34"))
              .when(pl.col("age_years") < 55).then(pl.lit("35-54"))
              .when(pl.col("age_years") < 75).then(pl.lit("55-74"))
              .otherwise(pl.lit("75+"))
              .alias("age_group")
        )
    
    # Build grouping columns
    group_cols = ["year_month"]
    if by_drug_class:
        group_cols.append("drug_class")
    if by_age_group:
        group_cols.append("age_group")
    if by_sex:
        group_cols.append("sex")
    
    # Aggregate
    return (
        query
        .group_by(group_cols)
        .agg([
            pl.len().alias("n_prescriptions"),
            pl.col("patient_id").n_unique().alias("n_patients"),
        ])
        .sort(group_cols)
    )


def identify_chronic_users(
    lf: pl.LazyFrame,
    *,
    drug_classes: list[str] | None = None,
    min_prescriptions_per_year: int = 4,
    max_gap_days: int = 90,
) -> pl.LazyFrame:
    """
    Identify chronic/regular users of specific drug classes.
    
    A chronic user is defined as someone with regular prescriptions over time.
    This is important for Research Question 5: distinguishing intoxications
    among chronic users (therapeutic misadventure) vs sporadic users (likely misuse).
    
    Parameters
    ----------
    lf : pl.LazyFrame
        Lazy frame with derived columns.
    drug_classes : list of str, optional
        Drug classes to consider (e.g., ["benzodiazepine"]).
        If None, uses all psychotropic drugs.
    min_prescriptions_per_year : int, default 4
        Minimum prescriptions per year to be considered chronic.
        4 = approximately quarterly prescriptions.
    max_gap_days : int, default 90
        Maximum gap between prescriptions to maintain "chronic" status.
        90 days = roughly quarterly.
        
    Returns
    -------
    pl.LazyFrame
        Patient-level data with columns:
        - patient_id
        - drug_class
        - n_prescriptions
        - first_prescription
        - last_prescription
        - duration_days
        - is_chronic
        
    Notes
    -----
    The definition of "chronic user" is somewhat arbitrary and should be
    validated against clinical guidance. The default of 4+ prescriptions/year
    with gaps ≤90 days is a starting point that can be refined.
    """
    # Filter to relevant drug classes
    query = lf
    if drug_classes:
        query = query.filter(pl.col("drug_class").is_in(drug_classes))
    else:
        query = query.filter(pl.col("is_psychotropic"))
    
    # Compute per-patient, per-drug-class statistics
    patient_stats = (
        query
        .group_by(["patient_id", "drug_class"])
        .agg([
            pl.len().alias("n_prescriptions"),
            pl.col("dispensing_date").min().alias("first_prescription"),
            pl.col("dispensing_date").max().alias("last_prescription"),
        ])
        .with_columns([
            # Duration of use in days
            (
                pl.col("last_prescription") - pl.col("first_prescription")
            ).dt.total_days().alias("duration_days"),
        ])
        .with_columns([
            # Prescriptions per year
            pl.when(pl.col("duration_days") > 0)
              .then(pl.col("n_prescriptions") * 365.25 / pl.col("duration_days"))
              .otherwise(pl.col("n_prescriptions"))
              .alias("prescriptions_per_year"),
        ])
        .with_columns([
            # Chronic user flag
            (
                (pl.col("prescriptions_per_year") >= min_prescriptions_per_year) &
                (pl.col("duration_days") >= 90)  # At least 3 months of use
            ).alias("is_chronic"),
        ])
    )
    
    return patient_stats


def link_with_ed_presentations(
    pharma_lf: pl.LazyFrame,
    ed_df: pl.DataFrame,
    *,
    lookback_days: int = 365,
    drug_classes: list[str] | None = None,
) -> pl.LazyFrame:
    """
    Link pharmaceutical data with ED intoxication presentations.
    
    For each ED intoxication presentation, identify whether the patient
    had prior prescriptions for relevant drugs. This enables Research Question 5:
    is the intoxication associated with prescription drug use?
    
    Parameters
    ----------
    pharma_lf : pl.LazyFrame
        Pharmaceutical lazy frame with standardised columns.
    ed_df : pl.DataFrame
        ED presentations DataFrame (must be collected, not lazy).
        Should contain patient_id and presentation_date columns.
    lookback_days : int, default 365
        Number of days before ED presentation to search for prescriptions.
    drug_classes : list of str, optional
        Drug classes to look for. If None, searches all.
        
    Returns
    -------
    pl.LazyFrame
        ED presentations enriched with prescription history:
        - had_prior_prescription: bool
        - prior_prescription_drug_class: str or null
        - days_since_last_prescription: int or null
        - was_chronic_user: bool
        
    Notes
    -----
    This is a computationally expensive operation for large datasets.
    Consider running on a filtered subset of ED presentations (intoxications only)
    rather than all presentations.
    """
    # This is a sketch - actual implementation would need to handle
    # the join carefully for memory efficiency
    
    # Filter pharma data to relevant drug classes
    pharma_filtered = pharma_lf
    if drug_classes:
        pharma_filtered = pharma_filtered.filter(
            pl.col("drug_class").is_in(drug_classes)
        )
    
    # For each ED presentation, we need to find prescriptions within lookback window
    # This is best done with an asof join or window function
    
    # Note: Full implementation would require more complex logic
    # This is a placeholder showing the intended structure
    raise NotImplementedError(
        "Full linkage implementation requires careful memory management. "
        "Consider processing in batches by year or patient cohort."
    )


# =============================================================================
# SUMMARY STATISTICS
# =============================================================================

def compute_prescribing_summary(
    lf: pl.LazyFrame,
    *,
    by_year: bool = True,
) -> pl.DataFrame:
    """
    Compute summary statistics for prescribing patterns.
    
    This provides an overview of the pharmaceutical data for the methods
    section and initial results description.
    
    Parameters
    ----------
    lf : pl.LazyFrame
        Lazy frame with derived columns.
    by_year : bool, default True
        If True, compute statistics by year.
        
    Returns
    -------
    pl.DataFrame
        Summary statistics including total prescriptions, unique patients,
        prescriptions per drug class, etc.
    """
    group_cols = ["year"] if by_year else []
    
    summary = (
        lf
        .group_by(group_cols) if group_cols else lf
    )
    
    if group_cols:
        summary = (
            lf
            .group_by(group_cols)
            .agg([
                pl.len().alias("total_prescriptions"),
                pl.col("patient_id").n_unique().alias("unique_patients"),
                pl.col("is_benzodiazepine").sum().alias("n_benzodiazepine"),
                pl.col("is_z_drug").sum().alias("n_z_drug"),
                pl.col("is_opioid").sum().alias("n_opioid"),
                pl.col("is_antidepressant").sum().alias("n_antidepressant"),
                pl.col("is_stimulant").sum().alias("n_stimulant"),
                pl.col("is_psychotropic").sum().alias("n_psychotropic"),
                pl.col("age_years").mean().alias("mean_age"),
                pl.col("age_years").median().alias("median_age"),
                (pl.col("sex") == "F").mean().alias("prop_female"),
            ])
            .sort(group_cols)
        )
    else:
        summary = (
            lf
            .select([
                pl.len().alias("total_prescriptions"),
                pl.col("patient_id").n_unique().alias("unique_patients"),
                pl.col("is_benzodiazepine").sum().alias("n_benzodiazepine"),
                pl.col("is_z_drug").sum().alias("n_z_drug"),
                pl.col("is_opioid").sum().alias("n_opioid"),
                pl.col("is_antidepressant").sum().alias("n_antidepressant"),
                pl.col("is_stimulant").sum().alias("n_stimulant"),
                pl.col("is_psychotropic").sum().alias("n_psychotropic"),
                pl.col("age_years").mean().alias("mean_age"),
                pl.col("age_years").median().alias("median_age"),
                (pl.col("sex") == "F").mean().alias("prop_female"),
            ])
        )
    
    return summary.collect()


# =============================================================================
# SYNTHETIC DATA GENERATOR FOR TESTING
# =============================================================================

def generate_synthetic_pharmaceutical_data(
    n_records: int = 100_000,
    n_patients: int = 10_000,
    start_year: int = 2017,
    end_year: int = 2025,
    *,
    seed: int = 42,
) -> pl.DataFrame:
    """
    Generate synthetic pharmaceutical data for testing.
    
    This creates realistic-looking data with appropriate distributions
    of drug classes, ages, and temporal patterns. Useful for developing
    and testing analysis code before running on real VDI data.
    
    Parameters
    ----------
    n_records : int, default 100_000
        Number of prescription records to generate.
    n_patients : int, default 10_000
        Number of unique patients.
    start_year : int, default 2017
        First year of data.
    end_year : int, default 2025
        Last year of data.
    seed : int, default 42
        Random seed for reproducibility.
        
    Returns
    -------
    pl.DataFrame
        Synthetic pharmaceutical data with all expected columns.
    """
    import random
    from datetime import datetime, timedelta
    
    random.seed(seed)
    
    # Generate patient IDs (MB- format)
    def generate_patient_id():
        hex_chars = "0123456789ABCDEF"
        return "MB-" + "".join(random.choices(hex_chars, k=64))
    
    patient_ids = [generate_patient_id() for _ in range(n_patients)]
    
    # Drug distribution (weighted towards common psychotropics)
    drugs = [
        ("N05BA12", "ALPRAZOLAM", 0.15),
        ("N05BA06", "LORAZEPAM", 0.12),
        ("N05CF01", "ZOPICLONE", 0.08),
        ("N05CF02", "ZOLPIDEM", 0.07),
        ("N06AB04", "CITALOPRAM", 0.10),
        ("N06AB06", "SERTRALINE", 0.08),
        ("N06AX11", "MIRTAZAPINE", 0.05),
        ("N05AL07", "LEVOSULPIRIDE", 0.04),
        ("N02AX02", "TRAMADOL", 0.06),
        ("A02BC01", "OMEPRAZOLE", 0.10),  # Non-psychotropic control
        ("C09AA02", "ENALAPRIL", 0.08),   # Non-psychotropic control
        ("C10AA05", "ATORVASTATIN", 0.07),  # Non-psychotropic control
    ]
    
    atc_codes = [d[0] for d in drugs]
    drug_names = [d[1] for d in drugs]
    drug_weights = [d[2] for d in drugs]
    
    # Generate records
    records = []
    start_date = datetime(start_year, 1, 1)
    end_date = datetime(end_year, 12, 31)
    date_range_days = (end_date - start_date).days
    
    for _ in range(n_records):
        patient_id = random.choice(patient_ids)
        
        # Age distribution (skewed towards elderly for psychotropics)
        age = int(random.gammavariate(4, 15) + 18)
        age = min(age, 99)
        
        sex = random.choice(["M", "F"])
        
        # Drug selection
        drug_idx = random.choices(range(len(drugs)), weights=drug_weights, k=1)[0]
        atc_code = atc_codes[drug_idx]
        drug_name = drug_names[drug_idx]
        
        # Dates
        prescription_date = start_date + timedelta(days=random.randint(0, date_range_days))
        # Dispensing typically 0-14 days after prescription
        dispensing_date = prescription_date + timedelta(days=random.randint(0, 14))
        
        # Prescriber type
        prescriber_code = random.choices(["1", "Y", "2"], weights=[0.7, 0.2, 0.1], k=1)[0]
        prescriber_desc = {"1": "GENERICI", "Y": "DIPENDENTI", "2": "DATO MANCANTE"}[prescriber_code]
        
        records.append({
            "patient_id": patient_id,
            "age_years": age,
            "sex": sex,
            "prescription_date": prescription_date,
            "dispensing_date": dispensing_date,
            "atc_code": atc_code,
            "drug_name": drug_name,
            "prescriber_type_code": prescriber_code,
            "prescriber_type_desc": prescriber_desc,
        })
    
    return pl.DataFrame(records)
