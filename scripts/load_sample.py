#!/usr/bin/env python3
"""
Carga una muestra de los N archivos ATOM más recientes del ZIP.
Deduplica por atom_id (primera aparición = más reciente gana).
Cada archivo contiene ~500 licitaciones; 60 archivos ≈ 30.000 únicos.

Uso:
    PYTHONPATH=/root/licitmap python scripts/load_sample.py          # 60 archivos (~30k)
    PYTHONPATH=/root/licitmap python scripts/load_sample.py --files 30
"""
import sys
import zipfile
from datetime import datetime, date

from app.database import SessionLocal
from app.models import Licitacion
from app.parser import parse_atom_bytes

ZIP_PATH = "data/marzo2026.zip"

n_files = 60
args = sys.argv[1:]
for i, arg in enumerate(args):
    if arg == "--files" and i + 1 < len(args):
        n_files = int(args[i + 1])
    elif arg.startswith("--files="):
        n_files = int(arg.split("=")[1])

# Paso 1: parsear y deduplicar (más reciente = mayor nombre de archivo gana)
with zipfile.ZipFile(ZIP_PATH) as zf:
    atom_files = sorted(
        [n for n in zf.namelist() if n.endswith(".atom")],
        reverse=True
    )
    seleccionados = atom_files[:n_files]
    print(f"Archivos disponibles: {len(atom_files)} | Procesando los {len(seleccionados)} más recientes")

    records = {}  # atom_id → dict de datos
    errores = 0

    for i, name in enumerate(seleccionados, 1):
        print(f"[{i}/{len(seleccionados)}] {name}", end=" ... ", flush=True)
        try:
            data = zf.read(name)
            datos = parse_atom_bytes(data)
        except Exception as e:
            print(f"ERROR: {e}")
            errores += 1
            continue

        nuevos = 0
        for d in datos:
            aid = d.get("atom_id")
            if aid and aid not in records:
                records[aid] = d
                nuevos += 1
        print(f"{nuevos} únicos acumulados (+{len(datos) - nuevos} dupes)")

print(f"\nTotal únicos: {len(records)} | Errores de parseo: {errores}")

# Paso 2: insertar en BD en lotes
BATCH = 500
db = SessionLocal()
total_ins = 0
items = list(records.values())

try:
    for start in range(0, len(items), BATCH):
        batch = items[start:start + BATCH]
        for d in batch:
            fecha_pub = None
            if d.get("fecha_publicacion"):
                try:
                    fecha_pub = datetime.fromisoformat(d["fecha_publicacion"])
                except (ValueError, TypeError):
                    pass

            fecha_lim = None
            if d.get("fecha_limite"):
                try:
                    fecha_lim = date.fromisoformat(d["fecha_limite"])
                except (ValueError, TypeError):
                    pass

            db.add(Licitacion(
                atom_id=d["atom_id"],
                expediente=d.get("expediente"),
                titulo=d.get("titulo"),
                organo_contratacion=d.get("organo_contratacion"),
                estado=d.get("estado"),
                presupuesto=d.get("presupuesto"),
                fecha_publicacion=fecha_pub,
                fecha_limite=fecha_lim,
                tipo_contrato=d.get("tipo_contrato"),
                comunidad_autonoma=d.get("comunidad_autonoma"),
                pais=d.get("pais"),
                url=d.get("url"),
                cpv=d.get("cpv"),
                municipio=d.get("municipio"),
                codigo_postal=d.get("codigo_postal"),
            ))

        db.commit()
        total_ins += len(batch)
        print(f"  Insertados: {total_ins}/{len(items)}", end="\r", flush=True)

    print(f"\nListo — {total_ins} licitaciones insertadas.")
finally:
    db.close()
