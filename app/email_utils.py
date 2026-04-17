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
