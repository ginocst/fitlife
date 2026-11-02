"""
Mixin para que la API aplique las mismas validaciones del modelo (método clean()) que el admin.
DRF no llama a Model.clean() por sí solo; el admin sí, a través de su formulario.
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers


class ValidarConModelo:
    def validate(self, attrs):
        attrs = super().validate(attrs)
        instancia = self.instance or self.Meta.model()
        for campo, valor in attrs.items():
            setattr(instancia, campo, valor)
        try:
            instancia.clean()
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.message_dict if hasattr(e, 'error_dict') else e.messages)
        return attrs
