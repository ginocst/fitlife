"""
Formulario de registro de socios
UserCreationForm ya valida usuario único, contraseña repetida y los validadores de contraseña;
aquí se le agregan los datos del socio (nombre, correo, RUT y teléfono).
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db import transaction

from .models import Socio
from .validators import normalizar_rut, validar_rut


class RegistroSocioForm(UserCreationForm):
    first_name = forms.CharField(label="Nombre", max_length=150)
    last_name = forms.CharField(label="Apellido", max_length=150)
    email = forms.EmailField(label="Correo")
    rut = forms.CharField(
        label="RUT",
        max_length=12,
        validators=[validar_rut],
        help_text="Ej: 12.345.678-5",
    )
    telefono = forms.CharField(label="Teléfono", max_length=20, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ["username", "first_name", "last_name", "email"]

    def clean_rut(self):
        rut = normalizar_rut(self.cleaned_data["rut"])
        if Socio.objects.filter(rut=rut).exists():
            raise forms.ValidationError("Ya existe un socio con este RUT.")
        return rut

    @transaction.atomic  # el usuario y su perfil de socio se crean juntos, o ninguno
    def save(self, commit=True):
        usuario = super().save()
        Socio.objects.create(
            usuario=usuario,
            rut=self.cleaned_data["rut"],
            telefono=self.cleaned_data["telefono"],
        )
        return usuario
