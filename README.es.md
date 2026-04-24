<sub>🇪🇸 **Español** · [🇬🇧 English](README.md)</sub>

# LicitMap

Plataforma web para explorar, analizar y recibir alertas de las licitaciones públicas españolas publicadas en el [PLACSP](https://contrataciondelestado.es/) (Plataforma de Contratación del Sector Público).

## Características

- **Búsqueda y filtrado** avanzado por CCAA, provincia, tipo de contrato, CPV, presupuesto y palabras clave.
- **Mapa interactivo** con licitaciones geolocalizadas por municipio (Leaflet).
- **Panel de análisis** con 10 gráficas sobre volumen, presupuesto, distribución geográfica y CPV.
- **Alertas por correo**: newsletter periódica, alertas personalizadas, suscripciones a entidad, seguimiento de licitaciones concretas.
- **Panel de administración** para gestionar usuarios, configuración SMTP y sincronización manual.
- **Sincronización automática** incremental con los feeds ATOM de PLACSP (cada 10 minutos + completa diaria).
- **Purga automática** de licitaciones antiguas configurable (años de histórico).
- **Exportación a Excel** de los resultados de búsqueda.
- **Interfaz bilingüe** español/inglés con selector en la navegación.

## Requisitos

- Debian 12+ o Ubuntu 22.04+
- 2 GB de RAM mínimo, 10 GB de disco libre
- Acceso a Internet (para descargar los feeds de PLACSP)
- Acceso como root (para instalar paquetes y configurar servicios)

## Instalación

```bash
git clone https://github.com/Ivisor/licitmap.git
cd licitmap
bash install.sh      # o 'sudo bash install.sh' si no eres root
```

El instalador es **interactivo** y pregunta:

- Ruta de instalación (por defecto `/opt/licitmap`)
- Usuario del sistema que ejecutará el servicio (por defecto `licitmap`)
- Credenciales del administrador (usuario, contraseña, correo)
- Años de histórico a mantener (por defecto 5)
- Tipo de PostgreSQL: **Docker**, **nativo** (apt, por defecto) o **externo**
- Configuración de nginx + Let's Encrypt (opcional)
- Configuración SMTP para envío de correos (opcional)
- Cuándo cargar los datos históricos (ahora, al primer cron, o no cargar)

Todos los parámetros tienen valores por defecto razonables: si das Enter a todo, obtienes una instalación funcional en localhost con PostgreSQL nativo, sin nginx, sin SMTP, con usuario `admin` y contraseña `admin` (se avisa al final para cambiarla).

Al finalizar, el servicio queda corriendo bajo `systemd`:

```bash
licitmap status              # resumen completo
systemctl status licitmap    # equivalente directo
licitmap logs                # logs de la app en vivo (tail de /var/log/licitmap.log)
```

## Desinstalación

Desinstalador interactivo — para el servicio, borra config/unit/CLI y opcionalmente elimina la base de datos y el usuario del sistema:

```bash
cd /ruta/al/licitmap-dev      # o donde esté clonado el repo
bash uninstall.sh
```

Versión manual (scripts, bucles de reinstalación limpia):

```bash
systemctl stop licitmap 2>/dev/null
systemctl disable licitmap 2>/dev/null
rm -f /etc/systemd/system/licitmap.service /etc/cron.d/licitmap /etc/default/licitmap
rm -f /usr/local/bin/licitmap /usr/bin/licitmap
rm -rf /opt/licitmap
rm -f /var/log/licitmap*.log
# PostgreSQL nativo (omitir si usaste Docker o externo)
runuser -u postgres -- psql -c "DROP DATABASE IF EXISTS licitmap;"
runuser -u postgres -- psql -c "DROP USER IF EXISTS licitmap;"
# Docker (si aplica)
# docker rm -f licitmap-db && docker volume rm licitmap-pgdata
# Nginx (si aplica)
# rm -f /etc/nginx/sites-enabled/licitmap /etc/nginx/sites-available/licitmap && systemctl reload nginx
userdel -r licitmap 2>/dev/null || true
git config --system --unset-all safe.directory 2>/dev/null || true
systemctl daemon-reload
```

Los paquetes del sistema (python, postgresql, docker, nginx, certbot) no se tocan para no afectar a otros servicios. Usa `apt remove` si quieres purgarlos.

## Estructura del proyecto

```
app/                 Código de la aplicación (FastAPI)
  database.py        Conexión a PostgreSQL (lee DATABASE_URL de .env)
  models.py          Modelos SQLAlchemy (User, Licitacion, Alerta, etc.)
  i18n.py            Traducciones y función t()
  routes/            Rutas HTTP (home, mapa, analisis, alertas, admin, auth)
  email_utils.py     Envío de correos SMTP
  parser.py          Parser de feeds ATOM de PLACSP
  utils.py           Helpers (navegación, settings, idioma)
scripts/
  licitmap           CLI de administración (instalado en /usr/local/bin/)
  sync.py            Sincronización incremental con PLACSP
  run_sync.sh        Wrapper bash usado por cron
  check_alertas.py   Procesa alertas y envía correos (cron horario)
static/              CSS, JS, datos (CPV, GeoJSON, coordenadas de municipios)
templates/           Plantillas HTML (sin Jinja2 — usa str.replace)
deploy/              Plantillas de systemd, nginx y cron
install.sh           Instalador interactivo
.env.example         Plantilla de configuración
```

## Configuración

Toda la configuración del runtime vive en `.env` (generado por el instalador):

```
DATABASE_URL=postgresql://licitmap:...@127.0.0.1:5432/licitmap
SECRET_KEY=<clave aleatoria>
HISTORY_YEARS=5
```

El resto de ajustes (SMTP, límites de exportación, políticas de seguridad) se gestionan desde el panel web en `/admin/config` y se guardan en la tabla `settings`.

## Idioma

LicitMap es bilingüe (español / inglés):

- **Interfaz web**: selector en la barra de navegación. La preferencia se guarda en cookie y, si hay sesión iniciada, también en el perfil del usuario.
- **CLI**: detecta automáticamente la variable `$LANG`. Override manual: `LICITMAP_LANG=en licitmap status` o con flag `licitmap --lang en status`.
- **Correos**: se envían en el idioma del usuario destinatario.
- **Datos de licitaciones**: título, organismo, CPV, etc. **no** se traducen — son los valores originales de PLACSP.

Idioma por defecto: español. Se puede cambiar sin salir de la sesión.

## CLI de administración

El instalador deja disponible el comando `licitmap` en el PATH del sistema. Cubre las operaciones más habituales sin necesidad de recordar rutas ni invocar `systemctl`/`runuser` a mano.

### Servicio

| Comando | Descripción |
|---|---|
| `licitmap status` | Resumen del servicio, conexión a BD, último sync y URL pública |
| `licitmap start` | Arranca el servicio |
| `licitmap stop` | Detiene el servicio |
| `licitmap restart` | Reinicia el servicio |
| `licitmap logs` | Logs de la app en vivo (equivalente a `journalctl -u licitmap -f`) |
| `licitmap logs sync` | Tail del log de sincronizaciones |
| `licitmap logs alertas` | Tail del log del procesado de alertas |
| `licitmap url` | Imprime la URL pública del servicio |

### Datos

| Comando | Descripción |
|---|---|
| `licitmap sync` | Sync rápido (máx. 5 páginas, ~250 licitaciones recientes) |
| `licitmap sync --full` | Sync completo con purga de históricos antiguos |
| `licitmap sync --since 2023-01-01` | Sync histórico desde la fecha indicada |
| `licitmap stats` | Estadísticas de la BD (licitaciones, usuarios, alertas) |

### Administración

| Comando | Descripción |
|---|---|
| `licitmap config` | Muestra `.env` con secretos enmascarados |
| `licitmap admin reset-password` | Resetea la contraseña del admin interactivamente |
| `licitmap update` | `git pull` + reinstala dependencias + reinicia el servicio |
| `licitmap version` | Muestra el commit desplegado |
| `licitmap help` | Ayuda completa con ejemplos (alias: `-h`, `--help`) |

### Ajustes fuera del CLI

- **Años de histórico**: editar `HISTORY_YEARS` en `/opt/licitmap/.env` y ejecutar `licitmap restart`.
- **SMTP, límite de exportación, políticas de seguridad**: desde el panel web en `/admin/config` (se guardan en la tabla `settings`).
- **Cambiar puerto o dominio**: reconfigurar nginx en `/etc/nginx/sites-available/licitmap` y la unidad systemd en `/etc/systemd/system/licitmap.service`.

### Cron instalado

```
*/10 * * * *  licitmap  run_sync.sh --max-pages 3       # sync rápido
0    3 * * *  licitmap  run_sync.sh                     # sync completo + purga
0    * * * *  licitmap  python check_alertas.py         # alertas email
```

## Desarrollo local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# editar .env con DATABASE_URL a tu Postgres local
uvicorn main:app --reload
```

## Stack

- **Backend**: FastAPI, SQLAlchemy 2.x, PostgreSQL 17
- **Frontend**: Bootstrap 5, vanilla JS, Chart.js, Leaflet
- **Infraestructura**: systemd, nginx (opcional), cron, Docker (opcional para PostgreSQL)

## Licencia

Este proyecto no tiene licencia explícita. Contacta con el autor para uso comercial.
