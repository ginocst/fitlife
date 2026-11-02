"""
Página de clases: la lista y los botones de reservar/cancelar trabajan con la API (fetch).
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def clases(request):
    return render(request, "web/clases.html")
