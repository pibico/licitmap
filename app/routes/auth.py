import secrets
import bcrypt
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from pathlib import Path
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.email_utils import send_otp_email

router = APIRouter()

_OTP_TTL = timedelta(minutes=15)


def _render(template: str, vars: dict) -> str:
    base = Path("templates/base.html").read_text()
    page = Path(f"templates/{template}").read_text()
    html = base.replace("{{content}}", page)
    defaults = {
        "active_busqueda": "",
        "active_mapa": "",
        "nav_auth_block": "",
        "nav_busqueda_display": "display:none",
        "error_block": "",
        "info_block": "",
    }
    defaults.update(vars)
    for key, value in defaults.items():
        html = html.replace("{{" + key + "}}", value)
    return html


def _err(template: str, msg: str, extra: dict | None = None) -> HTMLResponse:
    v = {"error_block": f'<div class="lm-login-error">{msg}</div>'}
    if extra:
        v.update(extra)
    return HTMLResponse(_render(template, v), status_code=400)


# ── Paso 1: formulario de usuario ────────────────────────────────────────────

@router.get("/login", response_class=HTMLResponse)
def login_get(request: Request):
    if request.session.get("username"):
        return RedirectResponse("/", status_code=303)
    return HTMLResponse(_render("login.html", {}))


@router.post("/login")
async def login_post(
    request: Request,
    username: str = Form(...),
    db: Session = Depends(get_db),
):
    if request.session.get("username"):
        return RedirectResponse("/", status_code=303)

    username = username.strip().lower()
    user = db.query(User).filter_by(username=username, is_active=True).first()
    if not user:
        return _err("login.html", "Usuario no encontrado o inactivo.")

    if username == "admin":
        # Admin usa contraseña — redirige al paso de contraseña
        return RedirectResponse(f"/login/password?u={username}", status_code=303)

    # Usuario normal — genera OTP y envía email
    if not user.email:
        return _err("login.html", "Este usuario no tiene correo electrónico configurado. Contacta con el administrador.")

    otp = f"{secrets.randbelow(1_000_000):06d}"
    user.otp_code = otp
    user.otp_expires_at = datetime.utcnow() + _OTP_TTL
    db.commit()

    try:
        send_otp_email(user.email, user.username, otp)
    except Exception as e:
        return _err("login.html", f"No se pudo enviar el correo: {e}")

    return RedirectResponse(f"/login/codigo?u={username}", status_code=303)


# ── Paso 2a: contraseña (solo admin) ─────────────────────────────────────────

@router.get("/login/password", response_class=HTMLResponse)
def login_password_get(request: Request, u: str = ""):
    if request.session.get("username"):
        return RedirectResponse("/", status_code=303)
    if u != "admin":
        return RedirectResponse("/login", status_code=303)
    return HTMLResponse(_render("login_password.html", {"login_username": u}))


@router.post("/login/password")
async def login_password_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    if username != "admin":
        return RedirectResponse("/login", status_code=303)
    user = db.query(User).filter_by(username="admin", is_active=True).first()
    if user and user.hashed_password and bcrypt.checkpw(password.encode(), user.hashed_password.encode()):
        request.session["username"] = user.username
        return RedirectResponse("/", status_code=303)
    return _err("login_password.html", "Contraseña incorrecta.", {"login_username": username})


# ── Paso 2b: código OTP (usuarios no-admin) ───────────────────────────────────

@router.get("/login/codigo", response_class=HTMLResponse)
def login_codigo_get(request: Request, u: str = ""):
    if request.session.get("username"):
        return RedirectResponse("/", status_code=303)
    if not u:
        return RedirectResponse("/login", status_code=303)
    return HTMLResponse(_render("login_codigo.html", {"login_username": u}))


@router.post("/login/codigo")
async def login_codigo_post(
    request: Request,
    username: str = Form(...),
    codigo: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter_by(username=username, is_active=True).first()
    if not user or not user.otp_code or not user.otp_expires_at:
        return _err("login_codigo.html", "Código inválido. Vuelve a iniciar sesión.", {"login_username": username})

    if datetime.utcnow() > user.otp_expires_at:
        user.otp_code = None
        user.otp_expires_at = None
        db.commit()
        return _err("login_codigo.html", "El código ha expirado. Vuelve a iniciar sesión.", {"login_username": username})

    if not secrets.compare_digest(codigo.strip(), user.otp_code):
        return _err("login_codigo.html", "Código incorrecto.", {"login_username": username})

    user.otp_code = None
    user.otp_expires_at = None
    db.commit()
    request.session["username"] = user.username
    return RedirectResponse("/", status_code=303)


# ── Logout ────────────────────────────────────────────────────────────────────

@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)
