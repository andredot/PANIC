# -*- coding: utf-8 -*-
"""
00_profile_raw_data.py
======================

Read-only structural profile of the real raw extracts in data/raw/.

Answers the open [CONFIRM] items from the audit without exporting any
patient-level data:
  - exact column headers, separator and encoding of each file
  - ED: esito codebook, ICD coding system per year, T-code length / intent
    distribution, monthly completeness (is 2025 a full year?)
  - FUR: DDD column name and number format, date format, monthly
    completeness, ATC N05/N06 volume, prescriber / sex codes
  - cod_sindromi_mental.txt: first lines (code list, no patient data)

Output: printed to console AND written to outputs/profile/raw_profile.txt.
Only aggregate counts are reported; cells below SMALL_CELL are suppressed,
so the output file can be shared outside the VDI.

pandas only. Files are read in chunks (CHUNK_ROWS) with every column as
string, so memory stays bounded on the ~1 GB extracts. Expect a few
minutes per file.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import pandas as pd

from config import DATA_DIR, OUTPUT_DIR

# =============================================================================
# SETTINGS
# =============================================================================

ED_FILES = [DATA_DIR / "PS2017_2025.csv", DATA_DIR / "ed_presentations.csv"]
FUR_FILES = sorted(DATA_DIR.glob("FUR_*.csv"))
MENTAL_CODES_FILE = DATA_DIR / "cod_sindromi_mental.txt"

CHUNK_ROWS = 500_000     # rows per chunk; lower it if memory is tight
SMALL_CELL = 10          # suppress counts below this
TOP_N = 40               # rows shown for value tables

MISSING_MARKERS = ["", "_", "?", "-", "DATO NON APPLICABILE", "NON APPLICABILE", "DATO MANCANTE"]

OUT_DIR = OUTPUT_DIR / "profile"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = OUT_DIR / "raw_profile.txt"

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)
pd.set_option("display.max_colwidth", 60)

_lines: list[str] = []


def out(text: str = "") -> None:
    print(text)
    _lines.append(text)


def section(title: str) -> None:
    out("\n" + "=" * 78)
    out(title)
    out("=" * 78)


def show(counts: pd.Series | pd.DataFrame, n: int = TOP_N, sort: bool = True) -> None:
    """Print a count table with small cells suppressed."""
    if isinstance(counts, pd.Series):
        counts = counts.rename("n").to_frame()
    if counts.empty:
        out("  (none)")
        return
    if sort:
        counts = counts.sort_values(counts.columns[0], ascending=False)
    shown = counts.head(n).astype("Int64").mask(lambda d: d < SMALL_CELL).astype(object)
    shown = shown.where(shown.notna(), f"<{SMALL_CELL}")
    out(shown.to_string())
    if len(counts) > n:
        out(f"  ... {len(counts) - n} more rows")


# =============================================================================
# CHUNKED COUNTING
# =============================================================================

class Tally:
    """Accumulates value counts across chunks, keyed by table name."""

    def __init__(self) -> None:
        self.tables: dict[str, pd.Series | pd.DataFrame] = {}

    def add(self, name: str, counts: pd.Series | pd.DataFrame) -> None:
        if name in self.tables:
            self.tables[name] = self.tables[name].add(counts, fill_value=0)
        else:
            self.tables[name] = counts

    def get(self, name: str) -> pd.Series:
        return self.tables.get(name, pd.Series(dtype="int64"))


class DistinctCounter:
    """Counts distinct values via 64-bit hashes (memory-light, collisions negligible)."""

    def __init__(self) -> None:
        self.seen = np.empty(0, dtype=np.uint64)

    def add(self, values: pd.Series) -> None:
        h = pd.util.hash_pandas_object(values.dropna(), index=False).to_numpy()
        self.seen = np.unique(np.concatenate([self.seen, np.unique(h)]))

    def __len__(self) -> int:
        return len(self.seen)


# =============================================================================
# FILE SNIFFING / READING
# =============================================================================

def sniff(path: Path) -> dict:
    """Detect encoding and separator from the first line."""
    raw = path.open("rb").read(64_000)
    if raw.startswith(b"\xef\xbb\xbf"):
        encoding = "utf-8-sig"
    else:
        try:
            raw.decode("utf-8")
            encoding = "utf-8"
        except UnicodeDecodeError:
            encoding = "latin-1"
    first = raw.split(b"\n", 1)[0].decode(encoding, errors="replace").lstrip("﻿").rstrip("\r")
    sep = max([";", ",", "\t", "|"], key=first.count)
    return {"encoding": encoding, "sep": sep, "header": first.split(sep)}


def read_chunks(path: Path, info: dict):
    return pd.read_csv(
        path,
        sep=info["sep"],
        encoding=info["encoding"],
        encoding_errors="replace",
        dtype=str,
        keep_default_na=False,   # keep markers as text; we count them ourselves
        chunksize=CHUNK_ROWS,
        on_bad_lines="warn",
    )


def describe_file(path: Path) -> dict:
    info = sniff(path)
    out(f"\nFile: {path.name}  ({path.stat().st_size / 1e6:,.0f} MB)")
    out(f"  encoding: {info['encoding']}   separator: {info['sep']!r}")
    out(f"  {len(info['header'])} columns:")
    for c in info["header"]:
        out(f"    - {c!r}")
    return info


def find_col(cols, *needles: str, exclude: str | None = None) -> str | None:
    for c in cols:
        low = c.lower()
        if all(n in low for n in needles) and not (exclude and exclude in low):
            return c
    return None


def is_missing(s: pd.Series) -> pd.Series:
    return s.str.strip().isin(MISSING_MARKERS)


def shape_of(s: pd.Series) -> pd.Series:
    """Replace digits with 9 so formats are visible without exposing values."""
    return s.str.strip().str.replace(r"\d", "9", regex=True)


def report_missing(tally: Tally, rows: int, cols) -> None:
    out(f"  rows: {rows:,}")
    out("  missing / marker share per column:")
    miss = tally.get("missing")
    for c in cols:
        out(f"    {c:<45} {100 * miss.get(c, 0) / max(rows, 1):6.2f}%")


# =============================================================================
# ED PROFILE
# =============================================================================

def profile_ed(path: Path) -> None:
    section(f"ED DATA: {path.name}")
    info = describe_file(path)
    cols = info["header"]

    ym = find_col(cols, "annomese") or find_col(cols, "anno")
    dx_cols = [c for c in (find_col(cols, "cod diagnosi", exclude="second"),
                           find_col(cols, "cod diagnosi", "second")) if c]
    esito = find_col(cols, "codice esito")
    esito_d = find_col(cols, "descrizione esito")
    pid = find_col(cols, "microbio")
    out(f"\n  detected: year_month={ym!r} diagnoses={dx_cols} esito={esito!r} patient={pid!r}")

    t, rows, patients = Tally(), 0, DistinctCounter()
    for chunk in read_chunks(path, info):
        rows += len(chunk)
        t.add("missing", chunk.apply(is_missing).sum())
        year = chunk[ym].str.replace(r"\D", "", regex=True).str[:4] if ym else pd.Series("all", index=chunk.index)

        if ym:
            t.add("ym_shape", shape_of(chunk[ym]).rename("format").value_counts())
            t.add("monthly", chunk[ym].str.replace(r"\D", "", regex=True).str[:6].rename("year_month").value_counts())
        if esito:
            keys = [esito] + ([esito_d] if esito_d else [])
            t.add("esito", chunk.groupby(keys).size())
        if pid:
            patients.add(chunk[pid])

        for dx in dx_cols:
            code = chunk[dx].str.replace(r"[.\s]", "", regex=True).str.upper()
            t10 = code.str.match(r"T(3[6-9]|4\d|50)")
            i9 = code.str.match(r"9(6\d|7\d)")
            flags = pd.DataFrame({
                "rows": 1,
                "missing": is_missing(chunk[dx]),
                "icd10_like": code.str.match(r"[A-Z]\d\d"),
                "icd9_like": code.str.match(r"(\d{3}|V\d\d|E\d{3})"),
                "T36_T50": t10,
                "960_979": i9,
                "F_codes": code.str.match(r"F\d"),
            }).astype(int)
            t.add(f"{dx}|by_year", flags.groupby(year.rename("year")).sum())

            tc = code[t10].rename("code")
            t.add(f"{dx}|t_len", tc.str.len().rename("length").value_counts())
            t.add(f"{dx}|t_shape", shape_of(tc).value_counts())
            t.add(f"{dx}|t_sub", tc.str[:4].rename("subcategory").value_counts())
            t.add(f"{dx}|intent", tc[tc.str.len() >= 6].str[5].rename("intent").value_counts())
            t.add(f"{dx}|i9_sub", code[i9].str[:4].rename("prefix").value_counts())

    report_missing(t, rows, cols)
    if pid:
        out(f"  distinct patients: {len(patients):,}")

    if ym:
        out(f"\n  Format of {ym!r} (digits -> 9):")
        show(t.get("ym_shape"), n=10)
        out("\n  Presentations per month (all diagnoses) - check for gaps / partial 2025:")
        show(t.get("monthly").sort_index(), n=200, sort=False)

    if esito:
        out("\n  Esito codebook (code x description):")
        show(t.get("esito"))

    for dx in dx_cols:
        out(f"\n  Diagnosis column {dx!r} - coding system by year:")
        show(t.get(f"{dx}|by_year").sort_index(), n=20, sort=False)
        out("\n  Length of T36-T50 codes (dots removed) - 7 = full ICD-10-CM:")
        show(t.get(f"{dx}|t_len").sort_index(), sort=False)
        out("\n  T36-T50 code shapes (digits -> 9):")
        show(t.get(f"{dx}|t_shape"), n=15)
        out("\n  T36-T50 by 4-char subcategory (e.g. T424 = benzodiazepines):")
        show(t.get(f"{dx}|t_sub"), n=80)
        out("\n  Intent character (6th char of 7-char ICD-10-CM T-codes; 1-6):")
        show(t.get(f"{dx}|intent").sort_index(), sort=False)
        out("\n  960-979 codes (if any) by 4-char prefix:")
        show(t.get(f"{dx}|i9_sub"))


# =============================================================================
# FUR PROFILE
# =============================================================================

def profile_fur(path: Path) -> None:
    section(f"FUR DATA: {path.name}")
    info = describe_file(path)
    cols = info["header"]

    ddd_cols = [c for c in cols if "ddd" in c.lower() or "dose" in c.lower()]
    date_cols = [c for c in cols if "data" in c.lower()]
    disp_date = find_col(cols, "erogazione") or (date_cols[0] if date_cols else None)
    atc = find_col(cols, "cod atc")
    pid = find_col(cols, "microbio")
    code_cols = [c for c in (find_col(cols, "cod tipo medico"), find_col(cols, "desc tipo medico"),
                             find_col(cols, "sesso")) if c]
    out(f"\n  detected: DDD-like={ddd_cols or 'NONE FOUND'} dates={date_cols} atc={atc!r}")

    t, rows, patients = Tally(), 0, DistinctCounter()
    for chunk in read_chunks(path, info):
        rows += len(chunk)
        t.add("missing", chunk.apply(is_missing).sum())
        for c in ddd_cols + date_cols:
            t.add(f"shape|{c}", shape_of(chunk[c]).value_counts())
        if disp_date:
            # Month key that works for YYYY/MM/DD, YYYY-MM-DD and DD/MM/YYYY
            d = pd.to_datetime(chunk[disp_date].str[:10], errors="coerce",
                               format="mixed", dayfirst=False)
            t.add("monthly", d.dt.strftime("%Y-%m").fillna("unparsed").rename("year_month").value_counts())
        if atc:
            a = chunk[atc].str.strip().str.upper()
            t.add("atc_len", a.str.len().rename("length").value_counts())
            t.add("atc5", a[a.str.match(r"(N05|N06|N02A|N07B)")].str[:5].rename("atc5").value_counts())
        for c in code_cols:
            t.add(f"values|{c}", chunk[c].value_counts())
        if pid:
            patients.add(chunk[pid])

    report_missing(t, rows, cols)
    if pid:
        out(f"  distinct patients: {len(patients):,}")

    for c in ddd_cols + date_cols:
        out(f"\n  Value shapes of {c!r} (digits -> 9; check date order / decimal separator):")
        show(t.get(f"shape|{c}"), n=10)
    if disp_date:
        out(f"\n  Dispensations per month by {disp_date!r}:")
        show(t.get("monthly").sort_index(), n=60, sort=False)
    if atc:
        out("\n  ATC code length:")
        show(t.get("atc_len").sort_index(), sort=False)
        out("\n  N05 / N06 / N02A / N07B volume by 5-char ATC:")
        show(t.get("atc5"))
    for c in code_cols:
        out(f"\n  Values of {c!r}:")
        show(t.get(f"values|{c}"), n=20)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    section("RAW DATA PROFILE")
    out(f"Data directory: {DATA_DIR}")
    for f in sorted(DATA_DIR.iterdir()):
        out(f"  {f.name:<30} {f.stat().st_size / 1e6:>10,.1f} MB")

    if MENTAL_CODES_FILE.exists():
        section(f"LOOKUP: {MENTAL_CODES_FILE.name}")
        text = MENTAL_CODES_FILE.read_bytes().decode("utf-8", errors="replace").splitlines()
        out(f"  {len(text)} lines; first 40:")
        for line in text[:40]:
            out(f"    {line}")

    for f in ED_FILES:
        if f.exists():
            profile_ed(f)

    for f in FUR_FILES:
        profile_fur(f)

    OUT_FILE.write_text("\n".join(_lines), encoding="utf-8")
    print(f"\nSaved profile to: {OUT_FILE}")
