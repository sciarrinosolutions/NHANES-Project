"""
labCorr/data.py
===============
Data layer for the Lab Correlation tool.

Responsibilities:
  - Load and cache reference_ranges.csv
  - Load XPT files for lab and independent variables
  - Flag rows as high / low / normal using gender-specific bounds
  - Run the correct correlation test based on variable types
  - Return structured results ready for the template and CSV export
"""

import importlib.util
import json
import logging
import os
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

log = logging.getLogger(__name__)


# ── Config loader ─────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_config():
    from django.conf import settings
    spec = importlib.util.spec_from_file_location(
        "labs_config", settings.LABS_CONFIG_PATH
    )
    cfg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cfg)
    return cfg


# ── Reference ranges ──────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def load_reference_ranges() -> pd.DataFrame:
    cfg  = _load_config()
    path = Path(cfg.REFERENCE_RANGES_PATH)
    if not path.exists():
        raise FileNotFoundError(
            f"reference_ranges.csv not found at: {path}\n"
            f"Update REFERENCE_RANGES_PATH in labs_config.py."
        )
    df = pd.read_csv(path)
    log.info("Loaded %d lab reference ranges from %s", len(df), path)
    return df


def get_lab_list() -> list[dict]:
    """Return all lab variables as a list of dicts, enriched with artifact metadata."""
    from varSearch.search_engine import get_variable

    df    = load_reference_ranges()
    labs  = []
    for _, row in df.iterrows():
        col      = row["Variable Code"]
        artifact = get_variable(col) or {}
        labs.append({
            "column_name" : col,
            "nhanes_file" : row["NHANES File"],
            "crr_m_low"   : row["CRR_M_Low"],
            "crr_m_high"  : row["CRR_M_High"],
            "crr_f_low"   : row["CRR_F_Low"],
            "crr_f_high"  : row["CRR_F_High"],
            "units"       : row["Units"],
            "panel"       : row["Panel"],
            "source"      : row["Source"],
            "sas_label"   : artifact.get("sas_label", col),
            "description" : artifact.get("description", ""),
            "data_file"   : artifact.get("data_file", ""),
            "component"   : artifact.get("component", "Laboratory"),
        })
    return labs


def get_lab(column_name: str) -> dict | None:
    labs = get_lab_list()
    return next((l for l in labs if l["column_name"] == column_name), None)


# ── XPT helpers ───────────────────────────────────────────────────────────────

def _get_data_path(session) -> str | None:
    cfg = _load_config()
    if cfg.XPT_DATA_PATH:
        return str(cfg.XPT_DATA_PATH)
    return session.get("nhanes_data_path", "")


def _resolve_xpt(base_path: str, component: str, data_file: str) -> str | None:
    if not base_path or not data_file:
        return None
    # Strip .xpt if already present in data_file
    stem = data_file.replace(".xpt", "")
    candidates = []
    if component:
        candidates.append(os.path.join(base_path, component, f"{stem}.xpt"))
    candidates.append(os.path.join(base_path, f"{stem}.xpt"))
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


def _load_xpt_cols(path: str, columns: list[str]) -> pd.DataFrame | None:
    try:
        import pyreadstat
        keep    = list(set(["SEQN", "RIAGENDR"] + columns))
        df, _   = pyreadstat.read_xport(path, usecols=keep)
        return df
    except Exception as e:
        log.error("XPT load failed %s: %s", path, e)
        return None


# ── Flagging ──────────────────────────────────────────────────────────────────

def flag_rows(df: pd.DataFrame, lab: dict, gender_filter: str) -> pd.DataFrame:
    """
    Add columns:  {col}_high, {col}_low, {col}_normal, {col}_flag (1=high, -1=low, 0=normal)
    Applies gender-specific bounds when RIAGENDR is present.
    gender_filter: 'both' | 'male' | 'female'
    """
    col = lab["column_name"]
    if col not in df.columns:
        return df

    # Apply gender filter
    if gender_filter == "male" and "RIAGENDR" in df.columns:
        df = df[df["RIAGENDR"] == 1].copy()
    elif gender_filter == "female" and "RIAGENDR" in df.columns:
        df = df[df["RIAGENDR"] == 2].copy()

    # Compute per-row bounds (gender-specific if RIAGENDR present)
    if "RIAGENDR" in df.columns:
        low  = np.where(df["RIAGENDR"] == 1, lab["crr_m_low"],  lab["crr_f_low"])
        high = np.where(df["RIAGENDR"] == 1, lab["crr_m_high"], lab["crr_f_high"])
    else:
        low  = np.full(len(df), lab["crr_m_low"])
        high = np.full(len(df), lab["crr_m_high"])

    values = pd.to_numeric(df[col], errors="coerce")

    df[f"{col}_low"]    = ((values < low)  & values.notna()).astype(float)
    df[f"{col}_high"]   = ((values > high) & values.notna()).astype(float)
    df[f"{col}_normal"] = (
        (values >= low) & (values <= high) & values.notna()
    ).astype(float)

    # Set NaN where original was NaN
    mask = values.isna()
    df.loc[mask, [f"{col}_low", f"{col}_high", f"{col}_normal"]] = np.nan

    # Composite flag: 1=high, -1=low, 0=normal, NaN=missing
    flag = pd.Series(np.nan, index=df.index)
    flag[df[f"{col}_normal"] == 1] = 0
    flag[df[f"{col}_high"]   == 1] = 1
    flag[df[f"{col}_low"]    == 1] = -1
    df[f"{col}_flag"] = flag

    return df


