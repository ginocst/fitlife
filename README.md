# FitLife: control de asistencia y reserva de clases

Plataforma web para el centro deportivo FitLife. Resuelve tres problemas del caso: congestión en el acceso, sobrecupo en las clases grupales e ingreso de personas con la membresía vencida.

## Aplicación desplegada (AWS)

- **Sitio:** http://54.197.181.146/
- **Django Admin:** http://54.197.181.146/admin/
- **API REST navegable:** http://54.197.181.146/api/


### Arquitectura del despliegue:

- **VPC `fitlife-vpc`**
- **EC2 (Ubuntu Server)** en una subred pública, con IP elástica: Nginx recibe en el puerto 80 y pasa las peticiones a Gunicorn, que ejecuta Django.
- **Amazon RDS PostgreSQL** en las subredes privadas, sin acceso público. Solo acepta conexiones desde el grupo de seguridad de la EC2.

## Funcionalidades

| Requerimiento del caso | Dónde se resuelve |
|---|---|
| CRUD de planes, pagos y estados de membresía (Activa, Vencida, Congelada) | Django Admin y API `/api/planes/`, `/api/pagos/`, `/api/membresias/` |
| Validación y registro de acceso por QR | Página **Recepción** y `POST /api/accesos/validar/` |
| Reserva de clases con cupos y lista de espera automática | Página **Clases** y `/api/reservas/` |
| Dashboard de aforo en tiempo real | Página **Aforo** (se actualiza cada 3 s) y `GET /api/dashboard/` |

Reglas de negocio principales:

- Un **pago** crea la membresía o extiende la vigente; anularlo descuenta esos días.
- Una membresía activa cuya fecha pasó se marca **vencida** automáticamente.
- **Congelar** pausa la membresía; al descongelar se devuelven los días congelados.
- El mismo QR registra **entrada y salida**. Se rechaza el acceso por código desconocido, falta de membresía, membresía vencida o congelada, y aforo completo.
- Si una clase está llena, la reserva queda **en espera**; al cancelar alguien (o al aumentar el cupo) el primero de la lista sube solo.

## Tecnologías

Python 3.12+, Django 6.1, Django REST Framework, PostgreSQL (Amazon RDS en producción), HTML/CSS/JavaScript, Gunicorn y Nginx en AWS EC2 (Ubuntu).

## Roles y usuarios de prueba

Se crean con `python manage.py cargar_datos`. Clave de todos: `FitLife2026`.

| Usuario | Rol | Qué puede hacer |
|---|---|---|
| `admin` | Administrador (superusuario) | Todo, incluido el Django Admin completo |
| `recepcion` | Recepción (personal) | Validar accesos, ver el aforo, registrar pagos, congelar membresías |
| `gabriela`, `iara`, `sofia` | Socio con membresía activa | Ver su QR, reservar y cancelar clases |
| `angie` | Socio con membresía por vencer | Ver su QR, reservar y cancelar clases |
| `rebeca` | Socio con membresía vencida | Su acceso es rechazado |
| `abigail` | Socio con membresía congelada | Su acceso es rechazado |
| `maria` | Socio sin membresía | No puede entrar ni reservar |


## API REST

| Método y ruta | Quién | Qué hace |
|---|---|---|
| `GET/POST /api/planes/`, `PUT/PATCH/DELETE /api/planes/{id}/` | Leer: con sesión. Escribir: personal con permiso | CRUD de planes |
| `GET /api/socios/` | Personal | Consulta de socios |
| `GET/POST/PUT/PATCH/DELETE /api/membresias/` | Personal con permiso | CRUD de membresías |
| `POST /api/membresias/{id}/congelar/` y `/descongelar/` | Personal con permiso | Cambia el estado |
| `GET/POST/PUT/PATCH/DELETE /api/pagos/` | Personal con permiso | CRUD de pagos (crean o renuevan la membresía) |
| `GET/POST/PUT/PATCH/DELETE /api/clases/` | Leer: con sesión. Escribir: personal | CRUD de clases |
| `GET/POST /api/reservas/`, `DELETE /api/reservas/{id}/` | Socio (las suyas) y personal | Reservar y cancelar |
| `POST /api/accesos/validar/` | Personal | Valida un código QR |
| `GET /api/accesos/` | Personal | Registros de acceso del día |
| `GET /api/dashboard/` | Personal | Datos del aforo |
| `GET /api/aforo/` | Público | Porcentaje de ocupación |

# FitLife: control de asistencia y reserva de clases

