# -*- coding: utf-8 -*-
"""
Setup script for the PANIC (Drug Intoxication Analysis) project.

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


# =============================================================================
# PACKAGE DEFINITIONS
# =============================================================================

# Core packages - required for basic functionality
CORE_PACKAGES = [
    ("pandas", "DataFrame operations, CSV I/O"),
    ("numpy", "Numerical computing"),
    ("matplotlib", "Visualisations"),
]

# Analysis packages - required for full analysis
ANALYSIS_PACKAGES = [
    ("polars", "Fast processing of large pharmaceutical files (1GB+)"),
    ("scipy", "Statistical tests"),
]

# Validation packages - for data quality and testing
VALIDATION_PACKAGES = [
    ("pandera", "DataFrame schema validation"),
    ("pydantic", "Data validation and settings management"),
    ("pytest", "Testing framework"),
]

# Optional packages - nice to have but not essential
OPTIONAL_PACKAGES = [
    ("seaborn", "Enhanced statistical visualisations"),
    ("statsmodels", "Segmented regression / interrupted time series"),
]


# =============================================================================
# INSTALLATION FUNCTIONS
# =============================================================================

def get_pip_command():
    """Get the appropriate pip command for this environment."""
    pip_args = [sys.executable, "-m", "pip", "install", "--quiet"]
    
    # Check if we're in a virtual environment
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    
    if not in_venv:
        pip_args.append("--user")
    
    return pip_args


def install_package(package_name: str, pip_args: list) -> bool:
    """Install a single package. Returns True if successful."""
    try:
        result = subprocess.run(
            pip_args + [package_name],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return True
        
        # Try with --break-system-packages for newer pip
        result2 = subprocess.run(
            pip_args + ["--break-system-packages", package_name],
            capture_output=True,
            text=True
        )
        return result2.returncode == 0
        
    except Exception:
        return False


def install_packages():
    """Install all required packages."""
    
    print("=" * 60)
    print("INSTALLING PACKAGES")
    print("=" * 60)
    
    pip_args = get_pip_command()
    
    # Check if we're using --user flag
    if "--user" in pip_args:
        print("\nNote: Installing with --user flag (not in virtual environment)")
    print()
    
    # Install core packages
    print("Core packages (required):")
    print("-" * 40)
    for package, description in CORE_PACKAGES:
        print(f"  {package:15} - {description}...", end=" ")
        if install_package(package, pip_args):
            print("OK")
        else:
            print("FAILED")
    
    print()
    
    # Install analysis packages
    print("Analysis packages (required):")
    print("-" * 40)
    for package, description in ANALYSIS_PACKAGES:
        print(f"  {package:15} - {description}...", end=" ")
        if install_package(package, pip_args):
            print("OK")
        else:
            print("FAILED")
    
    print()
    
    # Install validation packages
    print("Validation & testing packages:")
    print("-" * 40)
    for package, description in VALIDATION_PACKAGES:
        print(f"  {package:15} - {description}...", end=" ")
        if install_package(package, pip_args):
            print("OK")
        else:
            print("FAILED")
    
    print()
    
    # Install optional packages
    print("Optional packages (nice to have):")
    print("-" * 40)
    for package, description in OPTIONAL_PACKAGES:
        print(f"  {package:15} - {description}...", end=" ")
        if install_package(package, pip_args):
            print("OK")
        else:
            print("skipped")
    
    print()


def verify_installation():
    """Verify that all required packages can be imported."""
    
    print("=" * 60)
    print("VERIFYING INSTALLATION")
    print("=" * 60)
    print()
    
    packages_to_check = [
        # (import_name, display_name, required)
        # Core
        ("pandas", "pandas", True),
        ("numpy", "numpy", True),
        ("matplotlib.pyplot", "matplotlib", True),
        # Analysis
        ("polars", "polars", True),
        ("scipy", "scipy", True),
        # Validation
        ("pandera", "pandera", True),
        ("pydantic", "pydantic", True),
        ("pytest", "pytest", True),
        # Optional
        ("seaborn", "seaborn", False),
        ("statsmodels", "statsmodels", False),
    ]
    
    all_required_ok = True
    
    print("Package               Version      Status")
    print("-" * 50)
    
    for import_name, display_name, required in packages_to_check:
        try:
            # Import the package
            if "." in import_name:
                main_pkg = import_name.split(".")[0]
            else:
                main_pkg = import_name
            
            mod = __import__(main_pkg)
            version = getattr(mod, "__version__", "?")
            
            req_marker = "*" if required else " "
            print(f"  {display_name:18} {version:12} OK {req_marker}")
            
        except ImportError as e:
            req_marker = "*" if required else " "
            if required:
                print(f"  {display_name:18} {'--':12} MISSING {req_marker}")
                all_required_ok = False
            else:
                print(f"  {display_name:18} {'--':12} not installed")
    
    print()
    print("  * = required package")
    print()
    
    return all_required_ok


def setup_python_path():
    """Add the project root to Python path."""
    
    print("=" * 60)
    print("SETTING UP PYTHON PATH")
    print("=" * 60)
    print()
    
    # Get the project root (where this script is located)
    project_root = Path(__file__).parent.resolve()
    
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
        print(f"  Added to Python path: {project_root}")
    else:
        print(f"  Already in path: {project_root}")
    
    print()
    print("To make this permanent in Spyder:")
    print("  1. Go to: Tools → PYTHONPATH manager")
    print(f"  2. Add: {project_root}")
    print()


def test_project_imports():
    """Test that project modules can be imported."""
    
    print("=" * 60)
    print("TESTING PROJECT IMPORTS")
    print("=" * 60)
    print()
    
    # Ensure project root is in path
    project_root = Path(__file__).parent.resolve()
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    tests = [
        ("intox_analysis.data.schemas", "ICD code classification"),
        ("intox_analysis.data.generators", "Synthetic data generation"),
        ("intox_analysis.data.residence", "Urban/rural classification"),
        ("intox_analysis.data.pharmaceutical", "Pharmaceutical processing"),
        ("intox_analysis.analysis.trends", "Trend analysis"),
    ]
    
    all_ok = True
    for module_name, description in tests:
        try:
            __import__(module_name)
            print(f"  ✓ {description}")
        except ImportError as e:
            print(f"  ✗ {description}: {e}")
            all_ok = False
    
    print()
    return all_ok


def print_summary():
    """Print summary and next steps."""
    
    print("=" * 60)
    print("SETUP COMPLETE")
    print("=" * 60)
    print("""
