# -*- coding: utf-8 -*-
"""
Urban/Rural Classification Module (OPTIONAL)
=============================================

This module handles the classification of municipalities (comuni) as urban or rural
based on the ISTAT FUA (Functional Urban Areas) classification.

NOTE: This module is OPTIONAL. The FUA lookup may be unavailable due to privacy
restrictions. All functions handle missing data gracefully.

Reference:
    ISTAT FUA Classification (2021)
    https://www.istat.it/comunicato-stampa/aggiornamento-delle-fua-aree-funzionali-urbane/

Classification logic:
    - URBAN: Municipality has a value in City column that is NOT "No City"
    - RURAL: Municipality has "No City" or is missing from lookup
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Optional, Tuple


# =============================================================================
# CHECK AVAILABILITY
# =============================================================================

def is_fua_available(lookup_path: Optional[Path] = None) -> bool:
    """
    Check if FUA lookup table is available.
    
    Parameters
    ----------
    lookup_path : Path, optional
        Path to the FUA lookup CSV.
        
    Returns
    -------
    bool
        True if FUA lookup is available, False otherwise.
    """
    if lookup_path is not None:
        return lookup_path.exists()
    
    # Try standard locations
    possible_paths = [
        Path("data/lookups/istat_fua_comuni.csv"),
        Path("../data/lookups/istat_fua_comuni.csv"),
        Path("../../data/lookups/istat_fua_comuni.csv"),
    ]
    
    for p in possible_paths:
        if p.exists():
            return True
    
    return False


# =============================================================================
# LOADING FUNCTIONS
# =============================================================================

def load_fua_lookup(
    lookup_path: Optional[Path] = None,
    city_column: str = "City (City/Greater City) 2021",
    municipality_column: str = "Comune",
) -> Tuple[Optional[pd.DataFrame], str, str]:
    """
    Load the ISTAT FUA lookup table.
    
    Parameters
    ----------
    lookup_path : Path, optional
        Path to the FUA lookup CSV. If None, looks in default location.
    city_column : str
        Column name containing the City/Greater City classification.
    municipality_column : str
        Column name containing the municipality (comune) name.
        
    Returns
    -------
    tuple
        (DataFrame or None, city_column, municipality_column)
        Returns None for DataFrame if file not found.
    """
    if lookup_path is None:
        # Try to find in standard locations
        possible_paths = [
            Path("data/lookups/istat_fua_comuni.csv"),
            Path("../data/lookups/istat_fua_comuni.csv"),
            Path("../../data/lookups/istat_fua_comuni.csv"),
        ]
        for p in possible_paths:
            if p.exists():
                lookup_path = p
                break
        
        if lookup_path is None:
            return None, city_column, municipality_column
    
    if not lookup_path.exists():
        return None, city_column, municipality_column
    
    try:
        df = pd.read_csv(lookup_path, encoding="utf-8")
    except Exception as e:
        print(f"Warning: Could not load FUA lookup: {e}")
        return None, city_column, municipality_column
    
    # Try to find city column
    if city_column not in df.columns:
        city_cols = [c for c in df.columns if "city" in c.lower()]
        if city_cols:
            city_column = city_cols[0]
    
    # Try to find municipality column
    if municipality_column not in df.columns:
        muni_cols = [c for c in df.columns if "comune" in c.lower() or "municipality" in c.lower()]
        if muni_cols:
            municipality_column = muni_cols[0]
    
    return df, city_column, municipality_column


def create_urban_rural_mapping(
    lookup_df: Optional[pd.DataFrame],
    city_column: str,
    municipality_column: str,
    no_city_values: list = None,
) -> Dict[str, bool]:
    """
    Create a dictionary mapping municipality names to urban/rural status.
    
    Parameters
    ----------
    lookup_df : pd.DataFrame or None
        FUA lookup table. If None, returns empty mapping.
    city_column : str
        Column containing City classification.
    municipality_column : str
        Column containing municipality names.
    no_city_values : list, optional
        Values in city_column that indicate "not a city" (rural).
        
    Returns
    -------
    dict
        {municipality_name: is_urban} where is_urban is True/False
    """
    if lookup_df is None:
        return {}
    
    if no_city_values is None:
        no_city_values = ["No City", "No City/Citta", "", "nan", "None"]
    
    mapping = {}
    
    for _, row in lookup_df.iterrows():
        try:
            municipality = str(row[municipality_column]).strip()
            city_value = str(row[city_column]).strip()
            
            # Urban if city value exists and is not "No City" variant
            is_urban = city_value not in no_city_values and city_value.lower() != "nan"
            
            # Store with original case and lowercase for flexible matching
            mapping[municipality] = is_urban
            mapping[municipality.lower()] = is_urban
            mapping[municipality.upper()] = is_urban
        except Exception:
            continue
    
    return mapping


# =============================================================================
# CLASSIFICATION FUNCTIONS
# =============================================================================

def classify_residence(
    municipality_name: str,
    urban_rural_mapping: Dict[str, bool],
    default_value: str = "Unknown",
) -> str:
    """
    Classify a single municipality as urban or rural.
    
    Parameters
    ----------
    municipality_name : str
        Name of the municipality (comune).
    urban_rural_mapping : dict
        Mapping from create_urban_rural_mapping().
    default_value : str
        Value to return if municipality not found or mapping empty.
        
    Returns
    -------
    str
        "Urban", "Rural", or default_value
    """
    # Handle empty mapping (FUA unavailable)
    if not urban_rural_mapping:
        return default_value
    
    if not municipality_name or pd.isna(municipality_name):
        return default_value
    
    name = str(municipality_name).strip()
    
    # Try exact match first
    if name in urban_rural_mapping:
        return "Urban" if urban_rural_mapping[name] else "Rural"
    
    # Try lowercase
    if name.lower() in urban_rural_mapping:
        return "Urban" if urban_rural_mapping[name.lower()] else "Rural"
    
    return default_value


def add_urban_rural_column(
    df: pd.DataFrame,
    residence_column: str,
    urban_rural_mapping: Dict[str, bool],
    new_column_name: str = "residence_type",
    default_value: str = "Unknown",
) -> pd.DataFrame:
    """
    Add urban/rural classification column to a DataFrame.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with a residence/municipality column.
    residence_column : str
        Name of column containing municipality names.
    urban_rural_mapping : dict
        Mapping from create_urban_rural_mapping(). Can be empty.
    new_column_name : str
        Name for the new classification column.
    default_value : str
        Value to use when classification unavailable.
        
    Returns
    -------
    pd.DataFrame
        DataFrame with added urban/rural column.
    """
    df = df.copy()
    
    if not urban_rural_mapping:
        # FUA unavailable - fill with default
        df[new_column_name] = default_value
    else:
        df[new_column_name] = df[residence_column].apply(
            lambda x: classify_residence(x, urban_rural_mapping, default_value)
        )
    
    return df


def get_urban_rural_summary(
    df: pd.DataFrame,
    residence_type_column: str = "residence_type",
) -> pd.DataFrame:
    """
    Get summary statistics of urban vs rural distribution.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with residence_type column.
    residence_type_column : str
        Name of the urban/rural column.
        
    Returns
    -------
    pd.DataFrame
        Summary with counts and percentages.
    """
    counts = df[residence_type_column].value_counts()
    summary = pd.DataFrame({
        "Count": counts,
        "Percentage": (counts / len(df) * 100).round(1)
    })
    return summary


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

def setup_urban_rural_classification(
    lookup_path: Optional[Path] = None,
    silent: bool = False,
) -> Tuple[Dict[str, bool], Optional[pd.DataFrame]]:
    """
    One-step setup for urban/rural classification.
    
    This function handles missing FUA data gracefully - if the lookup
    is not available, it returns an empty mapping that will result
    in "Unknown" classifications.
    
    Parameters
    ----------
    lookup_path : Path, optional
        Path to FUA lookup CSV.
    silent : bool
        If True, suppress info messages.
        
    Returns
    -------
    tuple
        (urban_rural_mapping dict, lookup DataFrame or None)
        
    Example
    -------
    >>> mapping, lookup_df = setup_urban_rural_classification()
    >>> if mapping:
    ...     df["residence_type"] = df["comune"].apply(
    ...         lambda x: classify_residence(x, mapping)
    ...     )
    ... else:
    ...     print("FUA classification unavailable")
    """
    lookup_df, city_col, muni_col = load_fua_lookup(lookup_path)
    
    if lookup_df is None:
        if not silent:
            print("FUA lookup not available - urban/rural classification will be skipped")
        return {}, None
    
    mapping = create_urban_rural_mapping(lookup_df, city_col, muni_col)
    
    if not silent:
        # Count unique municipalities (divide by 3 because we store 3 case variants)
        n_total = len(mapping) // 3
        n_urban = sum(1 for i, v in enumerate(mapping.values()) if v and i % 3 == 0)
        n_rural = n_total - n_urban
        print(f"Loaded FUA classification: {n_urban} urban, {n_rural} rural municipalities")
    
    return mapping, lookup_df


# =============================================================================
# MODULE TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Urban/Rural Classification Module (OPTIONAL)")
    print("=" * 60)
    
    mapping, lookup_df = setup_urban_rural_classification()
    
    if mapping:
        # Test some known cities
        test_places = ["Milano", "Bergamo", "BRESCIA", "Lecco", "Sondrio", "unknown_place"]
        print("\nTest classifications:")
        for place in test_places:
            result = classify_residence(place, mapping)
            print(f"  {place}: {result}")
    else:
        print("\nFUA lookup not available.")
        print("To enable urban/rural classification:")
        print("  1. Download the FUA classification from ISTAT")
        print("  2. Save as 'data/lookups/istat_fua_comuni.csv'")
