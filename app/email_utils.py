"""Email sending for LicitMap. Reads SMTP config from the settings table (/admin/config)."""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.orm import Session

from app.i18n import t
from app.utils import get_setting


def _smtp_config(db: Session) -> tuple[str, int, str, str, str]:
    host      = get_setting(db, "smtp_host", "")
    port      = int(get_setting(db, "smtp_port", "587"))
    user      = get_setting(db, "smtp_user", "")
    password  = get_setting(db, "smtp_pass", "")
    from_addr = get_setting(db, "smtp_from", "") or user
    if not host or not user or not password:
        raise RuntimeError(
            "SMTP is not configured. Go to Admin → Settings → Email."
        )
    return host, port, user, password, from_addr


def _send(host, port, user, password, from_addr, to_email, subject, text, html):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = from_addr
    msg["To"]      = to_email
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))
    ctx = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=ctx) as smtp:
            smtp.login(user, password)
            smtp.sendmail(from_addr, to_email, msg.as_string())
    else:
        with smtplib.SMTP(host, port) as smtp:
            smtp.ehlo()
            smtp.starttls(context=ctx)
            smtp.login(user, password)
            smtp.sendmail(from_addr, to_email, msg.as_string())


# ── Email-specific copy (not yet in the i18n dict because they are multi-line blocks)

