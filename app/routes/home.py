from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from pathlib import Path
from urllib.parse import urlencode
from datetime import date

from app.database import get_db
from app.models import Licitacion

router = APIRouter()

PER_PAGE = 20

ESTADOS = {
    "PUB": "Publicada",
    "ADJ": "Adjudicada",
    "PRE": "Preevaluación",
    "RES": "Resuelta",
    "EV": "En evaluación",
    "ANUL": "Anulada",
}

TERRITORIOS_ESPECIALES = {"Todo el territorio", "Extra-Regio", "Extranjero"}

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
    ("5k",   "Menos de 5.000 €",   None,        5_000),
    ("15k",  "5.000 – 15.000 €",   5_000,       15_000),
    ("100k", "15.000 – 100.000 €", 15_000,      100_000),
    ("1m",   "100.000 – 1M €",     100_000,     1_000_000),
    ("1m+",  "Más de 1M €",        1_000_000,   None),
]


def render(template, **kwargs):
    base = Path("templates/base.html").read_text()
    page = Path(f"templates/{template}").read_text()
    html = base.replace("{{content}}", page)
    for key, value in kwargs.items():
        html = html.replace("{{" + key + "}}", str(value))
    return html


def build_pagination(page, total_pages, params):
    if total_pages <= 1:
        return ""

    def page_url(p):
        p_params = {k: v for k, v in params.items() if v}
        p_params["page"] = p
        return "/?" + urlencode(p_params)

    items = []
    items.append(
        f'<li class="page-item{"  disabled" if page == 1 else ""}"><a class="page-link" href="{page_url(page - 1)}">‹</a></li>'
    )

    pages = sorted(set(
        [1, 2, total_pages - 1, total_pages] +
        list(range(max(1, page - 2), min(total_pages + 1, page + 3)))
    ))

    prev = None
    for p in pages:
        if p < 1 or p > total_pages:
            continue
        if prev is not None and p - prev > 1:
            items.append('<li class="page-item disabled"><span class="page-link">…</span></li>')
        active = ' active' if p == page else ''
        items.append(f'<li class="page-item{active}"><a class="page-link" href="{page_url(p)}">{p}</a></li>')
        prev = p

    items.append(
        f'<li class="page-item{"  disabled" if page == total_pages else ""}"><a class="page-link" href="{page_url(page + 1)}">›</a></li>'
    )

    return '<nav><ul class="pagination justify-content-center flex-wrap">' + "".join(items) + "</ul></nav>"


def sidebar_item(label, count, field, value, active):
    active_class = " lm-active" if active else ""
    count_str = f"{count:,}".replace(",", ".")
    return (
        f'<a href="#" class="lm-sidebar-item{active_class}" '
        f'data-field="{field}" data-value="{value}">'
        f'<span>{label}</span>'
        f'<span class="lm-sidebar-count">{count_str}</span>'
        f'</a>'
    )


