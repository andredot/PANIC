"""
Data Schemas and ICD Code Classification
=========================================

This module provides functions for classifying ICD-9 and ICD-10 diagnosis codes
to identify drug intoxication cases. It's designed to work with Lombardy ED data.

Key Functions:
    is_drug_intoxication_icd9(code) - Check if ICD-9 code is drug poisoning
    is_drug_intoxication_icd10(code) - Check if ICD-10 code is drug poisoning
    classify_drug_intoxication(code) - Get detailed classification
    is_missing(value) - Check if a value represents missing data

Example:
    >>> is_drug_intoxication_icd9("9694")
    True
    >>> classify_drug_intoxication("T424X2A")
    {'is_intoxication': True, 'coding_system': 'ICD-10', 
     'drug_class': 'benzodiazepine', 'intent': 'Intentional self-harm'}
"""

import re
from typing import Optional, Dict, Any, Set

# =============================================================================
# ED DISPOSITION CODES (Esito)
# =============================================================================

# Confirmed from VDI: "1" = discharged home
# Other codes are provisional - verify against VDI codebook
ESITO_CODES = {
    "1": "Discharged home (DIMISSIONE A DOMICILIO)",  # CONFIRMED
    "2": "Admitted to ordinary ward",                  # Provisional
    "3": "Admitted to day hospital",                   # Provisional
    "4": "Admitted to ICU",                            # Provisional
    "5": "Transferred to another facility",            # Provisional
    "6": "Died in ED",                                 # Provisional
    "7": "Refused admission / left AMA",               # Provisional
    "8": "Left without being seen",                    # Provisional
}

# Codes that indicate hospital admission (for linking to SDO)
ADMISSION_CODES = {"2", "3", "4"}


# =============================================================================
# MISSING VALUE HANDLING
# =============================================================================

# Values observed in VDI that indicate missing/not applicable
MISSING_VALUE_MARKERS = {"_", "DATO NON APPLICABILE", "", None}


def is_missing(value: Optional[str]) -> bool:
    """
    Check if a value represents missing data in the Lombardy dataset.
    
    The VDI uses "_" and "DATO NON APPLICABILE" for missing values.
    
    Parameters
    ----------
    value : str or None
        The value to check.
        
    Returns
    -------
    bool
        True if the value represents missing/not applicable data.
        
    Examples
    --------
    >>> is_missing("_")
    True
    >>> is_missing("DATO NON APPLICABILE")
    True
    >>> is_missing("30750")
    False
    >>> is_missing(None)
    True
    """
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() in MISSING_VALUE_MARKERS or value.strip() == ""
    return False


# =============================================================================
# ICD-9 CODE CLASSIFICATION
# =============================================================================

# ICD-9-CM drug poisoning codes: 960-979
ICD9_DRUG_GROUPS = {
    "960": "Antibiotics",
    "961": "Other anti-infectives",
    "962": "Hormones",
    "963": "Systemic agents",
    "964": "Blood agents",
    "965": "Analgesics (including opioids)",
    "966": "Anticonvulsants",
    "967": "Sedatives and hypnotics",
    "968": "CNS depressants and anesthetics",
    "969": "Psychotropic agents",
    "970": "CNS stimulants",
    "971": "Autonomic drugs",
    "972": "Cardiovascular agents",
    "973": "GI agents",
    "974": "Metabolic drugs",
    "975": "Muscle agents",
    "976": "Dermatological agents",
    "977": "Other drugs",
    "978": "Bacterial vaccines",
    "979": "Other biologicals",
}

# Specific ICD-9 codes of interest
ICD9_BENZODIAZEPINES = {"9694"}  # 969.4 Benzodiazepine tranquilizers
ICD9_STIMULANTS = {"9697", "9700", "9701", "9709"}  # Psychostimulants, CNS stimulants
ICD9_ANTIDEPRESSANTS = {"9690", "9691"}  # Antidepressants
ICD9_OPIOIDS = {"9650", "9651", "9652", "96500", "96501", "96502", "96509"}  # Opiates


