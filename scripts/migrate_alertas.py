#!/usr/bin/env python3
"""Crea las tablas alertas y licitaciones_seguidas."""
import sys
sys.path.insert(0, '/root/licitmap')

from app.database import engine
from sqlalchemy import text

DDL = """
CREATE TABLE IF NOT EXISTS alertas (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    nombre VARCHAR NOT NULL,
    tipo VARCHAR NOT NULL,
    keywords VARCHAR,
    cpv_codes VARCHAR,
    tipo_contrato VARCHAR,
    comunidades VARCHAR,
    provincias VARCHAR,
    presupuesto_min FLOAT,
    presupuesto_max FLOAT,
    solo_activas BOOLEAN DEFAULT FALSE,
    entidad_tipo VARCHAR,
    entidad_valor VARCHAR,
    frecuencia VARCHAR DEFAULT 'diaria',
    dia_semana INTEGER DEFAULT 0,
    hora_envio INTEGER DEFAULT 8,
    activa BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    last_checked_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_alertas_user_id ON alertas(user_id);

CREATE TABLE IF NOT EXISTS licitaciones_seguidas (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    licitacion_id INTEGER NOT NULL,
    notif_cambio_estado BOOLEAN DEFAULT TRUE NOT NULL,
    notif_dias_vencimiento INTEGER,
    last_estado VARCHAR,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_licseg_user_id ON licitaciones_seguidas(user_id);
CREATE INDEX IF NOT EXISTS ix_licseg_lic_id  ON licitaciones_seguidas(licitacion_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_licseg_unique ON licitaciones_seguidas(user_id, licitacion_id);
"""

with engine.connect() as conn:
    conn.execute(text(DDL))
    conn.commit()

print("Tablas alertas y licitaciones_seguidas creadas.")
