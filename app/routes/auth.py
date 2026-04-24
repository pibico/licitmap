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
from app.i18n import get_lang_from_request
from app.utils import lang_selector_html

router = APIRouter()

_OTP_TTL = timedelta(minutes=15)


def _render(request: Request, template: str, vars: dict) -> str:
    base = Path("templates/base.html").read_text()
    page = Path(f"templates/{template}").read_text()
    html = base.replace("{{content}}", page)
    defaults = {
        "active_busqueda": "",
        "active_mapa": "",
        "nav_auth_block": "",
        "nav_busqueda_display": "display:none",
        "lang_selector": lang_selector_html(get_lang_from_request(request)),
        "error_block": "",
        "info_block": "",
    }
    defaults.update(vars)
    for key, value in defaults.items():
        html = html.replace("{{" + key + "}}", value)
    return html


def _err(request: Request, template: str, msg: str, extra: dict | None = None) -> HTMLResponse:
    v = {"error_block": f'<div class="lm-login-error">{msg}</div>'}
    if extra:
        v.update(extra)
    return HTMLResponse(_render(request, template, v), status_code=400)


# ── Paso 1: formulario de usuario ────────────────────────────────────────────

@router.get("/login", response_class=HTMLResponse)
def login_get(request: Request):
    if request.session.get("username"):
        return RedirectResponse("/", status_code=303)
    return HTMLResponse(_render(request, "login.html", {}))


def _login_redirect(user: User) -> RedirectResponse:
    """Redirige a la home tras login y sincroniza la cookie de idioma."""
    resp = RedirectResponse("/", status_code=303)
    if user.language:
        resp.set_cookie(
            "lm_lang", user.language, max_age=60 * 60 * 24 * 365, samesite="lax"
        )
    return resp


@router.post("/login")
async def login_post(
    request: Request,
    username: str = Form(...),
    db: Session = Depends(get_db),
):
    if request.session.get("username"):
        return RedirectResponse("/", status_code=303)

    identifier = username.strip().lower()

    user = db.query(User).filter_by(username=identifier, is_active=True).first()
    if not user:
        user = db.query(User).filter(
            User.email == identifier, User.is_active == True
        ).first()

    if not user:
        return _err(request, "login.html", "{{t.login.err_nouser}}")

    if user.username == "admin":
        return RedirectResponse("/login/password?u=admin", status_code=303)

    if not user.email:
        return _err(request, "login.html", "{{t.login.err_no_email}}")

    otp = f"{secrets.randbelow(1_000_000):06d}"
    user.otp_code = otp
    user.otp_expires_at = datetime.utcnow() + _OTP_TTL
    db.commit()

    try:
        send_otp_email(user.email, user.username, otp, db, lang=user.language)
    except Exception as e:
        return _err(request, "login.html", f"{{{{t.login.err_send_otp}}}} ({e})")

    return RedirectResponse(f"/login/codigo?u={user.username}", status_code=303)


@router.get("/login/password", response_class=HTMLResponse)
def login_password_get(request: Request, u: str = ""):
    if request.session.get("username"):
        return RedirectResponse("/", status_code=303)
    if u != "admin":
        return RedirectResponse("/login", status_code=303)
    return HTMLResponse(_render(request, "login_password.html", {"login_username": u}))


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
        return _login_redirect(user)
    return _err(request, "login_password.html", "{{t.login.err_bad_pass}}", {"login_username": username})


@router.get("/login/codigo", response_class=HTMLResponse)
def login_codigo_get(request: Request, u: str = ""):
    if request.session.get("username"):
        return RedirectResponse("/", status_code=303)
    if not u:
        return RedirectResponse("/login", status_code=303)
    return HTMLResponse(_render(request, "login_codigo.html", {"login_username": u}))


@router.post("/login/codigo")
async def login_codigo_post(
    request: Request,
    username: str = Form(...),
    codigo: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter_by(username=username, is_active=True).first()
    if not user or not user.otp_code or not user.otp_expires_at:
        return _err(request, "login_codigo.html", "{{t.login.err_bad_otp}}", {"login_username": username})

    if datetime.utcnow() > user.otp_expires_at:
        user.otp_code = None
        user.otp_expires_at = None
        db.commit()
        return _err(request, "login_codigo.html", "{{t.login.err_otp_expired}}", {"login_username": username})

    if not secrets.compare_digest(codigo.strip(), user.otp_code):
        return _err(request, "login_codigo.html", "{{t.login.err_bad_otp}}", {"login_username": username})

    user.otp_code = None
    user.otp_expires_at = None
    db.commit()
    request.session["username"] = user.username
    return _login_redirect(user)


# ── Logout ────────────────────────────────────────────────────────────────────

@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)
