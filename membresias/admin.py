"""
Django Admin: planes, socios, membresías y pagos
Personalización: columnas útiles, filtros laterales, búsqueda, etiquetas de color,
acciones masivas (congelar, descongelar, vencer), inlines y vista previa del QR.
"""

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.urls import reverse
from django.utils.html import format_html

from fitlife.admin_utils import etiqueta
from fitlife.formato import pesos

from .models import Membresia, Pago, Plan, Socio
from .validators import formatear_rut

# Textos de la cabecera del panel
admin.site.site_header = "FitLife: administración"
admin.site.site_title = "FitLife admin"
admin.site.index_title = "Gestión del centro deportivo"


# Usuarios: el perfil de socio se edita dentro del mismo usuario (inline)
class SocioInline(admin.StackedInline):
    model = Socio
    can_delete = False
    fields = ["rut", "telefono"]
    extra = 0


admin.site.unregister(User)


@admin.register(User)
class UsuarioAdmin(UserAdmin):
    inlines = [SocioInline]
    list_display = [
        "username",
        "first_name",
        "last_name",
        "email",
        "is_staff",
        "es_socio",
    ]

    @admin.display(boolean=True, description="Socio")
    def es_socio(self, obj):
        return hasattr(obj, "socio")


# Planes
@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = [
        "nombre",
        "precio_fmt",
        "duracion_dias",
        "membresias_activas",
        "activo",
    ]
    list_editable = ["activo"]  # activar o desactivar desde el listado
    list_filter = ["activo"]
    search_fields = ["nombre"]

    def get_queryset(self, request):
        # annotate: el conteo se hace en UNA consulta, no una por fila
        return (
            super()
            .get_queryset(request)
            .annotate(
                n_activas=Count(
                    "membresia", filter=Q(membresia__estado=Membresia.Estado.ACTIVA)
                )
            )
        )

    @admin.display(description="Precio", ordering="precio")
    def precio_fmt(self, obj):
        return pesos(obj.precio)

    @admin.display(description="Membresías activas", ordering="n_activas")
    def membresias_activas(self, obj):
        return obj.n_activas


# Socios
class MembresiaInline(admin.TabularInline):
    model = Membresia
    fields = ["plan", "fecha_inicio", "fecha_fin", "estado"]
    readonly_fields = fields  # se gestionan con pagos y acciones, no a mano
    extra = 0
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


class PagoInline(admin.TabularInline):
    model = Pago
    fields = ["fecha", "plan", "monto", "medio"]
    readonly_fields = fields
    extra = 0
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


class EstadoMembresiaFilter(admin.SimpleListFilter):
    """Filtro lateral por el estado de la membresía actual del socio."""

    title = "estado de membresía"
    parameter_name = "estado"

    def lookups(self, request, model_admin):
        return list(Membresia.Estado.choices) + [("SIN", "Sin membresía")]

    def queryset(self, request, queryset):
        if self.value() == "SIN":
            return queryset.filter(membresias__isnull=True)
        if self.value():
            return queryset.filter(membresias__estado=self.value()).distinct()
        return queryset


@admin.register(Socio)
class SocioAdmin(admin.ModelAdmin):
    list_display = [
        "__str__",
        "rut_fmt",
        "email",
        "telefono",
        "estado_membresia",
        "vence",
    ]
    list_filter = [EstadoMembresiaFilter]
    search_fields = [
        "usuario__username",
        "usuario__first_name",
        "usuario__last_name",
        "rut",
        "usuario__email",
    ]
    readonly_fields = ["codigo_qr", "vista_qr", "creado"]
    fields = ["usuario", "rut", "telefono", "codigo_qr", "vista_qr", "creado"]
    autocomplete_fields = ["usuario"]
    inlines = [MembresiaInline, PagoInline]
    list_select_related = ["usuario"]

    @admin.display(description="RUT", ordering="rut")
    def rut_fmt(self, obj):
        return format_html(
            '<span style="white-space:nowrap">{}</span>', formatear_rut(obj.rut)
        )

    @admin.display(description="Correo", ordering="usuario__email")
    def email(self, obj):
        return obj.usuario.email

    @admin.display(description="Membresía")
    def estado_membresia(self, obj):
        m = obj.membresia_actual()
        if m is None:
            return etiqueta("", "Sin membresía")
        return etiqueta(m.estado_actual, Membresia.Estado(m.estado_actual).label)

    @admin.display(description="Vence")
    def vence(self, obj):
        m = obj.membresia_actual()
        return (
            format_html(
                '<span style="white-space:nowrap">{}</span>',
                m.fecha_fin.strftime("%d-%m-%Y"),
            )
            if m
            else "-"
        )

    @admin.display(description="QR para imprimir")
    def vista_qr(self, obj):
        if not obj.pk:
            return "Se genera al guardar."
        return format_html(
            '<img src="{}" width="160" height="160" alt="QR de {}">',
            reverse("qr_socio", args=[obj.codigo_qr]),
            obj,
        )


