"""
API de clases y reservas
    /api/clases/    GET: usuarios con sesión (?proximas=1 o ?fecha=AAAA-MM-DD).
        POST/PUT/PATCH/DELETE: personal con permiso.
    /api/reservas/  GET: el socio ve las suyas; el personal ve todas (?clase=ID).
        POST {"clase": id}: el socio reserva -> CONFIRMADA o EN_ESPERA.
    /api/reservas/{id}/    DELETE: cancela (no borra) y promueve la lista de espera.
"""

from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from fitlife.permisos import EsSocio, LecturaSocioEscrituraPersonal

from .models import Clase, Reserva, ReservaError
from .serializers import ClaseSerializer, ReservaSerializer


class ClaseViewSet(viewsets.ModelViewSet):
    queryset = Clase.objects.all()
    serializer_class = ClaseSerializer
    permission_classes = [LecturaSocioEscrituraPersonal]

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        if params.get("proximas"):
            qs = qs.filter(inicio__gte=timezone.now())
        if params.get("fecha"):
            qs = qs.filter(inicio__date=params["fecha"])
        return qs


class ReservaViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Reserva.objects.select_related("clase", "socio__usuario")
    serializer_class = ReservaSerializer

    def get_permissions(self):
        # Crear exige ser socio; lo demás solo exige sesión (get_queryset limita qué ve cada uno)
        return [EsSocio()] if self.action == "create" else [IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_staff:
            qs = qs.filter(
                socio__usuario=user
            )  # un socio solo ve y cancela SUS reservas
        clase = self.request.query_params.get("clase")
        return qs.filter(clase_id=clase) if clase else qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            reserva = Reserva.reservar(
                serializer.validated_data["clase"], request.user.socio
            )
        except ReservaError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            self.get_serializer(reserva).data, status=status.HTTP_201_CREATED
        )

    def destroy(self, request, *args, **kwargs):
        """DELETE no borra la fila: la marca CANCELADA, para conservar el historial."""
        reserva = self.get_object()
        try:
            reserva.cancelar()
        except ReservaError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(reserva).data)
