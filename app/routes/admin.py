import bcrypt
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from pathlib import Path
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.utils import _nav_context

router = APIRouter(prefix="/admin")


def _require_admin(request: Request):
    return request.session.get("username") == "admin"


def _render_admin(request: Request, db: Session, error: str = "", ok: str = "") -> str:
    if not _require_admin(request):
        return None
    users = db.query(User).order_by(User.id).all()
    rows = ""
    for u in users:
        estado = "Activo" if u.is_active else "Inactivo"
        toggle_label = "Desactivar" if u.is_active else "Activar"
        toggle_action = f"/admin/usuarios/{u.id}/toggle"
        rows += f"""
        <tr>
          <td>{u.id}</td>
          <td>{u.username}</td>
          <td><span class="badge {'bg-success' if u.is_active else 'bg-secondary'}">{estado}</span></td>
          <td>
            <form method="post" action="{toggle_action}" style="display:inline">
              <button class="btn btn-sm btn-outline-secondary" type="submit"
                {'disabled' if u.username == 'admin' else ''}>{toggle_label}</button>
            </form>
          </td>
        </tr>"""

    error_block = f'<div class="alert alert-danger mt-2">{error}</div>' if error else ""
    ok_block = f'<div class="alert alert-success mt-2">{ok}</div>' if ok else ""

    base = Path("templates/base.html").read_text()
    page = Path("templates/admin_usuarios.html").read_text()
    html = base.replace("{{content}}", page)
    auth_block, busqueda_display = _nav_context(request)
    for key, value in {
        "active_busqueda": "",
        "active_mapa": "",
        "nav_auth_block": auth_block,
        "nav_busqueda_display": busqueda_display,
        "users_rows": rows,
        "error_block": error_block,
        "ok_block": ok_block,
    }.items():
        html = html.replace("{{" + key + "}}", value)
    return html


@router.get("/usuarios", response_class=HTMLResponse)
def admin_usuarios(request: Request, ok: str = "", db: Session = Depends(get_db)):
    if not _require_admin(request):
        return RedirectResponse("/login", status_code=303)
    return _render_admin(request, db, ok=ok)


@router.post("/usuarios/nuevo")
async def admin_crear_usuario(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    if not _require_admin(request):
        return RedirectResponse("/login", status_code=303)
    username = username.strip()
    if not username or not password:
        return HTMLResponse(_render_admin(request, db, error="Usuario y contraseña son obligatorios."))
    if db.query(User).filter_by(username=username).first():
        return HTMLResponse(_render_admin(request, db, error=f"El usuario '{username}' ya existe."))
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    db.add(User(username=username, hashed_password=hashed, is_active=True))
    db.commit()
    return RedirectResponse(f"/admin/usuarios?ok=Usuario+'{username}'+creado", status_code=303)


@router.post("/usuarios/{user_id}/toggle")
def admin_toggle_usuario(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    if not _require_admin(request):
        return RedirectResponse("/login", status_code=303)
    user = db.query(User).filter_by(id=user_id).first()
    if user and user.username != "admin":
        user.is_active = not user.is_active
        db.commit()
    return RedirectResponse("/admin/usuarios", status_code=303)