# Membresías
@admin.register(Membresia)
class MembresiaAdmin(admin.ModelAdmin):
    list_display = ["socio", "plan", "inicio", "fin", "estado_color", "dias_restantes"]
    list_filter = ["estado", "plan"]
    search_fields = [
        "socio__usuario__first_name",
        "socio__usuario__last_name",
        "socio__rut",
    ]
    date_hierarchy = "fecha_fin"
    autocomplete_fields = ["socio"]
    readonly_fields = [
        "estado",
        "congelada_desde",
    ]  # el estado cambia solo con acciones o al vencer
    actions = ["congelar", "descongelar", "actualizar_vencidas"]
    list_select_related = ["socio__usuario", "plan"]

    def changelist_view(self, request, extra_context=None):
        Membresia.vencer_caducadas()  # cada vez que se abre el listado, los estados quedan al día
        return super().changelist_view(request, extra_context)

    @admin.display(description="Estado", ordering="estado")
    def estado_color(self, obj):
        return etiqueta(obj.estado, obj.get_estado_display())

    # Fechas cortas (dd-mm-aaaa)
    @admin.display(description="Inicio", ordering="fecha_inicio")
    def inicio(self, obj):
        return obj.fecha_inicio.strftime("%d-%m-%Y")

    @admin.display(description="Fin", ordering="fecha_fin")
    def fin(self, obj):
        return obj.fecha_fin.strftime("%d-%m-%Y")

    @admin.action(
        description="Congelar las membresías seleccionadas", permissions=["change"]
    )
    def congelar(self, request, queryset):
        self._aplicar(request, queryset, "congelar", "congelada(s)")

    @admin.action(
        description="Descongelar (suma los días congelados al vencimiento)",
        permissions=["change"],
    )
    def descongelar(self, request, queryset):
        self._aplicar(request, queryset, "descongelar", "descongelada(s)")

    @admin.action(
        description="Marcar como vencidas las que ya pasaron su fecha",
        permissions=["change"],
    )
    def actualizar_vencidas(self, request, queryset):
        self.message_user(
            request,
            f"{Membresia.vencer_caducadas()} membresía(s) marcadas como vencidas.",
        )

    def _aplicar(self, request, queryset, metodo, verbo):
        """Ejecuta congelar/descongelar en cada membresía y avisa cuáles no se pudieron cambiar."""
        ok = 0
        for membresia in queryset:
            try:
                getattr(membresia, metodo)()
                ok += 1
            except ValueError as e:
                self.message_user(request, f"{membresia.socio}: {e}", messages.WARNING)
        if ok:
            self.message_user(request, f"{ok} membresía(s) {verbo}.")


# Pagos
@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ["fecha", "socio", "plan", "monto_fmt", "medio", "membresia_vence"]
    list_filter = ["medio", "plan", "fecha"]
    search_fields = [
        "socio__usuario__first_name",
        "socio__usuario__last_name",
        "socio__rut",
    ]
    date_hierarchy = "fecha"
    autocomplete_fields = ["socio"]
    list_select_related = ["socio__usuario", "plan", "membresia"]

    def get_readonly_fields(self, request, obj=None):
        # Al editar un pago ya registrado no se puede cambiar socio ni plan, ya que descuadraría la membresía
        return ["socio", "plan", "membresia_vence"] if obj else ["membresia_vence"]

    def delete_queryset(self, request, queryset):
        # El borrado masivo debe pasar por Pago.delete() para descontar los días de la membresía
        for pago in queryset:
            pago.delete()

    @admin.display(description="Monto", ordering="monto")
    def monto_fmt(self, obj):
        return pesos(obj.monto)

    @admin.display(description="Membresía vence")
    def membresia_vence(self, obj):
        return obj.membresia.fecha_fin.strftime("%d-%m-%Y") if obj.membresia else "-"
