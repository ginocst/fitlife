"""
Django Admin: clases y reservas
Las reservas las crean los socios desde la web; en el admin se consultan,
se filtran y se pueden cancelar (respetando la lista de espera).
"""

from django.contrib import admin, messages
from django.db.models import Count, Q

from fitlife.admin_utils import etiqueta

from .models import Clase, Reserva, ReservaError


class ReservaInline(admin.TabularInline):
    model = Reserva
    fields = ["socio", "estado", "creado"]
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Clase)
class ClaseAdmin(admin.ModelAdmin):
    list_display = ["nombre", "inicio", "instructor", "sala", "ocupacion", "espera"]
    list_filter = ["nombre", "sala", "inicio"]
    search_fields = ["nombre", "instructor"]
    date_hierarchy = "inicio"
    inlines = [ReservaInline]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(
                n_conf=Count(
                    "reservas", filter=Q(reservas__estado=Reserva.Estado.CONFIRMADA)
                ),
                n_espera=Count(
                    "reservas", filter=Q(reservas__estado=Reserva.Estado.EN_ESPERA)
                ),
            )
        )

    @admin.display(description="Ocupación", ordering="n_conf")
    def ocupacion(self, obj):
        color = "VENCIDA" if obj.n_conf >= obj.cupo else "ACTIVA"  # rojo si está llena
        return etiqueta(color, f"{obj.n_conf} / {obj.cupo}")

    @admin.display(description="En espera", ordering="n_espera")
    def espera(self, obj):
        return obj.n_espera


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ["clase", "socio", "estado_color", "posicion", "creado"]
    list_filter = ["estado", "clase__nombre", "clase__inicio"]
    search_fields = [
        "socio__usuario__first_name",
        "socio__usuario__last_name",
        "clase__nombre",
    ]
    date_hierarchy = "creado"
    readonly_fields = ["clase", "socio", "estado", "creado"]
    actions = ["cancelar"]
    list_select_related = ["clase", "socio__usuario"]

    def has_add_permission(self, request):
        return False  # las reservas se crean con las reglas de cupo (Reserva.reservar)

    @admin.display(description="Estado", ordering="estado")
    def estado_color(self, obj):
        return etiqueta(obj.estado, obj.get_estado_display())

    @admin.display(description="Posición en espera")
    def posicion(self, obj):
        return obj.posicion_espera or "-"

    @admin.action(
        description="Cancelar las reservas seleccionadas", permissions=["change"]
    )
    def cancelar(self, request, queryset):
        ok = 0
        for reserva in queryset:
            try:
                reserva.cancelar()  # si liberaba un cupo, sube el primero de la lista de espera
                ok += 1
            except ReservaError as e:
                self.message_user(request, f"{reserva}: {e}", messages.WARNING)
        if ok:
            self.message_user(request, f"{ok} reserva(s) cancelada(s).")
