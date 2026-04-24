from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from pathlib import Path
from datetime import datetime, timedelta, date
import re, json

from sqlalchemy import func

from app.database import get_db
from app.models import User, Alerta, LicitacionSeguida, Licitacion
from app.utils import _nav_context
from app.i18n import get_lang_from_request, t
from app.geo import PROVINCIA_TO_CP
from app.email_utils import (
    send_alerta_email, send_newsletter_email,
    send_seguimiento_email, send_vencimiento_email,
    _ESTADO_LABELS,
)

router = APIRouter()


def _parse_keywords(raw: str | None) -> str | None:
    if not raw:
        return None
    parts = [k.strip() for k in raw.replace("|", ",").split(",") if k.strip()]
    return "|".join(parts) if parts else None


def _pipe(values) -> str | None:
    """Convierte lista de strings en pipe-separated, None si queda vacío."""
    return "|".join(v for v in (values or []) if v) or None


def _apply_geo_filters(q, provincias: str | None, municipios: str | None):
    """Aplica filtros de provincia y municipio al query. `Licitacion.provincia`
    está siempre NULL (el sync ATOM no lo rellena), así que traducimos cada
    nombre de provincia al prefijo CP (2 dígitos) y filtramos por
    substr(codigo_postal, 1, 2)."""
    if provincias:
        names = [p for p in provincias.split("|") if p]
        prefixes = [PROVINCIA_TO_CP[n] for n in names if n in PROVINCIA_TO_CP]
        if prefixes:
            q = q.filter(func.substr(Licitacion.codigo_postal, 1, 2).in_(prefixes))
    if municipios:
        muns = [m for m in municipios.split("|") if m]
        if muns:
            q = q.filter(Licitacion.municipio.in_(muns))
    return q

CCAA_LIST = [
    "Andalucía", "Aragón", "Asturias", "Baleares", "Canarias", "Cantabria",
    "Castilla-La Mancha", "Castilla y León", "Cataluña", "Ceuta",
    "Comunidad de Madrid", "Comunidad Foral de Navarra", "Comunidad Valenciana",
    "Extremadura", "Galicia", "La Rioja", "Melilla", "País Vasco", "Región de Murcia",
]

TIPOS_CONTRATO = {k: f"{{{{t.tipo.{k}}}}}" for k in ("1", "2", "3", "7", "8", "22", "31", "32", "40", "50")}

ESTADOS = {k: f"{{{{t.estado.{k}}}}}" for k in ("PUB", "ADJ", "PRE", "RES", "EV", "ANUL")}

DIAS = [f"{{{{t.al.day.{i}}}}}" for i in range(7)]
DIAS_SHORT = [f"{{{{t.al.day_short.{i}}}}}" for i in range(7)]

ENTIDAD_TIPOS = {
    "ccaa":       "{{t.al.entidad.ccaa}}",
    "provincia":  "{{t.al.entidad.provincia}}",
    "organismo":  "{{t.al.entidad.organismo}}",
    "cpv":        "{{t.al.entidad.cpv}}",
}

ENTIDAD_ICONS = {
    "ccaa": '<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/><line x1="8" y1="2" x2="8" y2="18"/><line x1="16" y1="6" x2="16" y2="22"/></svg>',
    "provincia": '<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>',
    "organismo": '<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',
    "cpv": '<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>',
}

_SVG_PLAY = '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>'
_SVG_EDIT = '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>'
_SVG_TRASH = '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>'
_SVG_BELL_OFF = '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13.73 21a2 2 0 0 1-3.46 0"/><path d="M18.63 13A17.89 17.89 0 0 1 18 8"/><path d="M6.26 6.26A5.86 5.86 0 0 0 6 8c0 7-3 9-3 9h14"/><path d="M18 8a6 6 0 0 0-9.33-5"/><line x1="1" y1="1" x2="23" y2="23"/></svg>'


def _esc(s: str) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _hora_options(sel=8) -> str:
    return "".join(
        f'<option value="{h}"{" selected" if h == sel else ""}>{h:02d}:00</option>'
        for h in range(0, 24)
    )


def _dia_options(sel=0) -> str:
    return "".join(
        f'<option value="{i}"{" selected" if i == sel else ""}>{d}</option>'
        for i, d in enumerate(DIAS)
    )


def _ccaa_options(sel_pipe="") -> str:
    sel = set(sel_pipe.split("|")) if sel_pipe else set()
    return "".join(
        f'<option value="{_esc(c)}"{" selected" if c in sel else ""}>{_esc(c)}</option>'
        for c in CCAA_LIST
    )