def is_drug_intoxication_icd9(code: str) -> bool:
    """
    Check if an ICD-9-CM code represents drug poisoning.
    
    Drug poisoning codes are in the 960-979 range.
    
    Parameters
    ----------
    code : str
        ICD-9-CM diagnosis code, with or without decimal point.
        
    Returns
    -------
    bool
        True if the code falls within the drug poisoning range.
        
    Examples
    --------
    >>> is_drug_intoxication_icd9("9694")
    True
    >>> is_drug_intoxication_icd9("969.4")
    True
    >>> is_drug_intoxication_icd9("30750")  # Eating disorder
    False
    """
    if not code or not isinstance(code, str):
        return False
    
    # Remove decimal point and whitespace
    clean_code = code.replace(".", "").replace(" ", "").upper()
    
    # Need at least 3 characters
    if len(clean_code) < 3:
        return False
    
    # Check if starts with 96x or 97x (960-979 range)
    prefix = clean_code[:3]
    try:
        code_num = int(prefix)
        return 960 <= code_num <= 979
    except ValueError:
        return False


def classify_icd9_drug(code: str) -> Dict[str, Any]:
    """
    Classify an ICD-9 drug poisoning code into drug categories.
    
    Parameters
    ----------
    code : str
        ICD-9-CM diagnosis code.
        
    Returns
    -------
    dict
        Dictionary with drug_class, group_name, and other details.
    """
    if not is_drug_intoxication_icd9(code):
        return {"drug_class": None, "group_name": None}
    
    clean_code = code.replace(".", "").replace(" ", "")
    prefix = clean_code[:3]
    
    # Check specific drug classes
    if clean_code.startswith("9694"):
        return {"drug_class": "benzodiazepine", "group_name": "Psychotropic agents"}
    elif clean_code.startswith("9650") or clean_code.startswith("9651"):
        return {"drug_class": "opioid", "group_name": "Analgesics"}
    elif clean_code.startswith("9697") or clean_code.startswith("970"):
        return {"drug_class": "stimulant", "group_name": "CNS stimulants"}
    elif clean_code.startswith("9690"):
        return {"drug_class": "antidepressant", "group_name": "Psychotropic agents"}
    elif clean_code.startswith("967"):
        return {"drug_class": "sedative_hypnotic", "group_name": "Sedatives and hypnotics"}
    else:
        return {"drug_class": "other", "group_name": ICD9_DRUG_GROUPS.get(prefix, "Unknown")}


# =============================================================================
# ICD-10 CODE CLASSIFICATION
# =============================================================================

# ICD-10-CM intent codes (5th or 6th character after X)
ICD10_INTENT_CODES = {
    "1": "Accidental (unintentional)",
    "2": "Intentional self-harm",
    "3": "Assault",
    "4": "Undetermined",
    "5": "Adverse effect",      # Usually EXCLUDED from overdose surveillance
    "6": "Underdosing",         # Usually EXCLUDED from overdose surveillance
}

# Intents to INCLUDE in surveillance (exclude adverse effects and underdosing)
SURVEILLANCE_INTENTS = {"1", "2", "3", "4"}


def is_drug_intoxication_icd10(code: str, include_adverse_effects: bool = False) -> bool:
    """
    Check if an ICD-10-CM code represents drug poisoning.
    
    Drug poisoning codes are T36-T50. By default, adverse effects (intent=5)
    and underdosing (intent=6) are excluded per CDC guidance.
    
    Parameters
    ----------
    code : str
        ICD-10-CM diagnosis code (e.g., "T424X1A", "T42.4X1A", "T424").
    include_adverse_effects : bool, default False
        If True, include codes with intent "5" (adverse effects).
        
    Returns
    -------
    bool
        True if the code represents a drug poisoning to include in surveillance.
        
    Examples
    --------
    >>> is_drug_intoxication_icd10("T424X1A")  # Benzodiazepine, accidental
    True
    >>> is_drug_intoxication_icd10("T424X2A")  # Benzodiazepine, self-harm
    True
    >>> is_drug_intoxication_icd10("T424X5A")  # Benzodiazepine, adverse effect
    False
    >>> is_drug_intoxication_icd10("F329")    # Depression code
    False
    """
    if not code or not isinstance(code, str):
        return False
    
    # Clean and uppercase
    clean_code = code.replace(".", "").replace(" ", "").upper()
    
    # Must start with T and be at least 3 characters
    if not clean_code.startswith("T") or len(clean_code) < 3:
        return False
    
    # Extract the numeric part after T (should be 36-50)
    try:
        match = re.match(r"T(\d{2,3})", clean_code)
        if not match:
            return False
        code_num = int(match.group(1)[:2])  # Take first 2 digits
        
        # Check if in T36-T50 range
        if not (36 <= code_num <= 50):
            return False
            
    except (ValueError, AttributeError):
        return False
    
    # Check intent if code is long enough
    # Intent is after the X character (e.g., T424X1A -> intent is "1")
    if len(clean_code) >= 6:
        x_pos = clean_code.find("X")
        if x_pos != -1 and x_pos + 1 < len(clean_code):
            intent = clean_code[x_pos + 1]
            if intent in {"5", "6"} and not include_adverse_effects:
                return False
    
    return True