@router.get("/", response_class=HTMLResponse)
def home(
    db: Session = Depends(get_db),
    q: str = Query(default=""),
    ccaa: str = Query(default=""),
    pais: str = Query(default="España"),
    estado: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    partial: str = Query(default=""),
    tipo: str = Query(default=""),
    fecha_desde: str = Query(default=""),
    prange: str = Query(default=""),
):
    query = db.query(Licitacion)

    if q:
        like = f"%{q}%"
        query = query.filter(or_(
            Licitacion.titulo.ilike(like),
            Licitacion.organo_contratacion.ilike(like),
            Licitacion.expediente.ilike(like),
        ))
    if pais == "España":
        query = query.filter(Licitacion.pais == "España")
    elif pais:
        query = query.filter(Licitacion.pais == pais)
    if ccaa:
        query = query.filter(Licitacion.comunidad_autonoma == ccaa)
    if estado:
        query = query.filter(Licitacion.estado == estado)
    if tipo:
        query = query.filter(Licitacion.tipo_contrato == tipo)
    if fecha_desde:
        try:
            query = query.filter(Licitacion.fecha_limite >= date.fromisoformat(fecha_desde))
        except ValueError:
            pass
    if prange:
        for code, _label, pmin_v, pmax_v in PRANGES:
            if prange == code:
                if pmin_v is not None:
                    query = query.filter(Licitacion.presupuesto >= pmin_v)
                if pmax_v is not None:
                    query = query.filter(Licitacion.presupuesto < pmax_v)
                break

    total = db.query(Licitacion).count()
    resultados = query.count()
    total_pages = max(1, (resultados + PER_PAGE - 1) // PER_PAGE)
    page = min(page, total_pages)

    licitaciones = (
        query.order_by(Licitacion.fecha_publicacion.desc())
        .offset((page - 1) * PER_PAGE)
        .limit(PER_PAGE)
        .all()
    )

    # Cards
    filas = ""
    for lic in licitaciones:
        presupuesto_str = ("€ " + f"{lic.presupuesto:,.0f}".replace(",", ".")) if lic.presupuesto else "—"
        estado_val = lic.estado or "—"
        estado_label = ESTADOS.get(estado_val, estado_val)
        fecha_str = lic.fecha_limite.strftime("%d/%m/%Y") if lic.fecha_limite else "—"
        tipo_nombre = TIPOS_CONTRATO.get(lic.tipo_contrato or "", "—")
        if lic.comunidad_autonoma == "Extranjero":
            territorio = lic.pais or "Extranjero"
        else:
            territorio = lic.comunidad_autonoma or "—"

        filas += f"""<div class="lm-card">
  <div class="lm-card-top">
    <a href="{lic.url}" target="_blank" class="lm-card-title">{lic.titulo or '—'}</a>
    <span class="badge badge-{estado_val} flex-shrink-0">{estado_label}</span>
  </div>
  <div class="lm-card-meta">
    <span>Exp. {lic.expediente or '—'}</span>
    <span class="lm-dot">·</span>
    <span>Plazo {fecha_str}</span>
    <span class="lm-dot">·</span>
    <span>{tipo_nombre}</span>
  </div>
  <div class="lm-card-footer">
    <span class="lm-card-org">{lic.organo_contratacion or '—'} · {territorio}</span>
    <span class="lm-card-price">{presupuesto_str}</span>
  </div>
</div>"""

    params = {"q": q, "pais": pais, "ccaa": ccaa, "estado": estado, "tipo": tipo,
              "fecha_desde": fecha_desde, "prange": prange}
    paginacion = build_pagination(page, total_pages, params)

    if partial == "1":
        return JSONResponse({
            "filas": filas,
            "paginacion": paginacion,
            "resultados": resultados,
        })

    # --- Sidebar data (global counts) ---
    tipo_counts_raw = dict(
        db.query(Licitacion.tipo_contrato, func.count(Licitacion.id))
        .filter(Licitacion.tipo_contrato.isnot(None))
        .group_by(Licitacion.tipo_contrato).all()
    )
    ccaa_counts_raw = (
        db.query(Licitacion.comunidad_autonoma, func.count(Licitacion.id))
        .filter(
            Licitacion.comunidad_autonoma.isnot(None),
            Licitacion.comunidad_autonoma != "Extranjero",
            ~Licitacion.comunidad_autonoma.in_(TERRITORIOS_ESPECIALES),
        )
        .group_by(Licitacion.comunidad_autonoma)
        .order_by(func.count(Licitacion.id).desc()).all()
    )
    estado_counts_raw = dict(
        db.query(Licitacion.estado, func.count(Licitacion.id))
        .filter(Licitacion.estado.isnot(None))
        .group_by(Licitacion.estado).all()
    )
    en_plazo_count = estado_counts_raw.get("PUB", 0)

    sidebar_tipo = "".join(
        sidebar_item(label, tipo_counts_raw.get(code, 0), "tipo", code, tipo == code)
        for code, label in TIPOS_CONTRATO.items()
        if tipo_counts_raw.get(code, 0) > 0
    )

    top_ccaa = ccaa_counts_raw[:7]
    rest_ccaa = ccaa_counts_raw[7:]
    sidebar_ccaa = "".join(sidebar_item(v, c, "ccaa", v, ccaa == v) for v, c in top_ccaa)
    if rest_ccaa:
        sidebar_ccaa += (
            f'<a href="#" class="lm-sidebar-ver-todas">Ver todas ({len(rest_ccaa)} más)...</a>'
            f'<div class="lm-sidebar-extra" style="display:none">'
            + "".join(sidebar_item(v, c, "ccaa", v, ccaa == v) for v, c in rest_ccaa)
            + '<a href="#" class="lm-sidebar-ver-todas lm-sidebar-ver-menos">Ver menos...</a>'
            + '</div>'
        )

    # País sidebar
    pais_counts_raw = (
        db.query(Licitacion.pais, func.count(Licitacion.id))
        .filter(Licitacion.pais.isnot(None))
        .group_by(Licitacion.pais)
        .order_by(func.count(Licitacion.id).desc()).all()
    )
    espana_count = next((c for v, c in pais_counts_raw if v == "España"), 0)
    intl_count = sum(c for v, c in pais_counts_raw if v != "España")
    sidebar_pais = sidebar_item("España", espana_count, "pais", "España", pais == "España")
    if intl_count > 0:
        sidebar_pais += sidebar_item("Internacional", intl_count, "pais", "", pais == "")

    sidebar_estado = "".join(
        sidebar_item(label, estado_counts_raw.get(code, 0), "estado", code, estado == code)
        for code, label in ESTADOS.items()
        if estado_counts_raw.get(code, 0) > 0
    )

    def prange_count(pmin_v, pmax_v):
        rq = db.query(func.count(Licitacion.id)).filter(Licitacion.presupuesto.isnot(None))
        if pmin_v is not None:
            rq = rq.filter(Licitacion.presupuesto >= pmin_v)
        if pmax_v is not None:
            rq = rq.filter(Licitacion.presupuesto < pmax_v)
        return rq.scalar() or 0

    sidebar_prange = "".join(
        sidebar_item(label, prange_count(pmin_v, pmax_v), "prange", code, prange == code)
        for code, label, pmin_v, pmax_v in PRANGES
    )

    return render(
        "home.html",
        total=f"{total:,}".replace(",", "."),
        en_plazo=f"{en_plazo_count:,}".replace(",", "."),
        resultados=resultados,
        filas=filas,
        sidebar_tipo=sidebar_tipo,
        sidebar_pais=sidebar_pais,
        sidebar_ccaa=sidebar_ccaa,
        sidebar_estado=sidebar_estado,
        sidebar_prange=sidebar_prange,
        q=q,
        pais=pais,
        ccaa=ccaa,
        estado=estado,
        tipo=tipo,
        fecha_desde=fecha_desde,
        prange=prange,
        paginacion=paginacion,
    )