def _ccaa_chips(sel_pipe="") -> str:
    sel = set(sel_pipe.split("|")) if sel_pipe else set()
    return "".join(
        f'<button type="button" class="lm-chip{" lm-chip-active" if c in sel else ""}" data-val="{_esc(c)}">{_esc(c)}</button>'
        for c in CCAA_LIST
    )


def _tipo_options(sel_pipe="") -> str:
    sel = set(sel_pipe.split("|")) if sel_pipe else set()
    return "".join(
        f'<option value="{k}"{" selected" if k in sel else ""}>{_esc(v)}</option>'
        for k, v in TIPOS_CONTRATO.items()
    )


def _estado_options(sel_pipe="") -> str:
    sel = set(sel_pipe.split("|")) if sel_pipe else set()
    return "".join(
        f'<option value="{k}"{" selected" if k in sel else ""}>{_esc(v)}</option>'
        for k, v in ESTADOS.items()
    )


def _freq_label(a: Alerta) -> str:
    dia_s = DIAS_SHORT[a.dia_semana or 0]
    weekly = "{{t.al.nl_weekly}}"
    daily  = "{{t.al.nl_daily}}"
    if a.frecuencia == "semanal":
        return f"{weekly} ({dia_s}) · {(a.hora_envio or 8):02d}:00"
    return f"{daily} · {(a.hora_envio or 8):02d}:00"


def _alerta_meta(a: Alerta) -> str:
    parts = []
    if a.keywords:
        parts.append(f'"{_esc(a.keywords.replace("|", ", "))}"')
    if a.comunidades:
        cc = [c.split()[-1] for c in a.comunidades.split("|") if c]
        parts.append(", ".join(cc[:3]) + (" {{t.al.meta_more}}" if len(cc) > 3 else ""))
    if a.tipo_contrato:
        tp = [TIPOS_CONTRATO.get(t, t) for t in a.tipo_contrato.split("|") if t]
        parts.append(", ".join(tp[:2]))
    if a.cpv_codes:
        parts.append(f"CPV: {a.cpv_codes[:30]}")
    if a.presupuesto_min or a.presupuesto_max:
        lo = f"{a.presupuesto_min:,.0f} €" if a.presupuesto_min else "0 €"
        hi = f"{a.presupuesto_max:,.0f} €" if a.presupuesto_max else "∞"
        parts.append(f"{lo} – {hi}")
    return " · ".join(parts) if parts else "{{t.al.meta_all}}"


def _last_label(a: Alerta) -> str:
    if not a.last_checked_at:
        return "{{t.al.last_none}}"
    prefix = "{{t.al.last_prefix}}"
    return f"{prefix} {a.last_checked_at.strftime('%d/%m %H:%M')}"


