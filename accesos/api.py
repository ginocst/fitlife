"""
API de accesos y aforo
    POST /api/accesos/validar/    {"codigo": "..."} -> valida el QR y registra ENTRADA/SALIDA (personal).
    GET  /api/accesos/    registros de hoy, o de ?fecha=AAAA-MM-DD (personal, solo lectura).
    GET  /api/dashboard/  datos del dashboard de aforo (personal).
    GET  /api/aforo/  solo el nivel de ocupación (PÚBLICO, para la página de inicio).
"""

from django.conf import settings
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response

from .models import RegistroAcceso
from .serializers import RegistroAccesoSerializer, ValidarCodigoSerializer
from .servicios import aforo_actual, datos_dashboard, procesar_codigo


class RegistroAccesoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RegistroAcceso.objects.select_related("socio__usuario")
    serializer_class = RegistroAccesoSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        fecha = self.request.query_params.get("fecha") or timezone.localdate()
        return super().get_queryset().filter(fecha_hora__date=fecha)


@api_view(["POST"])
@permission_classes([IsAdminUser])
def validar_codigo(request):
    serializer = ValidarCodigoSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    registro = procesar_codigo(serializer.validated_data["codigo"])
    return Response(RegistroAccesoSerializer(registro).data)


@api_view(["GET"])
@permission_classes([IsAdminUser])
def dashboard(request):
    return Response(datos_dashboard())


@api_view(["GET"])
@permission_classes([AllowAny])
def aforo_publico(request):
    actual, maximo = aforo_actual(), settings.AFORO_MAXIMO
    return Response({"porcentaje": round(actual * 100 / maximo) if maximo else 0})
