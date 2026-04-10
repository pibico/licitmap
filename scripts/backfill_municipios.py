#!/usr/bin/env python3
"""
Backfill municipio y codigo_postal para registros existentes.
Reprocesa el ZIP original para extraer los campos nuevos.

Uso:
    PYTHONPATH=/root/licitmap python scripts/backfill_municipios.py
    PYTHONPATH=/root/licitmap python scripts/backfill_municipios.py --dry-run
"""
import sys
import zipfile
from app.database import SessionLocal
from app.models import Licitacion
from app.parser import parse_atom_bytes

ZIP_PATH = "data/marzo2026.zip"
DRY_RUN = "--dry-run" in sys.argv

db = SessionLocal()
actualizadas = 0
sin_datos = 0
errores = 0

with zipfile.ZipFile(ZIP_PATH) as zf:
    atom_files = [n for n in zf.namelist() if n.endswith(".atom")]
    total = len(atom_files)
    print(f"Archivos .atom: {total} | dry-run: {DRY_RUN}")

    for i, name in enumerate(atom_files, 1):
        print(f"[{i}/{total}] {name}", end=" ... ", flush=True)
        try:
            data = zf.read(name)
            datos = parse_atom_bytes(data)
        except Exception as e:
            print(f"ERROR: {e}")
            errores += 1
            continue

        file_act = 0
        for d in datos:
            if not d.get("atom_id"):
                continue
            municipio = d.get("municipio")
            codigo_postal = d.get("codigo_postal")
            if not municipio and not codigo_postal:
                sin_datos += 1
                continue

            if not DRY_RUN:
                rows = db.query(Licitacion).filter_by(atom_id=d["atom_id"]).update(
                    {"municipio": municipio, "codigo_postal": codigo_postal}
                )
                if rows:
                    file_act += 1
                    actualizadas += 1
            else:
                file_act += 1
                actualizadas += 1

        if not DRY_RUN:
            db.commit()
        print(f"{file_act} actualizadas")

db.close()
print(f"\nTotal — Actualizadas: {actualizadas} | Sin datos: {sin_datos} | Errores: {errores}")
