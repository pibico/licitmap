from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func, case
from pathlib import Path
from datetime import date, datetime
import json as _json

from app.database import get_db
from app.models import Licitacion
from app.utils import _nav_context

router = APIRouter()


def _load_provincias_canonical() -> list[str]:
    """Lista canónica de provincias desde el geojson (52 entradas).
    Usada para el autocompletado: funciona aunque la BD no tenga
    Licitacion.provincia populado (el sync ATOM no siempre lo rellena)."""
    path = Path(__file__).parents[2] / "static" / "data" / "provincias.geojson"
    try:
        data = _json.loads(path.read_text())
        return sorted({
            f["properties"].get("Texto")
            for f in data.get("features", [])
            if f.get("properties", {}).get("Texto")
        })
    except Exception:
        return []


_PROVINCIAS_CANONICAL = _load_provincias_canonical()

ESTADOS = {
    "PUB": "Publicada",
    "ADJ": "Adjudicada",
    "PRE": "Preevaluación",
    "RES": "Resuelta",
    "EV": "En evaluación",
    "ANUL": "Anulada",
}

TIPOS_CONTRATO = {
    "1": "Obras",
    "2": "Servicios",
    "3": "Suministros",
    "7": "Gestión de servicios públicos",
    "8": "Colaboración público-privada",
    "22": "Concesión de servicios",
    "31": "Privado",
    "32": "Patrimonial",
    "40": "Administrativo especial",
    "50": "Otros",
}

PRANGES = [
    ("5k",   "Menos de 5.000 €",   None,      5_000),
    ("15k",  "5.000 – 15.000 €",   5_000,     15_000),
    ("100k", "15.000 – 100.000 €", 15_000,    100_000),
    ("1m",   "100.000 – 1M €",     100_000,   1_000_000),
    ("1m+",  "Más de 1M €",        1_000_000, None),
]


def render(template, **kwargs):
    base = Path("templates/base.html").read_text()
    page = Path(f"templates/{template}").read_text()
    html = base.replace("{{content}}", page)
    for key, value in kwargs.items():
        html = html.replace("{{" + key + "}}", str(value))
    return html


def apply_common_filters(query, q, tipo, estado, prange, fecha_desde, fecha_hasta, cpv_q=""):
    """Aplica filtros comunes sin filtrar por territorio (eso se hace aparte)."""
    if q:
        query = query.filter(
            or_(
                Licitacion.titulo.ilike(f"%{q}%"),
                Licitacion.organo_contratacion.ilike(f"%{q}%"),
                Licitacion.expediente.ilike(f"%{q}%"),
            )
        )
    if cpv_q:
        query = query.filter(Licitacion.cpv.ilike(f"%{cpv_q}%"))

    if tipo:
        tipos = [t for t in tipo.split("|") if t]
        if tipos:
            query = query.filter(or_(*[Licitacion.tipo_contrato == t for t in tipos]))

    if estado:
        estados = [e for e in estado.split("|") if e]
        if estados:
            query = query.filter(or_(*[Licitacion.estado == e for e in estados]))

    if prange:
        pranges = [p for p in prange.split("|") if p]
        if pranges:
            conditions = []
            for key in pranges:
                for k, _, lo, hi in PRANGES:
                    if k == key:
                        if lo is not None and hi is not None:
                            conditions.append(and_(Licitacion.presupuesto >= lo, Licitacion.presupuesto < hi))
                        elif lo is not None:
                            conditions.append(Licitacion.presupuesto >= lo)
                        elif hi is not None:
                            conditions.append(Licitacion.presupuesto < hi)
            if conditions:
                query = query.filter(or_(*conditions))

    if fecha_desde:
        try:
            query = query.filter(Licitacion.fecha_limite >= date.fromisoformat(fecha_desde))
        except ValueError:
            pass

    if fecha_hasta:
        try:
            query = query.filter(Licitacion.fecha_limite <= date.fromisoformat(fecha_hasta))
        except ValueError:
            pass

    return query


def apply_territorio_filter(query):
    """Filtra solo licitaciones españolas con CCAA válida."""
    return query.filter(
        Licitacion.pais == "España",
        ~Licitacion.comunidad_autonoma.in_({"Todo el territorio", "Extra-Regio"}),
        Licitacion.comunidad_autonoma.isnot(None),
        Licitacion.comunidad_autonoma != "",
    )




