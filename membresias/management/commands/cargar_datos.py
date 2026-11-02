"""
Datos de prueba

Crea usuarios con cada rol, planes, socios en todos los estados de membresía, pagos,
clases (una llena con lista de espera) y movimientos de acceso de hoy.
Si los datos ya existen, no hace nada (se puede ejecutar varias veces).
"""

from datetime import timedelta

from django.contrib.auth.models import Group, Permission, User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accesos.servicios import procesar_codigo
from clases.models import Clase, Reserva
from membresias.models import Membresia, Pago, Plan, Socio
from membresias.validators import calcular_dv

CLAVE = "FitLife2026"

PLANES = [  # (nombre, precio, días, descripción)
    ("Pase diario", 5000, 1, "Ideal para probar."),
    ("Mensual", 29990, 30, "Acceso libre y clases grupales."),
    ("Trimestral", 79990, 90, "Ahorra un 11% frente al mensual."),
    ("Anual", 249990, 365, "El mejor precio por mes."),
]

# (usuario, nombre, apellido, número de RUT, situación de la membresía)
SOCIOS = [
    ("sofia", "Sofía", "Espinoza", 15234567, "activa"),
    ("rebeca", "Rebeca", "Díaz", 16345678, "vencida"),
    ("abigail", "Abigail", "Muñoz", 17456789, "congelada"),
    ("angie", "Angie", "Mora", 18567890, "por_vencer"),
    ("maria", "María", "Cardozo", 19678901, "sin_membresia"),
    ("iara", "Iara", "Anderson", 20789012, "activa"),
    ("gabriela", "Gabriela", "Romero", 21890123, "activa"),
]

# Permisos del rol Recepción: consulta casi todo, registra pagos y gestiona membresías y reservas
PERMISOS_RECEPCION = [
    "view_plan",
    "view_socio",
    "change_socio",
    "view_membresia",
    "change_membresia",
    "view_pago",
    "add_pago",
    "view_clase",
    "view_reserva",
    "change_reserva",
    "view_registroacceso",
]


class Command(BaseCommand):
    help = "Carga datos de prueba para FitLife."

    @transaction.atomic
    def handle(self, *args, **options):
        if Plan.objects.exists():
            self.stdout.write(
                self.style.WARNING("Los datos de prueba ya están cargados.")
            )
            return

        hoy = timezone.localdate()

        # ---- Personal ----
        User.objects.create_superuser(
            "admin", "admin@fitlife.cl", CLAVE, first_name="Administración"
        )
        recepcion = User.objects.create_user(
            "recepcion",
            "recepcion@fitlife.cl",
            CLAVE,
            first_name="Recepción",
            is_staff=True,
        )
        grupo, _ = Group.objects.get_or_create(name="Recepción")
        grupo.permissions.set(
            Permission.objects.filter(codename__in=PERMISOS_RECEPCION)
        )
        recepcion.groups.add(grupo)

        # ---- Planes ----
        planes = {
            n: Plan.objects.create(nombre=n, precio=p, duracion_dias=d, descripcion=t)
            for n, p, d, t in PLANES
        }

        # ---- Socios: la membresía nace de un PAGO ----
        socios = {}
        for usuario, nombre, apellido, numero, situacion in SOCIOS:
            user = User.objects.create_user(
                usuario,
                f"{usuario}@live.cl",
                CLAVE,
                first_name=nombre,
                last_name=apellido,
            )
            socio = Socio.objects.create(
                usuario=user,
                rut=f"{numero}-{calcular_dv(numero)}",
                telefono="+56911112222",
            )
            socios[usuario] = socio
            if situacion == "sin_membresia":
                continue
            pago = Pago.objects.create(
                socio=socio, plan=planes["Mensual"], medio=Pago.Medio.DEBITO
            )
            m = pago.membresia
            if (
                situacion == "vencida"
            ):  # se "retrocede" en el tiempo para simular un plan antiguo
                m.fecha_inicio, m.fecha_fin = (
                    hoy - timedelta(days=40),
                    hoy - timedelta(days=11),
                )
                m.save()
            elif situacion == "por_vencer":
                m.fecha_inicio, m.fecha_fin = (
                    hoy - timedelta(days=28),
                    hoy + timedelta(days=1),
                )
                m.save()
            elif situacion == "congelada":
                m.congelar()
                m.congelada_desde = hoy - timedelta(days=5)
                m.save()
        Membresia.vencer_caducadas()

        # ---- Clases: desde la próxima hora en punto, para hoy y los dos días siguientes ----
        base = timezone.localtime().replace(
            minute=0, second=0, microsecond=0
        ) + timedelta(hours=1)
        programa = [  # (nombre, instructor, sala, horas desde "base", cupo)
            # Cupo pequeño: se llena y genera lista de espera
            ("Zumba", "Paula", "Sala 1", 0, 3),
            ("HIIT", "José", "Sala 2", 2, 12),
            ("Funcional", "Camila", "Sala 1", 4, 10),
            ("Zumba", "Paula", "Sala 1", 24, 15),
            ("Pilates", "Laura", "Sala 2", 26, 10),
            ("HIIT", "José", "Sala 2", 48, 12),
        ]
        clases = [
            Clase.objects.create(
                nombre=n, instructor=i, sala=s, inicio=base + timedelta(hours=h), cupo=c
            )
            for n, i, s, h, c in programa
        ]

        # Zumba lleno: 3 confirmados y 1 en espera
        for usuario in ["sofia", "iara", "gabriela", "angie"]:
            Reserva.reservar(clases[0], socios[usuario])
        Reserva.reservar(clases[1], socios["sofia"])

        # ---- Accesos de hoy: Sofía entra, Angie entra y sale, Rebeca es rechazada ----
        for usuario in ["sofia", "angie", "angie", "rebeca"]:
            procesar_codigo(str(socios[usuario].codigo_qr))
        procesar_codigo("codigo-falso-123")

        self.stdout.write(
            self.style.SUCCESS(
                "Datos cargados. Usuarios: admin, recepcion, sofia, rebeca, abigail, "
                "angie, maria, iara, gabriela "
                f"(clave: {CLAVE})"
            )
        )