def _build_nl_section(nl: Alerta | None) -> str:
    checked   = " checked" if nl and nl.activa else ""
    nombre    = _esc(nl.nombre if nl else "Newsletter LicitMap")
    freq      = nl.frecuencia if nl else "diaria"
    dia       = nl.dia_semana if nl else 0
    hora      = nl.hora_envio if nl else 8
    keywords  = _esc((nl.keywords or "").replace("|", ", ") if nl else "")
    comunidades = nl.comunidades or "" if nl else ""
    presmin   = nl.presupuesto_min or "" if nl else ""
    solo      = " checked" if nl and nl.solo_activas else ""
    nl_id     = nl.id if nl else ""
    last      = _last_label(nl) if nl else ""
    dia_col_style = "" if freq == "semanal" else "display:none"
    d_sel     = " selected" if freq == "diaria" else ""
    s_sel     = " selected" if freq == "semanal" else ""

    L = {
        "active":   "{{t.al.nl_active}}",
        "name":     "{{t.al.field_name}}",
        "freq":     "{{t.al.nl_freq}}",
        "daily":    "{{t.al.nl_daily}}",
        "weekly":   "{{t.al.nl_weekly}}",
        "day":      "{{t.al.nl_day_short}}",
        "hour":     "{{t.al.nl_hour}}",
        "kw":       "{{t.al.field_keywords}}",
        "kw_opt":   "{{t.al.nl_keywords_opt}}",
        "kw_ph":    "{{t.al.nl_keywords_ph}}",
        "kw_hint":  "{{t.al.nl_keywords_hint}}",
        "presmin":  "{{t.al.nl_presmin}}",
        "solo":     "{{t.al.nl_solo}}",
        "ccaa":     "{{t.al.nl_ccaa_title}}",
        "ccaa_h":   "{{t.al.nl_ccaa_hint}}",
        "save":     "{{t.al.save_changes}}",
        "test":     "{{t.al.test}}",
    }

    return f"""
<form id="nl-form" data-id="{nl_id}">
  <div class="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
    <div class="d-flex align-items-center gap-2">
      <label class="lm-toggle-switch">
        <input type="checkbox" id="nl-activa"{checked}>
        <span class="lm-toggle-slider"></span>
      </label>
      <span class="fw-semibold small">{L['active']}</span>
    </div>
    <small class="text-muted">{last}</small>
  </div>
  <div class="row g-2 mb-2">
    <div class="col-12 col-sm-5">
      <label class="form-label small mb-1">{L['name']}</label>
      <input type="text" class="form-control form-control-sm" id="nl-nombre" value="{nombre}">
    </div>
    <div class="col-6 col-sm-3">
      <label class="form-label small mb-1">{L['freq']}</label>
      <select class="form-select form-select-sm" id="nl-frecuencia">
        <option value="diaria"{d_sel}>{L['daily']}</option>
        <option value="semanal"{s_sel}>{L['weekly']}</option>
      </select>
    </div>
    <div class="col-6 col-sm-2" id="nl-dia-col" style="{dia_col_style}">
      <label class="form-label small mb-1">{L['day']}</label>
      <select class="form-select form-select-sm" id="nl-dia">{_dia_options(dia)}</select>
    </div>
    <div class="col-6 col-sm-2">
      <label class="form-label small mb-1">{L['hour']}</label>
      <select class="form-select form-select-sm" id="nl-hora">{_hora_options(hora)}</select>
    </div>
  </div>
  <div class="row g-2 mb-2">
    <div class="col-12 col-sm-6">
      <label class="form-label small mb-1">{L['kw']} <span class="text-muted">{L['kw_opt']}</span></label>
      <input type="text" class="form-control form-control-sm" id="nl-keywords"
             value="{keywords}" placeholder="{L['kw_ph']}">
      <div class="form-text">{L['kw_hint']}</div>
    </div>
    <div class="col-6 col-sm-3">
      <label class="form-label small mb-1">{L['presmin']}</label>
      <input type="number" class="form-control form-control-sm" id="nl-presmin"
             value="{presmin}" placeholder="0" min="0" step="1000">
    </div>
    <div class="col-6 col-sm-3">
      <label class="form-label small mb-1">{L['solo']}</label>
      <div class="pt-1">
        <label class="lm-toggle-switch">
          <input type="checkbox" id="nl-solo-activas"{solo}>
          <span class="lm-toggle-slider"></span>
        </label>
      </div>
    </div>
  </div>
  <div class="mb-3">
    <label class="lm-form-label">{L['ccaa']} <span class="lm-form-hint" style="display:inline;margin:0">{L['ccaa_h']}</span></label>
    <div class="lm-chip-picker lm-chip-picker-scroll" id="nl-ccaa">
      {_ccaa_chips(comunidades)}
    </div>
  </div>
  <div class="d-flex gap-2 flex-wrap">
    <button type="button" class="btn btn-sm btn-primary" id="nl-guardar">{L['save']}</button>
    <button type="button" class="btn btn-sm btn-outline-secondary" id="nl-probar">{L['test']}</button>
  </div>
</form>"""


