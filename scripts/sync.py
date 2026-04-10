#!/usr/bin/env python3
"""
Sincronización incremental con PLACSP.
Descarga feeds ATOM de contrataciondelestado.es y actualiza la BD.

Uso:
    PYTHONPATH=/root/licitmap python scripts/sync.py           # Solo novedades
    PYTHONPATH=/root/licitmap python scripts/sync.py --force   # Forzar desde el inicio
    PYTHONPATH=/root/licitmap python scripts/sync.py --status  # Ver estado del último sync
"""
import sys
import json
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timezone, date

from app.database import SessionLocal
from app.models import Licitacion
from app.parser import parse_atom_bytes

BASE_URL = "https://contrataciondelestado.es/sindicacion/sindicacion_643/"
ROOT_FEED = "licitacionesPerfilesContratanteCompleto3.atom"
STATE_FILE = Path("data/sync_state.json")
NS_ATOM = "http://www.w3.org/2005/Atom"
HEADERS = {"User-Agent": "LicitMap/1.0 (github.com/Ivisor/licitmap)"}


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {}


def save_state(state):
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def parse_dt(s):
    """ISO 8601 → datetime UTC naive."""
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except (ValueError, TypeError):
        return None


def get_feed_meta(root):
    """Devuelve (next_url, feed_updated_dt)."""
    next_url = None
    for link in root.findall(f"{{{NS_ATOM}}}link"):
        if link.get("rel") == "next":
            href = link.get("href", "")
            next_url = href if href.startswith("http") else BASE_URL + href

    updated_el = root.find(f"{{{NS_ATOM}}}updated")
    feed_updated_dt = parse_dt(updated_el.text.strip() if updated_el is not None and updated_el.text else None)

    return next_url, feed_updated_dt


def upsert(db, entries):
    nuevas = actualizadas = 0
    for d in entries:
        if not d.get("atom_id"):
            continue

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

        existing = db.query(Licitacion).filter_by(atom_id=d["atom_id"]).first()
        if existing:
            existing.expediente = d["expediente"]
            existing.titulo = d["titulo"]
            existing.organo_contratacion = d["organo_contratacion"]
            existing.estado = d["estado"]
            existing.presupuesto = d["presupuesto"]
            existing.fecha_publicacion = fecha_pub
            existing.fecha_limite = fecha_lim
            existing.tipo_contrato = d.get("tipo_contrato")
            existing.comunidad_autonoma = d["comunidad_autonoma"]
            existing.pais = d["pais"]
            existing.url = d["url"]
            existing.cpv = d.get("cpv")
            existing.municipio = d.get("municipio")
            existing.codigo_postal = d.get("codigo_postal")
            actualizadas += 1
        else:
            db.add(Licitacion(
                atom_id=d["atom_id"],
                expediente=d["expediente"],
                titulo=d["titulo"],
                organo_contratacion=d["organo_contratacion"],
                estado=d["estado"],
                presupuesto=d["presupuesto"],
                fecha_publicacion=fecha_pub,
                fecha_limite=fecha_lim,
                tipo_contrato=d.get("tipo_contrato"),
                comunidad_autonoma=d["comunidad_autonoma"],
                pais=d["pais"],
                url=d["url"],
                cpv=d.get("cpv"),
                municipio=d.get("municipio"),
                codigo_postal=d.get("codigo_postal"),
            ))
            nuevas += 1

    db.commit()
    return nuevas, actualizadas


def main():
    if "--status" in sys.argv:
        state = load_state()
        if state:
            print(f"Último sync:   {state.get('last_sync', '—')}")
            print(f"Feeds leídos:  {state.get('feeds', '—')}")
            print(f"Nuevas:        {state.get('nuevas', '—')}")
            print(f"Actualizadas:  {state.get('actualizadas', '—')}")
        else:
            print("Sin sincronizaciones previas.")
        return

    force = "--force" in sys.argv
    state = load_state()

    last_sync_dt = None if force else parse_dt(state.get("last_sync"))

    if last_sync_dt:
        print(f"Último sync: {state['last_sync']} — buscando novedades...")
    else:
        print("Sync inicial o forzado — descargando todo (puede tardar).")

    db = SessionLocal()
    total_nuevas = total_actualizadas = total_feeds = 0
    url = BASE_URL + ROOT_FEED

    try:
        while url:
            filename = url.split("/")[-1]
            print(f"  [{filename}] ...", end=" ", flush=True)

            try:
                resp = requests.get(url, timeout=60, headers=HEADERS)
                resp.raise_for_status()
            except requests.RequestException as e:
                print(f"ERROR: {e}")
                break

            root = ET.fromstring(resp.content)
            next_url, feed_updated_dt = get_feed_meta(root)

            # Parar cuando este feed sea más antiguo que el último sync
            if last_sync_dt and feed_updated_dt and feed_updated_dt <= last_sync_dt:
                print(f"sin novedades (feed del {feed_updated_dt.strftime('%Y-%m-%d %H:%M')})")
                break

            entries = parse_atom_bytes(resp.content)
            nuevas, actualizadas = upsert(db, entries)
            total_nuevas += nuevas
            total_actualizadas += actualizadas
            total_feeds += 1

            ts = feed_updated_dt.strftime("%Y-%m-%d %H:%M") if feed_updated_dt else "?"
            print(f"+{nuevas} nuevas, ~{actualizadas} actualizadas  [{ts}]")

            url = next_url

    finally:
        db.close()

    print(f"\nTotal — Feeds: {total_feeds} | Nuevas: {total_nuevas} | Actualizadas: {total_actualizadas}")

    if total_feeds > 0 or not last_sync_dt:
        now_str = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
        save_state({
            "last_sync": now_str,
            "feeds": total_feeds,
            "nuevas": total_nuevas,
            "actualizadas": total_actualizadas,
        })
        print(f"Estado guardado: {now_str}")


if __name__ == "__main__":
    main()
