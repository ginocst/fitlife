"""
Django Admin: registros de acceso
Solo lectura: son la bitácora del torniquete y no deben editarse a mano.
"""

from django.contrib import admin

from fitlife.admin_utils import etiqueta

from .models import RegistroAcceso


@admin.register(RegistroAcceso)
class RegistroAccesoAdmin(admin.ModelAdmin):
    list_display = [
        "fecha_hora",
        "socio",
        "tipo",
        "resultado_color",
        "motivo",
        "tiempo_ms",
    ]
    list_filter = ["resultado", "tipo", "fecha_hora"]
    search_fields = [
        "socio__usuario__first_name",
        "socio__usuario__last_name",
        "socio__rut",
        "codigo",
    ]
    date_hierarchy = "fecha_hora"
    list_select_related = ["socio__usuario"]

    @admin.display(description="Resultado", ordering="resultado")
    def resultado_color(self, obj):
        return etiqueta(obj.resultado, obj.get_resultado_display())

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
