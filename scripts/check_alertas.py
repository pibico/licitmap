#!/usr/bin/env python3
"""
Envía emails de alertas, newsletter, suscripciones y watchlist.
Cron configurado automáticamente por el instalador en /etc/cron.d/licitmap.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime, timedelta, date
from sqlalchemy import or_, func

from app.database import SessionLocal
from app.models import Alerta, LicitacionSeguida, Licitacion, User
from app.geo import PROVINCIA_TO_CP
from app.email_utils import (
    send_alerta_email, send_newsletter_email,
    send_seguimiento_email, send_vencimiento_email,
)


def _apply_geo_filters(q, provincias: str | None, municipios: str | None):
    """Mismo filtro que app.routes.alertas._apply_geo_filters, replicado aquí
    para el cron: filtra por provincia vía prefijo CP (Licitacion.provincia
    siempre NULL) y por municipio exact match."""
    if provincias:
        prefixes = [PROVINCIA_TO_CP[n] for n in provincias.split("|") if n in PROVINCIA_TO_CP]
        if prefixes:
            q = q.filter(func.substr(Licitacion.codigo_postal, 1, 2).in_(prefixes))
    if municipios:
        muns = [m for m in municipios.split("|") if m]
        if muns:
            q = q.filter(Licitacion.municipio.in_(muns))
    return q


def _should_run(a: Alerta) -> bool:
    now = datetime.now()
    if a.frecuencia == "semanal":
        return now.weekday() == (a.dia_semana or 0)
    return True  # diaria: siempre


def _apply_alerta_filters(q, a: Alerta):
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
    return q


def check_alertas_newsletter(db):
    now = datetime.now()
    alertas = db.query(Alerta).filter(
        Alerta.activa == True,
        Alerta.tipo.in_(["alerta", "newsletter"]),
    ).all()

    for a in alertas:
        if not _should_run(a):
            continue
        user = db.query(User).filter_by(id=a.user_id).first()
        if not user or not user.email or not user.is_active:
            a.last_checked_at = now
            continue

        since = a.last_checked_at or (now - timedelta(days=1))
        q = db.query(Licitacion).filter(Licitacion.fecha_publicacion >= since)
        q = _apply_alerta_filters(q, a)
        lics = q.order_by(Licitacion.fecha_publicacion.desc()).limit(50).all()

        if lics:
            try:
                if a.tipo == "newsletter":
                    send_newsletter_email(user.email, user.username, lics, since, db, lang=user.language)
                else:
                    send_alerta_email(user.email, user.username, a.nombre, lics, db, lang=user.language)
                print(f"[OK] {a.tipo} '{a.nombre}' → {user.email} ({len(lics)} lics)")
            except Exception as e:
                print(f"[ERR] {a.tipo} {a.id}: {e}")

        a.last_checked_at = now

    db.commit()


def check_suscripciones(db):
    now = datetime.now()
    subs = db.query(Alerta).filter(
        Alerta.activa == True, Alerta.tipo == "suscripcion"
    ).all()

    for s in subs:
        if not _should_run(s):
            continue
        user = db.query(User).filter_by(id=s.user_id).first()
        if not user or not user.email or not user.is_active:
            s.last_checked_at = now
            continue

        since = s.last_checked_at or (now - timedelta(days=1))
        q = db.query(Licitacion).filter(Licitacion.fecha_publicacion >= since)

        if s.entidad_tipo == "ccaa":
            q = q.filter(Licitacion.comunidad_autonoma == s.entidad_valor)
        elif s.entidad_tipo == "provincia":
            # Licitacion.provincia siempre NULL → derivar vía CP prefix.
            cp = PROVINCIA_TO_CP.get(s.entidad_valor or "")
            if cp:
                q = q.filter(func.substr(Licitacion.codigo_postal, 1, 2) == cp)
            else:
                q = q.filter(False)
        elif s.entidad_tipo == "organismo":
            q = q.filter(Licitacion.organo_contratacion.ilike(f"%{s.entidad_valor}%"))
        elif s.entidad_tipo == "cpv":
            q = q.filter(Licitacion.cpv.ilike(f"%{s.entidad_valor}%"))

        # Filtros opcionales adicionales (provincia/municipio dentro de la
        # entidad principal — p. ej. suscripción a organismo X pero sólo en
        # Madrid).
        q = _apply_geo_filters(q, s.provincias, s.municipios)

        lics = q.order_by(Licitacion.fecha_publicacion.desc()).limit(50).all()
        if lics:
            try:
                send_alerta_email(user.email, user.username, s.nombre, lics, db, lang=user.language)
                print(f"[OK] suscripcion '{s.nombre}' → {user.email} ({len(lics)} lics)")
            except Exception as e:
                print(f"[ERR] suscripcion {s.id}: {e}")

        s.last_checked_at = now

    db.commit()


def check_watchlist(db):
    today = date.today()
    seguidas = db.query(LicitacionSeguida).all()

    for seg in seguidas:
        lic = db.query(Licitacion).filter_by(id=seg.licitacion_id).first()
        if not lic:
            continue
        user = db.query(User).filter_by(id=seg.user_id).first()
        if not user or not user.email:
            continue

        # Cambio de estado
        if seg.notif_cambio_estado and seg.last_estado and seg.last_estado != lic.estado:
            old = seg.last_estado
            try:
                send_seguimiento_email(user.email, user.username, lic, old, lic.estado, db, lang=user.language)
                print(f"[OK] estado change '{lic.titulo[:40]}' → {user.email}: {old}→{lic.estado}")
            except Exception as e:
                print(f"[ERR] estado change {seg.id}: {e}")

        if lic.estado:
            seg.last_estado = lic.estado

        # Vencimiento
        if seg.notif_dias_vencimiento and lic.fecha_limite:
            days_left = (lic.fecha_limite - today).days
            if days_left in (0, seg.notif_dias_vencimiento):
                try:
                    send_vencimiento_email(user.email, user.username, lic, days_left, db, lang=user.language)
                    print(f"[OK] vencimiento '{lic.titulo[:40]}' → {user.email}: {days_left}d")
                except Exception as e:
                    print(f"[ERR] vencimiento {seg.id}: {e}")

    db.commit()


if __name__ == "__main__":
    db = SessionLocal()
    try:
        print(f"=== check_alertas {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")
        check_alertas_newsletter(db)
        check_suscripciones(db)
        check_watchlist(db)
        print("=== done ===")
    finally:
        db.close()
