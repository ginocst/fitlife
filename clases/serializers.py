"""
Serializers de clases y reservas
"""

from rest_framework import serializers

from fitlife.serializers_utils import ValidarConModelo

from .models import Clase, Reserva


class ClaseSerializer(ValidarConModelo, serializers.ModelSerializer):
    confirmadas = serializers.IntegerField(read_only=True)
    en_espera = serializers.IntegerField(read_only=True)
    cupos_disponibles = serializers.IntegerField(read_only=True)
    mi_reserva = serializers.SerializerMethodField()

    class Meta:
        model = Clase
        fields = [
            "id",
            "nombre",
            "instructor",
            "sala",
            "inicio",
            "duracion_min",
            "cupo",
            "confirmadas",
            "en_espera",
            "cupos_disponibles",
            "mi_reserva",
        ]

    def get_mi_reserva(self, obj) -> dict:
        """La reserva (no cancelada) del socio que consulta, para dibujar el botón correcto."""
        socio = getattr(self.context["request"].user, "socio", None)
        if socio is None:
            return None
        r = (
            obj.reservas.filter(socio=socio)
            .exclude(estado=Reserva.Estado.CANCELADA)
            .first()
        )
        return (
            {"id": r.id, "estado": r.estado, "posicion_espera": r.posicion_espera}
            if r
            else None
        )


class ReservaSerializer(serializers.ModelSerializer):
    clase_nombre = serializers.CharField(source="clase.nombre", read_only=True)
    clase_inicio = serializers.DateTimeField(source="clase.inicio", read_only=True)
    socio_nombre = serializers.CharField(source="socio.__str__", read_only=True)
    posicion_espera = serializers.IntegerField(read_only=True)

    class Meta:
        model = Reserva
        fields = [
            "id",
            "clase",
            "clase_nombre",
            "clase_inicio",
            "socio_nombre",
            "estado",
            "posicion_espera",
            "creado",
        ]
        read_only_fields = ["estado", "creado"]
