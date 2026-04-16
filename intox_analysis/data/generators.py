# -*- coding: utf-8 -*-
"""
Synthetic Data Generators (Fast Vectorized Version)
====================================================

Generates realistic synthetic data for testing the analysis pipeline.
Uses vectorized numpy operations for speed.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Optional, Tuple


# =============================================================================
# CONSTANTS
# =============================================================================

URBAN_COMUNI = [
    "Milano", "Bergamo", "Brescia", "Monza", "Como", "Varese", "Pavia",
    "Cremona", "Lecco", "Lodi", "Mantova", "Busto Arsizio", "Sesto San Giovanni",
]

RURAL_COMUNI = [
    "Morbegno", "Chiavenna", "Bormio", "Livigno", "Tirano", "Edolo",
    "Ponte di Legno", "Aprica", "Madesimo", "Foppolo", "Branzi",
]

ED_FACILITIES = [
    "OSP_MI_NIGUARDA", "OSP_MI_POLICLINICO", "OSP_MI_SACCO",
    "OSP_MI_HUMANITAS", "OSP_BG_PAPA_GIOVANNI", "OSP_BS_CIVILI",
    "OSP_CO_SANT_ANNA", "OSP_VA_CIRCOLO", "OSP_PV_SAN_MATTEO",
]

# Diagnosis codes
INTOX_CODES_ICD10 = ["T424X1A", "T424X2A", "T400X1A", "T400X2A", "T391X1A", 
                     "T391X2A", "T436X1A", "T436X2A", "T430X2A", "T426X1A"]
INTOX_CODES_ICD9 = ["9694", "96940", "9650", "96500", "9697", "9690"]
MH_CODES = ["F320", "F329", "F410", "F411", "F431", "F500", "F200"]
OTHER_CODES = ["J189", "K529", "R104", "S0100", "I10", "N390"]

ATC_CODES_BENZO = ["N05BA12", "N05BA06", "N05BA01", "N05BA04"]
ATC_CODES_OTHER = ["N05CF01", "N05CF02", "N06AB06", "N06AB10", "N02AX02", "A02BC01"]


# =============================================================================
# FAST GENERATORS
# =============================================================================

def generate_patient_ids(n: int, seed: int = 42) -> np.ndarray:
    """Generate n unique patient IDs quickly."""
    np.random.seed(seed)
    hex_chars = np.array(list("0123456789ABCDEF"))
    # Generate all random hex characters at once
    random_hex = np.random.choice(hex_chars, size=(n, 64))
    # Join each row into a string
    ids = np.array(["MB-" + "".join(row) for row in random_hex])
    return ids


def generate_ed_presentations(
    n_records: int = 50000,
    start_year: int = 2017,
    end_year: int = 2025,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Generate synthetic ED presentation data (FAST version).
    """
    np.random.seed(seed)
    print(f"  Generating {n_records:,} ED records...", end=" ", flush=True)
    
    # Patient IDs (70% unique)
    n_unique = int(n_records * 0.7)
    patient_pool = generate_patient_ids(n_unique, seed)
    patient_ids = np.random.choice(patient_pool, n_records)
    
    # Years and months
    years = np.random.choice(range(start_year, end_year + 1), n_records)
    months = np.random.randint(1, 13, n_records)
    year_months = [f"{y}{m:02d}" for y, m in zip(years, months)]
    
    # Age (bimodal)
    ages = np.where(
        np.random.random(n_records) < 0.4,
        np.random.normal(25, 8, n_records),
        np.random.normal(55, 15, n_records)
    ).astype(int).clip(5, 99)
    
    # Sex
    sex = np.random.choice(["F", "M"], n_records, p=[0.55, 0.45])
    
    # Residence
    all_comuni = URBAN_COMUNI + RURAL_COMUNI
    urban_prob = 0.7 / len(URBAN_COMUNI)
    rural_prob = 0.3 / len(RURAL_COMUNI)
    probs = [urban_prob] * len(URBAN_COMUNI) + [rural_prob] * len(RURAL_COMUNI)
    residence = np.random.choice(all_comuni, n_records, p=probs)
    
    # Facility
    facility = np.random.choice(ED_FACILITIES, n_records)
    
    # Diagnosis type probabilities (intox increases over time)
    intox_probs = 0.05 + 0.08 * (years - start_year) / (end_year - start_year)
    mh_probs = np.full(n_records, 0.12)
    
    rolls = np.random.random(n_records)
    
    # Vectorized diagnosis assignment
    is_intox = rolls < intox_probs
    is_mh = (rolls >= intox_probs) & (rolls < intox_probs + mh_probs)
    is_other = ~is_intox & ~is_mh
    
    # Generate diagnosis codes
    diagnoses = np.empty(n_records, dtype=object)
    
    # ICD-10 for recent years, ICD-9 for older
    use_icd10 = years >= 2019
    
    # Intoxication codes
    intox_icd10 = np.random.choice(INTOX_CODES_ICD10, n_records)
    intox_icd9 = np.random.choice(INTOX_CODES_ICD9, n_records)
    diagnoses[is_intox & use_icd10] = intox_icd10[is_intox & use_icd10]
    diagnoses[is_intox & ~use_icd10] = intox_icd9[is_intox & ~use_icd10]
    
    # Mental health codes
    mh_codes = np.random.choice(MH_CODES, n_records)
    diagnoses[is_mh] = mh_codes[is_mh]
    
    # Other codes
    other_codes = np.random.choice(OTHER_CODES, n_records)
    diagnoses[is_other] = other_codes[is_other]
    
    # Secondary diagnosis
    has_secondary = np.random.random(n_records) < 0.3
    secondary = np.where(has_secondary, np.random.choice(MH_CODES, n_records), "_")
    
    # Esito (higher admission for intox)
    esito = np.empty(n_records, dtype=object)
    esito[is_intox] = np.random.choice(["1", "2", "3", "4"], is_intox.sum(), p=[0.65, 0.25, 0.07, 0.03])
    esito[~is_intox] = np.random.choice(["1", "2", "3"], (~is_intox).sum(), p=[0.80, 0.15, 0.05])
    
    esito_desc_map = {"1": "DIMISSIONE A DOMICILIO", "2": "RICOVERO ORDINARIO", 
                      "3": "RICOVERO DH", "4": "RICOVERO TERAPIA INTENSIVA"}
    esito_desc = np.array([esito_desc_map.get(e, "ALTRO") for e in esito])
    
    print("Done!")
    
    return pd.DataFrame({
        "Codice Fiscale Assistito MICROBIO": patient_ids,
        "Annomese_INGR": year_months,
        "Eta(calcolata)": ages,
        "Sesso (anag ass.to)": sex,
        "Sesso (flusso)": sex,
        "Cod Diagnosi": diagnoses,
        "Diagnosi": "Synthetic diagnosis",
        "Cod Diagnosi Secondaria": secondary,
        "Diagnosi Secondaria": np.where(secondary == "_", "DATO NON APPLICABILE", "Secondary"),
        "Codice Esito": esito,
        "Descrizione Esito": esito_desc,
        "Codice Nazione(flusso)": "100",
        "Conteggio Persone fisiche": 1,
        "facility_id": facility,
        "residence": residence,
    })