def get_icd10_intent(code: str) -> Optional[str]:
    """
    Extract the intent from an ICD-10-CM poisoning code.
    
    Parameters
    ----------
    code : str
        ICD-10-CM code (e.g., "T424X2A").
        
    Returns
    -------
    str or None
        Intent description, or None if not determinable.
        
    Examples
    --------
    >>> get_icd10_intent("T424X2A")
    'Intentional self-harm'
    >>> get_icd10_intent("T424")
    None
    """
    if not code:
        return None
    
    clean_code = code.replace(".", "").replace(" ", "").upper()
    x_pos = clean_code.find("X")
    
    if x_pos != -1 and x_pos + 1 < len(clean_code):
        intent_char = clean_code[x_pos + 1]
        return ICD10_INTENT_CODES.get(intent_char)
    
    return None


def classify_icd10_drug(code: str) -> Dict[str, Any]:
    """
    Classify an ICD-10 drug poisoning code into drug categories.
    
    Parameters
    ----------
    code : str
        ICD-10-CM diagnosis code.
        
    Returns
    -------
    dict
        Dictionary with drug_class, intent, and other details.
    """
    if not is_drug_intoxication_icd10(code, include_adverse_effects=True):
        return {"drug_class": None, "intent": None}
    
    clean_code = code.replace(".", "").replace(" ", "").upper()
    intent = get_icd10_intent(code)
    
    # Classify by T-code range
    # T42.4 = benzodiazepines
    if clean_code.startswith("T424"):
        return {"drug_class": "benzodiazepine", "intent": intent}
    # T42.6 = other antiepileptics and sedative-hypnotics
    elif clean_code.startswith("T426"):
        return {"drug_class": "sedative_hypnotic", "intent": intent}
    # T40 = opioids and other narcotics
    elif clean_code.startswith("T40"):
        return {"drug_class": "opioid", "intent": intent}
    # T43.0-T43.2 = antidepressants
    elif clean_code.startswith("T430") or clean_code.startswith("T431") or clean_code.startswith("T432"):
        return {"drug_class": "antidepressant", "intent": intent}
    # T43.6 = psychostimulants
    elif clean_code.startswith("T436"):
        return {"drug_class": "stimulant", "intent": intent}
    # T43 = other psychotropics
    elif clean_code.startswith("T43"):
        return {"drug_class": "other_psychotropic", "intent": intent}
    else:
        return {"drug_class": "other", "intent": intent}


# =============================================================================
# UNIFIED CLASSIFICATION FUNCTION
# =============================================================================

