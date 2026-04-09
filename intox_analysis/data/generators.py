# -*- coding: utf-8 -*-
"""
Synthetic Data Generators
=========================

This module generates realistic synthetic data for testing the analysis pipeline
without access to the VDI. All generated data mimics the structure and distributions
of the actual Lombardy health data.

Data generated:
1. ED presentations (with facility_id, residence, intoxication codes)
2. Pharmaceutical dispensing (with DDD, drug classes)
3. FUA lookup table (urban/rural classification)

Usage:
    from intox_analysis.data.generators import generate_all_synthetic_data
    
    data = generate_all_synthetic_data(output_dir="data/raw")
    # Creates CSV files ready for analysis scripts
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta


# =============================================================================
# CONSTANTS
# =============================================================================

# Lombardy municipalities (sample)
URBAN_COMUNI = [
    "Milano", "Bergamo", "Brescia", "Monza", "Como", "Varese", "Pavia",
    "Cremona", "Lecco", "Lodi", "Mantova", "Sondrio", "Busto Arsizio",
    "Cinisello Balsamo", "Sesto San Giovanni", "Legnano", "Gallarate",
]

RURAL_COMUNI = [
    "Morbegno", "Chiavenna", "Bormio", "Livigno", "Tirano", "Edolo",
    "Ponte di Legno", "Aprica", "Madesimo", "Castione della Presolana",
    "Foppolo", "Branzi", "Carona", "Valbondione", "Schilpario",
    "Angolo Terme", "Borno", "Clusone", "Gromo", "Valgoglio",
]

# ED Facilities
ED_FACILITIES = [
    "OSP_MI_NIGUARDA", "OSP_MI_POLICLINICO", "OSP_MI_SACCO",
    "OSP_MI_SAN_RAFFAELE", "OSP_MI_HUMANITAS",
    "OSP_BG_PAPA_GIOVANNI", "OSP_BG_HUMANITAS",
    "OSP_BS_CIVILI", "OSP_BS_POLIAMBULANZA",
    "OSP_CO_SANT_ANNA", "OSP_VA_CIRCOLO",
    "OSP_PV_SAN_MATTEO", "OSP_MN_CARLO_POMA",
    "OSP_LC_MANZONI", "OSP_LO_MAGGIORE",
]

# ICD codes for drug intoxications
ICD10_INTOX_CODES = {
    "Benzodiazepines": ["T424X1A", "T424X2A", "T424X4A"],
    "Opioids": ["T400X1A", "T400X2A", "T401X1A", "T401X2A", "T402X1A", "T402X2A"],
    "Stimulants": ["T436X1A", "T436X2A"],
    "Cocaine": ["T405X1A", "T405X2A"],
    "Antidepressants": ["T430X2A", "T431X2A", "T432X2A"],
    "Paracetamol": ["T391X1A", "T391X2A"],
    "Other_sedatives": ["T423X1A", "T426X1A", "T426X2A"],
    "Cannabis": ["T407X1A", "T407X2A"],
}

ICD9_INTOX_CODES = {
    "Benzodiazepines": ["9694", "96940", "96941"],
    "Opioids": ["9650", "96500", "96501", "96509"],
    "Stimulants": ["9697", "9700", "9701"],
    "Antidepressants": ["9690", "96900"],
}

# Mental health codes
ICD10_MH_CODES = {
    "Depression": ["F320", "F321", "F322", "F329", "F330", "F331", "F332", "F339"],
    "Anxiety": ["F410", "F411", "F412", "F419", "F400", "F401"],
    "Adjustment": ["F430", "F431", "F432", "F439"],
    "Eating_disorders": ["F500", "F501", "F502", "F509"],
    "Substance_use": ["F100", "F101", "F102", "F110", "F111", "F120", "F130", "F140"],
    "Bipolar": ["F310", "F311", "F312", "F313", "F314"],
    "Schizophrenia": ["F200", "F201", "F202", "F209"],
}

# Other common ED diagnoses (non-intoxication, non-MH)
OTHER_DIAGNOSES = [
    "J189", "J069", "J111",  # Respiratory
    "K529", "K590", "K219",  # GI
    "R104", "R51", "R55",    # Symptoms
    "S0100", "S610", "S720", # Injuries
    "I10", "I200", "I469",   # Cardiovascular
    "N390", "N200",          # Urinary
]

# ATC codes for pharmaceuticals
ATC_CODES = {
    "benzodiazepine": ["N05BA01", "N05BA06", "N05BA12", "N05BA04", "N05BA08", 
                        "N05CD01", "N05CD02", "N05CD08"],
    "z_drug": ["N05CF01", "N05CF02"],
    "opioid": ["N02AA01", "N02AA05", "N02AB03", "N02AX02", "N07BC02"],
    "antidepressant": ["N06AB03", "N06AB04", "N06AB05", "N06AB06", "N06AB10",
                        "N06AX11", "N06AX16", "N06AX21"],
    "stimulant": ["N06BA04", "N06BA09", "N06BA12"],
    "antipsychotic": ["N05AH03", "N05AH04", "N05AX08", "N05AX12"],
    "other": ["A02BC01", "C09AA02", "C10AA05", "B01AC06"],
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def generate_patient_id() -> str:
    """Generate a pseudonymised patient ID in MB-{64 hex} format."""
    hex_chars = "0123456789ABCDEF"
    return "MB-" + "".join(np.random.choice(list(hex_chars), 64))


def generate_date_in_range(start_year: int, end_year: int) -> datetime:
    """Generate a random date within the study period."""
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    delta = end - start
    random_days = np.random.randint(0, delta.days)
    return start + timedelta(days=random_days)


# =============================================================================
# ED DATA GENERATOR
# =============================================================================

def generate_ed_presentations(
    n_records: int = 50000,
    start_year: int = 2017,
    end_year: int = 2025,
    intox_prevalence: float = 0.08,
    mh_prevalence: float = 0.12,
    benzo_trend_increase: float = 0.15,  # 15% annual increase in benzos
    seed: int = 42,
) -> pd.DataFrame:
    """
    Generate synthetic ED presentation data.
    
    Includes realistic:
    - Temporal trends (increasing benzo intoxications)
    - Age/sex distributions
    - Urban/rural mix
    - Facility distribution
    - Admission rates (~20% for intoxications)
    
    Parameters
    ----------
    n_records : int
        Number of ED presentations to generate.
    start_year : int
        First year of data.
    end_year : int
        Last year of data.
    intox_prevalence : float
        Base prevalence of drug intoxication presentations.
    mh_prevalence : float
        Base prevalence of mental health presentations.
    benzo_trend_increase : float
        Annual increase in benzodiazepine intoxications.
    seed : int
        Random seed for reproducibility.
        
    Returns
    -------
    pd.DataFrame
        Synthetic ED presentation data.
    """
    np.random.seed(seed)
    
    records = []
    
    # Generate patient pool (some will have multiple visits)
    n_unique_patients = int(n_records * 0.7)
    patient_pool = [generate_patient_id() for _ in range(n_unique_patients)]
    
    for i in range(n_records):
        # Patient ID (allow repeats)
        patient_id = np.random.choice(patient_pool)
        
        # Date
        date = generate_date_in_range(start_year, end_year)
        year = date.year
        year_month = f"{year}{date.month:02d}"
        
        # Age - bimodal: young adults (15-35) and older adults (50-75)
        if np.random.random() < 0.4:
            age = int(np.random.normal(25, 8))
        else:
            age = int(np.random.normal(55, 15))
        age = max(5, min(99, age))
        
        # Sex - slightly more female for intox/MH
        sex = np.random.choice(["F", "M"], p=[0.55, 0.45])
        
        # Residence - 70% urban, 30% rural
        if np.random.random() < 0.70:
            residence = np.random.choice(URBAN_COMUNI)
        else:
            residence = np.random.choice(RURAL_COMUNI)
        
        # Facility - weighted by size
        facility_weights = [0.12, 0.10, 0.08, 0.10, 0.08,  # Milan
                           0.10, 0.06,  # Bergamo
                           0.08, 0.06,  # Brescia
                           0.05, 0.05, 0.04, 0.03, 0.03, 0.02]  # Others
        facility_id = np.random.choice(ED_FACILITIES, p=facility_weights)
        
        # Determine diagnosis type
        # Increase intoxication probability over time (especially benzos)
        years_from_start = year - start_year
        intox_prob = intox_prevalence * (1 + benzo_trend_increase * years_from_start / (end_year - start_year))
        
        roll = np.random.random()
        if roll < intox_prob:
            # Drug intoxication
            diagnosis_type = "intoxication"
            
            # Drug class distribution - benzos increasing, others stable
            benzo_weight = 0.35 + 0.20 * years_from_start / (end_year - start_year)
            other_weight = (1 - benzo_weight) / 6
            drug_weights = {
                "Benzodiazepines": benzo_weight,
                "Opioids": other_weight * 1.5,
                "Antidepressants": other_weight * 1.2,
                "Paracetamol": other_weight * 1.5,
                "Stimulants": other_weight * 0.8,
                "Cocaine": other_weight * 0.5,
                "Other_sedatives": other_weight * 0.5,
            }
            drug_class = np.random.choice(
                list(drug_weights.keys()),
                p=np.array(list(drug_weights.values())) / sum(drug_weights.values())
            )
            
            # ICD-10 vs ICD-9 (transition around 2019)
            if year >= 2019 or (year == 2018 and np.random.random() < 0.5):
                codes = ICD10_INTOX_CODES.get(drug_class, ["T509X1A"])
            else:
                codes = ICD9_INTOX_CODES.get(drug_class, ["9779"])
            
            diagnosis_primary = np.random.choice(codes)
            
            # Secondary diagnosis often MH
            if np.random.random() < 0.4:
                mh_class = np.random.choice(list(ICD10_MH_CODES.keys()))
                diagnosis_secondary = np.random.choice(ICD10_MH_CODES[mh_class])
            else:
                diagnosis_secondary = "_"
            
            # Higher admission rate for intoxications
            esito = np.random.choice(["1", "2", "3", "4"], p=[0.65, 0.25, 0.07, 0.03])
            
        elif roll < intox_prob + mh_prevalence:
            # Mental health (non-intoxication)
            diagnosis_type = "mental_health"
            mh_class = np.random.choice(list(ICD10_MH_CODES.keys()))
            diagnosis_primary = np.random.choice(ICD10_MH_CODES[mh_class])
            diagnosis_secondary = "_"
            esito = np.random.choice(["1", "2", "3"], p=[0.70, 0.22, 0.08])
            
        else:
            # Other diagnosis
            diagnosis_type = "other"
            diagnosis_primary = np.random.choice(OTHER_DIAGNOSES)
            diagnosis_secondary = "_"
            esito = np.random.choice(["1", "2", "3"], p=[0.85, 0.12, 0.03])
        
        # Esito description
        esito_desc = {
            "1": "DIMISSIONE A DOMICILIO",
            "2": "RICOVERO ORDINARIO",
            "3": "RICOVERO DH",
            "4": "RICOVERO TERAPIA INTENSIVA",
        }.get(esito, "ALTRO")
        
        records.append({
            "Codice Fiscale Assistito MICROBIO": patient_id,
            "Annomese_INGR": year_month,
            "Eta(calcolata)": age,
            "Sesso (anag ass.to)": sex,
            "Sesso (flusso)": sex,
            "Cod Diagnosi": diagnosis_primary,
            "Diagnosi": f"Diagnosis for {diagnosis_primary}",
            "Cod Diagnosi Secondaria": diagnosis_secondary,
            "Diagnosi Secondaria": "DATO NON APPLICABILE" if diagnosis_secondary == "_" else f"Secondary {diagnosis_secondary}",
            "Codice Esito": esito,
            "Descrizione Esito": esito_desc,
            "Codice Nazione(flusso)": "100",
            "Conteggio Persone fisiche": 1,
            # NEW FIELDS
            "facility_id": facility_id,
            "residence": residence,
        })
    
    return pd.DataFrame(records)


# =============================================================================
# PHARMACEUTICAL DATA GENERATOR
# =============================================================================

def generate_pharmaceutical_data(
    n_records: int = 100000,
    n_patients: int = 15000,
    start_year: int = 2017,
    end_year: int = 2025,
    benzo_trend_increase: float = 0.12,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Generate synthetic pharmaceutical dispensing data.
    
    Includes:
    - Realistic drug class distribution
    - Increasing benzodiazepine prescriptions over time
    - DDD values
    - Chronic vs sporadic users
    
    Parameters
    ----------
    n_records : int
        Number of prescription records.
    n_patients : int
        Number of unique patients.
    start_year : int
        First year of data.
    end_year : int
        Last year of data.
    benzo_trend_increase : float
        Annual increase in benzodiazepine prescriptions.
    seed : int
        Random seed.
        
    Returns
    -------
    pd.DataFrame
        Synthetic pharmaceutical data with DDD.
    """
    np.random.seed(seed)
    
    # Generate patient pool
    patient_pool = [generate_patient_id() for _ in range(n_patients)]
    
    # Some patients are chronic users (many prescriptions)
    n_chronic = int(n_patients * 0.15)
    chronic_patients = set(np.random.choice(patient_pool, n_chronic, replace=False))
    
    records = []
    
    for i in range(n_records):
        # Chronic patients get more prescriptions
        if np.random.random() < 0.4:
            patient_id = np.random.choice(list(chronic_patients))
        else:
            patient_id = np.random.choice(patient_pool)
        
        # Date
        date = generate_date_in_range(start_year, end_year)
        year = date.year
        
        # Age
        age = int(np.random.normal(55, 18))
        age = max(18, min(95, age))
        
        # Sex
        sex = np.random.choice(["F", "M"], p=[0.58, 0.42])
        
        # Drug class - with temporal trend
        years_from_start = year - start_year
        benzo_weight = 0.25 + 0.15 * years_from_start / (end_year - start_year)
        
        class_weights = {
            "benzodiazepine": benzo_weight,
            "z_drug": 0.08,
            "antidepressant": 0.25,
            "opioid": 0.08,
            "stimulant": 0.02,
            "antipsychotic": 0.07,
            "other": 1 - benzo_weight - 0.50,
        }
        
        drug_class = np.random.choice(
            list(class_weights.keys()),
            p=np.array(list(class_weights.values())) / sum(class_weights.values())
        )
        
        # ATC code
        atc_code = np.random.choice(ATC_CODES.get(drug_class, ATC_CODES["other"]))
        
        # Drug name (simplified)
        drug_names = {
            "N05BA12": "ALPRAZOLAM", "N05BA06": "LORAZEPAM", "N05BA01": "DIAZEPAM",
            "N05CF01": "ZOPICLONE", "N05CF02": "ZOLPIDEM",
            "N06AB06": "SERTRALINE", "N06AB10": "ESCITALOPRAM", "N06AB04": "CITALOPRAM",
            "N02AX02": "TRAMADOL", "N02AA05": "OXYCODONE",
            "N06BA04": "METHYLPHENIDATE",
        }
        drug_name = drug_names.get(atc_code, atc_code)
        
        # DDD - varies by drug class
        ddd_means = {
            "benzodiazepine": 30, "z_drug": 20, "antidepressant": 30,
            "opioid": 15, "stimulant": 30, "antipsychotic": 30, "other": 30
        }
        ddd = max(1, np.random.normal(ddd_means.get(drug_class, 30), 10))
        
        # Prescription vs dispensing date
        prescription_date = date - timedelta(days=np.random.randint(0, 14))
        dispensing_date = date
        
        # Prescriber type
        prescriber_code = np.random.choice(["1", "Y", "2"], p=[0.75, 0.20, 0.05])
        prescriber_desc = {"1": "GENERICI", "Y": "DIPENDENTI", "2": "DATO MANCANTE"}[prescriber_code]
        
        records.append({
            "Codice Fiscale Assistito MICROBIO": patient_id,
            "Eta Anni": age,
            "Sesso": sex,
            "Data Prescrizione.Data": prescription_date.strftime("%Y/%m/%d 00:00:00"),
            "Data Erogazione.Data": dispensing_date.strftime("%Y/%m/%d 00:00:00"),
            "Cod Atc": atc_code,
            "Desc Atc": drug_name,
            "Cod Tipo Medico": prescriber_code,
            "Desc Tipo Medico": prescriber_desc,
            "DDD": round(ddd, 2),
        })
    
    return pd.DataFrame(records)