@router.get("/map", response_class=HTMLResponse)
def mapa_page(
    request: Request,
    q: str = Query(default=""),
    cpv_q: str = Query(default=""),
    tipo: str = Query(default=""),
    estado: str = Query(default=""),
    prange: str = Query(default=""),
    fecha_desde: str = Query(default=""),
    fecha_hasta: str = Query(default=""),
    db: Session = Depends(get_db),
):
    # Total España sin filtros del usuario (todas las de pais=España, no solo las del mapa)
    total_espana = db.query(func.count(Licitacion.id)).filter(Licitacion.pais == "España").scalar()
    total_espana_str = f"{total_espana:,}".replace(",", ".")

    # Stats: toda España con filtros del usuario (no solo las del mapa)
    stats_query = apply_common_filters(
        db.query(Licitacion).filter(Licitacion.pais == "España"),
        q, tipo, estado, prange, fecha_desde, fecha_hasta, cpv_q=cpv_q
    )
    resultados = stats_query.count()
    en_plazo = (
        stats_query.filter(Licitacion.estado == "PUB", Licitacion.fecha_limite >= date.today()).count()
    )

    # Última sincronización
    _state_file = Path(__file__).parents[2] / "data" / "sync_state.json"
    ultima_sync = "—"
    if _state_file.exists():
        try:
            _state = _json.loads(_state_file.read_text())
            _last = _state.get("last_sync")
            if _last:
                _diff = (date.today() - datetime.fromisoformat(_last).date()).days
                ultima_sync = "Hoy" if _diff == 0 else "Ayer" if _diff == 1 else f"Hace {_diff} días"
        except Exception:
            pass

    # Sidebar tipo
    tipo_sel = set(tipo.split("|")) - {""} if tipo else set()
    tipo_items = []
    for cod, nombre in TIPOS_CONTRATO.items():
        active = "lm-active" if cod in tipo_sel else ""
        tipo_items.append(
            f'<div class="lm-sidebar-item lm-check-item {active}" data-group="tipo" data-value="{cod}">'
            f'<span>{nombre}</span></div>'
        )
    sidebar_tipo = "\n".join(tipo_items)

    # Sidebar estado
    estado_sel = set(estado.split("|")) - {""} if estado else set()
    estado_items = []
    for cod, nombre in ESTADOS.items():
        active = "lm-active" if cod in estado_sel else ""
        estado_items.append(
            f'<div class="lm-sidebar-item lm-check-item {active}" data-group="estado" data-value="{cod}">'
            f'<span>{nombre}</span></div>'
        )
    sidebar_estado = "\n".join(estado_items)

    # Sidebar presupuesto
    prange_sel = set(prange.split("|")) - {""} if prange else set()
    prange_items = []
    for cod, nombre, _, __ in PRANGES:
        active = "lm-active" if cod in prange_sel else ""
        prange_items.append(
            f'<div class="lm-sidebar-item lm-check-item {active}" data-group="prange" data-value="{cod}">'
            f'<span>{nombre}</span></div>'
        )
    sidebar_prange = "\n".join(prange_items)

    auth_block, busqueda_display, lang_selector = _nav_context(request)
    return render(
        "mapa.html",
        active_busqueda="",
        active_mapa="lm-nav-tab-active",
        nav_auth_block=auth_block,
        nav_busqueda_display=busqueda_display,
        lang_selector=lang_selector,
        q=q,
        cpv_q=cpv_q,
        tipo=tipo,
        estado=estado,
        prange=prange,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        total_espana=total_espana_str,
        resultados=f"{resultados:,}".replace(",", "."),
        en_plazo=f"{en_plazo:,}".replace(",", "."),
        ultima_sync=ultima_sync,
        sidebar_tipo=sidebar_tipo,
        sidebar_estado=sidebar_estado,
        sidebar_prange=sidebar_prange,
    )


@router.get("/api/map/nombres", response_class=JSONResponse)
def api_nombres(db: Session = Depends(get_db)):
    """Devuelve listas de provincias y municipios para autocomplete.

    Provincias: lista canónica del geojson (52). Los feeds ATOM no
    siempre populan Licitacion.provincia, así que derivarla de la BD
    daba una lista vacía o incompleta. Municipios: desde BD, donde
    sí es un dato consistente para licitaciones de España.
    """
    municipios = [
        r[0] for r in db.query(Licitacion.municipio).filter(
            Licitacion.municipio.isnot(None),
            Licitacion.pais == "España",
        ).distinct().order_by(Licitacion.municipio).all()
    ]
    return {"provincias": _PROVINCIAS_CANONICAL, "municipios": municipios}


