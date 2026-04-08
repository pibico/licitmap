from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routes.home import router as home_router

app = FastAPI(title="LicitMap")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(home_router)
