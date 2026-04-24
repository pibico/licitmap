from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from pathlib import Path
from datetime import date
import re

from app.database import get_db
from app.models import Licitacion
from app.utils import _nav_context
from app.i18n import get_lang_from_request, translate_html

router = APIRouter()

ESTADOS = {k: f"{{{{t.estado.{k}}}}}" for k in ("PUB", "ADJ", "PRE", "RES", "EV", "ANUL")}

TIPOS_CONTRATO = {k: f"{{{{t.tipo.{k}}}}}" for k in ("1", "2", "3", "7", "8", "22", "31", "32", "40", "50")}

PRANGES = [
    ("5k",   "{{t.prange.5k}}",     None,       5_000),
    ("15k",  "{{t.prange.15k}}",    5_000,      15_000),
    ("100k", "{{t.prange.100k}}",   15_000,     100_000),
    ("1m",   "{{t.prange.1m}}",     100_000,    1_000_000),
    ("1m+",  "{{t.prange.1mplus}}", 1_000_000,  None),
]

TERRITORIOS_ESPECIALES = {"Todo el territorio", "Extra-Regio", "Extranjero"}


def _render_page(request: Request) -> str:
    auth_block, busqueda_display, lang_selector = _nav_context(request)
    base = Path("templates/base.html").read_text()
    page = Path("templates/analisis.html").read_text()
    html = base.replace("{{content}}", page)
    for k, v in {
        "active_busqueda": "",
        "active_mapa": "",
        "nav_auth_block": auth_block,
        "nav_busqueda_display": busqueda_display,
        "lang_selector": lang_selector,
    }.items():
        html = html.replace("{{" + k + "}}", v)
    html = re.sub(r"\{\{[a-z_]+\}\}", "", html)
    return html


def _apply_filters(query, ccaa="", estado="", tipo="", prange="",
                   fecha_desde="", fecha_hasta="", solo_plazo=False, organismo=""):
    if solo_plazo:
        query = query.filter(
            Licitacion.estado == "PUB",
            Licitacion.fecha_limite >= date.today(),
        )
    if ccaa:
        items = [c for c in ccaa.split("|") if c]
        if items:
            query = query.filter(Licitacion.comunidad_autonoma.in_(items))
    if estado:
        items = [e for e in estado.split("|") if e]
        if items:
            query = query.filter(Licitacion.estado.in_(items))
    if tipo:
        items = [t for t in tipo.split("|") if t]
        if items:
            query = query.filter(Licitacion.tipo_contrato.in_(items))
    if fecha_desde:
        try:
            query = query.filter(Licitacion.fecha_publicacion >= date.fromisoformat(fecha_desde))
        except ValueError:
            pass
    if fecha_hasta:
        try:
            query = query.filter(Licitacion.fecha_publicacion <= date.fromisoformat(fecha_hasta))
        except ValueError:
            pass
    if prange:
        pranges = [p for p in prange.split("|") if p]
        conds = []
        for code in pranges:
            for c, _, lo, hi in PRANGES:
                if c == code:
                    rc = []
                    if lo is not None:
                        rc.append(Licitacion.presupuesto >= lo)
                    if hi is not None:
                        rc.append(Licitacion.presupuesto < hi)
                    if rc:
                        conds.append(and_(*rc))
                    break
        if conds:
            query = query.filter(or_(*conds))
    if organismo:
        query = query.filter(Licitacion.organo_contratacion.ilike(f"%{organismo}%"))
    return query


@router.get("/analytics", response_class=HTMLResponse)
def analisis_page(request: Request):
    if not request.session.get("username"):
        return RedirectResponse("/login", status_code=303)
    return HTMLResponse(_render_page(request))


