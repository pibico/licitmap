from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from pathlib import Path
from urllib.parse import urlencode
from datetime import date, datetime

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

    # Primera página
    items.append(
        f'<li class="page-item{"  disabled" if page == 1 else ""}" title="Primera página">'
        f'<a class="page-link" href="{page_url(1)}">«</a></li>'
    )

    # Ventana: página actual ±2
    for p in range(max(1, page - 2), min(total_pages, page + 2) + 1):
        active = ' active' if p == page else ''
        items.append(f'<li class="page-item{active}"><a class="page-link" href="{page_url(p)}">{p}</a></li>')

    # Última página
    items.append(
        f'<li class="page-item{"  disabled" if page == total_pages else ""}" title="Última página">'
        f'<a class="page-link" href="{page_url(total_pages)}">»</a></li>'
    )

    # Salto de página
    items.append(
        f'<li class="page-item lm-page-jump-item">'
        f'<span class="page-link lm-page-jump-wrap">'
        f'<input class="lm-page-input" type="number" min="1" max="{total_pages}" value="{page}" data-total="{total_pages}" aria-label="Ir a página">'
        f'<span class="lm-page-total">/ {total_pages}</span>'
        f'</span></li>'
    )

    return '<nav><ul class="pagination justify-content-center flex-wrap mb-0">' + "".join(items) + "</ul></nav>"


def sidebar_item(label, count, field, value, active):
    active_class = " lm-active" if active else ""
    count_str = f"{count:,}".replace(",", ".")
    return (
        f'<div class="lm-sidebar-item{active_class}" '
        f'data-field="{field}" data-value="{value}">'
        f'<span>{label}</span>'
        f'<span class="lm-sidebar-count">{count_str}</span>'
        f'</div>'
    )


def apply_filters(query, q, pais, ccaa, estado, tipo, fecha_desde, fecha_hasta, prange,
                  skip_pais=False, skip_ccaa=False, skip_estado=False,
                  skip_tipo=False, skip_prange=False, cpv_q=""):
    if q:
        like = f"%{q}%"
        query = query.filter(or_(
            Licitacion.titulo.ilike(like),
            Licitacion.organo_contratacion.ilike(like),
            Licitacion.expediente.ilike(like),
        ))
    if cpv_q:
        query = query.filter(Licitacion.cpv.ilike(f"%{cpv_q}%"))
    if not skip_pais:
        if pais == "España":
            query = query.filter(Licitacion.pais == "España")
        elif pais == "__intl__":
            query = query.filter(Licitacion.pais != "España")
        elif pais:
            query = query.filter(Licitacion.pais == pais)
    if not skip_ccaa and ccaa:
        ccaas = [c for c in ccaa.split("|") if c]
        if ccaas:
            query = query.filter(Licitacion.comunidad_autonoma.in_(ccaas))
    if not skip_estado and estado:
        estados = [e for e in estado.split("|") if e]
        if estados:
            query = query.filter(Licitacion.estado.in_(estados))
    if not skip_tipo and tipo:
        tipos = [t for t in tipo.split("|") if t]
        if tipos:
            query = query.filter(Licitacion.tipo_contrato.in_(tipos))
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
    if not skip_prange and prange:
        pranges_sel = [p for p in prange.split("|") if p]
        range_conds = []
        for p_code in pranges_sel:
            for code, _label, pmin_v, pmax_v in PRANGES:
                if p_code == code:
                    conds = []
                    if pmin_v is not None:
                        conds.append(Licitacion.presupuesto >= pmin_v)
                    if pmax_v is not None:
                        conds.append(Licitacion.presupuesto < pmax_v)
                    if conds:
                        range_conds.append(and_(*conds))
                    break
        if range_conds:
            query = query.filter(or_(*range_conds))
    return query


