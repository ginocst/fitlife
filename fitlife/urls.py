"""
Urls del proyecto
    Páginas web -> /  /registro/  /login/  /logout/  /panel/  /clases/  /recepcion/  /dashboard/
    Django Admin -> /admin/
    API REST -> /api/...
"""

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from django.urls import include, path, re_path
from rest_framework.routers import DefaultRouter

from accesos import api as accesos_api
from accesos import views as accesos_views
from clases import api as clases_api
from clases import views as clases_views
from membresias import api as membresias_api
from membresias import views as membresias_views

from . import views

# El router genera las rutas CRUD de cada ViewSet (lista, detalle, crear, editar, borrar)
router = DefaultRouter()
router.register("planes", membresias_api.PlanViewSet)
router.register("socios", membresias_api.SocioViewSet)
router.register("membresias", membresias_api.MembresiaViewSet)
router.register("pagos", membresias_api.PagoViewSet)
router.register("clases", clases_api.ClaseViewSet)
router.register("reservas", clases_api.ReservaViewSet)
router.register("accesos", accesos_api.RegistroAccesoViewSet)

urlpatterns = [
    # Páginas web
    path("", views.inicio, name="inicio"),
    path("registro/", membresias_views.registro, name="registro"),
    path(
        "login/",
        auth_views.LoginView.as_view(redirect_authenticated_user=True),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("despues-login/", views.despues_login, name="despues_login"),
    path("panel/", membresias_views.panel, name="panel"),
    path("qr/<uuid:codigo>.svg", membresias_views.qr_svg, name="qr_socio"),
    path("clases/", clases_views.clases, name="clases"),
    path("recepcion/", accesos_views.recepcion, name="recepcion"),
    path("dashboard/", accesos_views.dashboard, name="dashboard"),
    # Django Admin
    path("admin/", admin.site.urls),
    # API REST
    path("api/accesos/validar/", accesos_api.validar_codigo, name="api_validar"),
    path("api/dashboard/", accesos_api.dashboard, name="api_dashboard"),
    path("api/aforo/", accesos_api.aforo_publico, name="api_aforo"),
    path("api/", include(router.urls)),
    # Repath, cualquier URL desconocida lleva automáticamente al inicio (por ej: 127.0.0.1/XXX)
    re_path(r"^.*$", lambda request: redirect("inicio")),
]
