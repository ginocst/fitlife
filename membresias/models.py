"""
Modelos de membresía
    Usuario 1 ---- 1 Socio  (la cuenta con la que el socio inicia sesión)
    Plan    1 ---- N Membresia  (un plan se vende muchas veces)
    Socio   1 ---- N Membresia  (historial de membresías del socio)
    Socio   1 ---- N Pago   (cada pago crea o renueva una membresía)

Reglas de negocio
    Un pago crea una membresía nueva o extiende la vigente (Membresia.renovar_o_crear).
    Una membresía ACTIVA cuya fecha de fin ya pasó se marca VENCIDA automáticamente.
    Congelar pausa la membresía; al descongelar se suman los días congelados a su fin.
"""

import uuid
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone
from fitlife.formato import pesos

from .validators import normalizar_rut, validar_rut


class Plan(models.Model):
    """Producto que vende el gimnasio: mensual, trimestral, anual..."""

    nombre = models.CharField(max_length=80, unique=True)
    descripcion = models.TextField(blank=True)
    precio = models.PositiveIntegerField(help_text="En pesos chilenos, ej: 25000.")
    duracion_dias = models.PositiveIntegerField(
        "duración (días)", help_text="Días de vigencia que entrega el plan."
    )
    activo = models.BooleanField(
        default=True, help_text="Solo los planes activos se ofrecen a la venta."
    )

    class Meta:
        ordering = ["precio"]
        verbose_name_plural = "planes"

    def __str__(self):
        return self.nombre

    @property
    def precio_fmt(self):
        return pesos(self.precio)


class Socio(models.Model):
    """Perfil del cliente del gimnasio, unido 1 a 1 a su cuenta de usuario."""

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="socio"
    )
    rut = models.CharField("RUT", max_length=12, unique=True, validators=[validar_rut])
    telefono = models.CharField("teléfono", max_length=20, blank=True)
    # Código que va dentro del QR. UUID: único y con índice en la BD (búsqueda en ms).
    codigo_qr = models.UUIDField(
        "código QR", default=uuid.uuid4, unique=True, editable=False
    )
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["usuario__first_name", "usuario__last_name"]

    def __str__(self):
        return self.usuario.get_full_name() or self.usuario.username

    def clean(self):
        # Se guarda siempre con el mismo formato, para que la restricción "unique" funcione
        self.rut = normalizar_rut(self.rut)

    def membresia_actual(self):
        """La membresía más reciente (la de fecha de fin más lejana), o None."""
        return self.membresias.order_by("-fecha_fin").first()

    def membresia_vigente(self):
        """La membresía que hoy permite entrar y reservar, o None."""
        hoy = timezone.localdate()
        return self.membresias.filter(
            estado=Membresia.Estado.ACTIVA, fecha_inicio__lte=hoy, fecha_fin__gte=hoy
        ).first()


