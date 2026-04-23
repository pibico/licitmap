#!/usr/bin/env python3
"""
Envía emails de alertas, newsletter, suscripciones y watchlist.
Cron recomendado: 0 8 * * * /root/licitmap/.venv/bin/python /root/licitmap/scripts/check_alertas.py
"""
import sys
sys.path.insert(0, '/root/licitmap')

from datetime import datetime, timedelta, date
from sqlalchemy import or_

from app.database import SessionLocal
from app.models import Alerta, LicitacionSeguida, Licitacion, User
from app.email_utils import (
    send_alerta_email, send_newsletter_email,
    send_seguimiento_email, send_vencimiento_email,
)


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
    if a.solo_activas:
        q = q.filter(Licitacion.estado == "PUB", Licitacion.fecha_limite >= date.today())
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
                    send_newsletter_email(user.email, user.username, lics, since, db)
                else:
                    send_alerta_email(user.email, user.username, a.nombre, lics, db)
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
            q = q.filter(Licitacion.provincia == s.entidad_valor)
        elif s.entidad_tipo == "organismo":
            q = q.filter(Licitacion.organo_contratacion.ilike(f"%{s.entidad_valor}%"))
        elif s.entidad_tipo == "cpv":
            q = q.filter(Licitacion.cpv.ilike(f"%{s.entidad_valor}%"))

        lics = q.order_by(Licitacion.fecha_publicacion.desc()).limit(50).all()
        if lics:
            try:
                send_alerta_email(user.email, user.username, s.nombre, lics, db)
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
                send_seguimiento_email(user.email, user.username, lic, old, lic.estado, db)
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
                    send_vencimiento_email(user.email, user.username, lic, days_left, db)
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
