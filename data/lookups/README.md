# Data Lookups

This folder contains **public reference data** that CAN be committed to GitHub.

## Files

### `istat_fua_comuni.csv`

ISTAT FUA (Functional Urban Areas) classification for Italian municipalities.

**Source:** ISTAT - Aggiornamento delle FUA (Aree Funzionali Urbane)
- URL: https://www.istat.it/comunicato-stampa/aggiornamento-delle-fua-aree-funzionali-urbane/
- Portal: https://situas.istat.it/web/#/home

**Required columns:**
- Municipality name (e.g., "Comune", "Municipality")
- City classification (e.g., "Città (City/Greater City) 2021")

**Classification logic:**
- **URBAN**: Municipality has a City/Greater City value (not "No City/Città")
- **RURAL**: Municipality has "No City/Città" or is missing

**How to obtain:**
1. Go to https://situas.istat.it/web/#/home
2. Navigate to "Unità territoriali" → "Unità statistiche" → "Zone urbane funzionali"
3. Download the composition of Cities 2021
4. Save as `istat_fua_comuni.csv` in this folder

## Note

This is public ISTAT data released under Italian open data license.
Patient data should NEVER be placed in this folder.
