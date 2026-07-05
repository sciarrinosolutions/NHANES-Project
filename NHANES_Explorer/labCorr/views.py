import csv
import json
import logging

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render

from varSearch.models import Favorite
from varSearch.search_engine import get_variable, search

from .data import get_lab, get_lab_list, run_correlation_analysis

log = logging.getLogger(__name__)


# ── Lab list ──────────────────────────────────────────────────────────────────

def lab_list(request):
    try:
        labs = get_lab_list()
        error = None
    except FileNotFoundError as e:
        labs  = []
        error = str(e)

    # Group by panel
    panels: dict[str, list] = {}
    for lab in labs:
        panels.setdefault(lab["panel"], []).append(lab)

    return render(request, "labCorr/lab_list.html", {
        "panels": panels,
        "error" : error,
        "total" : len(labs),
    })


# ── Correlation setup ─────────────────────────────────────────────────────────

def correlate_setup(request, column_name):
    lab = get_lab(column_name)
    if not lab:
        return render(request, "varSearch/404.html", status=404)

    # Pre-populate with library variables (excluding this lab itself)
    library_vars = []
    for fav in Favorite.objects.exclude(column_name=column_name):
        var = get_variable(fav.column_name)
        if var:
            library_vars.append(var)

    return render(request, "labCorr/correlate_setup.html", {
        "lab"          : lab,
        "library_vars" : library_vars,
    })


# ── Variable search API (for adding extra vars on setup page) ─────────────────

def search_vars_api(request):
    query = request.GET.get("q", "").strip()
    if not query:
        return JsonResponse({"results": []})
    results = search(query, top_n=15)
    slim = [
        {
            "column_name": r["column_name"],
            "sas_label"  : r["sas_label"],
            "var_type"   : r["var_type"],
            "component"  : r["component"],
            "score"      : r["score"],
        }
        for r in results
    ]
    return JsonResponse({"results": slim})


# ── Run analysis ──────────────────────────────────────────────────────────────

def correlate_run(request, column_name):
    if request.method != "POST":
        from django.shortcuts import redirect
        return redirect("correlate_setup", column_name=column_name)

    lab = get_lab(column_name)
    if not lab:
        return render(request, "varSearch/404.html", status=404)

    indep_cols    = request.POST.getlist("indep_cols")
    gender_filter = request.POST.get("gender_filter", "both")

    if not indep_cols:
        return render(request, "labCorr/correlate_setup.html", {
            "lab"         : lab,
            "library_vars": [],
            "form_error"  : "Select at least one independent variable.",
        })

    output = run_correlation_analysis(
        lab_col       = column_name,
        indep_cols    = indep_cols,
        session       = request.session,
        gender_filter = gender_filter,
    )

    if "error" in output:
        return render(request, "labCorr/correlate_setup.html", {
            "lab"         : lab,
            "library_vars": [],
            "form_error"  : output["error"],
        })

    # Store results in session for CSV export
    request.session["last_corr_results"] = output["results"]
    request.session["last_corr_lab"]     = column_name
    request.session.modified = True

    # Build chart data: top 15 results per direction, sorted by abs(stat)
    def chart_data(direction):
        rows = [r for r in output["results"]
                if r["direction"] == direction and r.get("statistic") is not None][:15]
        return {
            "labels"    : [r["sas_label"][:30] for r in rows],
            "values"    : [r["statistic"] for r in rows],
            "colors"    : [
                "#0077b6" if (r.get("direction_r") == "positive" or r.get("direction_r") is None)
                else "#e63946"
                for r in rows
            ],
        }

    return render(request, "labCorr/results.html", {
        "lab"           : lab,
        "output"        : output,
        "gender_filter" : gender_filter,
        "chart_high"    : json.dumps(chart_data("high")),
        "chart_low"     : json.dumps(chart_data("low")),
        "column_name"   : column_name,
    })


# ── CSV export of last results ────────────────────────────────────────────────

def export_results_csv(request):
    results   = request.session.get("last_corr_results", [])
    lab_col   = request.session.get("last_corr_lab", "unknown")

    response  = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="corr_{lab_col}.csv"'
    )

    writer = csv.DictWriter(response, fieldnames=[
        "column_name", "sas_label", "var_type", "direction",
        "method", "statistic", "p_value", "significant",
        "strength", "direction_r", "n", "error",
    ])
    writer.writeheader()
    for r in results:
        writer.writerow({
            "column_name": r.get("column_name", ""),
            "sas_label"  : r.get("sas_label", ""),
            "var_type"   : r.get("var_type", ""),
            "direction"  : r.get("direction", ""),
            "method"     : r.get("method", ""),
            "statistic"  : r.get("statistic", ""),
            "p_value"    : r.get("p_value", ""),
            "significant": r.get("significant", ""),
            "strength"   : r.get("strength", ""),
            "direction_r": r.get("direction_r", ""),
            "n"          : r.get("n", ""),
            "error"      : r.get("error", ""),
        })
    return response
