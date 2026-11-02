"""Configuración de la app: el verbose_name es el título que se ve en el Django Admin."""

from django.apps import AppConfig


class ClasesConfig(AppConfig):
    name = "clases"
    verbose_name = "Clases grupales"