class Membresia(models.Model):
    """Periodo en que un socio tiene derecho a usar el gimnasio."""

    # CHOICES: estados de la membresía
    class Estado(models.TextChoices):
        ACTIVA = "ACTIVA", "Activa"
        VENCIDA = "VENCIDA", "Vencida"
        CONGELADA = "CONGELADA", "Congelada"

    socio = models.ForeignKey(
        Socio, on_delete=models.CASCADE, related_name="membresias"
    )
    plan = models.ForeignKey(
        Plan, on_delete=models.PROTECT
    )  # PROTECT: no se borra un plan ya vendido
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(help_text="Último día en que la membresía es válida.")
    estado = models.CharField(
        max_length=10, choices=Estado.choices, default=Estado.ACTIVA
    )
    congelada_desde = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-fecha_fin"]
        verbose_name = "membresía"
        verbose_name_plural = "membresías"

    def __str__(self):
        return f"{self.socio} - {self.plan} ({self.get_estado_display()})"

    def clean(self):
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            raise ValidationError(
                {"fecha_fin": "La fecha de fin no puede ser anterior a la de inicio."}
            )

    # consultas
    @property
    def estado_actual(self):
        """Estado real hoy: una ACTIVA con la fecha ya pasada se muestra VENCIDA aunque aún no se haya actualizado."""
        if self.estado == self.Estado.ACTIVA and self.fecha_fin < timezone.localdate():
            return self.Estado.VENCIDA
        return self.estado

    @property
    def dias_restantes(self):
        return max((self.fecha_fin - timezone.localdate()).days + 1, 0)

    # Reglas del negocio
    @classmethod
    def vencer_caducadas(cls):
        """Marca VENCIDA toda membresía ACTIVA cuya fecha de fin ya pasó. Devuelve cuántas cambió."""
        return cls.objects.filter(
            estado=cls.Estado.ACTIVA, fecha_fin__lt=timezone.localdate()
        ).update(estado=cls.Estado.VENCIDA)

    @classmethod
    def renovar_o_crear(cls, socio, plan):
        """
        Qué ocurre al pagar un plan:
            si el socio tiene una membresía ACTIVA o CONGELADA que no ha vencido, se EXTIENDE;
            si no, se CREA una nueva que empieza hoy.
        """
        hoy = timezone.localdate()
        vigente = socio.membresias.filter(
            estado__in=[cls.Estado.ACTIVA, cls.Estado.CONGELADA], fecha_fin__gte=hoy
        ).first()
        if vigente:
            vigente.fecha_fin += timedelta(days=plan.duracion_dias)
            vigente.plan = plan
            vigente.save(update_fields=["fecha_fin", "plan"])
            return vigente
        # fecha_fin es el último día válido: un plan de 30 días que parte hoy termina en hoy + 29
        return cls.objects.create(
            socio=socio,
            plan=plan,
            fecha_inicio=hoy,
            fecha_fin=hoy + timedelta(days=plan.duracion_dias - 1),
        )

    def congelar(self):
        """ACTIVA -> CONGELADA (por ejemplo, por una lesión)."""
        if self.estado_actual != self.Estado.ACTIVA:
            raise ValueError("Solo se puede congelar una membresía activa.")
        self.estado = self.Estado.CONGELADA
        self.congelada_desde = timezone.localdate()
        self.save(update_fields=["estado", "congelada_desde"])

    def descongelar(self):
        """CONGELADA -> ACTIVA, sumando a la fecha de fin los días que estuvo congelada."""
        if self.estado != self.Estado.CONGELADA:
            raise ValueError("La membresía no está congelada.")
        dias = (
            (timezone.localdate() - self.congelada_desde).days
            if self.congelada_desde
            else 0
        )
        self.fecha_fin += timedelta(days=dias)
        self.estado = self.Estado.ACTIVA
        self.congelada_desde = None
        self.save(update_fields=["fecha_fin", "estado", "congelada_desde"])


class Pago(models.Model):
    """Registro de un pago. Al crearlo se crea o renueva la membresía del socio."""

    # CHOICES: medios de pago
    class Medio(models.TextChoices):
        EFECTIVO = "EFECTIVO", "Efectivo"
        DEBITO = "DEBITO", "Débito"
        CREDITO = "CREDITO", "Crédito"
        TRANSFERENCIA = "TRANSFERENCIA", "Transferencia"

    socio = models.ForeignKey(
        Socio, on_delete=models.PROTECT, related_name="pagos"
    )  # PROTECT: protege el historial
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    monto = models.PositiveIntegerField(
        blank=True, help_text="Si se deja vacío, se usa el precio del plan actualmente."
    )
    medio = models.CharField(max_length=15, choices=Medio.choices, default=Medio.DEBITO)
    fecha = models.DateTimeField(default=timezone.now)
    membresia = models.ForeignKey(
        Membresia,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False,
        related_name="pagos",
    )

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.socio} - {self.plan} - ${self.monto}"

    @transaction.atomic  # el pago y la membresía se guardan juntos, o ninguno
    def save(self, *args, **kwargs):
        if self.monto is None:
            self.monto = self.plan.precio
        if self.pk is None:  # solo al CREAR el pago se toca la membresía
            self.membresia = Membresia.renovar_o_crear(self.socio, self.plan)
        super().save(*args, **kwargs)

    @transaction.atomic
    def delete(self, *args, **kwargs):
        """Anular un pago descuenta de la membresía los días que ese pago había agregado."""
        membresia = self.membresia
        resultado = super().delete(*args, **kwargs)
        if membresia:
            membresia.fecha_fin -= timedelta(days=self.plan.duracion_dias)
            if membresia.fecha_fin < membresia.fecha_inicio:
                membresia.delete()  # era la única compra de esa membresía
            else:
                membresia.save(update_fields=["fecha_fin"])
        return resultado
