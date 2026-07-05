"""
export/views.py
===============
Clean & Export feature.

Session keys used:
    nhanes_data_path        : str  -- base path to XPT data folder
    export_settings         : dict -- { column_name: { ... per-var settings } }

Per-variable settings schema:
    {
        "custom_header"    : str,          # defaults to column_name
        "sentinels"        : {code: repl}, # code->replacement (NaN if repl is "")
        "recode_binary"    : bool,         # True = map 1->0, 2->1
        "include"          : bool,         # False = skip this var
    }
"""

import json
import logging
import os
from io import StringIO

import pandas as pd

from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from varSearch.models import Favorite
from varSearch.search_engine import get_variable

log = logging.getLogger(__name__)

# ── Sentinel replacement sentinel: empty string means pd.NA ──────────────────
_NA = ""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _default_settings(variable: dict) -> dict:
    """Build default per-variable export settings from artifact data."""
    col  = variable.get("column_name", "")
    sv   = variable.get("sentinel_values", {})
    if isinstance(sv, str):
        try:
            sv = json.loads(sv)
        except Exception:
            sv = {}

    # Default: every sentinel maps to NaN (empty string replacement)
    sentinels = {code: _NA for code in sv.keys()}

    return {
        "custom_header" : col,
        "sentinels"     : sentinels,
        "recode_binary" : variable.get("var_type") == "binary",
        "include"       : True,
    }


def _get_export_settings(request) -> dict:
    return request.session.get("export_settings", {})


def _save_export_settings(request, settings: dict):
    request.session["export_settings"] = settings
    request.session.modified = True


def _resolve_xpt_path(base_path: str, component: str, data_file: str) -> str | None:
    """
    Resolve the XPT file path given the base data folder.
    Tries: base/Component/FILE.xpt  then  base/FILE.xpt
    """
    if not base_path or not data_file:
        return None

    candidates = []
    if component:
        candidates.append(os.path.join(base_path, component, f"{data_file}.xpt"))
    candidates.append(os.path.join(base_path, f"{data_file}.xpt"))

    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def _load_xpt(path: str, columns: list[str]) -> pd.DataFrame | None:
    """Load an XPT file, returning only the requested columns + SEQN."""
    try:
        import pyreadstat
        keep = list(set(["SEQN"] + columns))
        df, _ = pyreadstat.read_xport(path, usecols=keep)
        return df
    except Exception as e:
        log.error("Failed to load XPT %s: %s", path, e)
        return None


# ── Views ─────────────────────────────────────────────────────────────────────

def set_data_path(request):
    """POST: save the XPT base folder path to the session."""
    if request.method == "POST":
        path = request.POST.get("data_path", "").strip()
        if path and os.path.isdir(path):
            request.session["nhanes_data_path"] = path
            return JsonResponse({"ok": True, "path": path})
        return JsonResponse({"ok": False, "error": "Path does not exist or is not a directory."}, status=400)
    return JsonResponse({"ok": False}, status=405)


def export_page(request):
    """
    Main Clean & Export page.
    Loads all favorited variables, merges with saved session settings,
    and renders the configuration table.
    """
    favorites    = Favorite.objects.all()
    data_path    = request.session.get("nhanes_data_path", "")
    saved        = _get_export_settings(request)

    rows = []
    for fav in favorites:
        variable = get_variable(fav.column_name)
        if variable is None:
            continue

        # Merge defaults with any saved overrides
        defaults = _default_settings(variable)
        saved_var = saved.get(fav.column_name, {})
        settings  = {**defaults, **saved_var}

        # Check if XPT file is resolvable
        xpt_path = _resolve_xpt_path(
            data_path,
            variable.get("component", ""),
            variable.get("data_file", ""),
        )

        rows.append({
            "variable"  : variable,
            "settings"  : settings,
            "xpt_found" : bool(xpt_path),
            "xpt_path"  : xpt_path or "",
        })

    return render(request, "export/export_page.html", {
        "rows"       : rows,
        "data_path"  : data_path,
        "total"      : len(rows),
        "included"   : sum(1 for r in rows if r["settings"]["include"]),
        "xpt_missing": sum(1 for r in rows if not r["xpt_found"]),
    })