def compute_sidebar(db, q, pais, ccaa, estado, tipo, fecha_desde, fecha_hasta, prange, cpv_q=""):
    base = db.query(Licitacion)

    # Tipo: todos los filtros excepto tipo
    tipo_counts_raw = dict(
        apply_filters(base, q, pais, ccaa, estado, tipo, fecha_desde, fecha_hasta, prange, skip_tipo=True, cpv_q=cpv_q)
        .with_entities(Licitacion.tipo_contrato, func.count(Licitacion.id))
        .filter(Licitacion.tipo_contrato.isnot(None))
        .group_by(Licitacion.tipo_contrato).all()
    )

    # Presupuesto: todos los filtros excepto prange
    prange_base = apply_filters(base, q, pais, ccaa, estado, tipo, fecha_desde, fecha_hasta, prange, skip_prange=True, cpv_q=cpv_q)

    def prange_count(pmin_v, pmax_v):
        rq = prange_base.with_entities(func.count(Licitacion.id)).filter(Licitacion.presupuesto.isnot(None))
        if pmin_v is not None:
            rq = rq.filter(Licitacion.presupuesto >= pmin_v)
        if pmax_v is not None:
            rq = rq.filter(Licitacion.presupuesto < pmax_v)
        return rq.scalar() or 0

    # País: todos los filtros excepto pais y ccaa
    pais_counts_raw = (
        apply_filters(base, q, pais, ccaa, estado, tipo, fecha_desde, fecha_hasta, prange, skip_pais=True, skip_ccaa=True, cpv_q=cpv_q)
        .with_entities(Licitacion.pais, func.count(Licitacion.id))
        .filter(Licitacion.pais.isnot(None))
        .group_by(Licitacion.pais)
        .order_by(func.count(Licitacion.id).desc()).all()
    )

    # CCAA: todos los filtros excepto ccaa (pero mantiene el filtro de pais)
    ccaa_counts_raw = (
        apply_filters(base, q, pais, ccaa, estado, tipo, fecha_desde, fecha_hasta, prange, skip_ccaa=True, cpv_q=cpv_q)
        .with_entities(Licitacion.comunidad_autonoma, func.count(Licitacion.id))
        .filter(
            Licitacion.comunidad_autonoma.isnot(None),
            Licitacion.comunidad_autonoma != "Extranjero",
            ~Licitacion.comunidad_autonoma.in_(TERRITORIOS_ESPECIALES),
        )
        .group_by(Licitacion.comunidad_autonoma)
        .order_by(Licitacion.comunidad_autonoma).all()
    )

    # Estado: todos los filtros excepto estado
    estado_counts_raw = dict(
        apply_filters(base, q, pais, ccaa, estado, tipo, fecha_desde, fecha_hasta, prange, skip_estado=True, cpv_q=cpv_q)
        .with_entities(Licitacion.estado, func.count(Licitacion.id))
        .filter(Licitacion.estado.isnot(None))
        .group_by(Licitacion.estado).all()
    )

    tipos_list = [t for t in tipo.split("|") if t]
    estados_list = [e for e in estado.split("|") if e]
    pranges_list = [p for p in prange.split("|") if p]
    ccaas_list = [c for c in ccaa.split("|") if c]

    # HTML sidebar tipo — siempre muestra todos los tipos conocidos (0 si no hay resultados)
    sidebar_tipo = "".join(
        sidebar_item(label, tipo_counts_raw.get(code, 0), "tipo", code, code in tipos_list)
        for code, label in TIPOS_CONTRATO.items()
    )

    # HTML sidebar prange
    sidebar_prange = "".join(
        sidebar_item(label, prange_count(pmin_v, pmax_v), "prange", code, code in pranges_list)
        for code, label, pmin_v, pmax_v in PRANGES
    )

    # HTML sidebar pais (Todos / España / Internacional)
    espana_count = next((c for v, c in pais_counts_raw if v == "España"), 0)
    paises_ext_raw = sorted([(v, c) for v, c in pais_counts_raw if v != "España"], key=lambda x: x[0])
    intl_count = sum(c for _, c in paises_ext_raw)
    todos_count = espana_count + intl_count
    intl_active = pais not in ("España", "")

    sidebar_pais = sidebar_item("Todos los territorios", todos_count, "pais", "", pais == "")
    sidebar_pais += sidebar_item("España", espana_count, "pais", "España", pais == "España")
    if intl_count > 0:
        sidebar_pais += sidebar_item("Internacional", intl_count, "pais", "__intl__", intl_active)

    # HTML lista países extranjeros — todos visibles (scroll en CSS)
    sidebar_paises_ext = "".join(sidebar_item(v, c, "pais", v, pais == v) for v, c in paises_ext_raw)

    # HTML lista CCAA — todas visibles (scroll en CSS)
    sidebar_ccaa = "".join(sidebar_item(v, c, "ccaa", v, v in ccaas_list) for v, c in ccaa_counts_raw)

    # HTML sidebar estado — siempre muestra todos los estados (0 si no hay resultados)
    sidebar_estado = "".join(
        sidebar_item(label, estado_counts_raw.get(code, 0), "estado", code, code in estados_list)
        for code, label in ESTADOS.items()
    )

    return {
        "sidebar_tipo": sidebar_tipo,
        "sidebar_prange": sidebar_prange,
        "sidebar_pais": sidebar_pais,
        "sidebar_paises_ext": sidebar_paises_ext,
        "sidebar_ccaa": sidebar_ccaa,
        "sidebar_estado": sidebar_estado,
    }


