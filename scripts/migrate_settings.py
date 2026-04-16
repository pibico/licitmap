#!/usr/bin/env python3
"""Crea la tabla settings y siembra los valores por defecto."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import engine, SessionLocal
from app.models import Base, Setting

Base.metadata.create_all(bind=engine, tables=[Setting.__table__])

DEFAULTS = {
    "export_limit": "5000",
}

db = SessionLocal()
try:
    for key, value in DEFAULTS.items():
        if not db.query(Setting).filter_by(key=key).first():
            db.add(Setting(key=key, value=value))
            print(f"Creado: {key} = {value}")
        else:
            print(f"Ya existe: {key}")
    db.commit()
finally:
    db.close()
