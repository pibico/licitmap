# Codebase Structure

**Analysis Date:** 2026-04-09

## Directory Layout

```
licitmap/
├── app/                    # Core application package
│   ├── __init__.py
│   ├── database.py         # SQLAlchemy engine, session, Base, get_db()
│   ├── models.py           # ORM model: Licitacion
│   ├── parser.py           # PLACSP XML Atom parser
│   └── routes/             # FastAPI routers
│       ├── __init__.py
│       └── home.py         # GET / — licitaciones listing
├── data/                   # Raw data files (gitignored)
│   ├── marzo2026.zip
│   └── licitacionesPerfilesContratanteCompleto3.atom
├── scripts/                # CLI ETL scripts (run manually)
│   ├── init_db.py          # Create DB tables
│   └── load_data.py        # Parse ZIP and upsert into DB
├── static/                 # Public static assets
│   ├── css/
│   │   └── style.css       # Bootstrap overrides, status badge colors
│   ├── js/
│   │   └── app.js          # Empty placeholder
│   └── img/                # Empty placeholder
├── templates/              # HTML templates
│   ├── base.html           # Layout shell (navbar, Bootstrap CDN, footer)
│   ├── home.html           # Content fragment: licitaciones table
│   └── index.html          # Old self-contained prototype (unused)
├── .venv/                  # Python virtual environment (gitignored)
├── .planning/              # GSD planning documents
│   └── codebase/
├── main.py                 # FastAPI app entry point
├── requirements.txt        # Python dependencies
├── claude.md               # Project notes and task backlog
└── .gitignore
```

## Directory Purposes

**`app/`:**
- Purpose: The importable Python package containing all web application logic
- Contains: Database config, ORM models, XML parser, route handlers
- Key files: `app/database.py`, `app/models.py`, `app/parser.py`

**`app/routes/`:**
- Purpose: FastAPI `APIRouter` modules, one per logical page or feature area
- Contains: Route handler functions, the `render()` helper
- Key files: `app/routes/home.py`

**`scripts/`:**
- Purpose: Standalone ETL and maintenance scripts, not part of the ASGI app
- Contains: DB initialization and data loading scripts
- Run with: `python scripts/<script>.py` from project root with `.venv` activated

**`templates/`:**
- Purpose: HTML template fragments
- Pattern: `base.html` is the full page shell with `{{content}}` slot; page-specific files (e.g. `home.html`) are fragments dropped into that slot
- Rendering: Done manually via `render()` in `app/routes/home.py`, not Jinja2 engine

**`static/`:**
- Purpose: Files served directly by FastAPI `StaticFiles` mount at `/static`
- CSS overrides Bootstrap 5 defaults and defines `.badge-{STATE}` classes for tender status codes

**`data/`:**
- Purpose: Holds downloaded PLACSP ZIP files and extracted `.atom` files
- Gitignored — large binary files, not version controlled
- Feed files follow naming pattern: `licitacionesPerfilesContratanteCompleto3_AAAAMM.zip`

## Key File Locations

**Entry Points:**
- `main.py`: FastAPI app instantiation, static mount, router registration
- `scripts/init_db.py`: Table creation (run once or after model changes)
- `scripts/load_data.py`: Batch data ingestion from `data/marzo2026.zip`

**Configuration:**
- `app/database.py`: Database URL (hardcoded), engine and session setup
- `requirements.txt`: Python dependencies

**Core Logic:**
- `app/parser.py`: XML Atom parsing, CCAA detection, namespace map
- `app/models.py`: `Licitacion` table schema
- `app/routes/home.py`: Home page query, HTML generation, template rendering

**Templates:**
- `templates/base.html`: Page shell — change navbar, Bootstrap version, global CSS/JS here
- `templates/home.html`: Licitaciones table fragment — change table columns here

## Naming Conventions

**Files:**
- Python modules: `snake_case.py`
- Templates: `snake_case.html`
- Scripts: `snake_case.py` (imperative verb: `init_db`, `load_data`)

**Directories:**
- All lowercase, no separators: `app`, `routes`, `static`, `templates`, `scripts`

## Where to Add New Code

**New page/route:**
- Create router: `app/routes/<feature>.py` with `router = APIRouter()`
- Register in: `main.py` with `app.include_router(<router>)`
- Add template fragment: `templates/<feature>.html`

**New template:**
- Add fragment to `templates/<name>.html`
- Use `render("<name>.html", key=value)` from the route handler

**New model / table:**
- Add class to `app/models.py` extending `Base`
- Re-run `python scripts/init_db.py` to create the table (or use Alembic migration when implemented)

**New ETL script:**
- Add to `scripts/<name>.py`
- Import from `app.database`, `app.models`, `app.parser` as needed

**New static assets:**
- CSS: `static/css/style.css` (or add new file and link in `templates/base.html`)
- JS: `static/js/app.js` (currently empty — safe to start here)
- Images: `static/img/`

**New parser field:**
- Add XPath extraction in `app/parser.py` `_parse_entries()` function
- Add column to `app/models.py` `Licitacion`
- Re-run `scripts/init_db.py` (drops and recreates) or write Alembic migration

## Special Directories

**`.venv/`:**
- Purpose: Python virtual environment
- Generated: Yes (by `python -m venv .venv`)
- Committed: No (gitignored)

**`data/`:**
- Purpose: Raw source data files from PLACSP
- Generated: Yes (manual download via `wget`)
- Committed: No (gitignored — too large)

**`.planning/`:**
- Purpose: GSD planning documents (phase plans, codebase analysis)
- Generated: Yes (by GSD tooling)
- Committed: Yes

---

*Structure analysis: 2026-04-09*
