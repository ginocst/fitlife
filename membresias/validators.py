"""
Validación de RUT
El dígito verificador se calcula con el algoritmo "módulo 11":
    1) Se multiplican los dígitos del RUT, de derecha a izquierda, por 2, 3, 4, 5, 6, 7, 2, 3...
    2) Se suman el total del resultado anterior.
    3) DV = 11 - (suma % 11).  Si da 11 -> '0'; si da 10 -> 'K'; en los demás el número es tal cual.
"""

from django.core.exceptions import ValidationError


def normalizar_rut(rut):
    """'12.345.678-5' -> '12345678-5' (sin puntos, DV en mayúscula)."""
    limpio = str(rut).replace(".", "").replace("-", "").replace(" ", "").upper()
    return f"{limpio[:-1]}-{limpio[-1]}" if len(limpio) > 1 else limpio


def formatear_rut(rut):
    """'12345678-5' -> '12.345.678-5' (para mostrar)."""
    numero, _, dv = normalizar_rut(rut).partition("-")
    return f"{int(numero):,}".replace(",", ".") + f"-{dv}" if numero.isdigit() else rut


def calcular_dv(numero):
    """Calcula el dígito verificador a partir del número del RUT (sin guion ni DV)."""
    suma, factor = 0, 2
    for digito in reversed(str(numero)):
        suma += int(digito) * factor
        factor = 2 if factor == 7 else factor + 1
    dv = 11 - (suma % 11)
    return {11: "0", 10: "K"}.get(dv, str(dv))


def validar_rut(rut):
    """Lanza ValidationError si el RUT no es válido."""
    numero, _, dv = normalizar_rut(rut).partition("-")
    if not numero.isdigit() or len(numero) < 7 or not dv:
        raise ValidationError("Formato de RUT inválido. Ejemplo: 12.345.678-5")
    if calcular_dv(numero) != dv:
        raise ValidationError("El dígito verificador del RUT no es correcto.")
