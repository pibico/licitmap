import sys
import zipfile
from datetime import datetime
from app.database import SessionLocal
from app.models import Licitacion
from app.parser import parse_atom_bytes

ZIP_PATH = "data/marzo2026.zip"

db = SessionLocal()
nuevas = 0
actualizadas = 0
errores = 0

with zipfile.ZipFile(ZIP_PATH) as zf:
    atom_files = [n for n in zf.namelist() if n.endswith(".atom")]
    total = len(atom_files)
    print(f"Archivos .atom encontrados: {total}")

    for i, name in enumerate(atom_files, 1):
        print(f"[{i}/{total}] {name}", end=" ... ", flush=True)
        try:
            data = zf.read(name)
            datos = parse_atom_bytes(data)
        except Exception as e:
            print(f"ERROR al parsear: {e}")
            errores += 1
            continue

        file_nuevas = 0
        file_actualizadas = 0
        for d in datos:
            fecha = None
            if d["fecha_publicacion"]:
                try:
                    fecha = datetime.fromisoformat(d["fecha_publicacion"])
                except ValueError:
                    pass

            fecha_limite = None
            if d.get("fecha_limite"):
                try:
                    from datetime import date
                    fecha_limite = date.fromisoformat(d["fecha_limite"])
                except ValueError:
                    pass

            if not d.get("atom_id"):
                continue

            existente = db.query(Licitacion).filter_by(atom_id=d["atom_id"]).first()
            if existente:
                existente.expediente = d["expediente"]
                existente.titulo = d["titulo"]
                existente.organo_contratacion = d["organo_contratacion"]
                existente.estado = d["estado"]
                existente.presupuesto = d["presupuesto"]
                existente.fecha_publicacion = fecha
                existente.fecha_limite = fecha_limite
                existente.tipo_contrato = d.get("tipo_contrato")
                existente.comunidad_autonoma = d["comunidad_autonoma"]
                existente.pais = d["pais"]
                existente.url = d["url"]
                file_actualizadas += 1
                actualizadas += 1
            else:
                db.add(Licitacion(
                    atom_id=d["atom_id"],
                    expediente=d["expediente"],
                    titulo=d["titulo"],
                    organo_contratacion=d["organo_contratacion"],
                    estado=d["estado"],
                    presupuesto=d["presupuesto"],
                    fecha_publicacion=fecha,
                    fecha_limite=fecha_limite,
                    tipo_contrato=d.get("tipo_contrato"),
                    comunidad_autonoma=d["comunidad_autonoma"],
                    pais=d["pais"],
                    url=d["url"],
                ))
                file_nuevas += 1
                nuevas += 1

        db.commit()
        print(f"+{file_nuevas} nuevas, ~{file_actualizadas} actualizadas")

db.close()
print(f"\nTotal — Nuevas: {nuevas} | Actualizadas: {actualizadas} | Errores: {errores}")
