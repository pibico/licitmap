#!/usr/bin/env python3
"""Crea la tabla users y siembra el usuario admin con contraseña hasheada."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import bcrypt
from app.database import engine, SessionLocal
from app.models import Base, User

Base.metadata.create_all(bind=engine, tables=[User.__table__])

db = SessionLocal()
try:
    if not db.query(User).filter_by(username="admin").first():
        hashed = bcrypt.hashpw(b"admin", bcrypt.gensalt()).decode()
        admin = User(username="admin", hashed_password=hashed, is_active=True)
        db.add(admin)
        db.commit()
        print("Usuario 'admin' creado con contraseña 'admin'.")
    else:
        print("Usuario 'admin' ya existe — sin cambios.")
finally:
    db.close()
