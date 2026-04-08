# LicitMap

Plataforma web open source de licitaciones públicas de España. Consulta, filtra y visualiza en un mapa interactivo las licitaciones del Estado español.

## Estado actual del proyecto (08/04/2026)

El proyecto tiene una base funcional mínima:
- FastAPI sirviendo una web con listado de 406 licitaciones reales
- Base de datos PostgreSQL con tabla `licitaciones` poblada
- Parser XML funcional que extrae datos de los feeds Atom de PLACSP
- Estructura de carpetas profesional con rutas separadas, templates y estáticos
- Bootstrap 5 integrado por CDN

Solo se ha cargado el archivo principal del ZIP de marzo 2026. El ZIP contiene decenas de archivos .atom adicionales con miles de licitaciones más.

## Stack tecnológico

- **Backend**: FastAPI + Python 3.13 (servidor Debian 13)
- **Base de datos**: PostgreSQL 17 corriendo en Docker (`docker run`, no compose)
- **ORM**: SQLAlchemy (DeclarativeBase)
- **Frontend**: Templates HTML con Bootstrap 5 (CDN) + CSS custom
- **Datos**: XML Atom de PLACSP (Plataforma de Contratación del Sector Público)
- **Servidor dev**: `uvicorn main:app --reload --host 0.0.0.0`

## Bugs conocidos / Workarounds

- **Jinja2 3.1.6 tiene un bug con Python 3.13+** (`unhashable type: 'dict'` en el LRU cache). Fijado a versión 3.1.5 en requirements.txt. Como workaround adicional, los templates se renderizan con `Path().read_text()` y `str.replace()` manual en vez de `Jinja2Templates` de Starlette.
- El container Docker de PostgreSQL se llama `licitmap-db` y se lanzó con `docker run -d`, no con docker-compose.

## Estructura de carpetas

```
~/licitmap/
├── app/
│   ├── __init__.py
│   ├── database.py        # Conexión PostgreSQL (SQLAlchemy)
│   ├── models.py           # Modelo Licitacion
│   ├── parser.py           # Parser XML Atom de PLACSP
│   └── routes/
│       ├── __init__.py
│       └── home.py         # Ruta "/" con listado de licitaciones
├── static/
│   ├── css/
│   │   └── style.css       # Estilos custom (badges de estado, tabla)
│   ├── js/
│   │   └── app.js          # Vacío por ahora
│   └── img/
├── templates/
│   ├── base.html           # Layout base (navbar, Bootstrap CDN, footer)
│   └── home.html           # Tabla de licitaciones
├── scripts/
│   ├── init_db.py          # Crea las tablas en PostgreSQL
│   └── load_data.py        # Carga datos desde archivo .atom a la DB
├── data/                    # ZIPs y archivos .atom descargados
│   ├── marzo2026.zip
│   └── licitacionesPerfilesContratanteCompleto3.atom
├── main.py                  # Punto de entrada FastAPI
├── requirements.txt
└── CLAUDE.md
```

## Base de datos

### Conexión
```
postgresql://licitmap:licitmap@localhost:5432/licitmap
```

### Container Docker
```bash
docker run -d \
  --name licitmap-db \
  -e POSTGRES_USER=licitmap \
  -e POSTGRES_PASSWORD=licitmap \
  -e POSTGRES_DB=licitmap \
  -p 5432:5432 \
  --restart unless-stopped \
  postgres:17
```

### Modelo Licitacion
| Campo               | Tipo     | Notas                          |
|---------------------|----------|--------------------------------|
| id                  | Integer  | PK, autoincrement              |
| expediente          | String   | Unique, indexed                |
| titulo              | String   |                                |
| organo_contratacion | String   |                                |
| estado              | String   | PUB, ADJ, PRE, RES, EV, ANUL  |
| presupuesto         | Float    | Sin impuestos (EUR)            |
| fecha_publicacion   | DateTime |                                |
| comunidad_autonoma  | String   |                                |
| url                 | String   | Link a PLACSP                  |

## Fuente de datos: PLACSP

### Descarga de ZIPs mensuales
URL patrón:
```
https://contrataciondelsectorpublico.gob.es/sindicacion/sindicacion_643/licitacionesPerfilesContratanteCompleto3_AAAAMM.zip
```
Ejemplo marzo 2026: `...Completo3_202603.zip`

Hay ZIPs disponibles desde 2012. Archivos anuales completos y mensuales del año en curso.

### Estructura del XML
- Formato: Atom (RFC 4287) + namespaces CODICE de la DGPE
- Cada `<entry>` es una licitación o actualización de licitación
- El archivo principal es `licitacionesPerfilesContratanteCompleto3.atom`
- Tiene paginación: `<link rel="next">` apunta al siguiente archivo .atom
- Cada ZIP mensual contiene decenas de archivos .atom encadenados
- Máximo 500 entries por archivo

