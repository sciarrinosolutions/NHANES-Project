import json
import logging

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Favorite
from .search_engine import get_variable, search

log = logging.getLogger(__name__)


# ── Search ────────────────────────────────────────────────────────────────────

def search_view(request):
    query   = request.GET.get('q', '').strip()
    results = []
    error   = None

    if query:
        try:
            results = search(query, top_n=30)
        except FileNotFoundError as e:
            error = str(e)
        except Exception as e:
            log.exception("Search error")
            error = f"Search failed: {e}"

    # Annotate results with favorite status
    fav_set = set(Favorite.objects.values_list('column_name', flat=True))
    for r in results:
        r['is_favorite'] = r['column_name'] in fav_set

    return render(request, 'varSearch/search.html', {
        'query'  : query,
        'results': results,
        'error'  : error,
        'total'  : len(results),
    })


# ── Detail ────────────────────────────────────────────────────────────────────

def detail_view(request, column_name):
    variable = get_variable(column_name)
    if variable is None:
        return render(request, 'varSearch/404.html', status=404)

    is_favorite = Favorite.objects.filter(column_name=column_name).exists()

    # Build NHANES doc URL from lookup CSV data
    data_file = variable.get('data_file', '')
    nhanes_url = None
    if data_file:
        nhanes_url = (
            f"https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/"
            f"DataFiles/{data_file}.htm#{column_name}"
        )

    return render(request, 'varSearch/detail.html', {
        'variable'   : variable,
        'is_favorite': is_favorite,
        'nhanes_url' : nhanes_url,
    })


# ── Favorites library ─────────────────────────────────────────────────────────

def library_view(request):
    favorites = Favorite.objects.all()
    return render(request, 'varSearch/library.html', {
        'favorites': favorites,
    })


@require_POST
def toggle_favorite(request, column_name):
    """Add or remove a variable from favorites. Returns JSON for AJAX calls."""
    variable = get_variable(column_name)
    if variable is None:
        return JsonResponse({'error': 'Variable not found'}, status=404)

    fav, created = Favorite.objects.get_or_create(
        column_name=column_name,
        defaults={
            'sas_label' : variable.get('sas_label',  ''),
            'component' : variable.get('component',  ''),
            'data_file' : variable.get('data_file',  ''),
        }
    )

    if not created:
        fav.delete()
        is_favorite = False
    else:
        is_favorite = True

    # If AJAX request, return JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'is_favorite': is_favorite})

    # Otherwise redirect back to referring page
    return redirect(request.META.get('HTTP_REFERER', 'search'))


@require_POST
def remove_favorite(request, column_name):
    """Remove from library page."""
    Favorite.objects.filter(column_name=column_name).delete()
    return redirect('library')
