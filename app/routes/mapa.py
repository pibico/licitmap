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
from app.i18n import get_lang_from_request, t

router = APIRouter()


def _load_provincias_from_geojson() -> tuple[list[str], dict[str, str]]:
    """Devuelve (lista canónica de 52 provincias, dict {codigo2dig: nombre}).
    Usada para:
    - Autocompletado del sidebar (lista).
    - Derivar provincia desde codigo_postal (dict) en `/api/map/provincias`,
      porque Licitacion.provincia está vacío en BD (el sync ATOM no lo
      popula, pero sí rellena codigo_postal, cuyos 2 primeros dígitos son
      el código de provincia en España)."""
    path = Path(__file__).parents[2] / "static" / "data" / "provincias.geojson"
    try:
        features = _json.loads(path.read_text()).get("features", [])
    except Exception:
        return [], {}
    cp_to_name: dict[str, str] = {}
    for f in features:
        p = f.get("properties", {})
        cod, nom = p.get("Codigo"), p.get("Texto")
        if cod and nom:
            cp_to_name[cod.zfill(2)] = nom
    return sorted(cp_to_name.values()), cp_to_name


_PROVINCIAS_CANONICAL, _CP_TO_PROVINCIA = _load_provincias_from_geojson()

ESTADOS = {k: f"{{{{t.estado.{k}}}}}" for k in ("PUB", "ADJ", "PRE", "RES", "EV", "ANUL")}

TIPOS_CONTRATO = {k: f"{{{{t.tipo.{k}}}}}" for k in ("1", "2", "3", "7", "8", "22", "31", "32", "40", "50")}

PRANGES = [
    ("5k",   "{{t.prange.5k}}",     None,      5_000),
    ("15k",  "{{t.prange.15k}}",    5_000,     15_000),
    ("100k", "{{t.prange.100k}}",   15_000,    100_000),
    ("1m",   "{{t.prange.1m}}",     100_000,   1_000_000),
    ("1m+",  "{{t.prange.1mplus}}", 1_000_000, None),
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

    # Última sincronización (traducida)
    ultima_sync = "—"
    _state_file = Path(__file__).parents[2] / "data" / "sync_state.json"
    if _state_file.exists():
        try:
            _last = _json.loads(_state_file.read_text()).get("last_sync")
            if _last:
                _diff = (date.today() - datetime.fromisoformat(_last).date()).days
                _lang = get_lang_from_request(request)
                if _diff == 0:
                    ultima_sync = t("home.sync_today", _lang)
                elif _diff == 1:
                    ultima_sync = t("home.sync_yesterday", _lang)
                else:
                    ultima_sync = t("home.sync_days_ago", _lang, n=_diff)
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
    # Licitacion.provincia está vacía en BD. Derivamos la provincia desde los
    # 2 primeros dígitos del codigo_postal (esquema español: CP 28xxx = Madrid,
    # 08xxx = Barcelona, etc.). Filtramos por CP no nulo en vez de provincia.
    base = apply_common_filters(
        db.query(Licitacion).filter(Licitacion.pais == "España", Licitacion.codigo_postal.isnot(None)),
        q, tipo, estado, prange, fecha_desde, fecha_hasta, cpv_q=cpv_q,
    )
    if municipio:
        base = base.filter(Licitacion.municipio.ilike(f"%{municipio}%"))

    hoy = date.today()
    cp2 = func.substr(Licitacion.codigo_postal, 1, 2)
    en_plazo_expr = func.count(case((and_(Licitacion.estado == "PUB", Licitacion.fecha_limite >= hoy), 1)))
    rows = (
        base.with_entities(cp2.label("cp2"), func.count().label("n"), en_plazo_expr.label("ep"))
        .group_by("cp2")
        .all()
    )

    # Agregamos en {nombre_provincia: {total, en_plazo}}. Si el usuario filtra
    # por provincia, recortamos tras el mapeo (filtro por nombre, no por CP).
    result: dict[str, dict] = {}
    for code, n, ep in rows:
        nombre = _CP_TO_PROVINCIA.get((code or "").zfill(2))
        if not nombre:
            continue
        if provincia and nombre != provincia:
            continue
        acc = result.setdefault(nombre, {"total": 0, "en_plazo": 0})
        acc["total"]    += int(n or 0)
        acc["en_plazo"] += int(ep or 0)
    return {"provincias": result}


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
