# External Integrations

**Analysis Date:** 2026-04-09

## APIs & External Services

**Public Procurement Data (PLACSP):**
- Service: Plataforma de Contratación del Sector Público — Spanish government open data
- Access: Static ZIP file downloads (no API key required, public data)
- URL pattern: `https://contrataciondelsectorpublico.gob.es/sindicacion/sindicacion_643/licitacionesPerfilesContratanteCompleto3_AAAAMM.zip`
- Format: XML Atom feeds (RFC 4287) with CODICE namespaces from DGPE
- Data scope: All public tenders in Spain, from 2012 to present, monthly ZIPs
- Auth: None — fully public
- SDK/Client: Python stdlib `xml.etree.ElementTree` + `zipfile` in `app/parser.py` and `scripts/load_data.py`
- Live Atom feed: Was available but has been down since October 2025; ZIP downloads are the active method

**CDN (Bootstrap + JS):**
- Bootstrap 5.3.3 CSS: `https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css`
- Bootstrap 5.3.3 JS Bundle: `https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js`
- Provider: jsDelivr CDN
- No local copy — requires internet access to render pages correctly

## Data Storage

**Databases:**
- Type: PostgreSQL 17
- Container: Docker (`docker run`, not Docker Compose), container name `licitmap-db`
- Connection string (hardcoded): `postgresql://licitmap:licitmap@localhost:5432/licitmap`
- Connection env var: Not implemented — hardcoded in `app/database.py`
- Client: SQLAlchemy 2.0 (sync, `create_engine`) + psycopg2-binary adapter
- Schema: Single table `licitaciones`, created by `scripts/init_db.py`

**File Storage:**
- Local filesystem only
- Raw data files in `data/` directory (ZIP archives and `.atom` XML files)
- `data/` is gitignored — not version controlled

**Caching:**
- None

## Authentication & Identity

**Auth Provider:**
- None — no user authentication implemented

## Monitoring & Observability

**Error Tracking:**
- None

**Logs:**
- Uvicorn stdout/stderr, redirected to `uvicorn.log` when running in background via `nohup`
- `uvicorn.log` is gitignored

## CI/CD & Deployment

**Hosting:**
- Not deployed to production yet
- Development server: bare metal / VPS, direct uvicorn

**CI Pipeline:**
- None

## Environment Configuration

**Required env vars:**
- None currently (DB URL is hardcoded in `app/database.py` — this is a known gap)

**Planned env vars (not yet implemented):**
- Database connection credentials

**Secrets location:**
- No secrets management in place; credentials are hardcoded in `app/database.py`

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## XML Data Source Details

**Namespaces used in PLACSP Atom feeds** (defined in `app/parser.py`):
- `atom`: `http://www.w3.org/2005/Atom`
- `cbc`: `urn:dgpe:names:draft:codice:schema:xsd:CommonBasicComponents-2`
- `cac`: `urn:dgpe:names:draft:codice:schema:xsd:CommonAggregateComponents-2`
- `cac-place-ext`: `urn:dgpe:names:draft:codice-place-ext:schema:xsd:CommonAggregateComponents-2`
- `cbc-place-ext`: `urn:dgpe:names:draft:codice-place-ext:schema:xsd:CommonBasicComponents-2`

**Feed pagination:**
- Each `.atom` file contains max 500 entries
- `<link rel="next">` in the feed points to the next `.atom` file
- Each monthly ZIP contains dozens of chained `.atom` files

---

*Integration audit: 2026-04-09*
