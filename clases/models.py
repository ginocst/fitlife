"""
Modelos de clases grupales
    Clase 1 ---- N Reserva N ---- 1 Socio

Reglas de negocio (lista de espera automática)
    - Al reservar: si quedan cupos -> CONFIRMADA; si no -> EN_ESPERA (en orden de llegada).
    - Al cancelar una CONFIRMADA, o al aumentar el cupo, el primero de la lista de espera pasa solo a CONFIRMADA.
    - Solo reservan socios con membresía vigente, una vez por clase y antes de que empiece.
    - select_for_update() bloquea la clase mientras se reserva: dos socios no pueden quedarse a la vez con el último cupo.
"""

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone

from membresias.models import Socio


class ReservaError(Exception):
    """Se lanza cuando una reserva o cancelación no está permitida (el mensaje se muestra al socio)."""


class Clase(models.Model):
    nombre = models.CharField(max_length=80, help_text="Ej: Zumba, HIIT, Funcional.")
    instructor = models.CharField(max_length=80)
    sala = models.CharField(max_length=50, blank=True)
    inicio = models.DateTimeField()
    duracion_min = models.PositiveIntegerField(
        default=60, verbose_name="duración (min)"
    )
    cupo = models.PositiveIntegerField(help_text="Personas que pueden participar.")

    class Meta:
        ordering = ["inicio"]

    def __str__(self):
        return f"{self.nombre} {timezone.localtime(self.inicio):%d-%m %H:%M}"

    # consultas
    @property
    def fin(self):
        return self.inicio + timedelta(minutes=self.duracion_min)

    @property
    def confirmadas(self):
        return self.reservas.filter(estado=Reserva.Estado.CONFIRMADA).count()

    @property
    def en_espera(self):
        return self.reservas.filter(estado=Reserva.Estado.EN_ESPERA).count()

    @property
    def cupos_disponibles(self):
        return max(self.cupo - self.confirmadas, 0)

    # reglas
    def clean(self):
        # No se puede bajar el cupo por debajo de las reservas ya confirmadas
        if self.pk and self.cupo < self.confirmadas:
            raise ValidationError(
                {"cupo": f"Ya hay {self.confirmadas} reservas confirmadas."}
            )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.promover_lista_espera()  # si el cupo aumentó, entran los que esperaban

    def promover_lista_espera(self):
        """Confirma, en orden de llegada, a tantos socios en espera como cupos libres haya."""
        libres = self.cupo - self.confirmadas
        if libres <= 0:
            return 0
        siguientes = self.reservas.filter(estado=Reserva.Estado.EN_ESPERA).order_by(
            "creado"
        )[:libres]
        return Reserva.objects.filter(
            pk__in=list(siguientes.values_list("pk", flat=True))
        ).update(estado=Reserva.Estado.CONFIRMADA)


class Reserva(models.Model):
    # CHOICES: estados de la reserva
    class Estado(models.TextChoices):
        CONFIRMADA = "CONFIRMADA", "Confirmada"
        EN_ESPERA = "EN_ESPERA", "En lista de espera"
        CANCELADA = "CANCELADA", "Cancelada"

    clase = models.ForeignKey(Clase, on_delete=models.CASCADE, related_name="reservas")
    socio = models.ForeignKey(Socio, on_delete=models.CASCADE, related_name="reservas")
    estado = models.CharField(max_length=10, choices=Estado.choices)
    creado = models.DateTimeField(
        auto_now_add=True
    )  # define el orden de la lista de espera

    class Meta:
        ordering = ["creado"]
        constraints = [
            # Un socio solo puede tener UNA reserva no cancelada por clase
            models.UniqueConstraint(
                fields=["clase", "socio"],
                condition=~Q(estado="CANCELADA"),
                name="una_reserva_activa_por_clase",
            ),
        ]

    def __str__(self):
        return f"{self.socio} en {self.clase} ({self.get_estado_display()})"

    @property
    def posicion_espera(self):
        """1 = el próximo en entrar. None si no está en espera."""
        if self.estado != self.Estado.EN_ESPERA:
            return None
        return (
            self.clase.reservas.filter(
                estado=self.Estado.EN_ESPERA, creado__lt=self.creado
            ).count()
            + 1
        )

    @classmethod
    @transaction.atomic
    def reservar(cls, clase, socio):
        clase = Clase.objects.select_for_update().get(
            pk=clase.pk
        )  # bloquea la clase hasta terminar
        if clase.inicio <= timezone.now():
            raise ReservaError("La clase ya comenzó.")
        if socio.membresia_vigente() is None:
            raise ReservaError("Necesitas una membresía vigente para reservar.")
        if (
            clase.reservas.filter(socio=socio)
            .exclude(estado=cls.Estado.CANCELADA)
            .exists()
        ):
            raise ReservaError("Ya tienes una reserva para esta clase.")
        estado = (
            cls.Estado.CONFIRMADA
            if clase.confirmadas < clase.cupo
            else cls.Estado.EN_ESPERA
        )
        return cls.objects.create(clase=clase, socio=socio, estado=estado)

    @transaction.atomic
    def cancelar(self):
        clase = Clase.objects.select_for_update().get(pk=self.clase_id)
        if self.estado == self.Estado.CANCELADA:
            raise ReservaError("La reserva ya estaba cancelada.")
        if clase.inicio <= timezone.now():
            raise ReservaError("No se puede cancelar una clase que ya comenzó.")
        liberaba_cupo = self.estado == self.Estado.CONFIRMADA
        self.estado = self.Estado.CANCELADA
        self.save(update_fields=["estado"])
        if liberaba_cupo:
            clase.promover_lista_espera()  # el primero en espera toma el cupo
