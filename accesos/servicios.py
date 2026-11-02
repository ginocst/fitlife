"""
Lógica de acceso y aforo

Cómo funciona el torniquete:
    - El mismo QR sirve para entrar y salir: si el socio está DENTRO, la lectura registra su SALIDA;
        si está FUERA, se valida su membresía y el aforo antes de dejarlo ENTRAR.
    - "Dentro" = su último movimiento PERMITIDO de hoy fue una ENTRADA.
        Al cambiar el día se parte de cero (quien olvidó marcar salida no queda contado para siempre).

Velocidad: la búsqueda del socio usa el índice único de codigo_qr, así que toma pocos milisegundos.
"""

import time
import uuid

from django.conf import settings
from django.db.models import OuterRef, Subquery
from django.utils import timezone

from membresias.models import Membresia, Socio

from .models import RegistroAcceso


def _ultimos_movimientos_de_hoy():
    """Subconsulta: el tipo (ENTRADA/SALIDA) del último acceso permitido de hoy de cada socio."""
    return (
        RegistroAcceso.objects.filter(
            socio=OuterRef("pk"),
            resultado=RegistroAcceso.Resultado.PERMITIDO,
            fecha_hora__date=timezone.localdate(),
        )
        .order_by("-fecha_hora")
        .values("tipo")[:1]
    )


def socios_dentro():
    """Socios que están ahora en las instalaciones."""
    return (
        Socio.objects.annotate(ultimo=Subquery(_ultimos_movimientos_de_hoy()))
        .filter(ultimo=RegistroAcceso.Tipo.ENTRADA)
        .select_related("usuario")
    )


def aforo_actual():
    return socios_dentro().count()


def esta_dentro(socio):
    ultimo = (
        RegistroAcceso.objects.filter(
            socio=socio,
            resultado=RegistroAcceso.Resultado.PERMITIDO,
            fecha_hora__date=timezone.localdate(),
        )
        .order_by("-fecha_hora")
        .values_list("tipo", flat=True)
        .first()
    )
    return ultimo == RegistroAcceso.Tipo.ENTRADA


def motivo_sin_membresia(socio):
    """Explica por qué el socio no tiene una membresía vigente (y actualiza su estado si venció)."""
    actual = socio.membresia_actual()
    if actual is None:
        return "Sin membresía"
    if actual.estado == Membresia.Estado.CONGELADA:
        return "Membresía congelada"
    if actual.fecha_inicio > timezone.localdate():
        return f"Membresía comienza el {actual.fecha_inicio:%d-%m-%Y}"
    if actual.estado_actual == Membresia.Estado.VENCIDA:
        if actual.estado == Membresia.Estado.ACTIVA:  # venció y aún no se había marcado
            actual.estado = Membresia.Estado.VENCIDA
            actual.save(update_fields=["estado"])
        return f"Membresía vencida el {actual.fecha_fin:%d-%m-%Y}"
    return "Membresía no vigente"


def procesar_codigo(codigo):
    """
    Valida una lectura del QR y deja el registro en la base de datos.
    Devuelve el RegistroAcceso creado (con resultado y motivo).
    """
    inicio = time.perf_counter()
    codigo = (codigo or "").strip()
    socio, tipo = None, RegistroAcceso.Tipo.ENTRADA

    # ¿El código corresponde a un socio?
    try:
        socio = (
            Socio.objects.select_related("usuario")
            .filter(codigo_qr=uuid.UUID(codigo))
            .first()
        )
    except ValueError:
        socio = None

    if socio is None:
        resultado, motivo = RegistroAcceso.Resultado.DENEGADO, "Código no reconocido"
    elif esta_dentro(socio):
        # Ya estaba dentro: esta lectura es su salida
        tipo, resultado, motivo = (
            RegistroAcceso.Tipo.SALIDA,
            RegistroAcceso.Resultado.PERMITIDO,
            "Salida registrada",
        )
    elif socio.membresia_vigente() is None:
        # Quiere entrar sin membresía vigente
        resultado, motivo = (
            RegistroAcceso.Resultado.DENEGADO,
            motivo_sin_membresia(socio),
        )
    elif aforo_actual() >= settings.AFORO_MAXIMO:
        # Instalaciones llenas
        resultado, motivo = (
            RegistroAcceso.Resultado.DENEGADO,
            "Aforo completo, intenta en unos minutos",
        )
    else:
        resultado, motivo = RegistroAcceso.Resultado.PERMITIDO, "Bienvenido/a"

    return RegistroAcceso.objects.create(
        socio=socio,
        codigo=codigo[:64],
        tipo=tipo,
        resultado=resultado,
        motivo=motivo,
        tiempo_ms=round((time.perf_counter() - inicio) * 1000, 2),
    )


def datos_dashboard():
    """Todo lo que muestra el dashboard de aforo, calculado en el servidor."""
    from django.db.models import Avg, Count, Q

    from clases.models import Clase, Reserva

    Membresia.vencer_caducadas()
    hoy = timezone.localdate()
    actual, maximo = aforo_actual(), settings.AFORO_MAXIMO
    porcentaje = round(actual * 100 / maximo) if maximo else 0
    registros_hoy = RegistroAcceso.objects.filter(fecha_hora__date=hoy)
    resumen = registros_hoy.aggregate(
        entradas=Count(
            "id",
            filter=Q(
                tipo=RegistroAcceso.Tipo.ENTRADA,
                resultado=RegistroAcceso.Resultado.PERMITIDO,
            ),
        ),
        denegados=Count("id", filter=Q(resultado=RegistroAcceso.Resultado.DENEGADO)),
        promedio_ms=Avg("tiempo_ms"),
    )
    clases_hoy = Clase.objects.filter(inicio__date=hoy).annotate(
        conf=Count("reservas", filter=Q(reservas__estado=Reserva.Estado.CONFIRMADA)),
        espera=Count("reservas", filter=Q(reservas__estado=Reserva.Estado.EN_ESPERA)),
    )
    return {
        "aforo_actual": actual,
        "aforo_maximo": maximo,
        "porcentaje": porcentaje,
        # semáforo: verde < 70%, amarillo < 90%, rojo desde 90%
        "nivel": "alto"
        if porcentaje >= 90
        else "medio"
        if porcentaje >= 70
        else "bajo",
        "entradas_hoy": resumen["entradas"],
        "denegados_hoy": resumen["denegados"],
        "tiempo_promedio_ms": round(resumen["promedio_ms"] or 0, 2),
        "membresias": {
            e: Membresia.objects.filter(estado=e).count()
            for e in Membresia.Estado.values
        },
        "dentro": [str(s) for s in socios_dentro()[:30]],
        "clases_hoy": [
            {
                "nombre": c.nombre,
                "inicio": timezone.localtime(c.inicio).strftime("%H:%M"),
                "sala": c.sala,
                "confirmadas": c.conf,
                "cupo": c.cupo,
                "en_espera": c.espera,
            }
            for c in clases_hoy
        ],
        "ultimos_accesos": [
            {
                "hora": timezone.localtime(r.fecha_hora).strftime("%H:%M:%S"),
                "socio": str(r.socio) if r.socio else "(desconocido)",
                "tipo": r.tipo,
                "resultado": r.resultado,
                "motivo": r.motivo,
            }
            for r in registros_hoy.select_related("socio__usuario")[:10]
        ],
        "actualizado": timezone.localtime().strftime("%H:%M:%S"),
    }
