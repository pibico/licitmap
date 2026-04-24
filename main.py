import os
import secrets
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

load_dotenv(Path(__file__).resolve().parent / ".env")

from app.routes.home import router as home_router
from app.routes.mapa import router as mapa_router
from app.routes.auth import router as auth_router
from app.routes.admin import router as admin_router
from app.routes.analisis import router as analisis_router
from app.routes.alertas import router as alertas_router

app = FastAPI(title="LicitMap")

SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_urlsafe(32)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, session_cookie="lm_session")

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(home_router)
app.include_router(mapa_router)
app.include_router(analisis_router)
app.include_router(alertas_router)
