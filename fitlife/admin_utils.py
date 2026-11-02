"""
Utilidades compartidas del Django admin
Dibuja los estados (Activa, Vencida, Confirmada...) como etiquetas de color en los listados.
"""

from django.utils.html import format_html

COLORES = {
    "ACTIVA": "#1e8e5a",
    "PERMITIDO": "#1e8e5a",
    "CONFIRMADA": "#1e8e5a",
    "VENCIDA": "#c8322f",
    "DENEGADO": "#c8322f",
    "CANCELADA": "#7a7f8c",
    "CONGELADA": "#2f6fb7",
    "EN_ESPERA": "#c98a00",
}


def etiqueta(valor, texto):
    """Devuelve HTML seguro (format_html escapa el texto) con una etiqueta de color."""
    return format_html(
        '<span style="background:{};color:#fff;padding:2px 9px;border-radius:10px;'
        'font-size:11px;font-weight:700;white-space:nowrap">{}</span>',
        COLORES.get(valor, "#555"),
        texto,
    )
