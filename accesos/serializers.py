"""
Serializers de accesos
"""

from rest_framework import serializers

from .models import RegistroAcceso


class RegistroAccesoSerializer(serializers.ModelSerializer):
    socio_nombre = serializers.SerializerMethodField()

    class Meta:
        model = RegistroAcceso
        fields = [
            "id",
            "socio",
            "socio_nombre",
            "codigo",
            "tipo",
            "resultado",
            "motivo",
            "fecha_hora",
            "tiempo_ms",
        ]

    def get_socio_nombre(self, obj) -> str:
        return str(obj.socio) if obj.socio else None


class ValidarCodigoSerializer(serializers.Serializer):
    codigo = serializers.CharField(
        max_length=64, help_text="Texto leído del QR del socio."
    )
