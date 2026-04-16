from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from pathlib import Path

router = APIRouter()

# Credenciales hardcodeadas — sustituir por DB cuando se implemente el sistema de cuentas
USERS: dict[str, str] = {
    "admin": "admin",
}


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
):
    if USERS.get(username) == password:
        request.session["username"] = username
        return RedirectResponse("/", status_code=303)
    return HTMLResponse(_render_login("Usuario o contraseña incorrectos"), status_code=401)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)
