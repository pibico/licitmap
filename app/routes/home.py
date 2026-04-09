from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pathlib import Path
from urllib.parse import urlencode

from app.database import get_db
from app.models import Licitacion

router = APIRouter()

PER_PAGE = 50

ESTADOS = {
    "PUB": "Publicada",
    "ADJ": "Adjudicada",
    "PRE": "Preevaluación",
    "RES": "Resuelta",
    "EV": "En evaluación",
    "ANUL": "Anulada",
}


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


@router.get("/", response_class=HTMLResponse)
def home(
    db: Session = Depends(get_db),
    q: str = Query(default=""),
    ccaa: str = Query(default=""),
    estado: str = Query(default=""),
    pmin: str = Query(default=""),
    pmax: str = Query(default=""),
    page: int = Query(default=1, ge=1),
):
    query = db.query(Licitacion)

    if q:
        like = f"%{q}%"
        query = query.filter(or_(
            Licitacion.titulo.ilike(like),
            Licitacion.organo_contratacion.ilike(like),
            Licitacion.expediente.ilike(like),
        ))
    if ccaa:
        query = query.filter(Licitacion.comunidad_autonoma == ccaa)
    if estado:
        query = query.filter(Licitacion.estado == estado)
    if pmin:
        try:
            query = query.filter(Licitacion.presupuesto >= float(pmin))
        except ValueError:
            pass
    if pmax:
        try:
            query = query.filter(Licitacion.presupuesto <= float(pmax))
        except ValueError:
            pass

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

    # Filas
    filas = ""
    for lic in licitaciones:
        presupuesto = f"{lic.presupuesto:,.2f} €" if lic.presupuesto else "—"
        estado_val = lic.estado or "—"
        filas += f"""<tr>
            <td><a href="{lic.url}" target="_blank">{lic.expediente}</a></td>
            <td>{lic.titulo or '—'}</td>
            <td>{lic.organo_contratacion or '—'}</td>
            <td>{lic.comunidad_autonoma or '—'}</td>
            <td class="text-end">{presupuesto}</td>
            <td><span class="badge badge-{estado_val}">{estado_val}</span></td>
        </tr>"""

    # CCAA dropdown
    ccaa_rows = db.query(Licitacion.comunidad_autonoma).filter(
        Licitacion.comunidad_autonoma.isnot(None)
    ).distinct().order_by(Licitacion.comunidad_autonoma).all()
    ccaa_options = "".join(
        f'<option value="{r[0]}"{"  selected" if ccaa == r[0] else ""}>{r[0]}</option>'
        for r in ccaa_rows
    )

    # Estado dropdown
    estado_options = "".join(
        f'<option value="{code}"{"  selected" if estado == code else ""}>{label}</option>'
        for code, label in ESTADOS.items()
    )

    params = {"q": q, "ccaa": ccaa, "estado": estado, "pmin": pmin, "pmax": pmax}

    return render(
        "home.html",
        total=total,
        resultados=resultados,
        filas=filas,
        ccaa_options=ccaa_options,
        estado_options=estado_options,
        q=q,
        ccaa=ccaa,
        estado=estado,
        pmin=pmin,
        pmax=pmax,
        paginacion=build_pagination(page, total_pages, params),
    )
