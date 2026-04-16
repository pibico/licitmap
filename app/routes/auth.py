import bcrypt
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from pathlib import Path
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

router = APIRouter()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def get_user(db: Session, username: str) -> User | None:
    return db.query(User).filter_by(username=username, is_active=True).first()


def _render_login(error: str = "") -> str:
    base = Path("templates/base.html").read_text()
    page = Path("templates/login.html").read_text()
    html = base.replace("{{content}}", page)
    error_block = f'<div class="lm-login-error">{error}</div>' if error else ""
    for key, value in {
        "active_busqueda": "",
        "active_mapa": "",
        "nav_auth_block": "",
        "nav_busqueda_display": "display:none",
        "error_block": error_block,
    }.items():
        html = html.replace("{{" + key + "}}", value)
    return html


@router.get("/login", response_class=HTMLResponse)
def login_get(request: Request):
    if request.session.get("username"):
        return RedirectResponse("/", status_code=303)
    return _render_login()


@router.post("/login")
async def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = get_user(db, username)
    if user and verify_password(password, user.hashed_password):
        request.session["username"] = user.username
        return RedirectResponse("/", status_code=303)
    return HTMLResponse(_render_login("Usuario o contraseña incorrectos"), status_code=401)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)
