"""Configuración de la app: el verbose_name es el título que se ve en el Django Admin."""
from django.apps import AppConfig


class AccesosConfig(AppConfig):
    name = 'accesos'
    verbose_name = 'Control de acceso'