def generate_pharmaceutical_data(
    n_records: int = 100000,
    n_patients: int = 15000,
    start_year: int = 2017,
    end_year: int = 2025,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Generate synthetic pharmaceutical data (FAST version).
    """
    np.random.seed(seed)
    print(f"  Generating {n_records:,} pharma records...", end=" ", flush=True)
    
    # Patient IDs
    patient_pool = generate_patient_ids(n_patients, seed + 100)
    patient_ids = np.random.choice(patient_pool, n_records)
    
    # Dates
    years = np.random.choice(range(start_year, end_year + 1), n_records)
    months = np.random.randint(1, 13, n_records)
    days = np.random.randint(1, 29, n_records)
    dates = [f"{y}/{m:02d}/{d:02d} 00:00:00" for y, m, d in zip(years, months, days)]
    
    # Age and sex
    ages = np.random.normal(55, 18, n_records).astype(int).clip(18, 95)
    sex = np.random.choice(["F", "M"], n_records, p=[0.58, 0.42])
    
    # ATC codes (benzo increases over time)
    benzo_prob = 0.25 + 0.20 * (years - start_year) / (end_year - start_year)
    is_benzo = np.random.random(n_records) < benzo_prob
    
    atc_codes = np.where(
        is_benzo,
        np.random.choice(ATC_CODES_BENZO, n_records),
        np.random.choice(ATC_CODES_OTHER, n_records)
    )
    
    # Drug names
    drug_name_map = {"N05BA12": "ALPRAZOLAM", "N05BA06": "LORAZEPAM", 
                     "N05BA01": "DIAZEPAM", "N05BA04": "OXAZEPAM",
                     "N05CF01": "ZOPICLONE", "N05CF02": "ZOLPIDEM",
                     "N06AB06": "SERTRALINE", "N06AB10": "ESCITALOPRAM",
                     "N02AX02": "TRAMADOL", "A02BC01": "OMEPRAZOLE"}
    drug_names = np.array([drug_name_map.get(a, "OTHER") for a in atc_codes])
    
    # DDD
    ddd = np.random.uniform(10, 60, n_records).round(2)
    
    # Prescriber
    prescriber_code = np.random.choice(["1", "Y", "2"], n_records, p=[0.75, 0.20, 0.05])
    prescriber_desc_map = {"1": "GENERICI", "Y": "DIPENDENTI", "2": "DATO MANCANTE"}
    prescriber_desc = np.array([prescriber_desc_map[p] for p in prescriber_code])
    
    print("Done!")
    
    return pd.DataFrame({
        "Codice Fiscale Assistito MICROBIO": patient_ids,
        "Eta Anni": ages,
        "Sesso": sex,
        "Data Prescrizione.Data": dates,
        "Data Erogazione.Data": dates,
        "Cod Atc": atc_codes,
        "Desc Atc": drug_names,
        "Cod Tipo Medico": prescriber_code,
        "Desc Tipo Medico": prescriber_desc,
        "DDD": ddd,
    })


def generate_fua_lookup() -> pd.DataFrame:
    """Generate FUA lookup table."""
    records = []
    for comune in URBAN_COMUNI:
        records.append({
            "Comune": comune,
            "Provincia": "Lombardia",
            "City (City/Greater City) 2021": comune,
            "FUA": f"FUA_{comune}",
        })
    for comune in RURAL_COMUNI:
        records.append({
            "Comune": comune,
            "Provincia": "Lombardia",
            "City (City/Greater City) 2021": "No City",
            "FUA": "",
        })
    return pd.DataFrame(records)


def generate_linked_data(
    n_ed_records: int = 10000,
    n_pharma_records: int = 50000,
    linkage_rate: float = 0.6,
    seed: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate ED and pharma data with patient overlap for linkage testing.
    """
    np.random.seed(seed)
    
    # Generate shared patient pool
    n_shared = int(min(n_ed_records, n_pharma_records) * 0.1)
    shared_patients = generate_patient_ids(n_shared, seed + 200)
    
    # Generate base data
    ed_df = generate_ed_presentations(n_ed_records, seed=seed)
    pharma_df = generate_pharmaceutical_data(n_pharma_records, seed=seed + 1)
    
    # Add shared patients to both datasets
    # Replace some intox patients with shared IDs
    intox_mask = ed_df["Cod Diagnosi"].str.startswith(("T4", "96"))
    n_replace = min(int(intox_mask.sum() * linkage_rate), len(shared_patients))
    if n_replace > 0:
        replace_idx = ed_df[intox_mask].sample(n=n_replace, random_state=seed).index
        ed_df.loc[replace_idx, "Codice Fiscale Assistito MICROBIO"] = np.random.choice(
            shared_patients, len(replace_idx)
        )
    
    # Add shared patients to pharma
    n_pharma_shared = min(len(shared_patients) * 5, 1000)
    if n_pharma_shared > 0:
        shared_pharma = pd.DataFrame({
            "Codice Fiscale Assistito MICROBIO": np.random.choice(shared_patients, n_pharma_shared),
            "Eta Anni": np.random.randint(25, 70, n_pharma_shared),
            "Sesso": np.random.choice(["F", "M"], n_pharma_shared),
            "Data Prescrizione.Data": "2023/06/15 00:00:00",
            "Data Erogazione.Data": "2023/06/15 00:00:00",
            "Cod Atc": np.random.choice(ATC_CODES_BENZO, n_pharma_shared),
            "Desc Atc": "BENZODIAZEPINE",
            "Cod Tipo Medico": "1",
            "Desc Tipo Medico": "GENERICI",
            "DDD": np.random.uniform(20, 50, n_pharma_shared).round(2),
        })
        pharma_df = pd.concat([pharma_df, shared_pharma], ignore_index=True)
    
    return ed_df, pharma_df


def generate_all_synthetic_data(
    output_dir: Optional[Path] = None,
    n_ed_records: int = 50000,
    n_pharma_records: int = 100000,
    seed: int = 42,
    save_files: bool = True,
) -> Dict[str, pd.DataFrame]:
    """
    Generate all synthetic datasets.
    """
    print("=" * 60)
    print("GENERATING SYNTHETIC DATA")
    print("=" * 60)
    
    if output_dir is None:
        output_dir = Path(".")
    output_dir = Path(output_dir)
    
    print("\nGenerating ED and Pharmaceutical data...")
    ed_df, pharma_df = generate_linked_data(
        n_ed_records=n_ed_records,
        n_pharma_records=n_pharma_records,
        seed=seed,
    )
    
    # Count overlap
    ed_patients = set(ed_df["Codice Fiscale Assistito MICROBIO"].unique())
    pharma_patients = set(pharma_df["Codice Fiscale Assistito MICROBIO"].unique())
    overlap = len(ed_patients & pharma_patients)
    print(f"  Patient overlap: {overlap:,} ({100*overlap/len(ed_patients):.1f}% of ED patients)")
    
    print("\nGenerating FUA lookup table...")
    fua_df = generate_fua_lookup()
    print(f"  Municipalities: {len(fua_df)} ({len(URBAN_COMUNI)} urban, {len(RURAL_COMUNI)} rural)")
    
    if save_files:
        raw_dir = output_dir / "raw"
        lookups_dir = output_dir / "lookups"
        raw_dir.mkdir(parents=True, exist_ok=True)
        lookups_dir.mkdir(parents=True, exist_ok=True)
        
        ed_df.to_csv(raw_dir / "ed_presentations.csv", index=False)
        print(f"\n✓ Saved: {raw_dir / 'ed_presentations.csv'}")
        
        pharma_df.to_csv(raw_dir / "pharma_synthetic.csv", index=False)
        print(f"✓ Saved: {raw_dir / 'pharma_synthetic.csv'}")
        
        fua_df.to_csv(lookups_dir / "istat_fua_comuni.csv", index=False)
        print(f"✓ Saved: {lookups_dir / 'istat_fua_comuni.csv'}")
    
    print("\n" + "=" * 60)
    print("DONE!")
    print("=" * 60)
    
    return {"ed": ed_df, "pharma": pharma_df, "fua": fua_df}


if __name__ == "__main__":
    data = generate_all_synthetic_data(save_files=False)
    print(f"\nED shape: {data['ed'].shape}")
    print(f"Pharma shape: {data['pharma'].shape}")
