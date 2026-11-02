"""
Páginas del personal: recepción (lectura del QR) y dashboard de aforo.
"""

from django.conf import settings
from django.shortcuts import render

from fitlife.permisos import solo_personal


@solo_personal
def recepcion(request):
    return render(request, "web/recepcion.html")


@solo_personal
def dashboard(request):
    return render(
        request, "web/dashboard.html", {"aforo_maximo": settings.AFORO_MAXIMO}
    )