@router.get("/", response_class=HTMLResponse)
def home(
    db: Session = Depends(get_db),
    q: str = Query(default=""),
    ccaa: str = Query(default=""),
    pais: str = Query(default=""),
    estado: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    partial: str = Query(default=""),
    tipo: str = Query(default=""),
    fecha_desde: str = Query(default=""),
    fecha_hasta: str = Query(default=""),
    prange: str = Query(default=""),
    per_page: int = Query(default=20),
    orden: str = Query(default="asc"),
    cpv_q: str = Query(default=""),
):
    if per_page not in (5, 10, 15, 20):
        per_page = 20
    if orden not in ("asc", "desc"):
        orden = "asc"

    query = apply_filters(db.query(Licitacion), q, pais, ccaa, estado, tipo, fecha_desde, fecha_hasta, prange, cpv_q=cpv_q)

    total = db.query(func.count(Licitacion.id)).scalar()
    resultados = query.count()
    total_pages = max(1, (resultados + per_page - 1) // per_page)
    page = min(page, total_pages)

    if orden == "asc" and not fecha_desde:
        query = query.filter(Licitacion.fecha_limite >= date.today())

    sort_col = Licitacion.fecha_limite.asc().nullslast() if orden == "asc" else Licitacion.fecha_limite.desc().nullslast()
    licitaciones = (
        query.order_by(sort_col)
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    # Cards
    filas = ""
    for lic in licitaciones:
        if lic.presupuesto is None:
            presupuesto_str = "Sin especificar"
        else:
            presupuesto_str = f"{lic.presupuesto:,.0f}".replace(",", ".") + " €"
        estado_val = lic.estado or "—"
        estado_label = ESTADOS.get(estado_val, estado_val)
        fecha_str = lic.fecha_limite.strftime("%d/%m/%Y") if lic.fecha_limite else "no indicado"
        tipo_nombre = TIPOS_CONTRATO.get(lic.tipo_contrato or "", "—")
        cpv_str = lic.cpv.split()[0] if lic.cpv else None
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
    {('<span class="lm-dot">·</span><span class="lm-card-cpv">CPV ' + cpv_str + '</span>') if cpv_str else ''}
    <span class="lm-dot">·</span>
    <span>{tipo_nombre}</span>
  </div>
  <div class="lm-card-footer">
    <span class="lm-card-org">{lic.organo_contratacion or '—'} · {territorio}</span>
    <div class="lm-card-right">
      <span class="lm-card-deadline">Plazo {fecha_str}</span>
      <span class="lm-card-price">{presupuesto_str}</span>
    </div>
  </div>
</div>"""

    params = {"q": q, "cpv_q": cpv_q, "pais": pais, "ccaa": ccaa, "estado": estado, "tipo": tipo,
              "fecha_desde": fecha_desde, "fecha_hasta": fecha_hasta, "prange": prange,
              "per_page": per_page if per_page != 20 else "",
              "orden": orden if orden != "asc" else ""}
    paginacion = build_pagination(page, total_pages, params)

    sidebar = compute_sidebar(db, q, pais, ccaa, estado, tipo, fecha_desde, fecha_hasta, prange, cpv_q=cpv_q)

    # En plazo con filtros activos (ignorando filtro de estado, siempre cuenta PUB + fecha válida)
    en_plazo_count = (
        apply_filters(db.query(Licitacion), q, pais, ccaa, estado, tipo, fecha_desde, fecha_hasta, prange, skip_estado=True, cpv_q=cpv_q)
        .filter(Licitacion.estado == "PUB", Licitacion.fecha_limite >= date.today())
        .count()
    )
    resultados_str = f"{resultados:,}".replace(",", ".")
    en_plazo_str = f"{en_plazo_count:,}".replace(",", ".")

    if partial == "1":
        return JSONResponse({
            "filas": filas,
            "paginacion": paginacion,
            "resultados": resultados_str,
            "en_plazo": en_plazo_str,
            "sidebar": sidebar,
        })

    # Última sincronización: leída del fichero de estado del script de sync
    _state_file = Path(__file__).parents[2] / "data" / "sync_state.json"
    ultima_sync = "—"
    if _state_file.exists():
        try:
            import json as _json
            _state = _json.loads(_state_file.read_text())
            _last = _state.get("last_sync")
            if _last:
                _sync_date = datetime.fromisoformat(_last).date()
                _diff = (date.today() - _sync_date).days
                if _diff == 0:
                    ultima_sync = "Hoy"
                elif _diff == 1:
                    ultima_sync = "Ayer"
                else:
                    ultima_sync = f"Hace {_diff} días"
        except Exception:
            pass

    mostrar_ccaa = pais in ("España", "")
    ccaa_display = "" if mostrar_ccaa else "display:none"
    paises_display = "display:none" if mostrar_ccaa else ""
    territorio_title = "Comunidad autónoma" if mostrar_ccaa else "País"

    return render(
        "home.html",
        active_busqueda="lm-nav-tab-active",
        active_mapa="",
        total=f"{total:,}".replace(",", "."),
        en_plazo=en_plazo_str,
        resultados=resultados_str,
        ultima_sync=ultima_sync,
        filas=filas,
        sidebar_tipo=sidebar["sidebar_tipo"],
        sidebar_pais=sidebar["sidebar_pais"],
        sidebar_paises_ext=sidebar["sidebar_paises_ext"],
        sidebar_ccaa=sidebar["sidebar_ccaa"],
        ccaa_display=ccaa_display,
        paises_display=paises_display,
        territorio_title=territorio_title,
        sidebar_estado=sidebar["sidebar_estado"],
        sidebar_prange=sidebar["sidebar_prange"],
        q=q,
        cpv_q=cpv_q,
        pais=pais,
        ccaa=ccaa,
        estado=estado,
        tipo=tipo,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        prange=prange,
        per_page=per_page,
        orden=orden,
        orden_label="Pronta finalización" if orden == "asc" else "Más tiempo",
        orden_icon_desc="display:none" if orden == "asc" else "",
        orden_icon_asc="" if orden == "asc" else "display:none",
        paginacion=paginacion,
    )
