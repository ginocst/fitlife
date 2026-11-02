"""
API de membresías (CRUD)
    /api/planes/    GET: cualquier usuario con sesión. POST/PUT/PATCH/DELETE: personal con permiso.
    /api/socios/    GET: personal (consulta para recepción).
    /api/membresias/    CRUD del personal + acciones POST /{id}/congelar/ y /{id}/descongelar/
    /api/pagos/     CRUD del personal. Crear un pago crea o renueva la membresía; borrarlo la descuenta.
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from fitlife.permisos import (
    LecturaSocioEscrituraPersonal,
    PersonalConPermiso,
    PuedeCambiar,
)

from .models import Membresia, Pago, Plan, Socio
from .serializers import (
    MembresiaSerializer,
    PagoSerializer,
    PlanSerializer,
    SocioSerializer,
)


class PlanViewSet(viewsets.ModelViewSet):
    queryset = Plan.objects.all()
    serializer_class = PlanSerializer
    permission_classes = [LecturaSocioEscrituraPersonal]

    def get_queryset(self):
        # Los socios solo ven los planes a la venta; el personal ve todos
        qs = super().get_queryset()
        return qs if self.request.user.is_staff else qs.filter(activo=True)


class SocioViewSet(viewsets.ReadOnlyModelViewSet):
    """Los socios se crean con el registro web o en el admin (requieren usuario y contraseña)."""

    queryset = Socio.objects.select_related("usuario")
    serializer_class = SocioSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        qs = super().get_queryset()
        buscar = self.request.query_params.get("buscar")
        if buscar:  # ?buscar=ana -> por nombre o RUT
            qs = qs.filter(usuario__first_name__icontains=buscar) | qs.filter(
                rut__icontains=buscar
            )
        return qs


class MembresiaViewSet(viewsets.ModelViewSet):
    queryset = Membresia.objects.select_related("socio__usuario", "plan")
    serializer_class = MembresiaSerializer
    permission_classes = [PersonalConPermiso]

    def get_queryset(self):
        Membresia.vencer_caducadas()  # los estados siempre al día antes de responder
        qs = super().get_queryset()
        estado = self.request.query_params.get("estado")  # ?estado=VENCIDA
        return qs.filter(estado=estado) if estado else qs

    @action(detail=True, methods=["post"], permission_classes=[PuedeCambiar])
    def congelar(self, request, pk=None):
        return self._cambiar(self.get_object().congelar, request)

    @action(detail=True, methods=["post"], permission_classes=[PuedeCambiar])
    def descongelar(self, request, pk=None):
        return self._cambiar(self.get_object().descongelar, request)

    def _cambiar(self, metodo, request):
        try:
            metodo()
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(self.get_object()).data)


class PagoViewSet(viewsets.ModelViewSet):
    queryset = Pago.objects.select_related("socio__usuario", "plan", "membresia")
    serializer_class = PagoSerializer
    permission_classes = [PersonalConPermiso]
