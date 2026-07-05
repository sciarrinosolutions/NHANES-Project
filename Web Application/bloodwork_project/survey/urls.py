from django.urls import path
from . import views

urlpatterns = [
    path('',               views.index,         name='index'),
    path('survey/',        views.start_survey,  name='start_survey'),
    path('survey/submit/', views.submit_survey, name='submit_survey'),
    path('results/',       views.results,       name='results'),
]
