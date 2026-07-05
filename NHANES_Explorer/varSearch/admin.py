from django.contrib import admin
from .models import Favorite


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display  = ('column_name', 'sas_label', 'component', 'data_file', 'added_at')
    search_fields = ('column_name', 'sas_label', 'component')
    list_filter   = ('component',)
    ordering      = ('-added_at',)
