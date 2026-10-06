"""
Synthetic data generators for the Lombardy drug-intoxication project.

Produces test data that mirrors the real VDI extracts WITHOUT any real patient
information, so the analysis pipeline can be developed outside the secure VDI.

Two flows are generated, with the exact column headers seen in the real files:

ED ("ed_presentations.csv"):
    Codice Fiscale Assistito MICROBIO, Annomese_INGR, Eta(calcolata),
    Sesso (anag ass.to), Sesso (flusso), Cod Diagnosi, Diagnosi,
    Cod Diagnosi Secondaria, Diagnosi Secondaria, Codice Esito,
    Descrizione Esito, Codice Nazione(flusso), Conteggio Persone fisiche,
    facility_id, residence

Pharma / FUR ("pharma_synthetic.csv"):
    Codice Fiscale Assistito MICROBIO, Eta Anni, Sesso,
    Data Prescrizione.Data, Data Erogazione.Data, Cod Atc, Desc Atc,
    Cod Tipo Medico, Desc Tipo Medico, DDD

Drug-intoxication diagnosis codes follow the ATC-aligned taxonomy in schemas.py
(benzodiazepine, antipsychotic, anxiolytic, hypnotic_sedative, antidepressant,
psychostimulant, non_medical, other). Every intoxication code emitted here
classifies back to its intended class (see tests/test_generators.py).

NOTE on DDD: the real FUR column name is not yet confirmed. This generator emits
it as "DDD"; set DDD_COLUMN once the real name is known and the loader/config can
point at it.
"""

from __future__ import annotations

import hashlib
from datetime import date, timedelta

import numpy as np
import pandas as pd

# =============================================================================
# STUDY CONSTANTS
# =============================================================================

STUDY_START_YEAR = 2017
STUDY_END_YEAR = 2025
COVID_START_YEARMONTH = "202003"

# Real FUR DDD column name (placeholder until confirmed from the VDI codebook).
DDD_COLUMN = "DDD"

FEMALE_PROPORTION = 0.55
AGE_COMPONENTS = [  # mixture of normals (mean, std, weight)
    (16, 2, 0.10), (25, 8, 0.35), (45, 12, 0.30), (65, 15, 0.25),
]

SEASONAL_PATTERN = {1: 1.05, 2: 0.95, 3: 1.0, 4: 0.98, 5: 1.02, 6: 1.05,
                    7: 1.08, 8: 1.10, 9: 1.0, 10: 0.98, 11: 0.95, 12: 1.05}
COVID_IMMEDIATE_EFFECT = -0.15
COVID_TREND_CHANGE = 0.01

# Drug-class mix for intoxication cases (benzodiazepine predominance retained).
DRUG_CLASS_DISTRIBUTION = {
    "benzodiazepine": 0.34, "antidepressant": 0.18, "antipsychotic": 0.12,
    "hypnotic_sedative": 0.08, "psychostimulant": 0.07, "non_medical": 0.09,
    "anxiolytic": 0.04, "other": 0.08,
}

# ICD-10-CM codes (full 7-char form), verified to round-trip through the
# classifier. No "anxiolytic" key: ICD-10 has no clean anxiolytic-only code,
# so post-transition anxiolytic cases fall back to the benzodiazepine bucket.
ICD10_CODES_BY_CLASS = {
    "benzodiazepine":   ["T424X1A", "T424X2A", "T424X4A"],
    "antipsychotic":    ["T433X1A", "T433X2A", "T434X1A", "T435X1A"],
    "hypnotic_sedative": ["T423X1A", "T426X1A", "T426X2A"],
    "antidepressant":   ["T430X1A", "T431X1A", "T432X1A", "T432X2A"],
    "psychostimulant":  ["T436X1A", "T43621A", "T43631A"],
    "non_medical":      ["T400X1A", "T400X2A", "T401X1A", "T405X1A", "T407X1A", "T43641A"],
    "other":            ["T509X1A", "T460X1A", "T392X1A"],
}
ICD9_CODES_BY_CLASS = {
    "benzodiazepine":   ["9694"],
    "antipsychotic":    ["9691", "9692", "9693"],
    "anxiolytic":       ["9695"],
    "hypnotic_sedative": ["9670", "9671", "9678"],
    "antidepressant":   ["9690"],
    "psychostimulant":  ["9697", "9700", "97089"],
    "non_medical":      ["9696", "97081", "96500", "96501", "96502", "96509"],
    "other":            ["9654", "9720", "9620"],
}
ALL_INTOX_CODES = {c for codes in ICD10_CODES_BY_CLASS.values() for c in codes} | \
                  {c for codes in ICD9_CODES_BY_CLASS.values() for c in codes}

