import bcrypt
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from pathlib import Path
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.utils import _nav_context, get_setting, set_setting

router = APIRouter(prefix="/admin")


def _require_admin(request: Request) -> bool:
    return request.session.get("username") == "admin"


def _render(request: Request, page_tpl: str, active: str, extra: dict | None = None) -> str:
    auth_block, busqueda_display = _nav_context(request)
    base = Path("templates/base.html").read_text()
    admin_base = Path("templates/admin_base.html").read_text()
    page = Path(f"templates/{page_tpl}").read_text()

    html = base.replace("{{content}}", admin_base.replace("{{admin_content}}", page))
    vars = {
        "active_busqueda": "",
        "active_mapa": "",
        "nav_auth_block": auth_block,
        "nav_busqueda_display": busqueda_display,
        "admin_active_dashboard": "active" if active == "dashboard" else "",
        "admin_active_usuarios": "active" if active == "usuarios" else "",
        "admin_active_config": "active" if active == "config" else "",
        "error_block": "",
        "ok_block": "",
    }
    if extra:
        vars.update(extra)
    for key, value in vars.items():
        html = html.replace("{{" + key + "}}", value)
    return html


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    if not _require_admin(request):
        return RedirectResponse("/login", status_code=303)
    total_users = db.query(User).count()
    active_users = db.query(User).filter_by(is_active=True).count()
    export_limit = get_setting(db, "export_limit", "5000")
    return HTMLResponse(_render(request, "admin_dashboard.html", "dashboard", {
        "total_users": str(total_users),
        "active_users": str(active_users),
        "export_limit": export_limit,
    }))


@router.get("/usuarios", response_class=HTMLResponse)
def admin_usuarios(request: Request, ok: str = "", db: Session = Depends(get_db)):
    if not _require_admin(request):
        return RedirectResponse("/login", status_code=303)
    return HTMLResponse(_render(request, "admin_usuarios.html", "usuarios", {
        "users_rows": _users_rows(db),
        "ok_block": f'<div class="alert alert-success mt-2">{ok}</div>' if ok else "",
    }))


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
        return HTMLResponse(_render(request, "admin_usuarios.html", "usuarios", {
            "users_rows": _users_rows(db),
            "error_block": '<div class="alert alert-danger mt-2">Usuario y contraseña son obligatorios.</div>',
        }))
    if db.query(User).filter_by(username=username).first():
        return HTMLResponse(_render(request, "admin_usuarios.html", "usuarios", {
            "users_rows": _users_rows(db),
            "error_block": f'<div class="alert alert-danger mt-2">El usuario \'{username}\' ya existe.</div>',
        }))
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    db.add(User(username=username, hashed_password=hashed, is_active=True))
    db.commit()
    return RedirectResponse(f"/admin/usuarios?ok=Usuario+'{username}'+creado", status_code=303)


@router.get("/config", response_class=HTMLResponse)
def admin_config(request: Request, ok: str = "", db: Session = Depends(get_db)):
    if not _require_admin(request):
        return RedirectResponse("/login", status_code=303)
    export_limit = get_setting(db, "export_limit", "5000")
    return HTMLResponse(_render(request, "admin_config.html", "config", {
        "export_limit": export_limit,
        "ok_block": f'<div class="alert alert-success mt-2">{ok}</div>' if ok else "",
    }))


@router.post("/config/cambiar-password")
async def admin_cambiar_password(
    request: Request,
    password_actual: str = Form(...),
    password_nueva: str = Form(...),
    password_confirm: str = Form(...),
    db: Session = Depends(get_db),
):
    if not _require_admin(request):
        return RedirectResponse("/login", status_code=303)

    export_limit = get_setting(db, "export_limit", "5000")

    def _err(msg: str):
        return HTMLResponse(_render(request, "admin_config.html", "config", {
            "export_limit": export_limit,
            "error_block": f'<div class="alert alert-danger">{msg}</div>',
        }))

    if len(password_nueva) < 8:
        return _err("La nueva contraseña debe tener al menos 8 caracteres.")
    if password_nueva != password_confirm:
        return _err("La nueva contraseña y la confirmación no coinciden.")

    admin = db.query(User).filter_by(username="admin").first()
    if not admin or not bcrypt.checkpw(password_actual.encode(), admin.hashed_password.encode()):
        return _err("La contraseña actual no es correcta.")

    admin.hashed_password = bcrypt.hashpw(password_nueva.encode(), bcrypt.gensalt()).decode()
    db.commit()
    return RedirectResponse("/admin/config?ok=Contraseña+actualizada+correctamente", status_code=303)


@router.post("/config/guardar")
def admin_config_guardar(
    request: Request,
    export_limit: int = Form(...),
    db: Session = Depends(get_db),
):
    if not _require_admin(request):
        return RedirectResponse("/login", status_code=303)
    export_limit = max(100, min(50_000, export_limit))
    set_setting(db, "export_limit", str(export_limit))
    return RedirectResponse("/admin/config?ok=Configuración+guardada", status_code=303)


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


def _users_rows(db: Session) -> str:
    rows = ""
    for u in db.query(User).order_by(User.id).all():
        estado = "Activo" if u.is_active else "Inactivo"
        toggle_label = "Desactivar" if u.is_active else "Activar"
        rows += f"""
        <tr>
          <td style="padding-left:1rem;color:var(--tx-faint)">{u.id}</td>
          <td style="font-weight:500">{u.username}</td>
          <td><span class="badge {'bg-success' if u.is_active else 'bg-secondary'}">{estado}</span></td>
          <td>
            <form method="post" action="/admin/usuarios/{u.id}/toggle" style="display:inline">
              <button class="btn btn-sm btn-outline-secondary" type="submit"
                {'disabled' if u.username == 'admin' else ''}>{toggle_label}</button>
            </form>
          </td>
        </tr>"""
    return rows
