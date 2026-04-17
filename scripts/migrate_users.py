#!/usr/bin/env python3
"""Crea la tabla users y siembra el usuario admin con contraseña aleatoria."""
import sys
import os
import secrets
import string

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import bcrypt
from app.database import engine, SessionLocal
from app.models import Base, User

Base.metadata.create_all(bind=engine, tables=[User.__table__])

db = SessionLocal()
try:
    if not db.query(User).filter_by(username="admin").first():
        alphabet = string.ascii_letters + string.digits
        password = ''.join(secrets.choice(alphabet) for _ in range(14))
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        db.add(User(username="admin", hashed_password=hashed, is_active=True))
        db.commit()
        print("=" * 48)
        print("  Usuario admin creado.")
        print(f"  Usuario:     admin")
        print(f"  Contraseña:  {password}")
        print("  Guarda esta contraseña — no se mostrará")
        print("  de nuevo. Cámbiala desde /admin/config.")
        print("=" * 48)
    else:
        print("Usuario 'admin' ya existe — sin cambios.")
finally:
    db.close()