Plataforma web para el centro deportivo FitLife. Resuelve tres problemas del caso: congestión en el acceso, sobrecupo en las clases grupales e ingreso de personas con la membresía vencida.

## Aplicación desplegada (AWS)

- **Sitio:** http://54.197.181.146/
- **Django Admin:** http://54.197.181.146/admin/
- **API REST navegable:** http://54.197.181.146/api/


### Arquitectura del despliegue:

- **VPC `fitlife-vpc`**
- **EC2 (Ubuntu Server)** en una subred pública, con IP elástica: Nginx recibe en el puerto 80 y pasa las peticiones a Gunicorn, que ejecuta Django.
- **Amazon RDS PostgreSQL** en las subredes privadas, sin acceso público. Solo acepta conexiones desde el grupo de seguridad de la EC2.

## Funcionalidades

| Requerimiento del caso | Dónde se resuelve |
|---|---|
| CRUD de planes, pagos y estados de membresía (Activa, Vencida, Congelada) | Django Admin y API `/api/planes/`, `/api/pagos/`, `/api/membresias/` |
| Validación y registro de acceso por QR | Página **Recepción** y `POST /api/accesos/validar/` |
| Reserva de clases con cupos y lista de espera automática | Página **Clases** y `/api/reservas/` |
| Dashboard de aforo en tiempo real | Página **Aforo** (se actualiza cada 3 s) y `GET /api/dashboard/` |

Reglas de negocio principales:

- Un **pago** crea la membresía o extiende la vigente; anularlo descuenta esos días.
- Una membresía activa cuya fecha pasó se marca **vencida** automáticamente.
- **Congelar** pausa la membresía; al descongelar se devuelven los días congelados.
- El mismo QR registra **entrada y salida**. Se rechaza el acceso por código desconocido, falta de membresía, membresía vencida o congelada, y aforo completo.
- Si una clase está llena, la reserva queda **en espera**; al cancelar alguien (o al aumentar el cupo) el primero de la lista sube solo.

## Tecnologías

Python 3.12+, Django 6.1, Django REST Framework, PostgreSQL (Amazon RDS en producción), HTML/CSS/JavaScript, Gunicorn y Nginx en AWS EC2 (Ubuntu).

## Roles y usuarios de prueba

Se crean con `python manage.py cargar_datos`. Clave de todos: `FitLife2026`.

| Usuario | Rol | Qué puede hacer |
|---|---|---|
| `admin` | Administrador (superusuario) | Todo, incluido el Django Admin completo |
| `recepcion` | Recepción (personal) | Validar accesos, ver el aforo, registrar pagos, congelar membresías |
| `gabriela`, `iara`, `sofia` | Socio con membresía activa | Ver su QR, reservar y cancelar clases |
| `angie` | Socio con membresía por vencer | Ver su QR, reservar y cancelar clases |
| `rebeca` | Socio con membresía vencida | Su acceso es rechazado |
| `abigail` | Socio con membresía congelada | Su acceso es rechazado |
| `maria` | Socio sin membresía | No puede entrar ni reservar |


## API REST

| Método y ruta | Quién | Qué hace |
|---|---|---|
| `GET/POST /api/planes/`, `PUT/PATCH/DELETE /api/planes/{id}/` | Leer: con sesión. Escribir: personal con permiso | CRUD de planes |
| `GET /api/socios/` | Personal | Consulta de socios |
| `GET/POST/PUT/PATCH/DELETE /api/membresias/` | Personal con permiso | CRUD de membresías |
| `POST /api/membresias/{id}/congelar/` y `/descongelar/` | Personal con permiso | Cambia el estado |
| `GET/POST/PUT/PATCH/DELETE /api/pagos/` | Personal con permiso | CRUD de pagos (crean o renuevan la membresía) |
| `GET/POST/PUT/PATCH/DELETE /api/clases/` | Leer: con sesión. Escribir: personal | CRUD de clases |
| `GET/POST /api/reservas/`, `DELETE /api/reservas/{id}/` | Socio (las suyas) y personal | Reservar y cancelar |
| `POST /api/accesos/validar/` | Personal | Valida un código QR |
| `GET /api/accesos/` | Personal | Registros de acceso del día |
| `GET /api/dashboard/` | Personal | Datos del aforo |
| `GET /api/aforo/` | Público | Porcentaje de ocupación |

## Consideraciones

Al registrarse como usuario en el sistema, considerar colocar un rut válido usando el algoritmo módulo 11, esto es sólo un plus para evitar datos falsos o erróneos.

Para asignarle un plan a un usuario, recepción o admin debe gestionar el pago a través del panel. El pago genera la membresía al usuario.