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


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    if not _require_admin(request):
        return RedirectResponse("/login", status_code=303)
    total_users = db.query(User).count()
    active_users = db.query(User).filter_by(is_active=True).count()
    return HTMLResponse(_render(request, "admin_dashboard.html", "dashboard", {
        "total_users": str(total_users),
        "active_users": str(active_users),
        "export_limit": get_setting(db, "export_limit", "5000"),
    }))


# ── Usuarios ──────────────────────────────────────────────────────────────────

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
    email: str = Form(...),
    db: Session = Depends(get_db),
):
    if not _require_admin(request):
        return RedirectResponse("/login", status_code=303)
    username = username.strip().lower()
    email = email.strip().lower()

    def _err(msg):
        return HTMLResponse(_render(request, "admin_usuarios.html", "usuarios", {
            "users_rows": _users_rows(db),
            "error_block": f'<div class="alert alert-danger mt-2">{msg}</div>',
        }))

    if not username or not email:
        return _err("Usuario y correo electrónico son obligatorios.")
    if db.query(User).filter_by(username=username).first():
        return _err(f"El usuario '{username}' ya existe.")
    if db.query(User).filter_by(email=email).first():
        return _err(f"El correo '{email}' ya está registrado.")

    db.add(User(username=username, email=email, is_active=True))
    db.commit()
    return RedirectResponse(f"/admin/usuarios?ok=Usuario '{username}' creado", status_code=303)


@router.post("/usuarios/{user_id}/toggle")
def admin_toggle_usuario(user_id: int, request: Request, db: Session = Depends(get_db)):
    if not _require_admin(request):
        return RedirectResponse("/login", status_code=303)
    user = db.query(User).filter_by(id=user_id).first()
    if user and user.username != "admin":
        user.is_active = not user.is_active
        db.commit()
    return RedirectResponse("/admin/usuarios", status_code=303)


# ── Configuración: redirige a primera pestaña ─────────────────────────────────

@router.get("/config", response_class=HTMLResponse)
def admin_config_redirect(request: Request):
    if not _require_admin(request):
        return RedirectResponse("/login", status_code=303)
    return RedirectResponse("/admin/config/exportacion", status_code=303)


# ── Config / Exportación ──────────────────────────────────────────────────────

@router.get("/config/exportacion", response_class=HTMLResponse)
def admin_config_exportacion(request: Request, ok: str = "", db: Session = Depends(get_db)):
    if not _require_admin(request):
        return RedirectResponse("/login", status_code=303)
    return HTMLResponse(_render(request, "admin_config_exportacion.html", "config", {
        "export_limit": get_setting(db, "export_limit", "5000"),
        "ok_block": f'<div class="alert alert-success mb-3">{ok}</div>' if ok else "",
    }))


@router.post("/config/exportacion")
def admin_config_exportacion_post(
    request: Request, export_limit: int = Form(...), db: Session = Depends(get_db)
):
    if not _require_admin(request):
        return RedirectResponse("/login", status_code=303)
    set_setting(db, "export_limit", str(max(100, min(50_000, export_limit))))
    return RedirectResponse("/admin/config/exportacion?ok=Límite+guardado", status_code=303)


# ── Config / Correo SMTP ──────────────────────────────────────────────────────

@router.get("/config/correo", response_class=HTMLResponse)
def admin_config_correo(request: Request, ok: str = "", db: Session = Depends(get_db)):
    if not _require_admin(request):
        return RedirectResponse("/login", status_code=303)
    return HTMLResponse(_render(request, "admin_config_correo.html", "config", {
        "smtp_host":      get_setting(db, "smtp_host", ""),
        "smtp_port":      get_setting(db, "smtp_port", "587"),
        "smtp_user":      get_setting(db, "smtp_user", ""),
        "smtp_from":      get_setting(db, "smtp_from", ""),
        "smtp_pass_hint": "(ya configurada)" if get_setting(db, "smtp_pass", "") else "(no configurada)",
        "ok_block": f'<div class="alert alert-success mb-3">{ok}</div>' if ok else "",
    }))


@router.post("/config/correo")
async def admin_config_correo_post(
    request: Request,
    smtp_host: str = Form(""),
    smtp_port: int = Form(587),
    smtp_user: str = Form(""),
    smtp_pass: str = Form(""),
    smtp_from: str = Form(""),
    db: Session = Depends(get_db),
):
    if not _require_admin(request):
        return RedirectResponse("/login", status_code=303)
    set_setting(db, "smtp_host", smtp_host.strip())
    set_setting(db, "smtp_port", str(max(1, min(65535, smtp_port))))
    set_setting(db, "smtp_user", smtp_user.strip())
    if smtp_pass.strip():
        set_setting(db, "smtp_pass", smtp_pass.strip())
    set_setting(db, "smtp_from", smtp_from.strip())
    return RedirectResponse("/admin/config/correo?ok=Configuración+SMTP+guardada", status_code=303)


# ── Config / Seguridad ────────────────────────────────────────────────────────

@router.get("/config/seguridad", response_class=HTMLResponse)
def admin_config_seguridad(request: Request, ok: str = "", db: Session = Depends(get_db)):
    if not _require_admin(request):
        return RedirectResponse("/login", status_code=303)
    return HTMLResponse(_render(request, "admin_config_seguridad.html", "config", {
        "ok_block": f'<div class="alert alert-success mb-3">{ok}</div>' if ok else "",
    }))


@router.post("/config/seguridad")
async def admin_config_seguridad_post(
    request: Request,
    password_actual: str = Form(...),
    password_nueva: str = Form(...),
    password_confirm: str = Form(...),
    db: Session = Depends(get_db),
):
    if not _require_admin(request):
        return RedirectResponse("/login", status_code=303)

    def _err(msg):
        return HTMLResponse(_render(request, "admin_config_seguridad.html", "config", {
            "error_block": f'<div class="alert alert-danger mb-3">{msg}</div>',
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
    return RedirectResponse("/admin/config/seguridad?ok=Contraseña+actualizada", status_code=303)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _users_rows(db: Session) -> str:
    rows = ""
    for u in db.query(User).order_by(User.id).all():
        estado = "Activo" if u.is_active else "Inactivo"
        toggle_label = "Desactivar" if u.is_active else "Activar"
        email_cell = (
            '<span style="color:var(--tx-muted);font-size:0.8rem">—</span>'
            if u.username == "admin"
            else (u.email or '<span style="color:var(--co-red);font-size:0.8rem">sin correo</span>')
        )
        rows += f"""
        <tr>
          <td style="padding-left:1rem;color:var(--tx-faint)">{u.id}</td>
          <td style="font-weight:500">{u.username}</td>
          <td style="font-size:0.85rem">{email_cell}</td>
          <td><span class="badge {'bg-success' if u.is_active else 'bg-secondary'}">{estado}</span></td>
          <td>
            <form method="post" action="/admin/usuarios/{u.id}/toggle" style="display:inline">
              <button class="btn btn-sm btn-outline-secondary" type="submit"
                {'disabled' if u.username == 'admin' else ''}>{toggle_label}</button>
            </form>
          </td>
        </tr>"""
    return rows
