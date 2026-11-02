"""
Páginas generales: inicio (pública) y redirección según el rol después de iniciar sesión.
"""
from django.contrib import messages
from django.shortcuts import redirect, render

from membresias.models import Plan


def inicio(request):
    return render(request, 'web/inicio.html', {'planes': Plan.objects.filter(activo=True)})


def despues_login(request):
    """Cada rol aterriza en su página principal."""
    user = request.user
    if not user.is_authenticated:
        return redirect('login')
    if user.is_staff:
        return redirect('recepcion')
    if hasattr(user, 'socio'):
        return redirect('panel')
    messages.warning(request, 'Tu usuario no tiene un perfil de socio. Acércate a recepción.')
    return redirect('inicio')