EMAIL_STRINGS = {
    "es": {
        "otp.subject": "Tu código de acceso a LicitMap",
        "otp.hi": "Hola",
        "otp.subtitle": "Código de acceso",
        "otp.your_code": "Tu código de acceso es:",
        "otp.expires": "Expira en <strong>15 minutos</strong>. No lo compartas con nadie.",
        "alert.subject": "LicitMap — Alerta «%(name)s»: %(n)s nueva%(p)s",
        "alert.title_prefix": "Alerta:",
        "alert.subtitle": "Se encontraron %(n)s coincidencias",
        "alert.body": "Hola <strong>%(user)s</strong>, hay <strong>%(n)s licitación%(ep)s nueva%(p)s</strong> que coinciden con tu alerta <strong>«%(name)s»</strong>.",
        "alert.text": "Hola %(user)s,\n\nTu alerta «%(name)s» tiene %(n)s coincidencias.\nGestiona tus alertas en https://ivan.pibico.es/alertas\n\n— LicitMap",
        "news.subject": "LicitMap Newsletter — %(n)s licitación%(ep)s nueva%(p)s",
        "news.title": "Resumen: %(n)s licitaciones nuevas",
        "news.subtitle": "Newsletter periódico desde %(date)s",
        "news.body": "Hola <strong>%(user)s</strong>, resumen de licitaciones publicadas desde el <strong>%(date)s</strong>.",
        "news.text": "Hola %(user)s,\n\nResumen LicitMap: %(n)s licitaciones nuevas desde %(date)s.\nhttps://ivan.pibico.es/alertas\n\n— LicitMap",
        "follow.subject": "LicitMap — Actualización: %(title)s",
        "follow.title": "Actualización de licitación seguida",
        "follow.subtitle": "Cambio de estado detectado",
        "follow.body": "Hola <strong>%(user)s</strong>, una licitación que estás siguiendo ha cambiado de estado.",
        "follow.prev": "Estado anterior:",
        "follow.arrow": "→",
        "follow.cta": "Ver en PLACSP",
        "follow.text": "Hola %(user)s,\n\n%(title)s\nEstado: %(old)s → %(new)s\n%(url)s\n\n— LicitMap",
        "due.subj_today": "Vence hoy",
        "due.subj_tomorrow": "Vence mañana",
        "due.subj_days": "Vence en %(d)s días",
        "due.msg_today": "vence <strong>hoy</strong>",
        "due.msg_tomorrow": "vence <strong>mañana</strong>",
        "due.msg_days": "vence en <strong>%(d)s días</strong> (%(date)s)",
        "due.subject": "LicitMap — %(header)s: %(title)s",
        "due.title": "Recordatorio de vencimiento",
        "due.subtitle": "Fecha límite: %(date)s",
        "due.body": "Hola <strong>%(user)s</strong>, una licitación que sigues %(msg)s.",
        "due.deadline": "Fecha límite: %(date)s",
        "due.text": "Hola %(user)s,\n\n%(title)s\nFecha límite: %(date)s (%(d)s días)\n%(url)s\n\n— LicitMap",
        "tbl.lic": "Licitación",
        "tbl.status": "Estado",
        "tbl.budget": "Presupuesto",
        "tbl.deadline": "Fecha límite",
        "tbl.empty": "No se encontraron coincidencias en este período.",
        "footer.tagline": "LicitMap · Plataforma de Contratación del Sector Público",
        "footer.manage": "Gestionar alertas",
        "test.subject": "Correo de prueba — LicitMap",
        "test.title": "Configuración SMTP correcta",
        "test.subtitle": "Panel de administración",
        "test.intro": "El servidor de correo está funcionando correctamente.",
        "test.body": "Este es un correo de prueba enviado desde el panel de administración. Si lo recibes, la configuración SMTP de LicitMap es correcta.",
        "test.text": "Este es un correo de prueba enviado desde el panel de administración de LicitMap.\n\nSi recibes este mensaje, la configuración SMTP es correcta.\n\nServidor: %(host)s:%(port)s\nUsuario: %(user)s\n\n— LicitMap",
        "estado.PUB": "Publicada",
        "estado.ADJ": "Adjudicada",
        "estado.PRE": "Preevaluación",
        "estado.RES": "Resuelta",
        "estado.EV":  "En evaluación",
        "estado.ANUL": "Anulada",
    },
    "en": {
        "otp.subject": "Your LicitMap sign-in code",
        "otp.hi": "Hi",
        "otp.subtitle": "Sign-in code",
        "otp.your_code": "Your sign-in code is:",
        "otp.expires": "Expires in <strong>15 minutes</strong>. Do not share it with anyone.",
        "alert.subject": "LicitMap — Alert \"%(name)s\": %(n)s new",
        "alert.title_prefix": "Alert:",
        "alert.subtitle": "%(n)s matches found",
        "alert.body": "Hi <strong>%(user)s</strong>, there %(be)s <strong>%(n)s new tender%(p)s</strong> matching your alert <strong>\"%(name)s\"</strong>.",
        "alert.text": "Hi %(user)s,\n\nYour alert \"%(name)s\" has %(n)s matches.\nManage your alerts at https://ivan.pibico.es/alertas\n\n— LicitMap",
        "news.subject": "LicitMap Newsletter — %(n)s new tender%(p)s",
        "news.title": "Digest: %(n)s new tenders",
        "news.subtitle": "Periodic newsletter since %(date)s",
        "news.body": "Hi <strong>%(user)s</strong>, digest of tenders published since <strong>%(date)s</strong>.",
        "news.text": "Hi %(user)s,\n\nLicitMap digest: %(n)s new tenders since %(date)s.\nhttps://ivan.pibico.es/alertas\n\n— LicitMap",
        "follow.subject": "LicitMap — Update: %(title)s",
        "follow.title": "Watched tender update",
        "follow.subtitle": "Status change detected",
        "follow.body": "Hi <strong>%(user)s</strong>, a tender you are watching has changed status.",
        "follow.prev": "Previous status:",
        "follow.arrow": "→",
        "follow.cta": "View on PLACSP",
        "follow.text": "Hi %(user)s,\n\n%(title)s\nStatus: %(old)s → %(new)s\n%(url)s\n\n— LicitMap",
        "due.subj_today": "Due today",
        "due.subj_tomorrow": "Due tomorrow",
        "due.subj_days": "Due in %(d)s days",
        "due.msg_today": "is due <strong>today</strong>",
        "due.msg_tomorrow": "is due <strong>tomorrow</strong>",
        "due.msg_days": "is due in <strong>%(d)s days</strong> (%(date)s)",
        "due.subject": "LicitMap — %(header)s: %(title)s",
        "due.title": "Deadline reminder",
        "due.subtitle": "Deadline: %(date)s",
        "due.body": "Hi <strong>%(user)s</strong>, a tender you are watching %(msg)s.",
        "due.deadline": "Deadline: %(date)s",
        "due.text": "Hi %(user)s,\n\n%(title)s\nDeadline: %(date)s (%(d)s days)\n%(url)s\n\n— LicitMap",
        "tbl.lic": "Tender",
        "tbl.status": "Status",
        "tbl.budget": "Budget",
        "tbl.deadline": "Deadline",
        "tbl.empty": "No matches found in this period.",
        "footer.tagline": "LicitMap · Spanish Public Procurement Portal",
        "footer.manage": "Manage alerts",
        "test.subject": "Test email — LicitMap",
        "test.title": "SMTP configuration OK",
        "test.subtitle": "Admin panel",
        "test.intro": "The mail server is working correctly.",
        "test.body": "This is a test email sent from the admin panel. If you can read it, LicitMap's SMTP configuration is correct.",
        "test.text": "This is a test email sent from the LicitMap admin panel.\n\nIf you receive this message, your SMTP configuration is correct.\n\nServer: %(host)s:%(port)s\nUser:   %(user)s\n\n— LicitMap",
        "estado.PUB": "Published",
        "estado.ADJ": "Awarded",
        "estado.PRE": "Pre-evaluation",
        "estado.RES": "Resolved",
        "estado.EV":  "Under evaluation",
        "estado.ANUL": "Cancelled",
    },
}


