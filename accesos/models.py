"""
Modelo de accesos
    Socio 1 ---- N RegistroAcceso   (cada lectura del QR en el torniquete queda registrada)

Se guardan también los intentos DENEGADOS (con su motivo): sirven de auditoría y alimentan el dashboard.
"""

from django.db import models
from django.utils import timezone

from membresias.models import Socio


class RegistroAcceso(models.Model):
    # CHOICES: tipo de movimiento y resultado de la validación
    class Tipo(models.TextChoices):
        ENTRADA = "ENTRADA", "Entrada"
        SALIDA = "SALIDA", "Salida"

    class Resultado(models.TextChoices):
        PERMITIDO = "PERMITIDO", "Permitido"
        DENEGADO = "DENEGADO", "Denegado"

    # SET_NULL: si se borra un socio, su historial de accesos se conserva
    socio = models.ForeignKey(
        Socio, on_delete=models.SET_NULL, null=True, blank=True, related_name="accesos"
    )
    codigo = models.CharField(
        max_length=64, help_text="Texto leído del QR, tal como llegó."
    )
    tipo = models.CharField(max_length=7, choices=Tipo.choices, default=Tipo.ENTRADA)
    resultado = models.CharField(max_length=9, choices=Resultado.choices)
    motivo = models.CharField(max_length=120, blank=True)
    fecha_hora = models.DateTimeField(default=timezone.now)
    tiempo_ms = models.FloatField(
        default=0, help_text="Milisegundos que tardó la validación."
    )

    class Meta:
        ordering = ["-fecha_hora"]
        verbose_name = "registro de acceso"
        verbose_name_plural = "registros de acceso"
        # Índice para responder rápido "¿cuál fue el último movimiento de este socio hoy?"
        indexes = [models.Index(fields=["socio", "fecha_hora"])]

    def __str__(self):
        return f"{self.fecha_hora:%d-%m %H:%M} {self.socio or self.codigo} {self.tipo} {self.resultado}"
