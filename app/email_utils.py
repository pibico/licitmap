"""Envío de emails. Configuración leída de la tabla settings (panel /admin/config)."""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.orm import Session

from app.utils import get_setting


def _smtp_config(db: Session) -> tuple[str, int, str, str, str]:
    host      = get_setting(db, "smtp_host", "")
    port      = int(get_setting(db, "smtp_port", "587"))
    user      = get_setting(db, "smtp_user", "")
    password  = get_setting(db, "smtp_pass", "")
    from_addr = get_setting(db, "smtp_from", "") or user
    if not host or not user or not password:
        raise RuntimeError(
            "El correo no está configurado. "
            "Ve a Admin → Configuración → Correo SMTP."
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


def send_otp_email(to_email: str, username: str, code: str, db: Session) -> None:
    host, port, user, password, from_addr = _smtp_config(db)
    subject = "Tu código de acceso a LicitMap"
    text = (
        f"Hola {username},\n\n"
        f"Tu código de acceso a LicitMap es:\n\n"
        f"    {code}\n\n"
        f"Este código expira en 15 minutos. No lo compartas con nadie.\n\n"
        f"— LicitMap"
    )
    html = f"""
<div style="font-family:sans-serif;max-width:420px;margin:0 auto;padding:2rem">
  <h2 style="color:#059669;margin-bottom:0.25rem">LicitMap</h2>
  <p style="color:#71717a;margin-top:0">Código de acceso</p>
  <hr style="border:none;border-top:1px solid #e4e4e7;margin:1.5rem 0">
  <p style="color:#18181b">Hola <strong>{username}</strong>,</p>
  <p style="color:#3f3f46">Tu código de acceso es:</p>
  <div style="font-size:2.5rem;font-weight:800;letter-spacing:0.25em;
              color:#18181b;background:#f4f4f5;border-radius:8px;
              padding:1rem 1.5rem;text-align:center;margin:1rem 0">
    {code}
  </div>
  <p style="color:#71717a;font-size:0.85rem">
    Expira en <strong>15 minutos</strong>. No lo compartas con nadie.
  </p>
</div>"""
    _send(host, port, user, password, from_addr, to_email, subject, text, html)


# ── Helpers de formato ────────────────────────────────────────────────────────

def _fmt_price(v):
    if v is None:
        return "—"
    if v >= 1_000_000:
        return f"{v/1_000_000:.1f}M €"
    if v >= 1_000:
        return f"{v/1_000:.0f}K €"
    return f"{v:.0f} €"


_ESTADO_LABELS = {
    "PUB": "Publicada", "ADJ": "Adjudicada", "PRE": "Preevaluación",
    "RES": "Resuelta",  "EV": "En evaluación", "ANUL": "Anulada",
}

_ESTADO_COLORS = {
    "PUB": "#059669", "ADJ": "#2563eb", "PRE": "#d97706",
    "RES": "#71717a",  "EV": "#7c3aed",  "ANUL": "#dc2626",
}


def _lic_rows_html(licitaciones):
    rows = []
    for l in licitaciones:
        estado_label = _ESTADO_LABELS.get(l.estado, l.estado or "—")
        color = _ESTADO_COLORS.get(l.estado, "#71717a")
        fecha = l.fecha_limite.strftime("%d/%m/%Y") if l.fecha_limite else "—"
        presup = _fmt_price(l.presupuesto)
        rows.append(f"""
  <tr>
    <td style="padding:0.55rem 0.75rem;border-bottom:1px solid #e4e4e7;font-size:0.82rem;color:#18181b">
      <a href="{l.url or '#'}" target="_blank"
         style="color:#059669;text-decoration:none;font-weight:500">{l.titulo[:90] if l.titulo else '—'}</a>
      <div style="font-size:0.76rem;color:#71717a;margin-top:0.2rem">{l.organo_contratacion or ''}</div>
    </td>
    <td style="padding:0.55rem 0.75rem;border-bottom:1px solid #e4e4e7;white-space:nowrap">
      <span style="font-size:0.72rem;font-weight:600;color:{color};background:{color}18;
                   padding:0.15rem 0.45rem;border-radius:4px">{estado_label}</span>
    </td>
    <td style="padding:0.55rem 0.75rem;border-bottom:1px solid #e4e4e7;font-size:0.8rem;
               color:#3f3f46;white-space:nowrap">{presup}</td>
    <td style="padding:0.55rem 0.75rem;border-bottom:1px solid #e4e4e7;font-size:0.8rem;
               color:#3f3f46;white-space:nowrap">{fecha}</td>
  </tr>""")
    return "".join(rows)


def _base_email_wrapper(title, subtitle, body_html):
    return f"""
<div style="font-family:sans-serif;max-width:680px;margin:0 auto;padding:2rem;background:#fff">
  <h2 style="color:#059669;margin:0 0 0.15rem;font-size:1.3rem">LicitMap</h2>
  <p style="color:#71717a;margin:0 0 1.5rem;font-size:0.9rem">{subtitle}</p>
  <hr style="border:none;border-top:1px solid #e4e4e7;margin:0 0 1.5rem">
  <h3 style="margin:0 0 1rem;font-size:1rem;color:#18181b">{title}</h3>
  {body_html}
  <hr style="border:none;border-top:1px solid #e4e4e7;margin:1.5rem 0 1rem">
  <p style="color:#a1a1aa;font-size:0.72rem;margin:0">
    LicitMap &middot; Plataforma de Contrataci&oacute;n del Sector P&uacute;blico &middot;
    <a href="https://ivan.pibico.es/alertas" style="color:#059669">Gestionar alertas</a>
  </p>
</div>"""


def _lics_table(licitaciones):
    if not licitaciones:
        return '<p style="color:#71717a;font-size:0.9rem">No se encontraron coincidencias en este per&iacute;odo.</p>'
    rows = _lic_rows_html(licitaciones)
    return f"""
<table width="100%" cellpadding="0" cellspacing="0"
       style="border-collapse:collapse;border:1px solid #e4e4e7;border-radius:8px;overflow:hidden;font-size:0.82rem">
  <thead>
    <tr style="background:#f4f4f5">
      <th style="padding:0.5rem 0.75rem;text-align:left;font-size:0.75rem;color:#71717a;font-weight:600">Licitaci&oacute;n</th>
      <th style="padding:0.5rem 0.75rem;text-align:left;font-size:0.75rem;color:#71717a;font-weight:600">Estado</th>
      <th style="padding:0.5rem 0.75rem;text-align:left;font-size:0.75rem;color:#71717a;font-weight:600">Presupuesto</th>
      <th style="padding:0.5rem 0.75rem;text-align:left;font-size:0.75rem;color:#71717a;font-weight:600">Fecha l&iacute;mite</th>
    </tr>
  </thead>
  <tbody>{rows}</tbody>
</table>"""


# ── Funciones de alerta ───────────────────────────────────────────────────────

def send_alerta_email(to_email: str, username: str, alerta_nombre: str,
                      licitaciones: list, db) -> None:
    host, port, user, password, from_addr = _smtp_config(db)
    n = len(licitaciones)
    subject = f"LicitMap \u2014 Alerta \u00ab{alerta_nombre}\u00bb: {n} nueva{'s' if n != 1 else ''}"
    body_html = f"""
<p style="color:#3f3f46;font-size:0.9rem">
  Hola <strong>{username}</strong>, hay <strong>{n} licitaci&oacute;n{'es' if n != 1 else ''} nueva{'s' if n != 1 else ''}</strong>
  que coinciden con tu alerta <strong>&laquo;{alerta_nombre}&raquo;</strong>.
</p>
{_lics_table(licitaciones)}"""
    html = _base_email_wrapper(
        f"Alerta: {alerta_nombre}",
        f"Se encontraron {n} coincidencias",
        body_html,
    )
    text = f"Hola {username},\n\nTu alerta {alerta_nombre!r} tiene {n} coincidencias.\nGestiona tus alertas en https://ivan.pibico.es/alertas\n\n\u2014 LicitMap"
    _send(host, port, user, password, from_addr, to_email, subject, text, html)


def send_newsletter_email(to_email: str, username: str, licitaciones: list,
                          desde, db) -> None:
    host, port, user, password, from_addr = _smtp_config(db)
    n = len(licitaciones)
    desde_str = desde.strftime("%d/%m/%Y") if hasattr(desde, "strftime") else str(desde)
    subject = f"LicitMap Newsletter \u2014 {n} licitaci&oacute;n{'es' if n != 1 else ''} nueva{'s' if n != 1 else ''}"
    body_html = f"""
<p style="color:#3f3f46;font-size:0.9rem">
  Hola <strong>{username}</strong>, resumen de licitaciones publicadas desde el <strong>{desde_str}</strong>.
</p>
{_lics_table(licitaciones)}"""
    html = _base_email_wrapper(
        f"Resumen: {n} licitaciones nuevas",
        f"Newsletter peri&oacute;dico desde {desde_str}",
        body_html,
    )
    text = f"Hola {username},\n\nResumen LicitMap: {n} licitaciones nuevas desde {desde_str}.\nhttps://ivan.pibico.es/alertas\n\n\u2014 LicitMap"
    _send(host, port, user, password, from_addr, to_email, subject, text, html)


def send_seguimiento_email(to_email: str, username: str, lic,
                           estado_old: str, estado_new: str, db) -> None:
    host, port, user, password, from_addr = _smtp_config(db)
    old_label = _ESTADO_LABELS.get(estado_old, estado_old or "\u2014")
    new_label = _ESTADO_LABELS.get(estado_new, estado_new or "\u2014")
    new_color = _ESTADO_COLORS.get(estado_new, "#71717a")
    subject = f"LicitMap \u2014 Actualizaci\u00f3n: {(lic.titulo or '')[:60]}"
    body_html = f"""
<p style="color:#3f3f46;font-size:0.9rem">
  Hola <strong>{username}</strong>, una licitaci&oacute;n que est&aacute;s siguiendo ha cambiado de estado.
</p>
<div style="background:#f4f4f5;border-radius:8px;padding:1rem 1.25rem;margin-bottom:1rem">
  <p style="margin:0 0 0.5rem;font-weight:600;color:#18181b;font-size:0.9rem">{lic.titulo or '\u2014'}</p>
  <p style="margin:0;font-size:0.82rem;color:#71717a">{lic.organo_contratacion or ''}</p>
</div>
<p style="font-size:0.9rem;color:#3f3f46">
  Estado anterior: <strong>{old_label}</strong> &rarr;
  <strong style="color:{new_color}">{new_label}</strong>
</p>
<a href="{lic.url or '#'}" target="_blank"
   style="display:inline-block;background:#059669;color:#fff;text-decoration:none;
          padding:0.5rem 1rem;border-radius:6px;font-size:0.85rem;font-weight:600">
  Ver en PLACSP
</a>"""
    html = _base_email_wrapper("Actualizaci\u00f3n de licitaci\u00f3n seguida", "Cambio de estado detectado", body_html)
    text = f"Hola {username},\n\n{lic.titulo}\nEstado: {old_label} \u2192 {new_label}\n{lic.url or ''}\n\n\u2014 LicitMap"
    _send(host, port, user, password, from_addr, to_email, subject, text, html)


def send_vencimiento_email(to_email: str, username: str, lic,
                           dias_restantes: int, db) -> None:
    host, port, user, password, from_addr = _smtp_config(db)
    fecha_str = lic.fecha_limite.strftime("%d/%m/%Y") if lic.fecha_limite else "\u2014"
    if dias_restantes == 0:
        aviso = "vence <strong>hoy</strong>"
        subj_aviso = "Vence hoy"
    elif dias_restantes == 1:
        aviso = "vence <strong>ma\u00f1ana</strong>"
        subj_aviso = "Vence ma\u00f1ana"
    else:
        aviso = f"vence en <strong>{dias_restantes} d\u00edas</strong> ({fecha_str})"
        subj_aviso = f"Vence en {dias_restantes} d\u00edas"
    subject = f"LicitMap \u2014 {subj_aviso}: {(lic.titulo or '')[:55]}"
    body_html = f"""
<p style="color:#3f3f46;font-size:0.9rem">
  Hola <strong>{username}</strong>, una licitaci&oacute;n que sigues {aviso}.
</p>
<div style="background:#fff7ed;border:1px solid #fed7aa;border-radius:8px;padding:1rem 1.25rem;margin-bottom:1rem">
  <p style="margin:0 0 0.5rem;font-weight:600;color:#18181b;font-size:0.9rem">{lic.titulo or '\u2014'}</p>
  <p style="margin:0;font-size:0.82rem;color:#71717a">{lic.organo_contratacion or ''}</p>
  <p style="margin:0.5rem 0 0;font-size:0.82rem;color:#c2410c">
    <strong>Fecha l&iacute;mite: {fecha_str}</strong>
  </p>
</div>
<a href="{lic.url or '#'}" target="_blank"
   style="display:inline-block;background:#059669;color:#fff;text-decoration:none;
          padding:0.5rem 1rem;border-radius:6px;font-size:0.85rem;font-weight:600">
  Ver en PLACSP
</a>"""
    html = _base_email_wrapper("Recordatorio de vencimiento", f"Fecha l&iacute;mite: {fecha_str}", body_html)
    text = f"Hola {username},\n\n{lic.titulo}\nFecha l\u00edmite: {fecha_str} ({dias_restantes} d\u00edas)\n{lic.url or ''}\n\n\u2014 LicitMap"
    _send(host, port, user, password, from_addr, to_email, subject, text, html)


def send_test_email(to_email: str, db: Session) -> None:
    host, port, user, password, from_addr = _smtp_config(db)
    subject = "Correo de prueba — LicitMap"
    text = (
        "Este es un correo de prueba enviado desde el panel de administración de LicitMap.\n\n"
        "Si recibes este mensaje, la configuración SMTP es correcta.\n\n"
        f"Servidor: {host}:{port}\n"
        f"Usuario:  {user}\n\n"
        "— LicitMap"
    )
    html = f"""
<div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:2rem">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td>
        <h2 style="color:#059669;margin:0 0 0.15rem">LicitMap</h2>
        <p style="color:#71717a;margin:0 0 1.5rem;font-size:0.9rem">Panel de administración</p>
      </td>
    </tr>
  </table>
  <hr style="border:none;border-top:1px solid #e4e4e7;margin:0 0 1.5rem">
  <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;
              padding:1rem 1.25rem;margin-bottom:1.5rem;display:flex;align-items:flex-start;gap:0.75rem">
    <span style="font-size:1.25rem;line-height:1">✅</span>
    <div>
      <p style="margin:0;font-weight:700;color:#15803d">Configuración SMTP correcta</p>
      <p style="margin:0.25rem 0 0;font-size:0.85rem;color:#166534">
        El servidor de correo está funcionando correctamente.
      </p>
    </div>
  </div>
  <p style="color:#3f3f46;font-size:0.9rem;margin:0 0 1rem">
    Este es un correo de prueba enviado desde el panel de administración.
    Si lo recibes, la configuración SMTP de LicitMap es correcta.
  </p>
  <table style="width:100%;border-collapse:collapse;font-size:0.82rem;color:#71717a">
    <tr>
      <td style="padding:0.3rem 0;border-bottom:1px solid #f4f4f5;width:40%">Servidor</td>
      <td style="padding:0.3rem 0;border-bottom:1px solid #f4f4f5;color:#18181b;font-family:monospace">{host}:{port}</td>
    </tr>
    <tr>
      <td style="padding:0.3rem 0;width:40%">Usuario</td>
      <td style="color:#18181b;font-family:monospace">{user}</td>
    </tr>
  </table>
  <hr style="border:none;border-top:1px solid #e4e4e7;margin:1.5rem 0 1rem">
  <p style="color:#a1a1aa;font-size:0.75rem;margin:0">
    LicitMap — Plataforma de Contratación del Sector Público
  </p>
</div>"""
    _send(host, port, user, password, from_addr, to_email, subject, text, html)
