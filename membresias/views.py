"""
Páginas de socios: registro, panel personal y QR.
"""

import io

import qrcode
import qrcode.image.svg
from django.contrib import messages
from django.contrib.auth import login
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from fitlife.permisos import solo_socio

from .forms import RegistroSocioForm
from .models import Membresia, Socio


def registro(request):
    """Alta de socio: crea usuario + perfil y deja la sesión iniciada."""
    if request.user.is_authenticated:
        return redirect("despues_login")
    form = RegistroSocioForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = form.save()
        login(request, usuario)
        messages.success(
            request,
            "Cuenta creada. Para entrar al gimnasio, paga tu plan en recepción.",
        )
        return redirect("panel")
    return render(request, "web/registro.html", {"form": form})


@solo_socio
def panel(request):
    """Panel del socio: estado de su membresía, su QR, sus reservas y sus últimos accesos."""
    socio = request.user.socio
    Membresia.vencer_caducadas()
    reservas = (
        socio.reservas.select_related("clase")
        .filter(clase__inicio__gte=timezone.now())
        .exclude(estado="CANCELADA")
    )
    return render(
        request,
        "web/panel.html",
        {
            "socio": socio,
            "membresia": socio.membresia_actual(),
            "reservas": reservas,
            "accesos": socio.accesos.all()[:5],
        },
    )


def qr_svg(request, codigo):
    """Imagen SVG del QR. La ve el propio socio o el personal (vista previa en el admin)."""
    socio = get_object_or_404(Socio, codigo_qr=codigo)
    if not (request.user.is_staff or getattr(request.user, "socio", None) == socio):
        raise PermissionDenied
    imagen = qrcode.make(
        str(socio.codigo_qr), image_factory=qrcode.image.svg.SvgPathImage, box_size=12
    )
    buffer = io.BytesIO()
    imagen.save(buffer)
    respuesta = HttpResponse(buffer.getvalue(), content_type="image/svg+xml")
    respuesta["Cache-Control"] = (
        "private, max-age=3600"  # no se guarda en cachés compartidas
    )
    return respuesta
