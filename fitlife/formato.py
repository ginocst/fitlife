"""Formatos de presentación compartidos (templates y admin)."""


def pesos(monto):
    """29990 -> '$29.990'."""
    return f"${monto:,.0f}".replace(",", ".")