def _build_alertas_list(alertas: list) -> str:
    if not alertas:
        return '<div class="lm-alertas-empty">{{t.al.empty_alerts}}</div>'
    tt_test   = "{{t.al.tt_test}}"
    tt_edit   = "{{t.al.tt_edit}}"
    tt_delete = "{{t.al.tt_delete}}"
    items = []
    for a in alertas:
        checked  = " checked" if a.activa else ""
        inactive = "" if a.activa else " lm-ai-inactive"
        meta     = _alerta_meta(a)
        freq     = _freq_label(a)
        last     = _last_label(a)
        items.append(f"""
<div class="lm-alertas-item{inactive}" data-id="{a.id}">
  <div class="lm-ai-left">
    <label class="lm-toggle-switch lm-toggle-sm">
      <input type="checkbox" class="alerta-toggle" data-id="{a.id}"{checked}>
      <span class="lm-toggle-slider"></span>
    </label>
    <div class="lm-ai-info">
      <div class="lm-ai-nombre">{_esc(a.nombre)}</div>
      <div class="lm-ai-meta">{meta}</div>
      <div class="lm-ai-freq">
        <span class="lm-badge-freq">{freq}</span>
        <span class="lm-ai-last">{last}</span>
      </div>
    </div>
  </div>
  <div class="lm-ai-actions">
    <button class="lm-btn-icon btn-probar" data-id="{a.id}" title="{tt_test}">{_SVG_PLAY}</button>
    <button class="lm-btn-icon btn-editar" data-id="{a.id}"
      data-nombre="{_esc(a.nombre)}"
      data-keywords="{_esc(a.keywords or '')}"
      data-cpv="{_esc(a.cpv_codes or '')}"
      data-ccaa="{_esc(a.comunidades or '')}"
      data-tipo="{_esc(a.tipo_contrato or '')}"
      data-estado="{_esc(a.estado or '')}"
      data-presmin="{a.presupuesto_min or ''}"
      data-presmax="{a.presupuesto_max or ''}"
      data-soloactivas="{1 if a.solo_activas else 0}"
      data-frecuencia="{a.frecuencia}"
      data-dia="{a.dia_semana or 0}"
      data-hora="{a.hora_envio or 8}"
      title="{tt_edit}">{_SVG_EDIT}</button>
    <button class="lm-btn-icon lm-btn-danger btn-eliminar" data-id="{a.id}" title="{tt_delete}">{_SVG_TRASH}</button>
  </div>
</div>""")
    return "\n".join(items)


def _build_subs_list(subs: list) -> str:
    if not subs:
        return '<div class="lm-alertas-empty">{{t.al.empty_subs}}</div>'
    tt_test   = "{{t.al.tt_test}}"
    tt_edit   = "{{t.al.tt_edit}}"
    tt_delete = "{{t.al.tt_delete}}"
    items = []
    for s in subs:
        checked  = " checked" if s.activa else ""
        inactive = "" if s.activa else " lm-ai-inactive"
        icon     = ENTIDAD_ICONS.get(s.entidad_tipo or "", "")
        tipo_label = ENTIDAD_TIPOS.get(s.entidad_tipo or "", s.entidad_tipo or "")
        freq     = _freq_label(s)
        last     = _last_label(s)
        items.append(f"""
<div class="lm-alertas-item{inactive}" data-id="{s.id}">
  <div class="lm-ai-left">
    <label class="lm-toggle-switch lm-toggle-sm">
      <input type="checkbox" class="alerta-toggle" data-id="{s.id}"{checked}>
      <span class="lm-toggle-slider"></span>
    </label>
    <div class="lm-ai-info">
      <div class="lm-ai-nombre">{icon} {_esc(s.nombre)}</div>
      <div class="lm-ai-meta">{tipo_label}: <strong>{_esc(s.entidad_valor or '')}</strong></div>
      <div class="lm-ai-freq">
        <span class="lm-badge-freq">{freq}</span>
        <span class="lm-ai-last">{last}</span>
      </div>
    </div>
  </div>
  <div class="lm-ai-actions">
    <button class="lm-btn-icon btn-probar" data-id="{s.id}" title="{tt_test}">{_SVG_PLAY}</button>
    <button class="lm-btn-icon btn-editar-sub" data-id="{s.id}"
      data-nombre="{_esc(s.nombre)}"
      data-tipo="{_esc(s.entidad_tipo or '')}"
      data-valor="{_esc(s.entidad_valor or '')}"
      data-frecuencia="{s.frecuencia}"
      data-dia="{s.dia_semana or 0}"
      data-hora="{s.hora_envio or 8}"
      title="{tt_edit}">{_SVG_EDIT}</button>
    <button class="lm-btn-icon lm-btn-danger btn-eliminar" data-id="{s.id}" title="{tt_delete}">{_SVG_TRASH}</button>
  </div>
</div>""")
    return "\n".join(items)


