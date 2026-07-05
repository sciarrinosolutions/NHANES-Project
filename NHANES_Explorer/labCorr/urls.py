from django.urls import path
from . import views

urlpatterns = [
    path('',                              views.lab_list,          name='lab_list'),
    path('<str:column_name>/setup/',      views.correlate_setup,   name='correlate_setup'),
    path('<str:column_name>/run/',        views.correlate_run,     name='correlate_run'),
    path('api/search/',                   views.search_vars_api,   name='lab_search_api'),
    path('export/csv/',                   views.export_results_csv, name='export_results_csv'),
]
