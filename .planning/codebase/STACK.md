# Technology Stack

**Analysis Date:** 2026-04-09

## Languages

**Primary:**
- Python 3.13 - All backend logic, ORM, parsing, routing

**Secondary:**
- HTML/CSS - Jinja2-style templates (hand-rolled, not using Jinja2 engine)
- JavaScript - Placeholder only (`static/js/app.js` is empty)

## Runtime

**Environment:**
- Python 3.13 on Debian 13 (Bookworm)
- Virtual environment: `.venv/` (Python venv)

**Package Manager:**
- pip
- Lockfile: Not present (no `requirements.lock` or `pip freeze` output committed — only `requirements.txt` with loose pins except Jinja2)

## Frameworks

**Core:**
- FastAPI 0.135.3 - HTTP routing, dependency injection, static file serving
- Starlette 1.0.0 - ASGI foundation (indirect, via FastAPI)

**Template Rendering:**
- Jinja2 3.1.5 - Installed but NOT used via `Jinja2Templates`. Templates are rendered manually with `Path.read_text()` + `str.replace()`. See known bug below.

**Build/Dev:**
- Uvicorn 0.44.0 - ASGI server (`uvicorn main:app --reload --host 0.0.0.0`)

## Key Dependencies

**Critical:**
- `sqlalchemy` 2.0.49 - ORM (DeclarativeBase), database sessions, query building
- `psycopg2-binary` 2.9.11 - PostgreSQL adapter for SQLAlchemy
- `pydantic` 2.12.5 - Installed (FastAPI dependency), not directly used in app code yet
- `jinja2` 3.1.5 - **Pinned exactly** due to bug: Jinja2 3.1.6 raises `unhashable type: 'dict'` on Python 3.13+ LRU cache

**Infrastructure:**
- `anyio` 4.13.0 - Async I/O (Starlette/FastAPI dependency)
- `h11` 0.16.0 - HTTP/1.1 protocol (Uvicorn dependency)

## Configuration

**Environment:**
- Database URL is hardcoded in `app/database.py`: `postgresql://licitmap:licitmap@localhost:5432/licitmap`
- No `.env` file support implemented yet (listed in `.gitignore`, planned but not built)
- No environment variable reading (`os.environ` / `python-dotenv`) in codebase

**Build:**
- No build step — pure Python runtime
- No `pyproject.toml`, no `setup.py`

## Platform Requirements

**Development:**
- Python 3.13
- PostgreSQL 17 running locally (Docker container named `licitmap-db`)
- Docker: `docker run -d --name licitmap-db -e POSTGRES_USER=licitmap -e POSTGRES_PASSWORD=licitmap -e POSTGRES_DB=licitmap -p 5432:5432 --restart unless-stopped postgres:17`

**Production:**
- No production deployment configured yet
- Planned: Nginx reverse proxy + systemd service + Docker Compose

---

*Stack analysis: 2026-04-09*