def _build_watchlist(seguidas: list) -> str:
    if not seguidas:
        return '<div class="lm-alertas-empty">{{t.al.empty_watch}}</div>'
    deadline_prefix = "{{t.al.watch_limit}}"
    status_change   = "{{t.al.watch_status_change}}"
    deadline_label  = "{{t.al.watch_deadline_label}}"
    tt_view         = "{{t.al.tt_view_placsp}}"
    tt_unfollow     = "{{t.al.tt_unfollow}}"
    dias_labels = [
        (None, "{{t.al.watch_dias_no}}"),
        (3,    "{{t.al.watch_dias_3}}"),
        (7,    "{{t.al.watch_dias_7}}"),
        (15,   "{{t.al.watch_dias_15}}"),
    ]
    items = []
    for seg, lic in seguidas:
        estado_label = _ESTADO_LABELS.get(lic.estado, lic.estado or "—")
        estado_cls   = f"badge-{lic.estado}" if lic.estado else ""
        fecha = lic.fecha_limite.strftime("%d/%m/%Y") if lic.fecha_limite else "—"
        presup = ""
        if lic.presupuesto:
            if lic.presupuesto >= 1_000_000:
                presup = f"{lic.presupuesto/1_000_000:.1f}M €"
            else:
                presup = f"{lic.presupuesto/1_000:.0f}K €"
        cambio_chk = " checked" if seg.notif_cambio_estado else ""
        dias_opts  = "".join(
            f'<option value="{v}"{" selected" if seg.notif_dias_vencimiento == v else ""}>{l}</option>'
            for v, l in dias_labels
        )
        items.append(f"""
<div class="lm-watch-item" data-seg-id="{seg.id}">
  <div class="lm-watch-main">
    <div class="lm-watch-header">
      <span class="badge {estado_cls} me-2">{estado_label}</span>
      <span class="lm-watch-titulo">{_esc(lic.titulo or '—')}</span>
    </div>
    <div class="lm-watch-meta">
      <span>{_esc(lic.organo_contratacion or '')}</span>
      {"<span class='lm-watch-sep'>·</span><span>" + deadline_prefix + " " + fecha + "</span>" if fecha != "—" else ""}
      {"<span class='lm-watch-sep'>·</span><span>" + presup + "</span>" if presup else ""}
      {"<span class='lm-watch-sep'>·</span><span>" + _esc(lic.comunidad_autonoma or '') + "</span>" if lic.comunidad_autonoma else ""}
    </div>
    <div class="lm-watch-notifs">
      <label class="lm-watch-notif-label">
        <input type="checkbox" class="watch-cambio-toggle" data-seg-id="{seg.id}"{cambio_chk}>
        <span>{status_change}</span>
      </label>
      <label class="lm-watch-notif-label">
        <span>{deadline_label}</span>
        <select class="form-select form-select-sm lm-watch-dias-select" data-seg-id="{seg.id}">
          {dias_opts}
        </select>
      </label>
    </div>
  </div>
  <div class="lm-watch-actions">
    <a href="{_esc(lic.url or '#')}" target="_blank" class="lm-btn-icon" title="{tt_view}">
      <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="7" y1="17" x2="17" y2="7"/><polyline points="7 7 17 7 17 17"/></svg>
    </a>
    <button class="lm-btn-icon lm-btn-danger btn-unfollow" data-seg-id="{seg.id}" title="{tt_unfollow}">{_SVG_BELL_OFF}</button>
  </div>
</div>""")
    return "\n".join(items)


def _render_page(request: Request, nl, alertas_list, subs_list, watchlist, user) -> str:
    auth_block, busqueda_display, lang_selector = _nav_context(request)
    base = Path("templates/base.html").read_text()
    tpl  = Path("templates/alertas.html").read_text()

    no_email = (not user.email)
    email_notice = ""
    if no_email:
        email_notice = (
            '<div class="alert alert-warning py-2 px-3 small mt-3" role="alert">'
            '{{t.al.no_email_warn}}</div>'
        )

    html = base.replace("{{content}}", tpl)
    for k, v in {
        "active_busqueda":  "",
        "active_mapa":      "",
        "active_analisis":  "",
        "active_alertas":   "lm-nav-tab-active",
        "nav_auth_block":   auth_block,
        "nav_busqueda_display": busqueda_display,
        "lang_selector":    lang_selector,
        "nl_section":       _build_nl_section(nl),
        "alertas_list":     _build_alertas_list(alertas_list),
        "subs_list":        _build_subs_list(subs_list),
        "watchlist_list":   _build_watchlist(watchlist),
        "user_email_notice": email_notice,
    }.items():
        html = html.replace("{{" + k + "}}", v)
    html = re.sub(r"\{\{[a-z_]+\}\}", "", html)
    return html


def _get_user(request: Request, db: Session):
    username = request.session.get("username")
    if not username:
        return None
    return db.query(User).filter_by(username=username).first()


# ── Página principal ──────────────────────────────────────────────────────────

@router.get("/alerts", response_class=HTMLResponse)
def alertas_page(request: Request, db: Session = Depends(get_db)):
    user = _get_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    all_alertas = db.query(Alerta).filter_by(user_id=user.id).all()
    nl          = next((a for a in all_alertas if a.tipo == "newsletter"), None)
    al_list     = [a for a in all_alertas if a.tipo == "alerta"]
    subs        = [a for a in all_alertas if a.tipo == "suscripcion"]

    watchlist = (
        db.query(LicitacionSeguida, Licitacion)
        .join(Licitacion, LicitacionSeguida.licitacion_id == Licitacion.id)
        .filter(LicitacionSeguida.user_id == user.id)
        .order_by(LicitacionSeguida.created_at.desc())
        .all()
    )

    return HTMLResponse(_render_page(request, nl, al_list, subs, watchlist, user))


