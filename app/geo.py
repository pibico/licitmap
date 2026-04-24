"""Datos geográficos derivados de static/data/provincias.geojson.

Exporta:
- PROVINCIAS_CANONICAL: lista ordenada de 52 provincias españolas.
- CP_TO_PROVINCIA: dict {prefijo CP (2 dígitos): nombre}. En España los 2
  primeros dígitos del CP identifican la provincia, p. ej. 28xxx = Madrid.
- PROVINCIA_TO_CP: inverso {nombre: prefijo}.
- CCAA_TO_PROVINCIAS: dict {nombre CCAA (según feed ATOM): [nombres provincia]}.
- provincias_por_ccaa(ccaa_list): helper con normalización.

Se cargan al importar. Si el fichero falta o está corrupto, las estructuras
quedan vacías (la app sigue arrancando pero las derivaciones geográficas
devuelven datos vacíos)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

_GEOJSON_PATH = Path(__file__).resolve().parent.parent / "static" / "data" / "provincias.geojson"

# Alias del feed ATOM (Licitacion.comunidad_autonoma) → clave del geojson
# (properties.CCAA). Basado en los valores reales que emite el feed (ver
# comunidad_autonoma DISTINCT en BD). El geojson usa nombres cooficiales
# y cortos ("Illes Balears", "Rioja, La"…), mientras que el feed usa
# denominaciones largas ("Ciudad Autónoma de Melilla"…) o cortas ("La Rioja").
_CCAA_ALIAS = {
    # feed (Licitacion.comunidad_autonoma) → geojson CCAA
    "Illes Balears":                  "Illes Balears",          # coincide
    "Comunidad Valenciana":           "Comunitat Valenciana",
    "Principado de Asturias":         "Asturias, Principado de",
    "Castilla-La Mancha":             "Castilla - La Mancha",
    "La Rioja":                       "Rioja, La",
    "Ciudad Autónoma de Ceuta":       "Ceuta",
    "Ciudad Autónoma de Melilla":     "Melilla",
    # Formas cortas usadas por los CCAA pickers de /alerts (CCAA_LIST en
    # app/routes/alertas.py + chips del template) → geojson CCAA.
    "Asturias":                       "Asturias, Principado de",
    "Baleares":                       "Illes Balears",
    # Coinciden tal cual: Andalucía, Aragón, Canarias, Cantabria, Castilla y
    # León, Cataluña, Comunidad de Madrid, Comunidad Foral de Navarra,
    # Extremadura, Galicia, País Vasco, Región de Murcia.
}


def _load() -> tuple[list[str], dict[str, str], dict[str, str], dict[str, list[str]]]:
    try:
        features = json.loads(_GEOJSON_PATH.read_text()).get("features", [])
    except Exception:
        return [], {}, {}, {}

    cp_to_name: dict[str, str] = {}
    ccaa_to_provs: dict[str, list[str]] = {}
    for f in features:
        p = f.get("properties", {}) or {}
        cod, nom, ccaa = p.get("Codigo"), p.get("Texto"), p.get("CCAA")
        if not (cod and nom):
            continue
        cp_to_name[cod.zfill(2)] = nom
        if ccaa:
            ccaa_to_provs.setdefault(ccaa, []).append(nom)

    name_to_cp = {v: k for k, v in cp_to_name.items()}
    provincias = sorted(cp_to_name.values())
    return provincias, cp_to_name, name_to_cp, ccaa_to_provs


PROVINCIAS_CANONICAL, CP_TO_PROVINCIA, PROVINCIA_TO_CP, CCAA_TO_PROVINCIAS = _load()


def _normalize_ccaa(name: str) -> str:
    """Devuelve la clave del geojson (alias) o el nombre tal cual."""
    return _CCAA_ALIAS.get(name, name)


def provincias_por_ccaa(ccaa_list: Iterable[str]) -> list[str]:
    """Dadas una lista de nombres de CCAA (formato feed ATOM), devuelve la
    lista ordenada de provincias pertenecientes a cualquiera de ellas.
    Si la lista está vacía, devuelve todas las provincias."""
    names = [c for c in ccaa_list if c]
    if not names:
        return PROVINCIAS_CANONICAL
    result: set[str] = set()
    for raw in names:
        key = _normalize_ccaa(raw)
        result.update(CCAA_TO_PROVINCIAS.get(key, []))
    return sorted(result)