NON_INTOX_ICD10 = ["J189", "R104", "N390", "I10", "S0100", "F410", "F320", "F200", "R51"]
NON_INTOX_ICD9 = ["4659", "7890", "7840", "4019", "78900"]

# Esito codebook and approximate shares, confirmed from the real ED extract.
ESITO_DISTRIBUTION = {"1": 0.757, "2": 0.181, "3": 0.031, "5": 0.015, "7": 0.007,
                      "0": 0.004, "8": 0.003, "4": 0.001, "6": 0.001}
ESITO_DESCRIPTIONS = {
    "0": "TRATTAMENTO IN OSSERVAZIONE BREVE INTESIVA (OBI)",
    "1": "DIMISSIONE A DOMICILIO", "2": "RICOVERO IN REPARTO DEGENZA",
    "3": "TRASFERIMENTO AD ALTRO ISTITUTO", "4": "DECEDUTO IN PS",
    "5": "RIFIUTA IL RICOVERO",
    "6": "IL PAZIENTE ABBANDONA IL PS PRIMA DELLA VISITA MEDICA",
    "7": "IL PAZIENTE ABBANDONA IL PS IN CORSO DI ACCERTAMENTI E/O PRIMA DELLA "
         "CHIUSURA DELLA CARTELLA CLINICA",
    "8": "DIMISSIONE A STRUTTURE AMBULATORIALI",
}

FACILITIES = ["OSP_MI_HUMANITAS", "OSP_PV_SAN_MATTEO", "OSP_CO_SANT_ANNA",
              "OSP_MI_SACCO", "OSP_MI_NIGUARDA", "OSP_BS_CIVILI",
              "OSP_BG_PAPA_GIOVANNI", "OSP_MI_POLICLINICO", "OSP_VA_CIRCOLO"]
COMUNI = ["Milano", "Bergamo", "Brescia", "Como", "Mantova", "Pavia", "Varese",
          "Lecco", "Cremona", "Monza", "Sesto San Giovanni", "Busto Arsizio",
          "Lodi", "Sondrio", "Edolo", "Ponte di Legno", "Foppolo", "Branzi"]

# ATC vocabulary for the pharma flow (N05/N06), weighted toward the
# linkage-relevant groups. (atc, name, weight)
ATC_DRUGS = [
    ("N05BA01", "DIAZEPAM", 6), ("N05BA06", "LORAZEPAM", 6),
    ("N05BA12", "ALPRAZOLAM", 7), ("N05BA08", "BROMAZEPAM", 4),
    ("N05CD02", "NITRAZEPAM", 2), ("N05CF02", "ZOPICLONE", 3),
    ("N05AH03", "OLANZAPINA", 4), ("N05AH04", "QUETIAPINA", 5),
    ("N05AX12", "ARIPIPRAZOLO", 3), ("N05AX08", "RISPERIDONE", 3),
    ("N06AB06", "SERTRALINA", 7), ("N06AB10", "ESCITALOPRAM", 6),
    ("N06AB05", "PAROXETINA", 4), ("N06AX05", "TRAZODONE", 4),
    ("N06AX16", "VENLAFAXINA", 4), ("N06AB03", "FLUOXETINA", 4),
    ("N06BA04", "METILFENIDATO", 2), ("N06DA03", "RIVASTIGMINA", 2),
    ("N06DX01", "MEMANTINA", 2),
]
PRESCRIBER_TYPES = [(" -", "NON APPLICABILE", 0.55), ("?", "DATO MANCANTE", 0.30),
                    ("1", "MEDICO DI MEDICINA GENERALE", 0.15)]


# =============================================================================
# HELPERS
# =============================================================================

def generate_pseudonymised_id(seed: int | str) -> str:
    """Deterministic MB-{64 hex} pseudonymised identifier."""
    return "MB-" + hashlib.sha256(str(seed).encode("utf-8")).hexdigest().upper()


def generate_yearmonth_range(start_year=STUDY_START_YEAR, end_year=STUDY_END_YEAR):
    """List of YYYYMM strings spanning the study period."""
    return [f"{y}{m:02d}" for y in range(start_year, end_year + 1) for m in range(1, 13)]


def _sample_ages(rng, n):
    means, stds, weights = zip(*AGE_COMPONENTS)
    comp = rng.choice(len(AGE_COMPONENTS), size=n, p=np.array(weights) / sum(weights))
    ages = rng.normal(np.array(means)[comp], np.array(stds)[comp])
    return np.clip(ages, 0, 105).astype(int)