# ── Newsletter ────────────────────────────────────────────────────────────────

@router.post("/api/alerts/newsletter")
async def save_newsletter(request: Request, db: Session = Depends(get_db)):
    user = _get_user(request, db)
    if not user:
        return JSONResponse({"error": "no autenticado"}, status_code=401)

    data = await request.json()
    nl = db.query(Alerta).filter_by(user_id=user.id, tipo="newsletter").first()

    comunidades_raw = data.get("ccaa", [])
    comunidades_str = "|".join(c for c in comunidades_raw if c)

    if nl is None:
        nl = Alerta(
            user_id=user.id,
            tipo="newsletter",
            nombre=data.get("nombre", "Newsletter LicitMap") or "Newsletter LicitMap",
            created_at=datetime.now(),
        )
        db.add(nl)

    nl.nombre        = data.get("nombre") or "Newsletter LicitMap"
    nl.activa        = bool(data.get("activa", False))
    nl.frecuencia    = data.get("frecuencia", "diaria")
    nl.dia_semana    = int(data.get("dia_semana", 0))
    nl.hora_envio    = int(data.get("hora_envio", 8))
    nl.keywords      = _parse_keywords(data.get("keywords"))
    nl.comunidades   = comunidades_str or None
    nl.provincias    = _pipe(data.get("provincias"))
    nl.municipios    = _pipe(data.get("municipios"))
    nl.presupuesto_min = float(data["presmin"]) if data.get("presmin") else None
    nl.solo_activas  = bool(data.get("solo_activas", False))
    db.commit()
    return JSONResponse({"ok": True})


@router.post("/api/alerts/newsletter/probar")
async def test_newsletter(request: Request, db: Session = Depends(get_db)):
    user = _get_user(request, db)
    if not user:
        return JSONResponse({"error": "no autenticado"}, status_code=401)
    if not user.email:
        return JSONResponse({"error": "Sin email configurado"}, status_code=400)

    nl = db.query(Alerta).filter_by(user_id=user.id, tipo="newsletter").first()
    desde = datetime.now() - timedelta(days=7)
    q = db.query(Licitacion).filter(Licitacion.fecha_publicacion >= desde)
    if nl:
        if nl.keywords:
            for kw in nl.keywords.split("|"):
                q = q.filter(Licitacion.titulo.ilike(f"%{kw}%"))
        if nl.comunidades:
            cc = [c for c in nl.comunidades.split("|") if c]
            if cc:
                q = q.filter(Licitacion.comunidad_autonoma.in_(cc))
        q = _apply_geo_filters(q, nl.provincias, nl.municipios)
    lics = q.order_by(Licitacion.fecha_publicacion.desc()).limit(20).all()
    try:
        send_newsletter_email(user.email, user.username, lics, desde, db, lang=user.language)
        return JSONResponse({"ok": True, "count": len(lics)})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ── Alertas personalizadas ────────────────────────────────────────────────────

@router.post("/api/alerts/nueva")
async def create_alerta(request: Request, db: Session = Depends(get_db)):
    user = _get_user(request, db)
    if not user:
        return JSONResponse({"error": "no autenticado"}, status_code=401)

    data = await request.json()
    edit_id = data.get("edit_id")

    if edit_id:
        a = db.query(Alerta).filter_by(id=int(edit_id), user_id=user.id).first()
        if not a:
            return JSONResponse({"error": "no encontrado"}, status_code=404)
    else:
        a = Alerta(user_id=user.id, tipo="alerta", created_at=datetime.now())
        db.add(a)

    a.nombre        = data.get("nombre") or "Sin nombre"
    a.keywords      = _parse_keywords(data.get("keywords"))
    a.cpv_codes     = data.get("cpv") or None
    a.comunidades   = _pipe(data.get("ccaa"))
    a.provincias    = _pipe(data.get("provincias"))
    a.municipios    = _pipe(data.get("municipios"))
    a.tipo_contrato = _pipe(data.get("tipo"))
    a.estado        = _pipe(data.get("estado"))
    a.presupuesto_min = float(data["presmin"]) if data.get("presmin") else None
    a.presupuesto_max = float(data["presmax"]) if data.get("presmax") else None
    a.solo_activas  = bool(data.get("solo_activas", False))
    a.frecuencia    = data.get("frecuencia", "diaria")
    a.dia_semana    = int(data.get("dia_semana", 0))
    a.hora_envio    = int(data.get("hora_envio", 8))
    a.activa        = True
    db.commit()
    return JSONResponse({"ok": True})


