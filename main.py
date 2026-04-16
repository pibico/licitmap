from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.routes.home import router as home_router
from app.routes.mapa import router as mapa_router
from app.routes.auth import router as auth_router
from app.routes.admin import router as admin_router

app = FastAPI(title="LicitMap")

# Sesión firmada con cookie (itsdangerous) — cambiar SECRET_KEY en producción real
app.add_middleware(SessionMiddleware, secret_key="licitmap-session-secret-2026", session_cookie="lm_session")

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(home_router)
app.include_router(mapa_router)