Libraries installed:
  Core:        pandas, numpy, matplotlib
  Analysis:    polars, scipy
  Validation:  pandera, pydantic, pytest
  Optional:    seaborn, statsmodels

Pipeline scripts (run in order):
  1. notebooks/00_generate_synthetic_data.py  - Create test data
  2. notebooks/03_intoxication_trends.py      - Drug class trends
  3. notebooks/04_stratified_analysis.py      - Demographics
  4. notebooks/05_prescription_linkage.py     - Pharma linkage
  5. notebooks/06_generate_report.py          - Compile HTML report

Data folders:
  - data/raw/      <- Place your VDI CSV exports here
  - data/lookups/  <- ISTAT FUA lookup (can commit to GitHub)
  - outputs/       <- Generated figures, tables, reports

GitHub: https://github.com/andredot/PANIC
""")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print()
    print("╔" + "═" * 58 + "╗")
    print("║     PANIC - Drug Intoxication Analysis Setup Wizard      ║")
    print("╚" + "═" * 58 + "╝")
    print()
    
    install_packages()
    
    if verify_installation():
        setup_python_path()
        if test_project_imports():
            print_summary()
        else:
            print("\n⚠ Some project imports failed.")
            print("  Make sure you're running this from the project root.")
    else:
        print("\n⚠ Some required packages are missing.")
        print("  Try installing them manually with:")
        print("    pip install pandas numpy matplotlib polars scipy --user")
