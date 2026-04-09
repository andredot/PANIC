# Lombardy Drug Intoxication Analysis

Analysis of drug intoxication trends in Lombardy Emergency Departments, 2017-2025.

## Quick Start

1. **Open** `setup_environment.py` in Spyder and run it (F5) to install dependencies
2. **Open** `notebooks/01_getting_started.py` and run each cell (Ctrl+Enter) to learn the workflow
3. **Add your data** to `data/raw/` folder

## Folder Structure

```
intox_lombardy/
├── setup_environment.py      <- Run this FIRST!
├── data/
│   ├── raw/                  <- Put your VDI extracts here
│   └── processed/            <- Cleaned data goes here
├── src/intox_analysis/
│   ├── data/
│   │   ├── pharmaceutical.py <- Drug classification & Polars processing
│   │   └── schemas.py        <- ED data validation & ICD codes
│   └── analysis/             <- Statistical analysis (TBD)
├── notebooks/
│   └── 01_getting_started.py <- Start here after setup!
├── outputs/
│   ├── figures/              <- Generated plots
│   └── tables/               <- Generated tables
└── tests/                    <- Unit tests
```

## Key Features

**Memory-efficient processing** for large pharmaceutical files (1GB+):
```python
from intox_analysis.data import scan_pharmaceutical_data, add_derived_columns

# Lazy loading - doesn't use memory until .collect()
lf = scan_pharmaceutical_data(["pharma_2017.csv", "pharma_2018.csv"])
lf = add_derived_columns(lf)
result = lf.filter(pl.col("is_benzodiazepine")).collect()
```

**ATC drug classification**:
```python
from intox_analysis.data import classify_atc_code

classify_atc_code("N05BA12")  # → benzodiazepine (Alprazolam)
classify_atc_code("N05CF01")  # → z_drug (Zopiclone)
```

**ICD code classification** (for ED data):
```python
from intox_analysis.data import classify_drug_intoxication

classify_drug_intoxication("T424X2A")  # → benzodiazepine, self-harm
classify_drug_intoxication("9694")      # → benzodiazepine (ICD-9)
```

## Data Sources

| Source | File Pattern | Size |
|--------|--------------|------|
| ED Presentations | `ed_*.csv` | ~100 MB/year |
| Pharmaceutical | `pharma_*.csv` | ~1 GB/year |
| SDO (Hospital) | `sdo_*.csv` | TBD |
| Outpatient | `outpatient_*.csv` | TBD |

## Dependencies

Core: `polars`, `pandas`, `numpy`, `statsmodels`, `matplotlib`, `seaborn`

Optional: `pandera`, `pydantic` (for data validation)

All installed automatically by `setup_environment.py`.