def _expected_count(ym, baseline, trend, include_covid=True):
    year, month = int(ym[:4]), int(ym[4:6])
    months = (year - STUDY_START_YEAR) * 12 + (month - 1)
    val = baseline * (1 + trend) ** months * SEASONAL_PATTERN.get(month, 1.0)
    if include_covid and ym >= COVID_START_YEARMONTH:
        cy, cm = int(COVID_START_YEARMONTH[:4]), int(COVID_START_YEARMONTH[4:6])
        msc = (year - cy) * 12 + (month - cm)
        val *= (1 + COVID_IMMEDIATE_EFFECT) * (1 + COVID_TREND_CHANGE) ** msc
    return max(val, 0.0)


def _sampled_yearmonths(rng, n, trend, include_covid):
    yms = generate_yearmonth_range()
    probs = np.array([_expected_count(ym, 1.0, trend, include_covid) for ym in yms])
    probs = probs / probs.sum()
    return rng.choice(yms, size=n, p=probs)


# =============================================================================
# ED GENERATOR
# =============================================================================

def generate_ed_data(
    n_records: int = 50000,
    intoxication_rate: float = 0.04,
    seed: int = 42,
    icd10_transition_yearmonth: str = "201901",
    patient_ids: list[str] | None = None,
    include_covid_effect: bool = True,
) -> pd.DataFrame:
    """
    Generate synthetic ED presentations with the real Lombardy column headers.

    Intoxication codes follow the new taxonomy; an ICD-9->ICD-10 transition lets
    the data exercise both code systems (real extracts appear ICD-10 throughout,
    so set icd10_transition_yearmonth to the study start to disable ICD-9).
    """
    rng = np.random.default_rng(seed)
    yms = _sampled_yearmonths(rng, n_records, trend=0.006, include_covid=include_covid_effect)
    ages = _sample_ages(rng, n_records)
    sexes = np.where(rng.random(n_records) < FEMALE_PROPORTION, "F", "M")

    if patient_ids is None:
        patient_ids = [generate_pseudonymised_id(f"{seed}-ED-{i}") for i in range(n_records)]
    else:
        patient_ids = list(rng.choice(patient_ids, size=n_records))

    is_intox = rng.random(n_records) < intoxication_rate
    class_names = list(DRUG_CLASS_DISTRIBUTION)
    class_probs = np.array(list(DRUG_CLASS_DISTRIBUTION.values()))
    class_probs = class_probs / class_probs.sum()

    cod, cod2, desc2 = [], [], []
    for i in range(n_records):
        icd10 = yms[i] >= icd10_transition_yearmonth
        if is_intox[i]:
            cls = rng.choice(class_names, p=class_probs)
            table = ICD10_CODES_BY_CLASS if icd10 else ICD9_CODES_BY_CLASS
            if cls not in table:           # anxiolytic in ICD-10 era -> benzodiazepine
                cls = "benzodiazepine"
            cod.append(str(rng.choice(table[cls])))
            if rng.random() < 0.3:         # psychiatric comorbidity as secondary
                cod2.append("F410" if icd10 else "30000")
                desc2.append("Secondary")
            else:
                cod2.append("_")
                desc2.append("DATO NON APPLICABILE")
        else:
            cod.append(str(rng.choice(NON_INTOX_ICD10 if icd10 else NON_INTOX_ICD9)))
            cod2.append("_")
            desc2.append("DATO NON APPLICABILE")

    esito_p = np.array(list(ESITO_DISTRIBUTION.values()))
    esito = rng.choice(list(ESITO_DISTRIBUTION), size=n_records, p=esito_p / esito_p.sum())
    return pd.DataFrame({
        "Codice Fiscale Assistito MICROBIO": patient_ids,
        "Annomese_INGR": yms,
        "Eta(calcolata)": ages,
        "Sesso (anag ass.to)": sexes,
        "Sesso (flusso)": sexes,
        "Cod Diagnosi": cod,
        "Diagnosi": "Synthetic diagnosis",
        "Cod Diagnosi Secondaria": cod2,
        "Diagnosi Secondaria": desc2,
        "Codice Esito": esito,
        "Descrizione Esito": [ESITO_DESCRIPTIONS[e] for e in esito],
        "Codice Nazione(flusso)": "100",
        "Conteggio Persone fisiche": 1,
        "facility_id": rng.choice(FACILITIES, size=n_records),
        "residence": rng.choice(COMUNI, size=n_records),
    })


# =============================================================================
# PHARMA (FUR) GENERATOR
# =============================================================================

