import os
import secrets
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.middleware.sessions import SessionMiddleware

load_dotenv(Path(__file__).resolve().parent / ".env")

from app.database import engine
from app.i18n import I18nMiddleware
from app.routes.home import router as home_router
from app.routes.mapa import router as mapa_router
from app.routes.auth import router as auth_router
from app.routes.admin import router as admin_router
from app.routes.analisis import router as analisis_router
from app.routes.alertas import router as alertas_router
from app.routes.lang import router as lang_router
from app.routes.redirects import router as redirects_router


def _auto_migrate() -> None:
    """ALTER TABLE idempotentes al arranque para cerrar el gap entre un
    `licitmap update` (git pull + restart) y cambios de schema. Cada
    sentencia es un `IF NOT EXISTS` silencioso — no rompe nada si la
    columna ya está."""
    statements = [
        'ALTER TABLE users ADD COLUMN IF NOT EXISTS language VARCHAR(2) DEFAULT \'es\' NOT NULL',
        'ALTER TABLE alertas ADD COLUMN IF NOT EXISTS municipios VARCHAR',
    ]
    try:
        with engine.begin() as conn:
            for sql in statements:
                conn.execute(text(sql))
    except Exception:
        # No abortar el arranque si falla (p. ej. BD no accesible en tests);
        # el error real aparecerá cuando la app intente usar las columnas.
        pass


_auto_migrate()

app = FastAPI(title="LicitMap")

SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_urlsafe(32)
# Middlewares: se ejecutan en orden inverso al registro. Registramos primero
# i18n para que el SessionMiddleware esté "fuera" y, al procesar la respuesta,
# i18n ya tenga acceso a la request con cookies.
app.add_middleware(I18nMiddleware)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, session_cookie="lm_session")

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(home_router)
app.include_router(mapa_router)
app.include_router(analisis_router)
app.include_router(alertas_router)
app.include_router(lang_router)
# redirects last so they don't shadow the real routes
app.include_router(redirects_router)
