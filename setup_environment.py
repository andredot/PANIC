"""
Setup script for the Lombardy Drug Intoxication Analysis project.

Run this script FIRST after opening the project in Spyder to:
1. Install all required packages
2. Verify the installation
3. Set up the Python path

Instructions:
1. Open this file in Spyder
2. Press F5 (or click Run) to execute
3. Follow any prompts in the console

Author: Generated for VDI environment
"""

import subprocess
import sys
from pathlib import Path


def install_packages():
    """Install required packages using pip."""
    
    packages = [
        "polars",           # Fast DataFrame library for large files
        "pandas",           # Standard DataFrame library
        "numpy",            # Numerical computing
        "statsmodels",      # Statistical models (segmented regression)
        "scipy",            # Scientific computing
        "matplotlib",       # Plotting
        "seaborn",          # Statistical visualisation
        "openpyxl",         # Excel file support
        "xlsxwriter",       # Excel writing with formatting
    ]
    
    # Optional packages (install if available)
    optional_packages = [
        "pandera",          # DataFrame validation
        "pydantic",         # Data validation
        "pytest",           # Testing framework
    ]
    
    print("=" * 60)
    print("INSTALLING REQUIRED PACKAGES")
    print("=" * 60)
    print()
    
    # Check if we need --break-system-packages flag (for system Python)
    # This is common in VDI environments
    pip_args = [sys.executable, "-m", "pip", "install", "--quiet"]
    
    # Try to detect if we're in a virtual environment
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    
    if not in_venv:
        print("Note: Not in a virtual environment. Using --user flag.")
        pip_args.append("--user")
    
    # Install required packages
    for package in packages:
        print(f"Installing {package}...", end=" ")
        try:
            result = subprocess.run(
                pip_args + [package],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print("OK")
            else:
                # Try with --break-system-packages for newer pip
                result2 = subprocess.run(
                    pip_args + ["--break-system-packages", package],
                    capture_output=True,
                    text=True
                )
                if result2.returncode == 0:
                    print("OK")
                else:
                    print(f"FAILED: {result.stderr[:100]}")
        except Exception as e:
            print(f"ERROR: {e}")
    
    print()
    print("Installing optional packages...")
    for package in optional_packages:
        print(f"Installing {package}...", end=" ")
        try:
            result = subprocess.run(
                pip_args + [package],
                capture_output=True,
                text=True
            )
            print("OK" if result.returncode == 0 else "skipped")
        except:
            print("skipped")
    
    print()


def verify_installation():
    """Verify that all required packages can be imported."""
    
    print("=" * 60)
    print("VERIFYING INSTALLATION")
    print("=" * 60)
    print()
    
    packages_to_check = [
        ("polars", "pl"),
        ("pandas", "pd"),
        ("numpy", "np"),
        ("statsmodels", "sm"),
        ("matplotlib.pyplot", "plt"),
        ("seaborn", "sns"),
    ]
    
    all_ok = True
    for package, alias in packages_to_check:
        try:
            exec(f"import {package} as {alias}")
            # Get version if available
            main_pkg = package.split(".")[0]
            mod = __import__(main_pkg)
            version = getattr(mod, "__version__", "unknown")
            print(f"  {package}: OK (v{version})")
        except ImportError as e:
            print(f"  {package}: FAILED - {e}")
            all_ok = False
    
    print()
    return all_ok


def setup_python_path():
    """Add the src directory to Python path."""
    
    print("=" * 60)
    print("SETTING UP PYTHON PATH")
    print("=" * 60)
    print()
    
    # Get the project root (where this script is located)
    project_root = Path(__file__).parent.resolve()
    src_path = project_root / "src"
    
    if src_path.exists():
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))
            print(f"  Added to Python path: {src_path}")
        else:
            print(f"  Already in path: {src_path}")
    else:
        print(f"  WARNING: src directory not found at {src_path}")
    
    print()
    print("To make this permanent in Spyder:")
    print("  1. Go to: Tools → Preferences → Python interpreter")
    print("  2. Under 'Use the following Python interpreter', check the path")
    print("  3. Go to: Tools → PYTHONPATH manager")
    print(f"  4. Add: {src_path}")
    print()


def test_project_imports():
    """Test that project modules can be imported."""
    
    print("=" * 60)
    print("TESTING PROJECT IMPORTS")
    print("=" * 60)
    print()
    
    # First, make sure src is in path
    project_root = Path(__file__).parent.resolve()
    src_path = project_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    
    try:
        from intox_analysis.data.pharmaceutical import classify_atc_code
        result = classify_atc_code("N05BA12")
        print(f"  classify_atc_code('N05BA12'): {result['drug_class']}")
        print("  Pharmaceutical module: OK")
    except Exception as e:
        print(f"  Pharmaceutical module: FAILED - {e}")
    
    try:
        from intox_analysis.data.pharmaceutical import generate_synthetic_pharmaceutical_data
        df = generate_synthetic_pharmaceutical_data(n_records=100, n_patients=20)
        print(f"  Generated synthetic data: {len(df)} records")
        print("  Synthetic data generator: OK")
    except Exception as e:
        print(f"  Synthetic data generator: FAILED - {e}")
    
    print()


def print_quick_start():
    """Print quick start guide."""
    
    print("=" * 60)
    print("SETUP COMPLETE - QUICK START GUIDE")
    print("=" * 60)
    print("""
Next steps:

1. OPEN the '01_getting_started.py' script in the notebooks folder
   This will walk you through loading and exploring the data.

2. PLACE YOUR DATA in the 'data/raw/' folder:
   - ED presentations CSV
   - Pharmaceutical CSV files (one per year)
   - SDO data (when available)
   - Outpatient data (when available)

3. FOLDER STRUCTURE:
   intox_lombardy/
   ├── data/
   │   ├── raw/           <- Put your VDI extracts here
   │   └── processed/     <- Cleaned data will go here
   ├── src/
   │   └── intox_analysis/
   │       └── data/      <- Analysis code modules
   ├── notebooks/         <- Analysis scripts (run these!)
   ├── outputs/
   │   ├── figures/       <- Generated plots
   │   └── tables/        <- Generated tables
   └── tests/             <- Unit tests

4. KEY SCRIPTS:
   - notebooks/01_getting_started.py   <- Start here!
   - notebooks/02_ed_exploration.py    <- ED data analysis
   - notebooks/03_pharma_analysis.py   <- Pharmaceutical trends

For help, see README.md
""")


if __name__ == "__main__":
    print()
    print("╔" + "═" * 58 + "╗")
    print("║  LOMBARDY DRUG INTOXICATION ANALYSIS - SETUP WIZARD     ║")
    print("╚" + "═" * 58 + "╝")
    print()
    
    install_packages()
    
    if verify_installation():
        setup_python_path()
        test_project_imports()
        print_quick_start()
    else:
        print("Some packages failed to install. Please install them manually")
        print("and re-run this script.")
