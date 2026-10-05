from django.urls import path

from . import views

urlpatterns = [
    path("predict/", views.PredictView.as_view()),
    path("patients/", views.PatientListCreate.as_view()),
    path("patients/<int:pk>/", views.PatientDetail.as_view()),
    path("scans/", views.ScanList.as_view()),
    path("scans/<int:pk>/", views.ScanDetail.as_view()),
    path("stats/", views.StatsView.as_view()),
    path("health/", views.HealthView.as_view()),
]