def generate_pharma_data(
    n_records: int = 100000,
    seed: int = 43,
    patient_ids: list[str] | None = None,
    include_covid_effect: bool = True,
) -> pd.DataFrame:
    """
    Generate synthetic pharmaceutical (FUR) dispensations with the real columns,
    including the patient hash and a DDD column (name = DDD_COLUMN).
    """
    rng = np.random.default_rng(seed)

    if patient_ids is None:
        n_patients = max(1, n_records // 6)   # ~6 dispensations per patient on average
        patient_ids = [generate_pseudonymised_id(f"{seed}-RX-{i}") for i in range(n_patients)]
    # chronic users dispense more often: weight patient sampling by a heavy tail
    weights = rng.gamma(shape=1.5, scale=1.0, size=len(patient_ids))
    weights = weights / weights.sum()
    assigned = rng.choice(patient_ids, size=n_records, p=weights)

    atc_codes, atc_names, atc_w = zip(*ATC_DRUGS)
    atc_w = np.array(atc_w) / sum(atc_w)
    pick = rng.choice(len(ATC_DRUGS), size=n_records, p=atc_w)
    cod_atc = [atc_codes[k] for k in pick]
    desc_atc = [atc_names[k] for k in pick]

    yms = _sampled_yearmonths(rng, n_records, trend=0.004, include_covid=include_covid_effect)
    disp_dates, presc_dates = [], []
    for ym in yms:
        y, m = int(ym[:4]), int(ym[4:6])
        d = date(y, m, int(rng.integers(1, 28)))
        p = d - timedelta(days=int(rng.integers(0, 14)))
        disp_dates.append(d.strftime("%Y/%m/%d 00:00:00"))
        presc_dates.append(p.strftime("%Y/%m/%d 00:00:00"))

    sex = rng.choice(["M", "F", "?"], size=n_records, p=[0.42, 0.50, 0.08])
    ages = _sample_ages(rng, n_records).astype(object)
    ages[rng.random(n_records) < 0.15] = ""        # age often blank in FUR

    p_codes, p_descs, p_w = zip(*PRESCRIBER_TYPES)
    pk = rng.choice(len(PRESCRIBER_TYPES), size=n_records, p=np.array(p_w) / sum(p_w))
    ddd = np.round(rng.gamma(shape=2.0, scale=15.0, size=n_records), 2)  # plausible per-pack DDD

    return pd.DataFrame({
        "Codice Fiscale Assistito MICROBIO": assigned,
        "Eta Anni": ages,
        "Sesso": sex,
        "Data Prescrizione.Data": presc_dates,
        "Data Erogazione.Data": disp_dates,
        "Cod Atc": cod_atc,
        "Desc Atc": desc_atc,
        "Cod Tipo Medico": [p_codes[k] for k in pk],
        "Desc Tipo Medico": [p_descs[k] for k in pk],
        DDD_COLUMN: ddd,
    })


# =============================================================================
# LINKED GENERATION (controlled patient overlap for Q5 linkage testing)
# =============================================================================

def generate_linked_data(
    n_ed_records: int = 50000,
    n_pharma_records: int = 100000,
    linkage_rate: float = 0.6,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate ED and pharma data sharing patients, so a controllable fraction of
    intoxication patients also have prescriptions (for Q5 linkage testing).
    """
    rng = np.random.default_rng(seed)
    ed = generate_ed_data(n_records=n_ed_records, seed=seed)

    intox_patients = ed.loc[ed["Cod Diagnosi"].isin(ALL_INTOX_CODES),
                            "Codice Fiscale Assistito MICROBIO"].unique().tolist()
    n_linked = int(len(intox_patients) * linkage_rate)
    linked = list(rng.choice(intox_patients, size=n_linked, replace=False)) if n_linked else []
    # pharma patient pool = linked intox patients + a set of fresh Rx-only patients
    n_fresh = max(1, len(linked))
    fresh = [generate_pseudonymised_id(f"{seed}-RXONLY-{i}") for i in range(n_fresh)]
    pool = linked + fresh if (linked or fresh) else None

    pharma = generate_pharma_data(n_records=n_pharma_records, seed=seed + 1, patient_ids=pool)
    return ed, pharma


def generate_all_synthetic_data(
    output_dir=None,
    n_ed_records: int = 50000,
    n_pharma_records: int = 100000,
    seed: int = 42,
    save_files: bool = True,
) -> dict:
    """Generate the full synthetic dataset and optionally save CSVs to <dir>/raw/."""
    from pathlib import Path
    ed, pharma = generate_linked_data(n_ed_records, n_pharma_records, seed=seed)
    if save_files:
        raw = Path(output_dir or ".") / "raw"
        raw.mkdir(parents=True, exist_ok=True)
        ed.to_csv(raw / "ed_presentations.csv", index=False)
        pharma.to_csv(raw / "pharma_synthetic.csv", index=False)
    return {"ed": ed, "pharma": pharma}


if __name__ == "__main__":
    out = generate_all_synthetic_data(n_ed_records=5000, n_pharma_records=10000, save_files=False)
    print("ED:", out["ed"].shape, "| Pharma:", out["pharma"].shape)
