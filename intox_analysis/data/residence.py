# -*- coding: utf-8 -*-
"""
Urban/Rural Classification Module
==================================

This module handles the classification of municipalities (comuni) as urban or rural
based on the ISTAT FUA (Functional Urban Areas) classification.

Reference:
    ISTAT FUA Classification (2021)
    https://www.istat.it/comunicato-stampa/aggiornamento-delle-fua-aree-funzionali-urbane/

Classification logic:
    - URBAN: Municipality has a value in "Città (City/Greater City) 2021" 
             that is NOT "No City/Città"
    - RURAL: Municipality has "No City/Città" or is missing from lookup

The lookup table should be placed in: data/lookups/istat_fua_comuni.csv
This is public ISTAT data and CAN be committed to GitHub.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Optional, Tuple


def load_fua_lookup(
    lookup_path: Optional[Path] = None,
    city_column: str = "Città (City/Greater City) 2021",
    municipality_column: str = "Comune",
) -> pd.DataFrame:
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
    pd.DataFrame
        Lookup table with municipality names and urban/rural classification.
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
            raise FileNotFoundError(
                "FUA lookup table not found. Please place 'istat_fua_comuni.csv' "
                "in data/lookups/ folder."
            )
    
    df = pd.read_csv(lookup_path, encoding="utf-8")
    
    # Standardise column names if needed
    if city_column not in df.columns:
        # Try to find similar column
        city_cols = [c for c in df.columns if "citt" in c.lower() or "city" in c.lower()]
        if city_cols:
            city_column = city_cols[0]
            print(f"Using column '{city_column}' for City classification")
    
    if municipality_column not in df.columns:
        # Try to find similar column
        muni_cols = [c for c in df.columns if "comune" in c.lower() or "municipality" in c.lower()]
        if muni_cols:
            municipality_column = muni_cols[0]
            print(f"Using column '{municipality_column}' for municipality name")
    
    return df, city_column, municipality_column


def create_urban_rural_mapping(
    lookup_df: pd.DataFrame,
    city_column: str,
    municipality_column: str,
    no_city_values: list = None,
) -> Dict[str, bool]:
    """
    Create a dictionary mapping municipality names to urban/rural status.
    
    Parameters
    ----------
    lookup_df : pd.DataFrame
        FUA lookup table.
    city_column : str
        Column containing City classification.
    municipality_column : str
        Column containing municipality names.
    no_city_values : list, optional
        Values in city_column that indicate "not a city" (rural).
        Default: ["No City/Città", "No City", ""]
        
    Returns
    -------
    dict
        {municipality_name: is_urban} where is_urban is True/False
    """
    if no_city_values is None:
        no_city_values = ["No City/Città", "No City", "", "nan", "None"]
    
    mapping = {}
    
    for _, row in lookup_df.iterrows():
        municipality = str(row[municipality_column]).strip()
        city_value = str(row[city_column]).strip()
        
        # Urban if city value exists and is not "No City" variant
        is_urban = city_value not in no_city_values and city_value.lower() != "nan"
        
        # Store with original case and lowercase for flexible matching
        mapping[municipality] = is_urban
        mapping[municipality.lower()] = is_urban
        mapping[municipality.upper()] = is_urban
    
    return mapping


def classify_residence(
    municipality_name: str,
    urban_rural_mapping: Dict[str, bool],
    default_to_rural: bool = True,
) -> str:
    """
    Classify a single municipality as urban or rural.
    
    Parameters
    ----------
    municipality_name : str
        Name of the municipality (comune).
    urban_rural_mapping : dict
        Mapping from create_urban_rural_mapping().
    default_to_rural : bool
        If municipality not found, return "Rural" (True) or "Unknown" (False).
        
    Returns
    -------
    str
        "Urban" or "Rural" (or "Unknown" if not found and default_to_rural=False)
    """
    if not municipality_name or pd.isna(municipality_name):
        return "Unknown"
    
    name = str(municipality_name).strip()
    
    # Try exact match first
    if name in urban_rural_mapping:
        return "Urban" if urban_rural_mapping[name] else "Rural"
    
    # Try lowercase
    if name.lower() in urban_rural_mapping:
        return "Urban" if urban_rural_mapping[name.lower()] else "Rural"
    
    # Not found
    if default_to_rural:
        return "Rural"
    else:
        return "Unknown"


def add_urban_rural_column(
    df: pd.DataFrame,
    residence_column: str,
    urban_rural_mapping: Dict[str, bool],
    new_column_name: str = "residence_type",
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
        Mapping from create_urban_rural_mapping().
    new_column_name : str
        Name for the new classification column.
        
    Returns
    -------
    pd.DataFrame
        DataFrame with added urban/rural column.
    """
    df = df.copy()
    df[new_column_name] = df[residence_column].apply(
        lambda x: classify_residence(x, urban_rural_mapping)
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
) -> Tuple[Dict[str, bool], pd.DataFrame]:
    """
    One-step setup for urban/rural classification.
    
    Parameters
    ----------
    lookup_path : Path, optional
        Path to FUA lookup CSV.
        
    Returns
    -------
    tuple
        (urban_rural_mapping dict, lookup DataFrame)
        
    Example
    -------
    >>> mapping, lookup_df = setup_urban_rural_classification()
    >>> df["residence_type"] = df["comune"].apply(
    ...     lambda x: classify_residence(x, mapping)
    ... )
    """
    lookup_df, city_col, muni_col = load_fua_lookup(lookup_path)
    mapping = create_urban_rural_mapping(lookup_df, city_col, muni_col)
    
    # Print summary
    n_urban = sum(1 for v in mapping.values() if v)
    n_rural = sum(1 for v in mapping.values() if not v)
    # Divide by 3 because we store each name 3 times (original, lower, upper)
    print(f"Loaded FUA classification: ~{n_urban//3} urban, ~{n_rural//3} rural municipalities")
    
    return mapping, lookup_df


# =============================================================================
# QUICK TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Urban/Rural Classification Module")
    print("=" * 60)
    
    # Test with sample data (if lookup exists)
    try:
        mapping, lookup_df = setup_urban_rural_classification()
        
        # Test some known cities
        test_places = ["Milano", "Bergamo", "BRESCIA", "Lecco", "Sondrio", "unknown_place"]
        print("\nTest classifications:")
        for place in test_places:
            result = classify_residence(place, mapping)
            print(f"  {place}: {result}")
            
    except FileNotFoundError as e:
        print(f"\n{e}")
        print("\nTo use this module:")
        print("1. Download the FUA classification from ISTAT")
        print("2. Save as 'data/lookups/istat_fua_comuni.csv'")
        print("3. Ensure it has columns for municipality name and City classification")