def classify_drug_intoxication(code: str) -> Dict[str, Any]:
    """
    Classify any ICD diagnosis code for drug intoxication.
    
    Automatically detects whether the code is ICD-9 or ICD-10 and 
    returns a standardised classification.
    
    Parameters
    ----------
    code : str
        Any ICD-9-CM or ICD-10-CM diagnosis code.
        
    Returns
    -------
    dict
        Dictionary containing:
        - is_intoxication: bool
        - coding_system: 'ICD-9' or 'ICD-10' or None
        - drug_class: str (benzodiazepine, opioid, stimulant, etc.)
        - intent: str or None (only for ICD-10)
        
    Examples
    --------
    >>> classify_drug_intoxication("9694")
    {'is_intoxication': True, 'coding_system': 'ICD-9', 
     'drug_class': 'benzodiazepine', 'intent': None}
    >>> classify_drug_intoxication("T424X2A")
    {'is_intoxication': True, 'coding_system': 'ICD-10',
     'drug_class': 'benzodiazepine', 'intent': 'Intentional self-harm'}
    >>> classify_drug_intoxication("30750")
    {'is_intoxication': False, 'coding_system': None,
     'drug_class': None, 'intent': None}
    """
    if not code or not isinstance(code, str):
        return {
            "is_intoxication": False,
            "coding_system": None,
            "drug_class": None,
            "intent": None,
        }
    
    clean_code = code.replace(".", "").replace(" ", "").upper()
    
    # Check if it's ICD-10 (starts with T)
    if clean_code.startswith("T"):
        if is_drug_intoxication_icd10(code):
            classification = classify_icd10_drug(code)
            return {
                "is_intoxication": True,
                "coding_system": "ICD-10",
                "drug_class": classification["drug_class"],
                "intent": classification["intent"],
            }
        else:
            # It's a T-code but not a drug intoxication (e.g., T-code outside 36-50)
            return {
                "is_intoxication": False,
                "coding_system": "ICD-10",
                "drug_class": None,
                "intent": None,
            }
    
    # Check if it's ICD-9 drug poisoning
    if is_drug_intoxication_icd9(code):
        classification = classify_icd9_drug(code)
        return {
            "is_intoxication": True,
            "coding_system": "ICD-9",
            "drug_class": classification["drug_class"],
            "intent": None,  # ICD-9 doesn't encode intent in the code itself
        }
    
    # Not a drug intoxication code
    return {
        "is_intoxication": False,
        "coding_system": None,
        "drug_class": None,
        "intent": None,
    }


# =============================================================================
# COLUMN NAME UTILITIES
# =============================================================================

# Mapping from Italian VDI column names to standardised English names
ED_COLUMN_MAPPING = {
    "Codice Fiscale Assistito MICROBIO": "patient_id",
    "Annomese_INGR": "year_month",
    "Eta(calcolata)": "age_years",
    "Eta (flusso)": "age_flow",  # Don't use - encoding unclear (e.g., "2856" for 16yo)
    "Sesso (anag ass.to)": "sex_registry",
    "Sesso (flusso)": "sex_flow",
    "Cod Diagnosi": "diagnosis_code_primary",
    "Diagnosi": "diagnosis_desc_primary",
    "Cod Diagnosi Secondaria": "diagnosis_code_secondary",
    "Diagnosi Secondaria": "diagnosis_desc_secondary",
    "Codice Esito": "disposition_code",
    "Descrizione Esito": "disposition_desc",
    "Codice Nazione(flusso)": "nationality_code",
    "Conteggio Persone fisiche": "count",
}


def standardise_column_names(df, column_mapping: Optional[Dict[str, str]] = None):
    """
    Rename DataFrame columns from Italian VDI names to English.
    
    Works with both pandas and polars DataFrames.
    
    Parameters
    ----------
    df : DataFrame
        pandas or polars DataFrame with Italian column names.
    column_mapping : dict, optional
        Custom mapping dict. If None, uses ED_COLUMN_MAPPING.
        
    Returns
    -------
    DataFrame
        DataFrame with renamed columns.
    """
    if column_mapping is None:
        column_mapping = ED_COLUMN_MAPPING
    
    # Works for both pandas and polars
    return df.rename(columns=column_mapping) if hasattr(df, 'rename') else df.rename(column_mapping)


# =============================================================================
# QUICK TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("ICD Code Classification Tests")
    print("=" * 60)
    
    test_codes = [
        ("9694", "ICD-9 Benzodiazepine"),
        ("969.4", "ICD-9 Benzodiazepine with decimal"),
        ("30750", "ICD-9 Eating disorder (not intox)"),
        ("T424X1A", "ICD-10 Benzodiazepine, accidental"),
        ("T424X2A", "ICD-10 Benzodiazepine, self-harm"),
        ("T424X5A", "ICD-10 Benzodiazepine, adverse effect"),
        ("T400X1A", "ICD-10 Opioid, accidental"),
        ("F329", "ICD-10 Depression (not intox)"),
    ]
    
    for code, description in test_codes:
        result = classify_drug_intoxication(code)
        status = "✓ INTOX" if result["is_intoxication"] else "✗ Not intox"
        print(f"\n{code} ({description})")
        print(f"  {status}")
        print(f"  System: {result['coding_system']}, Class: {result['drug_class']}, Intent: {result['intent']}")