@router.get("/api/analytics/data")
def analisis_data(
    request: Request,
    db: Session = Depends(get_db),
    ccaa: str = Query(default=""),
    estado: str = Query(default=""),
    tipo: str = Query(default=""),
    prange: str = Query(default=""),
    fecha_desde: str = Query(default=""),
    fecha_hasta: str = Query(default=""),
    solo_plazo: str = Query(default=""),
    organismo: str = Query(default=""),
):
    if not request.session.get("username"):
        return JSONResponse({"error": "no autenticado"}, status_code=401)

    sp = solo_plazo in ("1", "true", "yes")
    base = _apply_filters(
        db.query(Licitacion), ccaa, estado, tipo, prange,
        fecha_desde, fecha_hasta, sp, organismo,
    )

    # ── KPIs ─────────────────────────────────────────────────────────────────
    total = base.count()
    en_plazo = (
        base.filter(Licitacion.estado == "PUB", Licitacion.fecha_limite >= date.today())
        .count()
    )

    base_pres = base.filter(Licitacion.presupuesto.isnot(None))
    con_presupuesto = base_pres.count()
    presup_stats = base_pres.with_entities(
        func.sum(Licitacion.presupuesto),
        func.avg(Licitacion.presupuesto),
        func.max(Licitacion.presupuesto),
        func.min(Licitacion.presupuesto),
    ).one()
    presup_total, presup_medio, presup_max, presup_min = presup_stats

    organismos_dist = (
        base.with_entities(func.count(func.distinct(Licitacion.organo_contratacion)))
        .scalar() or 0
    )
    municipios_dist = (
        base.filter(Licitacion.municipio.isnot(None), Licitacion.municipio != "")
        .with_entities(func.count(func.distinct(Licitacion.municipio)))
        .scalar() or 0
    )
    provincias_dist = (
        base.filter(Licitacion.provincia.isnot(None), Licitacion.provincia != "")
        .with_entities(func.count(func.distinct(Licitacion.provincia)))
        .scalar() or 0
    )

    # ── Por CCAA ─────────────────────────────────────────────────────────────
    por_ccaa = (
        base.with_entities(Licitacion.comunidad_autonoma, func.count(Licitacion.id))
        .filter(
            Licitacion.comunidad_autonoma.isnot(None),
            Licitacion.comunidad_autonoma != "Extranjero",
            ~Licitacion.comunidad_autonoma.in_(TERRITORIOS_ESPECIALES),
        )
        .group_by(Licitacion.comunidad_autonoma)
        .order_by(func.count(Licitacion.id).desc())
        .all()
    )

    # ── Por tipo ─────────────────────────────────────────────────────────────
    por_tipo = (
        base.with_entities(Licitacion.tipo_contrato, func.count(Licitacion.id))
        .filter(Licitacion.tipo_contrato.isnot(None))
        .group_by(Licitacion.tipo_contrato)
        .order_by(func.count(Licitacion.id).desc())
        .all()
    )

    # ── Por estado ────────────────────────────────────────────────────────────
    por_estado = (
        base.with_entities(Licitacion.estado, func.count(Licitacion.id))
        .filter(Licitacion.estado.isnot(None))
        .group_by(Licitacion.estado)
        .order_by(func.count(Licitacion.id).desc())
        .all()
    )

    # ── Por rango presupuesto ─────────────────────────────────────────────────
    prange_data = []
    for code, label, lo, hi in PRANGES:
        q2 = base_pres
        if lo is not None:
            q2 = q2.filter(Licitacion.presupuesto >= lo)
        if hi is not None:
            q2 = q2.filter(Licitacion.presupuesto < hi)
        prange_data.append({"label": label, "value": q2.count()})

    # ── Evolución mensual ─────────────────────────────────────────────────────
    mes_col = func.to_char(
        func.date_trunc("month", Licitacion.fecha_publicacion), "YYYY-MM"
    ).label("mes")
    por_mes = (
        base.with_entities(mes_col, func.count(Licitacion.id))
        .filter(Licitacion.fecha_publicacion.isnot(None))
        .group_by(mes_col)
        .order_by(mes_col)
        .all()
    )

    # ── Top organismos ────────────────────────────────────────────────────────
    top_org = (
        base.with_entities(Licitacion.organo_contratacion, func.count(Licitacion.id))
        .filter(Licitacion.organo_contratacion.isnot(None))
        .group_by(Licitacion.organo_contratacion)
        .order_by(func.count(Licitacion.id).desc())
        .limit(15)
        .all()
    )

    # ── Top provincias ────────────────────────────────────────────────────────
    top_prov = (
        base.with_entities(Licitacion.provincia, func.count(Licitacion.id))
        .filter(Licitacion.provincia.isnot(None), Licitacion.provincia != "")
        .group_by(Licitacion.provincia)
        .order_by(func.count(Licitacion.id).desc())
        .limit(15)
        .all()
    )

    # ── Top municipios ────────────────────────────────────────────────────────
    top_mun = (
        base.with_entities(Licitacion.municipio, func.count(Licitacion.id))
        .filter(Licitacion.municipio.isnot(None), Licitacion.municipio != "")
        .group_by(Licitacion.municipio)
        .order_by(func.count(Licitacion.id).desc())
        .limit(15)
        .all()
    )

    # ── Presupuesto por CCAA ──────────────────────────────────────────────────
    presup_ccaa_base = base.filter(
        Licitacion.presupuesto.isnot(None),
        Licitacion.comunidad_autonoma.isnot(None),
        Licitacion.comunidad_autonoma != "Extranjero",
        ~Licitacion.comunidad_autonoma.in_(TERRITORIOS_ESPECIALES),
    )
    presup_medio_ccaa = (
        presup_ccaa_base
        .with_entities(Licitacion.comunidad_autonoma, func.avg(Licitacion.presupuesto))
        .group_by(Licitacion.comunidad_autonoma)
        .order_by(func.avg(Licitacion.presupuesto).desc())
        .all()
    )
    presup_total_ccaa = (
        presup_ccaa_base
        .with_entities(Licitacion.comunidad_autonoma, func.sum(Licitacion.presupuesto))
        .group_by(Licitacion.comunidad_autonoma)
        .order_by(func.sum(Licitacion.presupuesto).desc())
        .all()
    )

    _lang = get_lang_from_request(request)

    def f(v):
        return round(float(v), 2) if v is not None else None

    return JSONResponse({
        "kpis": {
            "total": total,
            "en_plazo": en_plazo,
            "pct_en_plazo": round(en_plazo / total * 100, 1) if total else 0,
            "con_presupuesto": con_presupuesto,
            "pct_presupuesto": round(con_presupuesto / total * 100, 1) if total else 0,
            "presupuesto_total": f(presup_total),
            "presupuesto_medio": f(presup_medio),
            "presupuesto_max": f(presup_max),
            "presupuesto_min": f(presup_min),
            "organismos_distintos": int(organismos_dist),
            "municipios_distintos": int(municipios_dist),
            "provincias_distintas": int(provincias_dist),
        },
        "por_ccaa": [{"label": r[0], "value": r[1]} for r in por_ccaa],
        "por_tipo": [{"label": translate_html(TIPOS_CONTRATO.get(r[0], r[0]), _lang), "value": r[1]} for r in por_tipo],
        "por_estado": [{"label": translate_html(ESTADOS.get(r[0], r[0]), _lang), "value": r[1]} for r in por_estado],
        "por_prange": [{"label": translate_html(d["label"], _lang), "value": d["value"]} for d in prange_data],
        "por_mes": [{"label": r[0], "value": r[1]} for r in por_mes if r[0]],
        "top_organismos": [{"label": r[0], "value": r[1]} for r in top_org],
        "top_provincias": [{"label": r[0], "value": r[1]} for r in top_prov],
        "top_municipios": [{"label": r[0], "value": r[1]} for r in top_mun],
        "presupuesto_medio_ccaa": [{"label": r[0], "value": f(r[1])} for r in presup_medio_ccaa],
        "presupuesto_total_ccaa": [{"label": r[0], "value": f(r[1])} for r in presup_total_ccaa],
    })
