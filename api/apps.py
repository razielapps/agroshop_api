from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api"


"""
# apps.py
from django.apps import AppConfig
from django.db.models.signals import post_save


class AgroshopConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'agroshop'
    
    def ready(self):
        from . import signals
"""
