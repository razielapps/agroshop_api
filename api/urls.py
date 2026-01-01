from django.urls import path
from .views import HealthView

urlpatterns = [
    path("v1/health/", HealthView.as_view()),
]
