# -*- coding: utf-8 -*-
"""
00_verify_setup.py
==================

Run this script first to verify your Spyder setup is working correctly.
It checks that all required packages are installed and that the project
structure is correct.

To run: Press F5 or click the green "Run" button in Spyder.
"""

import sys
from pathlib import Path

print("=" * 70)
print("LOMBARDY DRUG INTOXICATION ANALYSIS - SETUP VERIFICATION")
print("=" * 70)
print()

# Step 1: Check Python version
print("1. Python Version")
print(f"   Python {sys.version}")
print()

# Step 2: Add project to path (important for imports to work)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
print(f"2. Project Root: {project_root}")
print(f"   Added to Python path: ✓")
print()

# Step 3: Check required packages
print("3. Required Packages")
packages = {
    "polars": "polars",
    "pandas": "pandas", 
    "numpy": "numpy",
    "matplotlib": "matplotlib.pyplot",
    "scipy": "scipy",
}

missing = []
for name, import_name in packages.items():
    try:
        __import__(import_name.split(".")[0])
        print(f"   ✓ {name}")
    except ImportError:
        print(f"   ✗ {name} - NOT INSTALLED")
        missing.append(name)

if missing:
    print()
    print("   To install missing packages, run in Anaconda Prompt:")
    print(f"   pip install {' '.join(missing)}")
print()

# Step 4: Check project modules
print("4. Project Modules")
try:
    from intox_analysis.data import schemas
    print("   ✓ intox_analysis.data.schemas")
except ImportError as e:
    print(f"   ✗ intox_analysis.data.schemas - {e}")

try:
    from intox_analysis.data import pharmaceutical
    print("   ✓ intox_analysis.data.pharmaceutical")
except ImportError as e:
    print(f"   ✗ intox_analysis.data.pharmaceutical - {e}")
print()

# Step 5: Test ICD classification
print("5. Quick Function Test")
try:
    from intox_analysis.data.schemas import classify_drug_intoxication
    
    result = classify_drug_intoxication("T424X2A")
    if result["is_intoxication"] and result["drug_class"] == "benzodiazepine":
        print("   ✓ ICD classification working correctly")
    else:
        print("   ✗ ICD classification returned unexpected result")
        print(f"     Got: {result}")
except Exception as e:
    print(f"   ✗ Error testing classification: {e}")
print()

# Step 6: Check directory structure
print("6. Directory Structure")
dirs_to_check = [
    project_root / "data" / "raw",
    project_root / "data" / "processed",
    project_root / "outputs" / "figures",
    project_root / "outputs" / "tables",
]
for d in dirs_to_check:
    status = "✓" if d.exists() else "✗ (will be created)"
    print(f"   {status} {d.relative_to(project_root)}")
    if not d.exists():
        d.mkdir(parents=True, exist_ok=True)
print()

# Step 7: Check for data files
print("7. Data Files in data/raw/")
data_dir = project_root / "data" / "raw"
if data_dir.exists():
    files = list(data_dir.glob("*"))
    if files:
        for f in files[:10]:
            size_mb = f.stat().st_size / (1024 * 1024) if f.is_file() else 0
            print(f"   • {f.name} ({size_mb:.1f} MB)")
        if len(files) > 10:
            print(f"   ... and {len(files) - 10} more files")
    else:
        print("   (no files yet - place your data extracts here)")
else:
    print("   (directory doesn't exist yet)")
print()

# Summary
print("=" * 70)
if not missing:
    print("✓ Setup looks good! You're ready to start the analysis.")
else:
    print("⚠ Some packages are missing. Install them before proceeding.")
print("=" * 70)