@require_POST
def save_settings(request):
    """
    AJAX POST: receive the full settings payload from the export page
    and persist it to the session.

    Expected JSON body:
    {
      "SEQN": { ... },
      "LBXGH": {
          "custom_header" : "ha1c",
          "sentinels"     : {"0": ""},
          "recode_binary" : false,
          "include"       : true
      },
      ...
    }
    """
    try:
        payload = json.loads(request.body)
    except Exception:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)

    _save_export_settings(request, payload)
    return JsonResponse({"ok": True, "saved": len(payload)})


@require_POST
def run_export(request):
    """
    POST: apply cleaning pipeline and stream a CSV response.

    Steps:
      1. Load saved settings from session
      2. Group included variables by XPT file
      3. Load each XPT once, apply sentinel replacement + binary recode
      4. Outer join all frames on SEQN
      5. Rename columns with custom headers
      6. Stream as CSV attachment
    """
    data_path = request.session.get("nhanes_data_path", "")
    settings  = _get_export_settings(request)

    if not settings:
        return JsonResponse({"error": "No export settings found. Configure and save first."}, status=400)

    if not data_path:
        return JsonResponse({"error": "No data folder configured."}, status=400)

    # ── Build a plan: {xpt_path: [{col, settings, variable}, ...]} ────────────
    plan: dict[str, list] = {}
    errors = []

    for col_name, var_settings in settings.items():
        if not var_settings.get("include", True):
            continue

        variable = get_variable(col_name)
        if variable is None:
            errors.append(f"{col_name}: not found in artifact")
            continue

        xpt_path = _resolve_xpt_path(
            data_path,
            variable.get("component", ""),
            variable.get("data_file", ""),
        )
        if not xpt_path:
            errors.append(
                f"{col_name}: XPT file not found "
                f"({variable.get('data_file', '?')}.xpt in {variable.get('component', '?')})"
            )
            continue

        plan.setdefault(xpt_path, []).append({
            "col"      : col_name,
            "settings" : var_settings,
            "variable" : variable,
        })

    if not plan:
        return JsonResponse({
            "error": "No variables could be resolved. Check that your data folder is correct.",
            "details": errors,
        }, status=400)

    # ── Load and clean each XPT file ──────────────────────────────────────────
    frames = []

    for xpt_path, var_list in plan.items():
        cols = [v["col"] for v in var_list]
        df   = _load_xpt(xpt_path, cols)

        if df is None:
            for v in var_list:
                errors.append(f"{v['col']}: failed to load {xpt_path}")
            continue

        for var_info in var_list:
            col      = var_info["col"]
            vs       = var_info["settings"]

            if col not in df.columns:
                errors.append(f"{col}: column not found in {xpt_path}")
                continue

            # ── Sentinel replacement ──────────────────────────────────────────
            sentinels = vs.get("sentinels", {})
            for code_str, replacement in sentinels.items():
                try:
                    code_val = float(code_str)
                except ValueError:
                    code_val = code_str

                if replacement == _NA or replacement == "NaN":
                    df[col] = df[col].replace(code_val, pd.NA)
                else:
                    try:
                        repl_val = float(replacement)
                    except ValueError:
                        repl_val = replacement
                    df[col] = df[col].replace(code_val, repl_val)

            # ── Binary recode: 1 -> 0, 2 -> 1 ────────────────────────────────
            if vs.get("recode_binary", False):
                df[col] = df[col].replace({1.0: 0.0, 2.0: 1.0})

        frames.append(df)

    if not frames:
        return JsonResponse({
            "error" : "No data could be loaded.",
            "details": errors,
        }, status=500)

    # ── Outer join all frames on SEQN ─────────────────────────────────────────
    combined = frames[0]
    for df in frames[1:]:
        new_cols = [c for c in df.columns if c != "SEQN"]
        combined = combined.merge(
            df[["SEQN"] + new_cols],
            on="SEQN",
            how="outer",
        )

    # ── Rename columns using custom headers ───────────────────────────────────
    rename_map = {"SEQN": "SEQN"}
    for col_name, vs in settings.items():
        if vs.get("include", True):
            custom = vs.get("custom_header", "").strip()
            rename_map[col_name] = custom if custom else col_name

    combined = combined.rename(columns=rename_map)

    # ── Sort by SEQN ──────────────────────────────────────────────────────────
    if "SEQN" in combined.columns:
        combined = combined.sort_values("SEQN").reset_index(drop=True)

    # ── Stream CSV response ───────────────────────────────────────────────────
    buffer = StringIO()
    combined.to_csv(buffer, index=False)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="nhanes_export.csv"'

    if errors:
        response["X-Export-Warnings"] = json.dumps(errors[:10])

    return response