def _e(key: str, lang: str, **kwargs) -> str:
    value = EMAIL_STRINGS.get(lang, {}).get(key) or EMAIL_STRINGS["es"].get(key, key)
    if kwargs:
        try:
            return value % kwargs
        except (KeyError, TypeError, ValueError):
            return value
    return value


def _lang(lang: str | None) -> str:
    return lang if lang in ("es", "en") else "es"


# Backwards-compat: other modules imported this map directly.
_ESTADO_LABELS = {
    "PUB": "Publicada", "ADJ": "Adjudicada", "PRE": "Preevaluación",
    "RES": "Resuelta",  "EV": "En evaluación", "ANUL": "Anulada",
}


# ── Formatters ──────────────────────────────────────────────────────────

def _fmt_price(v):
    if v is None:
        return "—"
    if v >= 1_000_000:
        return f"{v/1_000_000:.1f}M €"
    if v >= 1_000:
        return f"{v/1_000:.0f}K €"
    return f"{v:.0f} €"


_ESTADO_COLORS = {
    "PUB": "#059669", "ADJ": "#2563eb", "PRE": "#d97706",
    "RES": "#71717a",  "EV": "#7c3aed",  "ANUL": "#dc2626",
}


def _estado_label(estado: str, lang: str) -> str:
    if not estado:
        return "—"
    return _e(f"estado.{estado}", lang) if f"estado.{estado}" in EMAIL_STRINGS["es"] else estado


def _lic_rows_html(licitaciones, lang: str):
    rows = []
    for l in licitaciones:
        label = _estado_label(l.estado, lang)
        color = _ESTADO_COLORS.get(l.estado, "#71717a")
        fecha = l.fecha_limite.strftime("%d/%m/%Y") if l.fecha_limite else "—"
        presup = _fmt_price(l.presupuesto)
        rows.append(f"""
  <tr>
    <td style="padding:0.55rem 0.75rem;border-bottom:1px solid #e4e4e7;font-size:0.82rem;color:#18181b">
      <a href="{l.url or '#'}" target="_blank"
         style="color:#059669;text-decoration:none;font-weight:500">{(l.titulo or '—')[:90]}</a>
      <div style="font-size:0.76rem;color:#71717a;margin-top:0.2rem">{l.organo_contratacion or ''}</div>
    </td>
    <td style="padding:0.55rem 0.75rem;border-bottom:1px solid #e4e4e7;white-space:nowrap">
      <span style="font-size:0.72rem;font-weight:600;color:{color};background:{color}18;
                   padding:0.15rem 0.45rem;border-radius:4px">{label}</span>
    </td>
    <td style="padding:0.55rem 0.75rem;border-bottom:1px solid #e4e4e7;font-size:0.8rem;
               color:#3f3f46;white-space:nowrap">{presup}</td>
    <td style="padding:0.55rem 0.75rem;border-bottom:1px solid #e4e4e7;font-size:0.8rem;
               color:#3f3f46;white-space:nowrap">{fecha}</td>
  </tr>""")
    return "".join(rows)


