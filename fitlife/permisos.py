"""
Seguridad: roles y permisos

Roles del caso:
    - Socio -> usuario con perfil Socio. Ve su panel y QR, reserva clases.
    - Recepción -> usuario is_staff del grupo "Recepción". Valida accesos, ve el dashboard
        y usa el admin con permisos limitados.
    - Administrador -> superusuario. Todo, incluido el Django Admin completo.

Las páginas usan decoradores (solo_socio, solo_personal) y la API usa clases de permiso de DRF.
DjangoModelPermissions hace que la API respete los MISMOS permisos que el Django Admin
(ver, agregar, cambiar, eliminar), así un rol no puede hacer por la API lo que el admin le prohíbe.
"""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from rest_framework.permissions import (
    SAFE_METHODS,
    BasePermission,
    DjangoModelPermissions,
    IsAdminUser,
)


# Páginas HTML
def es_socio(user):
    return user.is_authenticated and hasattr(user, "socio")


def solo_socio(vista):
    """La página exige sesión iniciada y perfil de socio (si no: 403)."""

    @login_required
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        if not es_socio(request.user):
            raise PermissionDenied
        return vista(request, *args, **kwargs)

    return envoltura


def solo_personal(vista):
    """La página exige sesión iniciada y ser personal del gimnasio (is_staff)."""

    @login_required
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied
        return vista(request, *args, **kwargs)

    return envoltura


# API (DRF)
class EsSocio(BasePermission):
    message = "Solo los socios pueden realizar esta acción."

    def has_permission(self, request, view):
        return es_socio(request.user)


# Personal con el permiso del modelo correspondiente (el mismo del admin)
PersonalConPermiso = IsAdminUser & DjangoModelPermissions


class LecturaSocioEscrituraPersonal(BasePermission):
    """Leer: cualquier usuario con sesión. Crear/editar/borrar: personal con permiso del modelo."""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return PersonalConPermiso().has_permission(request, view)


class PuedeCambiar(BasePermission):
    """
    Para acciones POST que modifican un registro existente (ej: congelar una membresía).
    DjangoModelPermissions pediría el permiso 'add' por ser POST; aquí se exige 'change'.
    """

    def has_permission(self, request, view):
        meta = view.queryset.model._meta
        return request.user.is_staff and request.user.has_perm(
            f"{meta.app_label}.change_{meta.model_name}"
        )
