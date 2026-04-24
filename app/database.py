import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://licitmap:licitmap@localhost:5432/licitmap",
)

# client_encoding=utf8 fuerza UTF-8 en la conexión aunque la BD se haya creado
# con locale C/SQL_ASCII (caso habitual en sistemas sin locales UTF-8 generadas,
# como LXC minimal). Sin esto, psycopg2 explota al leer datos con ñ/acentos.
engine = create_engine(DATABASE_URL, connect_args={"client_encoding": "utf8"})
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