# =============================================================================
# FUA LOOKUP GENERATOR
# =============================================================================

def generate_fua_lookup() -> pd.DataFrame:
    """
    Generate a synthetic FUA (urban/rural) lookup table.
    
    Returns
    -------
    pd.DataFrame
        FUA classification for Lombardy municipalities.
    """
    records = []
    
    # Urban municipalities get a City name
    for comune in URBAN_COMUNI:
        records.append({
            "Comune": comune,
            "Provincia": "Lombardia",
            "Città (City/Greater City) 2021": comune if comune in ["Milano", "Bergamo", "Brescia"] else f"FUA_{comune}",
            "FUA": f"FUA_{comune}",
        })
    
    # Rural municipalities have no city
    for comune in RURAL_COMUNI:
        records.append({
            "Comune": comune,
            "Provincia": "Lombardia",
            "Città (City/Greater City) 2021": "No City/Città",
            "FUA": "",
        })
    
    return pd.DataFrame(records)


# =============================================================================
# LINKED SYNTHETIC DATA (for testing linkage)
# =============================================================================

def generate_linked_data(
    n_ed_records: int = 10000,
    n_pharma_records: int = 50000,
    linkage_rate: float = 0.6,
    seed: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate ED and pharmaceutical data with controlled patient overlap.
    
    This ensures realistic linkage scenarios:
    - Some intoxication patients have prior prescriptions
    - Some don't (new users, illicit sources)
    - Some prescription patients never have intoxication
    
    Parameters
    ----------
    n_ed_records : int
        Number of ED records.
    n_pharma_records : int
        Number of pharmaceutical records.
    linkage_rate : float
        Proportion of intoxication patients with prior prescriptions.
    seed : int
        Random seed.
        
    Returns
    -------
    tuple of (pd.DataFrame, pd.DataFrame)
        (ED data, Pharmaceutical data) with overlapping patient IDs.
    """
    np.random.seed(seed)
    
    # Generate shared patient pool
    n_shared = int(min(n_ed_records, n_pharma_records) * linkage_rate * 0.3)
    shared_patients = [generate_patient_id() for _ in range(n_shared)]
    
    # Generate ED data with some shared patients
    ed_df = generate_ed_presentations(n_records=n_ed_records, seed=seed)
    
    # Replace some ED patient IDs with shared ones (for intoxication cases)
    intox_mask = ed_df["Cod Diagnosi"].str.startswith(("T4", "96"))
    n_to_replace = min(int(intox_mask.sum() * linkage_rate), len(shared_patients))
    replace_indices = ed_df[intox_mask].sample(n=n_to_replace, random_state=seed).index
    ed_df.loc[replace_indices, "Codice Fiscale Assistito MICROBIO"] = np.random.choice(
        shared_patients, len(replace_indices)
    )
    
    # Generate pharmaceutical data
    pharma_df = generate_pharmaceutical_data(n_records=n_pharma_records, seed=seed+1)
    
    # Add shared patients to pharma (multiple prescriptions each)
    extra_pharma = []
    for patient in shared_patients:
        n_rx = np.random.randint(3, 15)
        for _ in range(n_rx):
            date = generate_date_in_range(2017, 2025)
            extra_pharma.append({
                "Codice Fiscale Assistito MICROBIO": patient,
                "Eta Anni": np.random.randint(25, 70),
                "Sesso": np.random.choice(["F", "M"]),
                "Data Prescrizione.Data": date.strftime("%Y/%m/%d 00:00:00"),
                "Data Erogazione.Data": date.strftime("%Y/%m/%d 00:00:00"),
                "Cod Atc": np.random.choice(["N05BA12", "N05BA06", "N05CF01"]),
                "Desc Atc": "BENZODIAZEPINE",
                "Cod Tipo Medico": "1",
                "Desc Tipo Medico": "GENERICI",
                "DDD": round(np.random.uniform(20, 60), 2),
            })
    
    pharma_df = pd.concat([pharma_df, pd.DataFrame(extra_pharma)], ignore_index=True)
    
    return ed_df, pharma_df


# =============================================================================
# MAIN GENERATOR FUNCTION
# =============================================================================

def generate_all_synthetic_data(
    output_dir: Optional[Path] = None,
    n_ed_records: int = 50000,
    n_pharma_records: int = 100000,
    seed: int = 42,
    save_files: bool = True,
) -> Dict[str, pd.DataFrame]:
    """
    Generate all synthetic datasets for end-to-end testing.
    
    Creates:
    - ED presentations (with facility, residence, diagnoses)
    - Pharmaceutical data (with DDD)
    - FUA lookup table
    
    Parameters
    ----------
    output_dir : Path, optional
        Directory to save CSV files. If None, uses current directory.
    n_ed_records : int
        Number of ED records.
    n_pharma_records : int
        Number of pharmaceutical records.
    seed : int
        Random seed.
    save_files : bool
        If True, save CSV files to disk.
        
    Returns
    -------
    dict
        Dictionary with all generated DataFrames.
    """
    print("=" * 60)
    print("GENERATING SYNTHETIC DATA")
    print("=" * 60)
    
    if output_dir is None:
        output_dir = Path(".")
    output_dir = Path(output_dir)
    
    # Generate linked data for realistic linkage testing
    print("\nGenerating ED and Pharmaceutical data (with patient overlap)...")
    ed_df, pharma_df = generate_linked_data(
        n_ed_records=n_ed_records,
        n_pharma_records=n_pharma_records,
        linkage_rate=0.6,
        seed=seed,
    )
    print(f"  ED records: {len(ed_df):,}")
    print(f"  Pharma records: {len(pharma_df):,}")
    
    # Check overlap
    ed_patients = set(ed_df["Codice Fiscale Assistito MICROBIO"].unique())
    pharma_patients = set(pharma_df["Codice Fiscale Assistito MICROBIO"].unique())
    overlap = len(ed_patients & pharma_patients)
    print(f"  Patient overlap: {overlap:,} ({100*overlap/len(ed_patients):.1f}% of ED patients)")
    
    # Generate FUA lookup
    print("\nGenerating FUA lookup table...")
    fua_df = generate_fua_lookup()
    print(f"  Municipalities: {len(fua_df)}")
    print(f"  Urban: {(fua_df['Città (City/Greater City) 2021'] != 'No City/Città').sum()}")
    print(f"  Rural: {(fua_df['Città (City/Greater City) 2021'] == 'No City/Città').sum()}")
    
    # Save files
    if save_files:
        raw_dir = output_dir / "raw"
        lookups_dir = output_dir / "lookups"
        raw_dir.mkdir(parents=True, exist_ok=True)
        lookups_dir.mkdir(parents=True, exist_ok=True)
        
        ed_path = raw_dir / "ed_presentations.csv"
        ed_df.to_csv(ed_path, index=False)
        print(f"\n✓ Saved: {ed_path}")
        
        pharma_path = raw_dir / "pharma_synthetic.csv"
        pharma_df.to_csv(pharma_path, index=False)
        print(f"✓ Saved: {pharma_path}")
        
        fua_path = lookups_dir / "istat_fua_comuni.csv"
        fua_df.to_csv(fua_path, index=False)
        print(f"✓ Saved: {fua_path}")
    
    print("\n" + "=" * 60)
    print("SYNTHETIC DATA GENERATION COMPLETE")
    print("=" * 60)
    
    return {
        "ed": ed_df,
        "pharma": pharma_df,
        "fua": fua_df,
    }


# =============================================================================
# QUICK TEST
# =============================================================================

if __name__ == "__main__":
    # Generate sample data
    data = generate_all_synthetic_data(
        output_dir=Path("data"),
        n_ed_records=10000,
        n_pharma_records=30000,
        save_files=False,
    )
    
    print("\n--- ED Data Sample ---")
    print(data["ed"].head(3))
    
    print("\n--- Pharma Data Sample ---")
    print(data["pharma"].head(3))
    
    print("\n--- FUA Lookup Sample ---")
    print(data["fua"].head(5))