@router.post("/api/alerts/{alerta_id}/toggle")
async def toggle_alerta(alerta_id: int, request: Request, db: Session = Depends(get_db)):
    user = _get_user(request, db)
    if not user:
        return JSONResponse({"error": "no autenticado"}, status_code=401)
    a = db.query(Alerta).filter_by(id=alerta_id, user_id=user.id).first()
    if not a:
        return JSONResponse({"error": "no encontrado"}, status_code=404)
    a.activa = not a.activa
    db.commit()
    return JSONResponse({"ok": True, "activa": a.activa})


@router.post("/api/alerts/{alerta_id}/eliminar")
async def delete_alerta(alerta_id: int, request: Request, db: Session = Depends(get_db)):
    user = _get_user(request, db)
    if not user:
        return JSONResponse({"error": "no autenticado"}, status_code=401)
    a = db.query(Alerta).filter_by(id=alerta_id, user_id=user.id).first()
    if not a:
        return JSONResponse({"error": "no encontrado"}, status_code=404)
    db.delete(a)
    db.commit()
    return JSONResponse({"ok": True})


@router.post("/api/alerts/{alerta_id}/probar")
async def test_alerta(alerta_id: int, request: Request, db: Session = Depends(get_db)):
    user = _get_user(request, db)
    if not user:
        return JSONResponse({"error": "no autenticado"}, status_code=401)
    if not user.email:
        return JSONResponse({"error": "Sin email configurado"}, status_code=400)

    a = db.query(Alerta).filter_by(id=alerta_id, user_id=user.id).first()
    if not a:
        return JSONResponse({"error": "no encontrado"}, status_code=404)

    desde = datetime.now() - timedelta(days=30)
    q = db.query(Licitacion).filter(Licitacion.fecha_publicacion >= desde)

    if a.tipo == "suscripcion":
        if a.entidad_tipo == "ccaa":
            q = q.filter(Licitacion.comunidad_autonoma == a.entidad_valor)
        elif a.entidad_tipo == "provincia":
            # Licitacion.provincia está siempre NULL; derivamos vía CP prefix.
            cp = PROVINCIA_TO_CP.get(a.entidad_valor or "")
            if cp:
                q = q.filter(func.substr(Licitacion.codigo_postal, 1, 2) == cp)
            else:
                q = q.filter(False)  # provincia desconocida → 0 resultados
        elif a.entidad_tipo == "organismo":
            q = q.filter(Licitacion.organo_contratacion.ilike(f"%{a.entidad_valor}%"))
        elif a.entidad_tipo == "cpv":
            q = q.filter(Licitacion.cpv.ilike(f"%{a.entidad_valor}%"))
    else:
        if a.keywords:
            for kw in a.keywords.split("|"):
                q = q.filter(Licitacion.titulo.ilike(f"%{kw}%"))
        if a.comunidades:
            cc = [c for c in a.comunidades.split("|") if c]
            if cc:
                q = q.filter(Licitacion.comunidad_autonoma.in_(cc))
        if a.tipo_contrato:
            tp = [t for t in a.tipo_contrato.split("|") if t]
            if tp:
                q = q.filter(Licitacion.tipo_contrato.in_(tp))
        if a.cpv_codes:
            cpvs = [c.strip() for c in a.cpv_codes.replace(",", "|").split("|") if c.strip()]
            if cpvs:
                q = q.filter(or_(*[Licitacion.cpv.ilike(f"%{c}%") for c in cpvs]))
        if a.presupuesto_min is not None:
            q = q.filter(Licitacion.presupuesto >= a.presupuesto_min)
        if a.presupuesto_max is not None:
            q = q.filter(Licitacion.presupuesto <= a.presupuesto_max)
        if a.estado:
            estados = [e for e in a.estado.split("|") if e]
            if estados:
                q = q.filter(Licitacion.estado.in_(estados))
        if a.solo_activas:
            q = q.filter(Licitacion.estado == "PUB", Licitacion.fecha_limite >= date.today())
    q = _apply_geo_filters(q, a.provincias, a.municipios)

    lics = q.order_by(Licitacion.fecha_publicacion.desc()).limit(20).all()
    try:
        send_alerta_email(user.email, user.username, a.nombre, lics, db, lang=user.language)
        return JSONResponse({"ok": True, "count": len(lics)})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ── Suscripciones de entidad ──────────────────────────────────────────────────

