"""
Data schemas and validation for Lombardy Emergency Department data.

This module defines the expected structure of ED presentation data, including:
- Pandera schemas for DataFrame validation
- Pydantic models for individual records
- ICD-9 to ICD-10 code mappings for drug intoxications
- Constants for categorical variables (sex, esito, etc.)

The schemas mirror the actual data structure from the Lombardy regional
syndromic surveillance system, with pseudonymised identifiers.
"""

from __future__ import annotations

import re
from datetime import date
from enum import Enum
from typing import Annotated, Literal

import pandas as pd
import pandera as pa
from pandera.typing import Series
from pydantic import BaseModel, Field, field_validator


# =============================================================================
# CONSTANTS AND ENUMERATIONS
# =============================================================================

class Sex(str, Enum):
    """Biological sex categories as coded in Lombardy health data."""
    FEMALE = "F"
    MALE = "M"
    UNKNOWN = "U"  # May appear for data quality issues


class EsitoED(str, Enum):
    """
    ED disposition codes (Codice Esito).
    
    These codes indicate the patient's status at the end of the ED encounter.
    CONFIRMED from VDI:
        "1" = "DIMISSIONE A DOMICILIO" (discharged home)
    
    Values below are provisional based on standard Italian ED data flows;
    verify against actual codebook in the VDI environment.
    """
    DIMISSIONE_DOMICILIO = "1"       # CONFIRMED: Discharged home
    RICOVERO_ORDINARIO = "2"         # Admitted to ordinary ward (provisional)
    RICOVERO_DH = "3"                # Admitted to day hospital (provisional)
    RICOVERO_TERAPIA_INTENSIVA = "4" # Admitted to ICU (provisional)
    TRASFERIMENTO = "5"              # Transferred to another facility (provisional)
    DECESSO = "6"                    # Died in ED (provisional)
    RIFIUTO_RICOVERO = "7"           # Refused admission/left AMA (provisional)
    ABBANDONO = "8"                  # Left without being seen (provisional)
    # TODO: Verify codes 2-8 against actual VDI codebook


# Esito codes that indicate hospital admission (for SDO linkage)
ADMISSION_ESITO_CODES = {
    EsitoED.RICOVERO_ORDINARIO.value,
    EsitoED.RICOVERO_DH.value,
    EsitoED.RICOVERO_TERAPIA_INTENSIVA.value,
}


# =============================================================================
# MISSING VALUE CONVENTIONS
# =============================================================================

# Values observed in VDI that indicate missing/not applicable data
# CONFIRMED: Secondary diagnosis uses "_" when not applicable
MISSING_VALUE_MARKERS = {"_", "DATO NON APPLICABILE", "", None}


