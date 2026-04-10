from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from pathlib import Path
from datetime import date

from app.database import get_db
from app.models import Licitacion

router = APIRouter()

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


def apply_common_filters(query, q, tipo, estado, prange, fecha_desde, fecha_hasta):
    """Aplica filtros comunes sin filtrar por territorio (eso se hace aparte)."""
    if q:
        query = query.filter(
            or_(
                Licitacion.titulo.ilike(f"%{q}%"),
                Licitacion.organo_contratacion.ilike(f"%{q}%"),
                Licitacion.expediente.ilike(f"%{q}%"),
                Licitacion.cpv.ilike(f"%{q}%"),
            )
        )

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


@router.get("/mapa", response_class=HTMLResponse)
def mapa_page(
    q: str = Query(default=""),
    tipo: str = Query(default=""),
    estado: str = Query(default=""),
    prange: str = Query(default=""),
    fecha_desde: str = Query(default=""),
    fecha_hasta: str = Query(default=""),
    db: Session = Depends(get_db),
):
    query = apply_territorio_filter(
        apply_common_filters(db.query(Licitacion), q, tipo, estado, prange, fecha_desde, fecha_hasta)
    )
    total = query.count()
    en_plazo = query.filter(Licitacion.fecha_limite >= date.today()).count()

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

    return render(
        "mapa.html",
        active_busqueda="",
        active_mapa="lm-nav-tab-active",
        q=q,
        tipo=tipo,
        estado=estado,
        prange=prange,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        total=f"{total:,}".replace(",", "."),
        en_plazo=f"{en_plazo:,}".replace(",", "."),
        sidebar_tipo=sidebar_tipo,
        sidebar_estado=sidebar_estado,
        sidebar_prange=sidebar_prange,
    )


@router.get("/api/mapa", response_class=JSONResponse)
def api_mapa(
    q: str = Query(default=""),
    tipo: str = Query(default=""),
    estado: str = Query(default=""),
    prange: str = Query(default=""),
    fecha_desde: str = Query(default=""),
    fecha_hasta: str = Query(default=""),
    db: Session = Depends(get_db),
):
    base = apply_territorio_filter(
        apply_common_filters(db.query(Licitacion), q, tipo, estado, prange, fecha_desde, fecha_hasta)
    )
    rows = (
        base.with_entities(Licitacion.comunidad_autonoma, func.count().label("n"))
        .group_by(Licitacion.comunidad_autonoma)
        .all()
    )
    return {row[0]: row[1] for row in rows if row[0]}
