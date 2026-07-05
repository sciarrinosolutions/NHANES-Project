from django.urls import path
from . import views
from . import export_views

urlpatterns = [
    path('',                                    views.search_view,        name='search'),
    path('variable/<str:column_name>/',         views.detail_view,        name='detail'),
    path('library/',                            views.library_view,       name='library'),
    path('favorite/<str:column_name>/toggle/',  views.toggle_favorite,    name='toggle_favorite'),
    path('favorite/<str:column_name>/remove/',  views.remove_favorite,    name='remove_favorite'),

    # Export
    path('export/',                             export_views.export_page,   name='export_page'),
    path('export/save-settings/',               export_views.save_settings, name='save_settings'),
    path('export/run/',                         export_views.run_export,    name='run_export'),
    path('export/set-data-path/',               export_views.set_data_path, name='set_data_path'),
]
