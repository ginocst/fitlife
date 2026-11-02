"""
Serializers de membresía : convierten los modelos a JSON y validan lo que llega a la API.
"""

from rest_framework import serializers

from fitlife.serializers_utils import ValidarConModelo

from .models import Membresia, Pago, Plan, Socio


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ["id", "nombre", "descripcion", "precio", "duracion_dias", "activo"]


class SocioSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(source="__str__", read_only=True)
    email = serializers.EmailField(source="usuario.email", read_only=True)
    estado_membresia = serializers.SerializerMethodField()
    vence = serializers.SerializerMethodField()

    class Meta:
        model = Socio
        fields = [
            "id",
            "nombre",
            "rut",
            "email",
            "telefono",
            "codigo_qr",
            "estado_membresia",
            "vence",
        ]

    def get_estado_membresia(self, obj) -> str:
        m = obj.membresia_actual()
        return m.estado_actual if m else "SIN_MEMBRESIA"

    def get_vence(self, obj) -> str:
        m = obj.membresia_actual()
        return m.fecha_fin.isoformat() if m else None


class MembresiaSerializer(ValidarConModelo, serializers.ModelSerializer):
    socio_nombre = serializers.CharField(source="socio.__str__", read_only=True)
    plan_nombre = serializers.CharField(source="plan.nombre", read_only=True)
    estado_actual = serializers.CharField(read_only=True)
    dias_restantes = serializers.IntegerField(read_only=True)

    class Meta:
        model = Membresia
        fields = [
            "id",
            "socio",
            "socio_nombre",
            "plan",
            "plan_nombre",
            "fecha_inicio",
            "fecha_fin",
            "estado",
            "estado_actual",
            "dias_restantes",
            "congelada_desde",
        ]
        # El estado cambia solo con las acciones congelar/descongelar o al vencer
        read_only_fields = ["estado", "congelada_desde"]


class PagoSerializer(serializers.ModelSerializer):
    socio_nombre = serializers.CharField(source="socio.__str__", read_only=True)
    plan_nombre = serializers.CharField(source="plan.nombre", read_only=True)
    membresia_vence = serializers.DateField(
        source="membresia.fecha_fin", read_only=True
    )

    class Meta:
        model = Pago
        fields = [
            "id",
            "socio",
            "socio_nombre",
            "plan",
            "plan_nombre",
            "monto",
            "medio",
            "fecha",
            "membresia",
            "membresia_vence",
        ]
        read_only_fields = ["membresia"]
        extra_kwargs = {"monto": {"required": False}}

    def validate(self, attrs):
        # Un pago ya registrado no puede cambiar de socio ni de plan (descuadraría la membresía)
        if self.instance:
            for campo in ("socio", "plan"):
                if campo in attrs and attrs[campo] != getattr(self.instance, campo):
                    raise serializers.ValidationError(
                        {campo: "No se puede cambiar en un pago ya registrado."}
                    )
        return attrs
