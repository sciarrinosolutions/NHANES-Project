from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('varSearch.urls')),
    path('labs/', include('labCorr.urls')),
]
