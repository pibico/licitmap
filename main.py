from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routes.home import router as home_router
from app.routes.mapa import router as mapa_router

app = FastAPI(title="LicitMap")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(home_router)
app.include_router(mapa_router)
