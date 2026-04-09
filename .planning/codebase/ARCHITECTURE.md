# Architecture

**Analysis Date:** 2026-04-09

## Pattern Overview

**Overall:** Monolithic MVC-lite web application with a separate ETL pipeline

**Key Characteristics:**
- Single FastAPI application serving HTML pages (server-side rendering, no API endpoints)
- No async database access — synchronous SQLAlchemy engine with `SessionLocal`
- Template rendering is hand-rolled string replacement, not Jinja2 engine (due to known bug with Python 3.13)
- ETL (data loading) is a standalone set of scripts, not integrated into the web app
- No service layer — route handlers query the database directly

## Layers

**HTTP Layer:**
- Purpose: Route HTTP requests, render HTML responses
- Location: `app/routes/`
- Contains: FastAPI `APIRouter` instances, route handler functions
- Depends on: Database layer (`app/database.py`), Models (`app/models.py`), templates
- Used by: `main.py` (router registration)

**Database Layer:**
- Purpose: Engine and session configuration, base class for models
- Location: `app/database.py`
- Contains: `engine`, `SessionLocal`, `Base`, `get_db` dependency
- Depends on: Hardcoded `DATABASE_URL` string
- Used by: Routes (via `Depends(get_db)`), scripts

**Model Layer:**
- Purpose: ORM schema definition
- Location: `app/models.py`
- Contains: `Licitacion` SQLAlchemy model mapping to `licitaciones` table
- Depends on: `app/database.py` (`Base`)
- Used by: Routes, scripts

**Parser Layer:**
- Purpose: Transform raw PLACSP XML Atom bytes/files into Python dicts
- Location: `app/parser.py`
- Contains: `parse_atom_file()`, `parse_atom_bytes()`, `extract_comunidad()`, XML namespace definitions
- Depends on: Python stdlib only (`xml.etree.ElementTree`)
- Used by: `scripts/load_data.py`

**Template Layer:**
- Purpose: HTML presentation
- Location: `templates/`
- Contains: `base.html` (layout shell), `home.html` (content fragment)
- Pattern: `base.html` has `{{content}}` placeholder; route handler reads both files, substitutes, then substitutes additional `{{key}}` placeholders with data strings
- Note: `templates/index.html` is an old self-contained prototype, not used by the live routes

**Static Assets:**
- Location: `static/`
- Contains: `css/style.css` (Bootstrap overrides + status badge colors), `js/app.js` (empty), `img/` (empty)
- Served by: FastAPI `StaticFiles` mount at `/static`

**ETL Scripts:**
- Purpose: Standalone data pipeline — not part of the web app lifecycle
- Location: `scripts/`
- Contains: `init_db.py` (creates tables), `load_data.py` (parses ZIPs and upserts into DB)
- Depends on: `app.database`, `app.models`, `app.parser`
- Run manually from the command line

## Data Flow

**HTTP Request (page render):**
1. Request hits `GET /` in `app/routes/home.py`
2. `get_db()` dependency opens a `SessionLocal` session
3. Route queries `Licitacion` ORM objects (latest 100 by `fecha_publicacion`) and COUNT
4. Route builds raw HTML string by iterating rows and f-string interpolation
5. `render("home.html", total=..., filas=...)` reads `templates/base.html` and `templates/home.html` from disk on every request, concatenates, then does `str.replace()` substitutions
6. Returns `HTMLResponse`

**ETL (data ingestion):**
1. Download monthly ZIP from PLACSP URL to `data/`
2. Run `python scripts/init_db.py` to create tables (idempotent, `create_all`)
3. Run `python scripts/load_data.py` — opens ZIP, iterates `.atom` files
4. Each `.atom` file is parsed with `parse_atom_bytes()` using `xml.etree.ElementTree`
5. For each entry: query by `expediente`; update if exists, insert if new
6. `db.commit()` after each `.atom` file

**State Management:**
- No application state — all state is in PostgreSQL
- No caching layer
- No session/cookie state (no user auth)

## Key Abstractions

**`Licitacion` model:**
- Purpose: Maps one public tender to one database row
- File: `app/models.py`
- Pattern: SQLAlchemy `DeclarativeBase` with 9 columns; `expediente` is the natural key (unique, indexed)

**`get_db()` dependency:**
- Purpose: Provides a scoped SQLAlchemy session per request, closes on teardown
- File: `app/database.py`
- Pattern: Generator-based FastAPI dependency (`yield`)

**`render()` function:**
- Purpose: Ad-hoc template engine replacement
- File: `app/routes/home.py`
- Pattern: Reads template files from disk, does sequential `str.replace("{{key}}", value)` — no escaping

**`parse_atom_bytes()` / `parse_atom_file()`:**
- Purpose: Parse PLACSP XML into list of dicts with normalized field names
- File: `app/parser.py`
- Pattern: `xml.etree.ElementTree` with hardcoded namespace map; `extract_comunidad()` walks the `ParentLocatedParty` hierarchy to identify the autonomous community

## Entry Points

**Web Application:**
- Location: `main.py`
- Triggers: `uvicorn main:app --reload --host 0.0.0.0`
- Responsibilities: Creates `FastAPI` instance, mounts static files, registers `home_router`

**DB Initialization:**
- Location: `scripts/init_db.py`
- Triggers: Manual CLI (`python scripts/init_db.py`)
- Responsibilities: Calls `Base.metadata.create_all(bind=engine)`

**Data Load:**
- Location: `scripts/load_data.py`
- Triggers: Manual CLI (`python scripts/load_data.py`)
- Responsibilities: Opens `data/marzo2026.zip`, parses all `.atom` files, upserts into DB

## Error Handling

**Strategy:** Minimal — only in the ETL script

**Patterns:**
- `scripts/load_data.py`: `try/except Exception` around per-file parsing; increments error counter and continues
- Routes: No explicit error handling — unhandled exceptions propagate to FastAPI's default 500 handler
- Parser: Returns `None` for missing XML fields (via `text()` helper); no exceptions raised for missing data

## Cross-Cutting Concerns

**Logging:** Uvicorn access logs to stdout/`uvicorn.log`; no application-level structured logging
**Validation:** None — data from XML is inserted as-is (no Pydantic validation in the pipeline)
**Authentication:** None

---

*Architecture analysis: 2026-04-09*