def is_missing(value: str | None) -> bool:
    """
    Check if a value represents missing data in the Lombardy ED dataset.
    
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
# ICD CODE DEFINITIONS FOR DRUG INTOXICATION
# =============================================================================

# ICD-9-CM codes for drug poisoning (used in Italy until ~2017-2019 depending on region)
ICD9_DRUG_POISONING_CODES = {
    # 960-979: Poisoning by drugs, medicaments, and biological substances
    "960": "Poisoning by antibiotics",
    "961": "Poisoning by other anti-infectives",
    "962": "Poisoning by hormones and synthetic substitutes",
    "963": "Poisoning by primarily systemic agents",
    "964": "Poisoning by agents affecting blood constituents",
    "965": "Poisoning by analgesics, antipyretics, antirheumatics",
    "966": "Poisoning by anticonvulsants and anti-Parkinsonism drugs",
    "967": "Poisoning by sedatives and hypnotics",
    "968": "Poisoning by other CNS depressants and anesthetics",
    "969": "Poisoning by psychotropic agents",
    "970": "Poisoning by CNS stimulants",
    "971": "Poisoning by drugs affecting autonomic nervous system",
    "972": "Poisoning by agents affecting cardiovascular system",
    "973": "Poisoning by agents affecting GI system",
    "974": "Poisoning by water, mineral, and uric acid metabolism drugs",
    "975": "Poisoning by agents acting on smooth and skeletal muscles",
    "976": "Poisoning by agents affecting skin and mucous membrane",
    "977": "Poisoning by other and unspecified drugs and medicaments",
    "978": "Poisoning by bacterial vaccines",
    "979": "Poisoning by other vaccines and biological substances",
}

# ICD-9-CM subgroups of particular interest
ICD9_BENZODIAZEPINE_CODES = {"9694"}  # 969.4: Poisoning by benzodiazepine tranquilizers
ICD9_STIMULANT_CODES = {"9697", "970"}  # 969.7: Psychostimulants, 970: CNS stimulants
ICD9_ANTIDEPRESSANT_CODES = {"9690", "9691"}  # 969.0: Antidepressants, 969.1: Phenothiazines


# ICD-10-CM codes for drug poisoning (T36-T50)
# These are base codes; actual codes have additional characters for intent and encounter
ICD10_DRUG_POISONING_RANGES = [
    ("T36", "T50"),  # Poisoning by drugs, medicaments, biological substances
]

# ICD-10-CM codes of particular interest (base codes without intent/encounter suffix)
ICD10_BENZODIAZEPINE_CODES = {"T424"}  # T42.4: Poisoning by benzodiazepines
ICD10_STIMULANT_CODES = {"T436"}       # T43.6: Poisoning by psychostimulants
ICD10_ANTIDEPRESSANT_CODES = {
    "T430",  # T43.0: Poisoning by tricyclic antidepressants
    "T431",  # T43.1: Poisoning by tetracyclic antidepressants
    "T432",  # T43.2: Poisoning by other and unspecified antidepressants
}

# Intent suffixes in ICD-10-CM T-codes (5th or 6th character position)
ICD10_INTENT_CODES = {
    "1": "Accidental (unintentional)",
    "2": "Intentional self-harm",
    "3": "Assault",
    "4": "Undetermined",
    "5": "Adverse effect",  # Excluded from overdose surveillance
    "6": "Underdosing",     # Excluded from overdose surveillance
}

# Intents to INCLUDE in drug intoxication surveillance
SURVEILLANCE_INTENTS = {"1", "2", "3", "4"}  # Exclude adverse effects and underdosing


# =============================================================================
# HELPER FUNCTIONS FOR ICD CODE CLASSIFICATION
# =============================================================================

def is_drug_intoxication_icd9(code: str) -> bool:
    """
    Check if an ICD-9-CM code represents drug poisoning.
    
    Parameters
    ----------
    code : str
        ICD-9-CM diagnosis code, with or without decimal point.
        
    Returns
    -------
    bool
        True if the code falls within the drug poisoning range (960-979).
        
    Examples
    --------
    >>> is_drug_intoxication_icd9("9694")
    True
    >>> is_drug_intoxication_icd9("969.4")
    True
    >>> is_drug_intoxication_icd9("30750")
    False
    """
    # Remove decimal point and any whitespace
    clean_code = code.replace(".", "").replace(" ", "").upper()
    
    # Check if code starts with 96x or 97x (960-979 range)
    if len(clean_code) < 3:
        return False
    
    prefix = clean_code[:3]
    try:
        code_num = int(prefix)
        return 960 <= code_num <= 979
    except ValueError:
        return False


def is_drug_intoxication_icd10(code: str, include_adverse_effects: bool = False) -> bool:
    """
    Check if an ICD-10-CM code represents drug poisoning.
    
    Parameters
    ----------
    code : str
        ICD-10-CM diagnosis code (e.g., "T424X1A", "T42.4X1A", "T424").
    include_adverse_effects : bool, default False
        If True, include codes with intent "5" (adverse effects).
        For overdose surveillance, this should typically be False.
        
    Returns
    -------
    bool
        True if the code falls within T36-T50 range with appropriate intent.
        
    Examples
    --------
    >>> is_drug_intoxication_icd10("T424X1A")  # Benzodiazepine, accidental, initial
    True
    >>> is_drug_intoxication_icd10("T424X5A")  # Benzodiazepine, adverse effect
    False
    >>> is_drug_intoxication_icd10("T424X5A", include_adverse_effects=True)
    True
    >>> is_drug_intoxication_icd10("F329")     # Depression code
    False
    """
    # Clean and uppercase
    clean_code = code.replace(".", "").replace(" ", "").upper()
    
    # Must start with T and be at least 3 characters
    if not clean_code.startswith("T") or len(clean_code) < 3:
        return False
    
    # Extract the numeric part after T
    try:
        # Get the first 2-3 digits after T
        match = re.match(r"T(\d{2,3})", clean_code)
        if not match:
            return False
        code_num = int(match.group(1)[:2])  # Take first 2 digits
        
        # Check if in T36-T50 range
        if not (36 <= code_num <= 50):
            return False
            
    except (ValueError, AttributeError):
        return False
    
    # Check intent if code is long enough to have it
    # Intent is typically at position 5 or 6 (after T##.#X or T###X)
    if len(clean_code) >= 6:
        # Find the intent character (digit after the X)
        x_pos = clean_code.find("X")
        if x_pos != -1 and x_pos + 1 < len(clean_code):
            intent = clean_code[x_pos + 1]
            if intent in {"5", "6"} and not include_adverse_effects:
                return False
    
    return True


def classify_drug_intoxication(code: str) -> dict[str, str | bool]:
    """
    Classify a drug intoxication code into subgroups.
    
    Parameters
    ----------
    code : str
        ICD-9-CM or ICD-10-CM diagnosis code.
        
    Returns
    -------
    dict
        Dictionary with classification results:
        - is_intoxication: bool
        - coding_system: "ICD-9" or "ICD-10" or "unknown"
        - drug_class: "benzodiazepine", "stimulant", "antidepressant", "other", or None
        - intent: intent description or None
        
    Examples
    --------
    >>> classify_drug_intoxication("T424X2A")
    {'is_intoxication': True, 'coding_system': 'ICD-10', 
     'drug_class': 'benzodiazepine', 'intent': 'Intentional self-harm'}
    """
    clean_code = code.replace(".", "").replace(" ", "").upper()
    
    result = {
        "is_intoxication": False,
        "coding_system": "unknown",
        "drug_class": None,
        "intent": None,
    }
    
    # Check ICD-10-CM first (starts with T)
    if clean_code.startswith("T"):
        result["coding_system"] = "ICD-10"
        
        if is_drug_intoxication_icd10(code):
            result["is_intoxication"] = True
            
            # Classify drug class
            base_code = clean_code[:4]  # e.g., "T424"
            if base_code in ICD10_BENZODIAZEPINE_CODES:
                result["drug_class"] = "benzodiazepine"
            elif base_code in ICD10_STIMULANT_CODES:
                result["drug_class"] = "stimulant"
            elif base_code in ICD10_ANTIDEPRESSANT_CODES:
                result["drug_class"] = "antidepressant"
            else:
                result["drug_class"] = "other"
            
            # Extract intent
            x_pos = clean_code.find("X")
            if x_pos != -1 and x_pos + 1 < len(clean_code):
                intent_code = clean_code[x_pos + 1]
                result["intent"] = ICD10_INTENT_CODES.get(intent_code, "unknown")
    
    # Check ICD-9-CM (numeric codes starting with 96x or 97x)
    elif clean_code[0].isdigit():
        result["coding_system"] = "ICD-9"
        
        if is_drug_intoxication_icd9(code):
            result["is_intoxication"] = True
            
            # Classify drug class
            prefix = clean_code[:4] if len(clean_code) >= 4 else clean_code[:3]
            if prefix in ICD9_BENZODIAZEPINE_CODES or clean_code.startswith("9694"):
                result["drug_class"] = "benzodiazepine"
            elif prefix in ICD9_STIMULANT_CODES or clean_code.startswith("9697") or clean_code.startswith("970"):
                result["drug_class"] = "stimulant"
            elif prefix in ICD9_ANTIDEPRESSANT_CODES or clean_code.startswith("9690") or clean_code.startswith("9691"):
                result["drug_class"] = "antidepressant"
            else:
                result["drug_class"] = "other"
            
            # ICD-9-CM intent is in external cause codes (E codes), not in the diagnosis
            result["intent"] = "requires E-code lookup"
    
    return result


# =============================================================================
# PANDERA SCHEMA FOR ED DATA VALIDATION
# =============================================================================

class EDPresentationSchema(pa.DataFrameModel):
    """
    Pandera schema for validating Lombardy ED presentation data.
    
    This schema reflects the actual data structure from the regional
    syndromic surveillance system. Use this to validate data extracts
    before analysis to catch data quality issues early.
    
    Example
    -------
    >>> import pandas as pd
    >>> from intox_analysis.data.schemas import EDPresentationSchema
    >>> df = pd.read_csv("ed_data.csv")
    >>> validated_df = EDPresentationSchema.validate(df)
    """
    
    # Pseudonymised patient identifier (SHA-256 hash with MB- prefix)
    codice_fiscale_assistito_microbio: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^MB-[A-F0-9]{64}$",
        description="Pseudonymised patient identifier using PPRL hash"
    )
    
    # Year-month of ED presentation in YYYYMM format
    annomese_ingr: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^(201[7-9]|202[0-5])(0[1-9]|1[0-2])$",
        description="Year-month of ED presentation (YYYYMM format)"
    )
    
    # Age (calculated) - should be reasonable range
    eta_calcolata: Series[int] = pa.Field(
        ge=0, le=120,
        nullable=True,
        description="Patient age in years, calculated from DOB"
    )
    
    # Age from flow (may have different encoding)
    # NOTE: Observed value "2856" for a 16-year-old patient. This is NOT age in years.
    # Possible encodings: days of life, categorical band code, or other regional scheme.
    # Use eta_calcolata as the primary age variable; eta_flusso for quality checks only.
    eta_flusso: Series[str] = pa.Field(
        nullable=True,
        description="Age encoding from administrative flow (NOT years; use eta_calcolata instead)"
    )
    
    # Sex from patient registry
    sesso_anag_ass_to: Series[str] = pa.Field(
        isin=["F", "M", "U"],
        nullable=True,
        description="Sex from patient registry"
    )
    
    # Sex from administrative flow
    sesso_flusso: Series[str] = pa.Field(
        isin=["F", "M", "U"],
        nullable=True,
        description="Sex from administrative flow"
    )
    
    # Primary diagnosis code
    cod_diagnosi: Series[str] = pa.Field(
        nullable=True,
        description="Primary diagnosis code (ICD-9-CM or ICD-10-CM)"
    )
    
    # Primary diagnosis description
    diagnosi: Series[str] = pa.Field(
        nullable=True,
        description="Primary diagnosis text description"
    )
    
    # Secondary diagnosis code
    cod_diagnosi_secondaria: Series[str] = pa.Field(
        nullable=True,
        description="Secondary diagnosis code"
    )
    
    # Secondary diagnosis description  
    diagnosi_secondaria: Series[str] = pa.Field(
        nullable=True,
        description="Secondary diagnosis text description"
    )
    
    # ED disposition code
    codice_esito: Series[str] = pa.Field(
        nullable=True,
        description="ED disposition/outcome code"
    )
    
    # ED disposition description
    descrizione_esito: Series[str] = pa.Field(
        nullable=True,
        description="ED disposition/outcome description"
    )
    
    # Nationality code
    codice_nazione_flusso: Series[str] = pa.Field(
        nullable=True,
        description="Nationality code from administrative flow"
    )
    
    # Count of unique individuals (should be 1 for event-level data)
    conteggio_persone_fisiche: Series[int] = pa.Field(
        ge=1,
        nullable=False,
        description="Count of unique individuals (typically 1)"
    )
    
    class Config:
        """Pandera schema configuration."""
        name = "EDPresentationSchema"
        strict = False  # Allow additional columns
        coerce = True   # Attempt type coercion


# Relaxed schema for initial data exploration (fewer constraints)
class EDPresentationSchemaRelaxed(pa.DataFrameModel):
    """
    Relaxed schema for initial data exploration.
    
    Use this when first loading data to identify quality issues
    without strict validation failures.
    """
    codice_fiscale_assistito_microbio: Series[str] = pa.Field(nullable=False)
    annomese_ingr: Series[str] = pa.Field(nullable=False)
    eta_calcolata: Series[object] = pa.Field(nullable=True)  # Allow any type initially
    cod_diagnosi: Series[str] = pa.Field(nullable=True)
    codice_esito: Series[str] = pa.Field(nullable=True)
    conteggio_persone_fisiche: Series[object] = pa.Field(nullable=True)
    
    class Config:
        strict = False
        coerce = False


# =============================================================================
# PYDANTIC MODEL FOR INDIVIDUAL RECORDS
# =============================================================================

class EDPresentation(BaseModel):
    """
    Pydantic model for a single ED presentation record.
    
    Use this for type-safe handling of individual records,
    API responses, or when working with records one at a time.
    
    Example
    -------
    >>> record = EDPresentation(
    ...     codice_fiscale_assistito_microbio="MB-0643EBF4C0B837E4F239756CA2C1F5C80D67FF1E0A79413D13954A56F7F03E97",
    ...     annomese_ingr="201907",
    ...     eta_calcolata=16,
    ...     sesso="F",
    ...     cod_diagnosi="30750",
    ...     codice_esito="1",
    ... )
    >>> record.is_drug_intoxication
    False
    """
    
    codice_fiscale_assistito_microbio: str = Field(
        ..., 
        pattern=r"^MB-[A-F0-9]{64}$",
        description="Pseudonymised patient identifier"
    )
    annomese_ingr: str = Field(
        ...,
        pattern=r"^\d{6}$",
        description="Year-month of presentation (YYYYMM)"
    )
    eta_calcolata: int | None = Field(
        default=None,
        ge=0, le=120,
        description="Age in years"
    )
    sesso: Literal["F", "M", "U"] | None = Field(
        default=None,
        description="Sex (F=female, M=male, U=unknown)"
    )
    cod_diagnosi: str | None = Field(
        default=None,
        description="Primary diagnosis code"
    )
    diagnosi: str | None = Field(
        default=None,
        description="Primary diagnosis description"
    )
    cod_diagnosi_secondaria: str | None = Field(
        default=None,
        description="Secondary diagnosis code"
    )
    codice_esito: str | None = Field(
        default=None,
        description="ED disposition code"
    )
    conteggio_persone_fisiche: int = Field(
        default=1,
        ge=1,
        description="Count of individuals"
    )
    
    @property
    def year_month(self) -> tuple[int, int]:
        """Extract year and month as integers."""
        return int(self.annomese_ingr[:4]), int(self.annomese_ingr[4:6])
    
    @property
    def is_drug_intoxication(self) -> bool:
        """Check if this presentation is a drug intoxication case."""
        for code in [self.cod_diagnosi, self.cod_diagnosi_secondaria]:
            if code and (is_drug_intoxication_icd9(code) or is_drug_intoxication_icd10(code)):
                return True
        return False
    
    @property
    def is_admitted(self) -> bool:
        """Check if patient was admitted to hospital."""
        return self.codice_esito in ADMISSION_ESITO_CODES
    
    @property
    def drug_classification(self) -> dict[str, str | bool] | None:
        """Get drug classification for intoxication cases."""
        for code in [self.cod_diagnosi, self.cod_diagnosi_secondaria]:
            if code:
                classification = classify_drug_intoxication(code)
                if classification["is_intoxication"]:
                    return classification
        return None
    
    @field_validator("annomese_ingr")
    @classmethod
    def validate_date_range(cls, v: str) -> str:
        """Validate that date is within study period (2017-2025)."""
        year = int(v[:4])
        month = int(v[4:6])
        if year < 2017 or year > 2025:
            raise ValueError(f"Year {year} outside study period 2017-2025")
        if month < 1 or month > 12:
            raise ValueError(f"Invalid month {month}")
        return v


# =============================================================================
# COLUMN NAME MAPPINGS
# =============================================================================

# Mapping from Italian column names to standardised English names
COLUMN_NAME_MAPPING = {
    "Codice Fiscale Assistito MICROBIO": "codice_fiscale_assistito_microbio",
    "Annomese_INGR": "annomese_ingr",
    "Eta(calcolata)": "eta_calcolata",
    "Eta (flusso)": "eta_flusso",
    "Sesso (anag ass.to)": "sesso_anag_ass_to",
    "Sesso (flusso)": "sesso_flusso",
    "Cod Diagnosi": "cod_diagnosi",
    "Diagnosi": "diagnosi",
    "Cod Diagnosi Secondaria": "cod_diagnosi_secondaria",
    "Diagnosi Secondaria": "diagnosi_secondaria",
    "Codice Esito": "codice_esito",
    "Descrizione Esito": "descrizione_esito",
    "Codice Nazione(flusso)": "codice_nazione_flusso",
    "Conteggio Persone fisiche": "conteggio_persone_fisiche",
}

# Reverse mapping for converting back to Italian names
COLUMN_NAME_MAPPING_REVERSE = {v: k for k, v in COLUMN_NAME_MAPPING.items()}


def standardise_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert Italian column names to standardised lowercase snake_case.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with original Italian column names.
        
    Returns
    -------
    pd.DataFrame
        DataFrame with standardised column names.
    """
    return df.rename(columns=COLUMN_NAME_MAPPING)


def restore_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert standardised column names back to original Italian names.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with standardised column names.
        
    Returns
    -------
    pd.DataFrame
        DataFrame with original Italian column names.
    """
    return df.rename(columns=COLUMN_NAME_MAPPING_REVERSE)