### Namespaces XML
```python
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "cbc": "urn:dgpe:names:draft:codice:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:dgpe:names:draft:codice:schema:xsd:CommonAggregateComponents-2",
    "cac-place-ext": "urn:dgpe:names:draft:codice-place-ext:schema:xsd:CommonAggregateComponents-2",
    "cbc-place-ext": "urn:dgpe:names:draft:codice-place-ext:schema:xsd:CommonBasicComponents-2",
}
```

### Campos extraídos por entry
| Dato                 | XPath desde entry                                                                     |
|----------------------|---------------------------------------------------------------------------------------|
| expediente           | `cac-place-ext:ContractFolderStatus/cbc:ContractFolderID`                            |
| titulo               | `.../cac:ProcurementProject/cbc:Name`                                                |
| organo_contratacion  | `.../cac-place-ext:LocatedContractingParty/cac:Party/cac:PartyName/cbc:Name`        |
| estado               | `.../cbc-place-ext:ContractFolderStatusCode`                                         |
| presupuesto          | `.../cac:BudgetAmount/cbc:TaxExclusiveAmount`                                        |
| fecha_publicacion    | `atom:updated`                                                                        |
| comunidad_autonoma   | Se extrae de la cadena `ParentLocatedParty` buscando contra lista conocida de CCAA   |
| url                  | `atom:link/@href`                                                                     |

### Detección de Comunidad Autónoma
La jerarquía `ParentLocatedParty` tiene profundidad variable:
- `[municipio, "Ayuntamientos", CCAA, "ENTIDADES LOCALES", "Sector Público"]`
- `[municipio, "Ayuntamientos", provincia, CCAA, "ENTIDADES LOCALES", "Sector Público"]`

Se recorre la cadena y se busca coincidencia contra un set de las 19 CCAA/ciudades autónomas.

### Estados de licitación conocidos
- **PUB** — Publicada (abierta a ofertas)
- **ADJ** — Adjudicada
- **PRE** — Preevaluación
- **RES** — Resuelta
- **EV** — En evaluación
- **ANUL** — Anulada

## Tareas pendientes (por orden de prioridad)

### 1. Cargar todos los datos del ZIP
Actualmente solo se parsea el archivo principal (`licitacionesPerfilesContratanteCompleto3.atom`). El ZIP de marzo contiene decenas de archivos .atom con miles de licitaciones más. Hay que:
- Descomprimir el ZIP completo
- Parsear TODOS los archivos .atom del ZIP
- Upsert en la DB (actualizar si el expediente ya existe, insertar si es nuevo)
- Considerar descargar y procesar ZIPs de meses/años anteriores

### 2. Filtros y búsqueda
- Filtrar por CCAA (dropdown)
- Filtrar por estado (PUB, ADJ, PRE, etc.)
- Filtrar por rango de presupuesto
- Búsqueda por texto (título, órgano, expediente)
- Paginación de resultados (ahora limitado a 100)

### 3. Mapa interactivo
- Leaflet.js para mostrar mapa de España
- Licitaciones agrupadas por CCAA
- Click en CCAA para ver sus licitaciones
- La tabla de municipios del INE puede servir para geolocalizar por código postal

### 4. Carga automática de datos
- Script/cron que descargue el ZIP del mes actual periódicamente
- Feed Atom en vivo (si vuelve a funcionar; estuvo caído desde oct 2025)
- Carga incremental diaria

### 5. Mejoras de diseño
- Responsive completo
- Dark mode
- Gráficos de estadísticas (licitaciones por CCAA, por estado, evolución temporal)
- Detalle de licitación individual (página propia)

### 6. Preparar para producción
- Variables de entorno (.env) para credenciales DB
- Docker Compose como método de instalación secundario
- Script bash de instalación como método principal
- Nginx como reverse proxy
- Systemd service para uvicorn
- Alembic para migraciones de DB

## Comandos útiles

```bash
# Activar entorno
cd ~/licitmap && source .venv/bin/activate

# Arrancar servidor
uvicorn main:app --reload --host 0.0.0.0

# Arrancar en background
nohup uvicorn main:app --reload --host 0.0.0.0 > uvicorn.log 2>&1 &

# Parar servidor
kill $(pgrep -f uvicorn)

# Ver logs
tail -f uvicorn.log

# Crear tablas
python scripts/init_db.py

# Cargar datos
python scripts/load_data.py

# Verificar DB
docker exec licitmap-db psql -U licitmap -c "SELECT count(*) FROM licitaciones;"

# Descargar ZIP de un mes
wget -O data/AAAAMM.zip "https://contrataciondelsectorpublico.gob.es/sindicacion/sindicacion_643/licitacionesPerfilesContratanteCompleto3_AAAAMM.zip"
```