def _lics_table(licitaciones, lang: str):
    if not licitaciones:
        return f'<p style="color:#71717a;font-size:0.9rem">{_e("tbl.empty", lang)}</p>'
    rows = _lic_rows_html(licitaciones, lang)
    return f"""
<table width="100%" cellpadding="0" cellspacing="0"
       style="border-collapse:collapse;border:1px solid #e4e4e7;border-radius:8px;overflow:hidden;font-size:0.82rem">
  <thead>
    <tr style="background:#f4f4f5">
      <th style="padding:0.5rem 0.75rem;text-align:left;font-size:0.75rem;color:#71717a;font-weight:600">{_e("tbl.lic", lang)}</th>
      <th style="padding:0.5rem 0.75rem;text-align:left;font-size:0.75rem;color:#71717a;font-weight:600">{_e("tbl.status", lang)}</th>
      <th style="padding:0.5rem 0.75rem;text-align:left;font-size:0.75rem;color:#71717a;font-weight:600">{_e("tbl.budget", lang)}</th>
      <th style="padding:0.5rem 0.75rem;text-align:left;font-size:0.75rem;color:#71717a;font-weight:600">{_e("tbl.deadline", lang)}</th>
    </tr>
  </thead>
  <tbody>{rows}</tbody>
</table>"""


def _wrapper(title, subtitle, body_html, lang: str):
    return f"""
<div style="font-family:sans-serif;max-width:680px;margin:0 auto;padding:2rem;background:#fff">
  <h2 style="color:#059669;margin:0 0 0.15rem;font-size:1.3rem">LicitMap</h2>
  <p style="color:#71717a;margin:0 0 1.5rem;font-size:0.9rem">{subtitle}</p>
  <hr style="border:none;border-top:1px solid #e4e4e7;margin:0 0 1.5rem">
  <h3 style="margin:0 0 1rem;font-size:1rem;color:#18181b">{title}</h3>
  {body_html}
  <hr style="border:none;border-top:1px solid #e4e4e7;margin:1.5rem 0 1rem">
  <p style="color:#a1a1aa;font-size:0.72rem;margin:0">
    {_e("footer.tagline", lang)} ·
    <a href="https://ivan.pibico.es/alertas" style="color:#059669">{_e("footer.manage", lang)}</a>
  </p>
</div>"""


# ── Senders ─────────────────────────────────────────────────────────────

def send_otp_email(to_email: str, username: str, code: str, db: Session, lang: str | None = None) -> None:
    lang = _lang(lang)
    host, port, user, password, from_addr = _smtp_config(db)
    subject = _e("otp.subject", lang)
    text = (
        f"{_e('otp.hi', lang)} {username},\n\n"
        f"{_e('otp.your_code', lang)}\n\n"
        f"    {code}\n\n"
        f"— LicitMap"
    )
    html = f"""
<div style="font-family:sans-serif;max-width:420px;margin:0 auto;padding:2rem">
  <h2 style="color:#059669;margin-bottom:0.25rem">LicitMap</h2>
  <p style="color:#71717a;margin-top:0">{_e('otp.subtitle', lang)}</p>
  <hr style="border:none;border-top:1px solid #e4e4e7;margin:1.5rem 0">
  <p style="color:#18181b">{_e('otp.hi', lang)} <strong>{username}</strong>,</p>
  <p style="color:#3f3f46">{_e('otp.your_code', lang)}</p>
  <div style="font-size:2.5rem;font-weight:800;letter-spacing:0.25em;
              color:#18181b;background:#f4f4f5;border-radius:8px;
              padding:1rem 1.5rem;text-align:center;margin:1rem 0">
    {code}
  </div>
  <p style="color:#71717a;font-size:0.85rem">{_e('otp.expires', lang)}</p>
</div>"""
    _send(host, port, user, password, from_addr, to_email, subject, text, html)