@router.get("/api/map/provincias", response_class=JSONResponse)
def api_provincias(
    q: str = Query(default=""),
    cpv_q: str = Query(default=""),
    tipo: str = Query(default=""),
    estado: str = Query(default=""),
    prange: str = Query(default=""),
    fecha_desde: str = Query(default=""),
    fecha_hasta: str = Query(default=""),
    provincia: str = Query(default=""),
    municipio: str = Query(default=""),
    db: Session = Depends(get_db),
):
    base = apply_common_filters(
        db.query(Licitacion).filter(Licitacion.pais == "España", Licitacion.provincia.isnot(None)),
        q, tipo, estado, prange, fecha_desde, fecha_hasta, cpv_q=cpv_q,
    )
    if provincia:
        base = base.filter(Licitacion.provincia == provincia)
    if municipio:
        base = base.filter(Licitacion.municipio.ilike(f"%{municipio}%"))
    hoy = date.today()
    en_plazo_expr = func.count(case((and_(Licitacion.estado == "PUB", Licitacion.fecha_limite >= hoy), 1)))
    rows = (
        base.with_entities(Licitacion.provincia, func.count().label("n"), en_plazo_expr.label("ep"))
        .group_by(Licitacion.provincia)
        .order_by(func.count().desc())
        .all()
    )
    return {"provincias": {row[0]: {"total": row[1], "en_plazo": row[2]} for row in rows if row[0]}}


@router.get("/api/map/municipios", response_class=JSONResponse)
def api_municipios(
    ccaa: str = Query(default=""),
    q: str = Query(default=""),
    cpv_q: str = Query(default=""),
    tipo: str = Query(default=""),
    estado: str = Query(default=""),
    prange: str = Query(default=""),
    fecha_desde: str = Query(default=""),
    fecha_hasta: str = Query(default=""),
    provincia: str = Query(default=""),
    municipio: str = Query(default=""),
    db: Session = Depends(get_db),
):
    base = apply_common_filters(
        db.query(Licitacion).filter(Licitacion.pais == "España", Licitacion.municipio.isnot(None)),
        q, tipo, estado, prange, fecha_desde, fecha_hasta, cpv_q=cpv_q
    )
    if ccaa:
        base = base.filter(Licitacion.comunidad_autonoma == ccaa)
    if provincia:
        base = base.filter(Licitacion.provincia == provincia)
    if municipio:
        base = base.filter(Licitacion.municipio.ilike(f"%{municipio}%"))

    hoy = date.today()
    en_plazo_expr = func.count(case((and_(Licitacion.estado == "PUB", Licitacion.fecha_limite >= hoy), 1)))
    rows = (
        base.with_entities(Licitacion.municipio, func.count().label("n"), en_plazo_expr.label("ep"))
        .group_by(Licitacion.municipio)
        .order_by(func.count().desc())
        .limit(300)
        .all()
    )
    return {"municipios": {row[0]: {"total": row[1], "en_plazo": row[2]} for row in rows if row[0]}}


@router.get("/api/map", response_class=JSONResponse)
def api_mapa(
    q: str = Query(default=""),
    cpv_q: str = Query(default=""),
    tipo: str = Query(default=""),
    estado: str = Query(default=""),
    prange: str = Query(default=""),
    fecha_desde: str = Query(default=""),
    fecha_hasta: str = Query(default=""),
    provincia: str = Query(default=""),
    municipio: str = Query(default=""),
    db: Session = Depends(get_db),
):
    common = apply_common_filters(db.query(Licitacion), q, tipo, estado, prange, fecha_desde, fecha_hasta, cpv_q=cpv_q)
    if provincia:
        common = common.filter(Licitacion.provincia == provincia)
    if municipio:
        common = common.filter(Licitacion.municipio.ilike(f"%{municipio}%"))
    base = apply_territorio_filter(common)
    hoy = date.today()
    en_plazo_expr = func.count(case((and_(Licitacion.estado == "PUB", Licitacion.fecha_limite >= hoy), 1)))
    rows = (
        base.with_entities(Licitacion.comunidad_autonoma, func.count().label("n"), en_plazo_expr.label("ep"))
        .group_by(Licitacion.comunidad_autonoma)
        .all()
    )
    # Stats globales sobre toda España
    stats_query = common.filter(Licitacion.pais == "España")
    resultados = stats_query.count()
    en_plazo_total = stats_query.filter(Licitacion.estado == "PUB", Licitacion.fecha_limite >= hoy).count()
    return {
        "ccaa": {row[0]: {"total": row[1], "en_plazo": row[2]} for row in rows if row[0]},
        "resultados": f"{resultados:,}".replace(",", "."),
        "en_plazo": f"{en_plazo_total:,}".replace(",", "."),
    }
