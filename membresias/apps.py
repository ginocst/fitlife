"""Configuración de la app: el verbose_name es el título que se ve en el Django Admin."""

from django.apps import AppConfig


class MembresiasConfig(AppConfig):
    name = "membresias"
    verbose_name = "Membresías y pagos"
