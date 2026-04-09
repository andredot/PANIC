# Setting Up the Project in Spyder

## Step 1: Open the Project Folder

In Spyder, go to **Projects → New Project → Existing directory** and select this folder (`intox_lombardy_spyder`).

Alternatively, you can simply open files directly from **File → Open** and navigate to this folder.

## Step 2: Set the Working Directory

This is important! Spyder needs to know where your project root is.

Go to the **Files** pane (usually on the right side), navigate to this folder, right-click and select **"Set as current working directory"**.

Or in the IPython console at the bottom, type:
```python
import os
os.chdir(r"C:\path\to\intox_lombardy_spyder")  # Replace with your actual path
```

## Step 3: Install Required Packages

Open the **Anaconda Prompt** (or terminal) and run:

```bash
pip install polars pandas numpy statsmodels scipy matplotlib seaborn
```

If you're using Anaconda, you might prefer:
```bash
conda install polars pandas numpy statsmodels scipy matplotlib seaborn -c conda-forge
```

## Step 4: Verify Setup

Open `notebooks/00_verify_setup.py` in Spyder and run it (F5 or the green play button). It will check that everything is working.

## Folder Structure

```
intox_lombardy_spyder/
│
├── SETUP_SPYDER.md          # This file
├── config.py                # Project configuration (paths, constants)
│
├── intox_analysis/          # Main analysis code
│   ├── __init__.py
│   └── data/
│       ├── __init__.py
│       ├── schemas.py       # ED data schemas & ICD classification
│       └── pharmaceutical.py # Pharma data processing (Polars)
│
├── notebooks/               # Analysis scripts (run these!)
│   ├── 00_verify_setup.py   # Check your installation
│   ├── 01_load_ed_data.py   # Load and explore ED data
│   └── 02_load_pharma_data.py # Load pharmaceutical data
│
├── data/
│   ├── raw/                 # Put your CSV exports here
│   └── processed/           # Intermediate files
│
└── outputs/
    ├── figures/             # Generated plots
    └── tables/              # Generated tables
```

## Step 5: Place Your Data

Copy your data extracts into the `data/raw/` folder:
- ED presentation CSVs
- Pharmaceutical CSVs (one per year is fine)

Then update the paths in `config.py` to match your filenames.

## Getting Help

If you get import errors like "No module named 'intox_analysis'", make sure:
1. Your working directory is set to this folder
2. You've run: `import sys; sys.path.insert(0, '.')` 

This is handled automatically in the notebook scripts.