def send_alerta_email(to_email: str, username: str, alerta_nombre: str,
                      licitaciones: list, db, lang: str | None = None) -> None:
    lang = _lang(lang)
    host, port, user, password, from_addr = _smtp_config(db)
    n = len(licitaciones)
    p = "s" if n != 1 else ""
    ep = "es" if (lang == "es" and n != 1) else ("" if lang == "es" else "")
    be = "are" if n != 1 else "is"
    subject = _e("alert.subject", lang, name=alerta_nombre, n=n, p=p)
    body_html = f"""
<p style="color:#3f3f46;font-size:0.9rem">
  {_e("alert.body", lang, user=username, n=n, ep=ep, p=p, be=be, name=alerta_nombre)}
</p>
{_lics_table(licitaciones, lang)}"""
    html = _wrapper(
        f"{_e('alert.title_prefix', lang)} {alerta_nombre}",
        _e("alert.subtitle", lang, n=n),
        body_html, lang,
    )
    text = _e("alert.text", lang, user=username, name=alerta_nombre, n=n)
    _send(host, port, user, password, from_addr, to_email, subject, text, html)


def send_newsletter_email(to_email: str, username: str, licitaciones: list,
                          desde, db, lang: str | None = None) -> None:
    lang = _lang(lang)
    host, port, user, password, from_addr = _smtp_config(db)
    n = len(licitaciones)
    p = "s" if n != 1 else ""
    ep = "es" if (lang == "es" and n != 1) else ("" if lang == "es" else "")
    desde_str = desde.strftime("%d/%m/%Y") if hasattr(desde, "strftime") else str(desde)
    subject = _e("news.subject", lang, n=n, ep=ep, p=p)
    body_html = f"""
<p style="color:#3f3f46;font-size:0.9rem">
  {_e("news.body", lang, user=username, date=desde_str)}
</p>
{_lics_table(licitaciones, lang)}"""
    html = _wrapper(
        _e("news.title", lang, n=n),
        _e("news.subtitle", lang, date=desde_str),
        body_html, lang,
    )
    text = _e("news.text", lang, user=username, n=n, date=desde_str)
    _send(host, port, user, password, from_addr, to_email, subject, text, html)


def send_seguimiento_email(to_email: str, username: str, lic,
                           estado_old: str, estado_new: str, db,
                           lang: str | None = None) -> None:
    lang = _lang(lang)
    host, port, user, password, from_addr = _smtp_config(db)
    old_label = _estado_label(estado_old, lang)
    new_label = _estado_label(estado_new, lang)
    new_color = _ESTADO_COLORS.get(estado_new, "#71717a")
    titulo = (lic.titulo or '')[:60]
    subject = _e("follow.subject", lang, title=titulo)
    body_html = f"""
<p style="color:#3f3f46;font-size:0.9rem">{_e("follow.body", lang, user=username)}</p>
<div style="background:#f4f4f5;border-radius:8px;padding:1rem 1.25rem;margin-bottom:1rem">
  <p style="margin:0 0 0.5rem;font-weight:600;color:#18181b;font-size:0.9rem">{lic.titulo or '—'}</p>
  <p style="margin:0;font-size:0.82rem;color:#71717a">{lic.organo_contratacion or ''}</p>
</div>
<p style="font-size:0.9rem;color:#3f3f46">
  {_e("follow.prev", lang)} <strong>{old_label}</strong> {_e("follow.arrow", lang)}
  <strong style="color:{new_color}">{new_label}</strong>
</p>
<a href="{lic.url or '#'}" target="_blank"
   style="display:inline-block;background:#059669;color:#fff;text-decoration:none;
          padding:0.5rem 1rem;border-radius:6px;font-size:0.85rem;font-weight:600">
  {_e("follow.cta", lang)}
</a>"""
    html = _wrapper(_e("follow.title", lang), _e("follow.subtitle", lang), body_html, lang)
    text = _e("follow.text", lang, user=username, title=lic.titulo or '',
              old=old_label, new=new_label, url=lic.url or '')
    _send(host, port, user, password, from_addr, to_email, subject, text, html)


