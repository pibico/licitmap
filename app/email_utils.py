"""Envío de emails de OTP. Configuración leída de la tabla settings (panel /admin/config)."""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.orm import Session

from app.utils import get_setting


def send_otp_email(to_email: str, username: str, code: str, db: Session) -> None:
    host     = get_setting(db, "smtp_host", "")
    port     = int(get_setting(db, "smtp_port", "587"))
    user     = get_setting(db, "smtp_user", "")
    password = get_setting(db, "smtp_pass", "")
    from_addr = get_setting(db, "smtp_from", "") or user

    if not host or not user or not password:
        raise RuntimeError(
            "El correo no está configurado. "
            "Ve a Admin → Configuración y rellena los datos SMTP."
        )

    subject = "Tu código de acceso a LicitMap"
    body_text = (
        f"Hola {username},\n\n"
        f"Tu código de acceso a LicitMap es:\n\n"
        f"    {code}\n\n"
        f"Este código expira en 15 minutos. No lo compartas con nadie.\n\n"
        f"— LicitMap"
    )
    body_html = f"""
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

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = from_addr
    msg["To"]      = to_email
    msg.attach(MIMEText(body_text, "plain"))
    msg.attach(MIMEText(body_html, "html"))

    context = ssl.create_default_context()
    with smtplib.SMTP(host, port) as smtp:
        smtp.ehlo()
        smtp.starttls(context=context)
        smtp.login(user, password)
        smtp.sendmail(from_addr, to_email, msg.as_string())