@router.post("/api/alerts/suscripcion")
async def create_suscripcion(request: Request, db: Session = Depends(get_db)):
    user = _get_user(request, db)
    if not user:
        return JSONResponse({"error": "no autenticado"}, status_code=401)

    data    = await request.json()
    edit_id = data.get("edit_id")

    if edit_id:
        s = db.query(Alerta).filter_by(id=int(edit_id), user_id=user.id, tipo="suscripcion").first()
        if not s:
            return JSONResponse({"error": "no encontrado"}, status_code=404)
    else:
        s = Alerta(user_id=user.id, tipo="suscripcion", created_at=datetime.now())
        db.add(s)

    entidad_tipo  = data.get("entidad_tipo", "ccaa")
    entidad_valor = (data.get("entidad_valor") or "").strip()
    lang          = get_lang_from_request(request)
    tipo_label    = t(f"al.entidad.{entidad_tipo}", lang) if entidad_tipo in ("ccaa", "provincia", "organismo", "cpv") else entidad_tipo
    s.nombre        = data.get("nombre") or f"{tipo_label}: {entidad_valor}"
    s.entidad_tipo  = entidad_tipo
    s.entidad_valor = entidad_valor
    s.provincias    = _pipe(data.get("provincias"))
    s.municipios    = _pipe(data.get("municipios"))
    s.frecuencia    = data.get("frecuencia", "diaria")
    s.dia_semana    = int(data.get("dia_semana", 0))
    s.hora_envio    = int(data.get("hora_envio", 8))
    s.activa        = True
    db.commit()
    return JSONResponse({"ok": True})


# ── Watchlist / Seguir licitaciones ──────────────────────────────────────────

@router.get("/api/alerts/seguidos")
def get_seguidos(request: Request, db: Session = Depends(get_db)):
    user = _get_user(request, db)
    if not user:
        return JSONResponse([])
    ids = [r.licitacion_id for r in db.query(LicitacionSeguida).filter_by(user_id=user.id).all()]
    return JSONResponse(ids)


@router.post("/api/alerts/seguir/{licitacion_id}")
async def toggle_seguir(licitacion_id: int, request: Request, db: Session = Depends(get_db)):
    user = _get_user(request, db)
    if not user:
        return JSONResponse({"error": "no autenticado"}, status_code=401)

    existing = db.query(LicitacionSeguida).filter_by(
        user_id=user.id, licitacion_id=licitacion_id
    ).first()

    if existing:
        db.delete(existing)
        db.commit()
        return JSONResponse({"seguida": False})
    else:
        lic = db.query(Licitacion).filter_by(id=licitacion_id).first()
        seg = LicitacionSeguida(
            user_id=user.id,
            licitacion_id=licitacion_id,
            notif_cambio_estado=True,
            last_estado=lic.estado if lic else None,
            created_at=datetime.now(),
        )
        db.add(seg)
        db.commit()
        return JSONResponse({"seguida": True})


@router.post("/api/alerts/watchlist/{seg_id}/config")
async def config_watchlist(seg_id: int, request: Request, db: Session = Depends(get_db)):
    user = _get_user(request, db)
    if not user:
        return JSONResponse({"error": "no autenticado"}, status_code=401)
    seg = db.query(LicitacionSeguida).filter_by(id=seg_id, user_id=user.id).first()
    if not seg:
        return JSONResponse({"error": "no encontrado"}, status_code=404)
    data = await request.json()
    if "notif_cambio_estado" in data:
        seg.notif_cambio_estado = bool(data["notif_cambio_estado"])
    if "notif_dias_vencimiento" in data:
        v = data["notif_dias_vencimiento"]
        seg.notif_dias_vencimiento = int(v) if v else None
    db.commit()
    return JSONResponse({"ok": True})


@router.post("/api/alerts/watchlist/{seg_id}/eliminar")
async def delete_watchlist(seg_id: int, request: Request, db: Session = Depends(get_db)):
    user = _get_user(request, db)
    if not user:
        return JSONResponse({"error": "no autenticado"}, status_code=401)
    seg = db.query(LicitacionSeguida).filter_by(id=seg_id, user_id=user.id).first()
    if not seg:
        return JSONResponse({"error": "no encontrado"}, status_code=404)
    db.delete(seg)
    db.commit()
    return JSONResponse({"ok": True})