def send_vencimiento_email(to_email: str, username: str, lic,
                           dias_restantes: int, db,
                           lang: str | None = None) -> None:
    lang = _lang(lang)
    host, port, user, password, from_addr = _smtp_config(db)
    fecha_str = lic.fecha_limite.strftime("%d/%m/%Y") if lic.fecha_limite else "—"
    if dias_restantes == 0:
        msg = _e("due.msg_today", lang)
        header = _e("due.subj_today", lang)
    elif dias_restantes == 1:
        msg = _e("due.msg_tomorrow", lang)
        header = _e("due.subj_tomorrow", lang)
    else:
        msg = _e("due.msg_days", lang, d=dias_restantes, date=fecha_str)
        header = _e("due.subj_days", lang, d=dias_restantes)
    titulo = (lic.titulo or '')[:55]
    subject = _e("due.subject", lang, header=header, title=titulo)
    body_html = f"""
<p style="color:#3f3f46;font-size:0.9rem">{_e("due.body", lang, user=username, msg=msg)}</p>
<div style="background:#fff7ed;border:1px solid #fed7aa;border-radius:8px;padding:1rem 1.25rem;margin-bottom:1rem">
  <p style="margin:0 0 0.5rem;font-weight:600;color:#18181b;font-size:0.9rem">{lic.titulo or '—'}</p>
  <p style="margin:0;font-size:0.82rem;color:#71717a">{lic.organo_contratacion or ''}</p>
  <p style="margin:0.5rem 0 0;font-size:0.82rem;color:#c2410c">
    <strong>{_e("due.deadline", lang, date=fecha_str)}</strong>
  </p>
</div>
<a href="{lic.url or '#'}" target="_blank"
   style="display:inline-block;background:#059669;color:#fff;text-decoration:none;
          padding:0.5rem 1rem;border-radius:6px;font-size:0.85rem;font-weight:600">
  {_e("follow.cta", lang)}
</a>"""
    html = _wrapper(_e("due.title", lang), _e("due.subtitle", lang, date=fecha_str), body_html, lang)
    text = _e("due.text", lang, user=username, title=lic.titulo or '',
              date=fecha_str, d=dias_restantes, url=lic.url or '')
    _send(host, port, user, password, from_addr, to_email, subject, text, html)


def send_test_email(to_email: str, db: Session, lang: str | None = None) -> None:
    lang = _lang(lang)
    host, port, user, password, from_addr = _smtp_config(db)
    subject = _e("test.subject", lang)
    text = _e("test.text", lang, host=host, port=port, user=user)
    html = f"""
<div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:2rem">
  <h2 style="color:#059669;margin:0 0 0.15rem">LicitMap</h2>
  <p style="color:#71717a;margin:0 0 1.5rem;font-size:0.9rem">{_e("test.subtitle", lang)}</p>
  <hr style="border:none;border-top:1px solid #e4e4e7;margin:0 0 1.5rem">
  <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;
              padding:1rem 1.25rem;margin-bottom:1.5rem">
    <p style="margin:0;font-weight:700;color:#15803d">{_e("test.title", lang)}</p>
    <p style="margin:0.25rem 0 0;font-size:0.85rem;color:#166534">{_e("test.intro", lang)}</p>
  </div>
  <p style="color:#3f3f46;font-size:0.9rem;margin:0 0 1rem">{_e("test.body", lang)}</p>
  <table style="width:100%;border-collapse:collapse;font-size:0.82rem;color:#71717a">
    <tr>
      <td style="padding:0.3rem 0;border-bottom:1px solid #f4f4f5;width:40%">{_e("ac.email_host", lang) if "ac.email_host" in EMAIL_STRINGS["es"] else "Server"}</td>
      <td style="padding:0.3rem 0;border-bottom:1px solid #f4f4f5;color:#18181b;font-family:monospace">{host}:{port}</td>
    </tr>
    <tr>
      <td style="padding:0.3rem 0;width:40%">{_e("ac.email_user", lang) if "ac.email_user" in EMAIL_STRINGS["es"] else "User"}</td>
      <td style="color:#18181b;font-family:monospace">{user}</td>
    </tr>
  </table>
  <hr style="border:none;border-top:1px solid #e4e4e7;margin:1.5rem 0 1rem">
  <p style="color:#a1a1aa;font-size:0.75rem;margin:0">{_e("footer.tagline", lang)}</p>
</div>"""
    _send(host, port, user, password, from_addr, to_email, subject, text, html)