# ── Correlation engine ────────────────────────────────────────────────────────

STRENGTH_THRESHOLDS_PB = [
    (0.50, "Strong"),
    (0.30, "Moderate"),
    (0.10, "Weak"),
    (0.00, "Negligible"),
]

STRENGTH_THRESHOLDS_CV = [
    (0.60, "Very Strong"),
    (0.40, "Strong"),
    (0.20, "Moderate"),
    (0.10, "Weak"),
    (0.00, "Negligible"),
]


def _strength_pb(r):
    for threshold, label in STRENGTH_THRESHOLDS_PB:
        if abs(r) >= threshold:
            return label
    return "Negligible"


def _strength_cv(v):
    for threshold, label in STRENGTH_THRESHOLDS_CV:
        if v >= threshold:
            return label
    return "Negligible"


def _cramers_v(a: pd.Series, b: pd.Series) -> float:
    mask = a.notna() & b.notna()
    a, b = a[mask], b[mask]
    if a.nunique() < 2 or b.nunique() < 2:
        return np.nan
    ct   = pd.crosstab(a, b)
    chi2 = stats.chi2_contingency(ct, correction=False)[0]
    n    = ct.values.sum()
    r, k = ct.shape
    denom = n * (min(r, k) - 1)
    return float(np.sqrt(chi2 / denom)) if denom > 0 else np.nan


def _point_biserial(flag: pd.Series, cont: pd.Series):
    mask = flag.notna() & cont.notna()
    f, c = flag[mask].astype(float), cont[mask].astype(float)
    if f.nunique() < 2 or len(f) < 5:
        return np.nan, np.nan
    r, p = stats.pointbiserialr(f, c)
    return float(r), float(p)


def _pearson(a: pd.Series, b: pd.Series):
    mask = a.notna() & b.notna()
    a, b = a[mask].astype(float), b[mask].astype(float)
    if len(a) < 5:
        return np.nan, np.nan
    r, p = stats.pearsonr(a, b)
    return float(r), float(p)


def _spearman(a: pd.Series, b: pd.Series):
    mask = a.notna() & b.notna()
    a, b = a[mask].astype(float), b[mask].astype(float)
    if len(a) < 5:
        return np.nan, np.nan
    r, p = stats.spearmanr(a, b)
    return float(r), float(p)


def _run_one_correlation(
    flag_series: pd.Series,
    lab_series:  pd.Series,
    indep_series: pd.Series,
    indep_var:   dict,
    direction:   str,   # 'high' or 'low'
    min_n:       int,
) -> dict:
    """
    Auto-select and run the appropriate correlation test for one independent var.

    Returns a result dict.
    """
    var_type = indep_var.get("var_type", "continuous")
    col      = indep_var.get("column_name", "")
    sas      = indep_var.get("sas_label", col)

    base = {
        "column_name" : col,
        "sas_label"   : sas,
        "var_type"    : var_type,
        "direction"   : direction,
        "n"           : int(flag_series.notna().sum()),
        "statistic"   : None,
        "p_value"     : None,
        "method"      : None,
        "significant" : False,
        "strength"    : "N/A",
        "direction_r" : None,
        "error"       : None,
    }

    # Filter to high|normal or low|normal rows
    mask         = flag_series.notna() & indep_series.notna()
    flag_clean   = flag_series[mask]
    indep_clean  = indep_series[mask]

    if flag_clean.nunique() < 2 or len(flag_clean) < min_n:
        base["error"] = f"Insufficient data (n={len(flag_clean)})"
        return base

    base["n"] = int(len(flag_clean))

    try:
        if var_type == "continuous":
            # Point-biserial: flag (binary) vs continuous independent
            r, p = _point_biserial(flag_clean, indep_clean)
            if np.isnan(r):
                base["error"] = "Could not compute"
                return base
            base["method"]      = "Point-Biserial r"
            base["statistic"]   = round(r, 4)
            base["p_value"]     = round(p, 4)
            base["significant"] = p < 0.05
            base["strength"]    = _strength_pb(r)
            base["direction_r"] = "positive" if r > 0 else "negative"

        elif var_type in ("ordinal", "binary", "categorical"):
            # Cramer's V: flag vs ordinal/binary/categorical
            v = _cramers_v(flag_clean, indep_clean)
            if np.isnan(v):
                base["error"] = "Could not compute"
                return base
            base["method"]    = "Cramer's V"
            base["statistic"] = round(v, 4)
            base["p_value"]   = None
            base["strength"]  = _strength_cv(v)

        else:
            # Fallback: Spearman for unknown types
            r, p = _spearman(flag_clean, indep_clean)
            if np.isnan(r):
                base["error"] = "Could not compute"
                return base
            base["method"]      = "Spearman r"
            base["statistic"]   = round(r, 4)
            base["p_value"]     = round(p, 4)
            base["significant"] = p < 0.05
            base["strength"]    = _strength_pb(r)
            base["direction_r"] = "positive" if r > 0 else "negative"

    except Exception as e:
        base["error"] = str(e)

    return base


