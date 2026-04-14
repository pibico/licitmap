# LicitMap — Documentación del proyecto

Plataforma web de licitaciones públicas españolas (PLACSP).

## Stack
- Backend: FastAPI + Python 3.13, SQLAlchemy ORM (síncrono)
- DB: PostgreSQL 17 en Docker (`licitmap-db`, puerto 5432)
- Frontend: Templates HTML con Bootstrap 5 — renderizado manual con `Path().read_text()` + `str.replace()`. Jinja2 3.1.6 tiene bug con Python 3.13; NO actualizar.
- Servidor: uvicorn gestionado por supervisor (2 workers, puerto 8000)
- Proxy: nginx con SSL Let's Encrypt en `https://ivan.pibico.es`
- Repo: https://github.com/Ivisor/licitmap (branch main, SSH configurado)

## DB
- Conexión: `postgresql://licitmap:licitmap@localhost:5432/licitmap`
- ~22.800 licitaciones únicas (17-31 marzo 2026), 100% con municipio/CP/provincia
- Clave única: `atom_id` (ID interno PLACSP) — `expediente` NO es único globalmente

## Modelo `Licitacion`
| Campo | Notas |
|-------|-------|
| atom_id | PK única (URL interna PLACSP) |
| expediente | Indexado, no único globalmente |
| titulo, organo_contratacion, estado | String |
| presupuesto | Float, sin IVA |
| fecha_publicacion | DateTime |
| fecha_limite | Date — plazo de presentación |
| tipo_contrato | Código numérico CODICE (1=Obras, 2=Servicios, 3=Suministros…) |
| comunidad_autonoma | CCAA, Extra-Regio, Todo el territorio, Extranjero |
| pais | "España" para nacionales, nombre del país para extranjeros |
| url | Link a PLACSP |
| cpv | Códigos CPV separados por espacio (índice btree eliminado — supera 2700 bytes) |
| municipio | CityName de LocatedContractingParty/Party/PostalAddress |
| codigo_postal | PostalZone (5 dígitos) |
| provincia | Derivada del código postal (2 primeros dígitos → nombre de provincia) |

## Filtros y parámetros de URL (búsqueda `/`)
| Param | Descripción |
|-------|-------------|
| q | Texto libre (título, órgano, expediente) |
| cpv_q | Búsqueda solo por CPV |
| pais | "" (Todos), "España", "__intl__", o nombre de país |
| ccaa | CCAA pipe-separated: "Madrid\|Cataluña" |
| estado | Código pipe-separated: "PUB\|ADJ" |
| tipo | Código tipo pipe-separated: "1\|2" |
| prange | Rango presupuesto pipe-separated: "100k\|1m" |
| fecha_desde / fecha_hasta | Fecha límite (YYYY-MM-DD) |
| municipio | Texto (ilike) |
| provincia | Nombre exacto de provincia |
| per_page | 5/10/15/20 (default 20) |
| orden | "asc" pronta finalización (default), "desc" más tiempo |
| partial | "1" para respuesta JSON (AJAX) |

## Layout búsqueda
- Dos columnas: sidebar izquierdo (col-lg-3) + cards (col-lg-9)
- Dos barras de búsqueda: principal (q) + CPV separada (cpv_q)
- Stats bar: Total | En plazo ahora | Resultados filtrados | Última sync
- Sidebar: Fecha límite → Tipo → Presupuesto → Territorio (radio) → CCAA/País → Provincia (autocomplete) → Municipio (autocomplete) → Estado
- PER_PAGE dinámico: 5/10/15/20
- Sidebar facetado: cada sección ignora su propio filtro para los conteos; ítems con 0 permanecen visibles

## Funcionamiento AJAX
- `fetchResultados()` en `app.js` hace fetch a `/?partial=1&...params`
- Actualiza URL con `history.replaceState`
- Backend devuelve JSON: `{filas, paginacion, resultados, en_plazo, sidebar, municipio}`
- Al seleccionar CCAA: auto-activa España si no está seleccionado

## Mapa (`/mapa`)
- Leaflet + GeoJSONs locales (ccaa, provincias, municipios en `static/data/`)
- Coropleta con 3 niveles según zoom: CCAA (zoom <7), Provincias (7-9), Municipios (≥9)
- **Click en CCAA** → navega a búsqueda con `pais=España&ccaa=<nombre>`
- **Click en provincia** → navega a búsqueda con `pais=España&provincia=<nombre>`
- **Click en municipio** → navega a búsqueda con `pais=España&municipio=<nombre>`
- Sidebar del mapa: mismos filtros que búsqueda (q, cpv_q, tipo, estado, prange, fechas, provincia, municipio) — se arrastran al navegar
- Stats AJAX via `/api/mapa` (actualiza en_plazo y resultados filtrados)
- Caché API: 30s por nivel; prefetch silencioso de GeoJSONs al cargar
- `static/data/municipios_coords.json`: ~170 municipios con lat/lng (pendiente ampliar)

## APIs del mapa
- `GET /api/mapa` → conteos por CCAA + stats globales
- `GET /api/mapa/provincias` → conteos por provincia
- `GET /api/mapa/municipios` → conteos por municipio
- `GET /api/mapa/nombres` → listas para autocomplete (provincias + municipios)

## Sistema de temas (dark/light)
- Toggle sol/luna en navbar, persistencia en localStorage
- Atributo `data-theme="dark"` en `<html>`
- Light "Zinc": Base #f4f4f5 | Texto #18181b | Acento #059669
- Dark "Slate": Base #20232b | Texto #e2e8f4 | Acento #34d399

## Infraestructura
- Supervisor: `/etc/supervisor/conf.d/licitmap.conf`
- Nginx: proxy + static + SSL. `/root` tiene permisos 701 para nginx
- Cache estáticos nginx: `expires 7d` → cache-busting con `?v=N` (actualmente v=45)
- SSL: Let's Encrypt, expira 2026-07-08
- Logs: `/var/log/supervisor/licitmap.{out,err}.log`

## Tareas pendientes
- Ampliar cobertura de coordenadas en `municipios_coords.json`
- Decidir volumen de datos en producción (ahora ~22.800 como muestra)
- Optimizar sync incremental (solo insertar novedades)
