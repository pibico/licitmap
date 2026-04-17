#!/usr/bin/env python3
"""Añade columnas email, otp_code, otp_expires_at a users y hace hashed_password nullable."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text
from app.database import engine

with engine.connect() as conn:
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR"))
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS otp_code VARCHAR"))
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS otp_expires_at TIMESTAMP"))
    conn.execute(text("ALTER TABLE users ALTER COLUMN hashed_password DROP NOT NULL"))
    conn.commit()
    print("Migración completada: columnas email, otp_code, otp_expires_at añadidas.")