# ── Main analysis runner ──────────────────────────────────────────────────────

def run_correlation_analysis(
    lab_col:        str,
    indep_cols:     list[str],
    session,
    gender_filter:  str = "both",
) -> dict:
    """
    Full pipeline:
      1. Load lab XPT + all independent variable XPTs
      2. Flag rows as high / low / normal
      3. Run correlations for each independent variable x {high, low}
      4. Return structured results

    Returns:
    {
      "lab"        : dict,
      "n_total"    : int,
      "n_high"     : int,
      "n_low"      : int,
      "n_normal"   : int,
      "results"    : [ result_dict, ... ],
      "errors"     : [ str, ... ],
      "gender_filter": str,
    }
    """
    from varSearch.search_engine import get_variable

    cfg       = _load_config()
    min_n     = cfg.MIN_GROUP_SIZE
    data_path = _get_data_path(session)
    lab       = get_lab(lab_col)
    errors    = []

    if not lab:
        return {"error": f"Lab variable {lab_col} not found in reference ranges."}
    if not data_path:
        return {"error": "No XPT data folder configured. Set it on the Export page or in labs_config.py."}

    # ── Step 1: Load lab XPT ──────────────────────────────────────────────────
    lab_xpt = _resolve_xpt(data_path, "Laboratory", lab["nhanes_file"])
    if not lab_xpt:
        return {"error": f"Could not find XPT for {lab_col} ({lab['nhanes_file']})"}

    lab_df = _load_xpt_cols(lab_xpt, [lab_col])
    if lab_df is None:
        return {"error": f"Failed to load {lab_xpt}"}

    # ── Step 2: Flag rows ─────────────────────────────────────────────────────
    lab_df = flag_rows(lab_df, lab, gender_filter)

    n_high   = int((lab_df.get(f"{lab_col}_high",   pd.Series()) == 1).sum())
    n_low    = int((lab_df.get(f"{lab_col}_low",    pd.Series()) == 1).sum())
    n_normal = int((lab_df.get(f"{lab_col}_normal", pd.Series()) == 1).sum())

    # ── Step 3: Load independent variables ───────────────────────────────────
    # Group by XPT file for efficient loading
    xpt_groups: dict[str, list[str]] = {}
    indep_meta: dict[str, dict]      = {}

    for col in indep_cols:
        if col == lab_col:
            continue
        var = get_variable(col)
        if not var:
            errors.append(f"{col}: not found in artifact")
            continue
        indep_meta[col] = var
        xpt_path = _resolve_xpt(
            data_path,
            var.get("component", ""),
            var.get("data_file", ""),
        )
        if not xpt_path:
            errors.append(f"{col}: XPT not found ({var.get('data_file', '?')}.xpt)")
            continue
        xpt_groups.setdefault(xpt_path, []).append(col)

    # Load each XPT once and merge onto lab_df via SEQN
    merged = lab_df[["SEQN", lab_col,
                      f"{lab_col}_high", f"{lab_col}_low",
                      f"{lab_col}_normal", f"{lab_col}_flag"]].copy()

    for xpt_path, cols in xpt_groups.items():
        indep_df = _load_xpt_cols(xpt_path, cols)
        if indep_df is None:
            for c in cols:
                errors.append(f"{c}: failed to load {xpt_path}")
            continue
        keep_cols = ["SEQN"] + [c for c in cols if c in indep_df.columns]
        merged = merged.merge(indep_df[keep_cols], on="SEQN", how="left")

    # ── Step 4: Run correlations ──────────────────────────────────────────────
    results = []

    for col, var in indep_meta.items():
        if col not in merged.columns:
            continue

        indep_series = pd.to_numeric(merged[col], errors="coerce")

        for direction in ("high", "low"):
            flag_col_name = f"{lab_col}_{direction}"
            if flag_col_name not in merged.columns:
                continue

            flag_norm_mask = (
                (merged[flag_col_name] == 1) | (merged[f"{lab_col}_normal"] == 1)
            )
            flag_series = merged.loc[flag_norm_mask, flag_col_name]
            indep_sub   = indep_series[flag_norm_mask]

            result = _run_one_correlation(
                flag_series, merged[lab_col], indep_sub,
                var, direction, min_n
            )
            results.append(result)

    # Sort by abs(statistic) descending
    def sort_key(r):
        s = r.get("statistic")
        return abs(s) if s is not None else 0.0

    results.sort(key=sort_key, reverse=True)

    return {
        "lab"           : lab,
        "n_total"       : int(lab_df[lab_col].notna().sum()),
        "n_high"        : n_high,
        "n_low"         : n_low,
        "n_normal"      : n_normal,
        "results"       : results,
        "errors"        : errors,
        "gender_filter" : gender_filter,
    }
