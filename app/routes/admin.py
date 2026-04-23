import bcrypt
import json
import os
import signal
import subprocess
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pathlib import Path
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Licitacion
from app.utils import _nav_context, get_setting, set_setting
from app.email_utils import send_test_email

SYNC_STATE_FILE  = Path("/root/licitmap/data/sync_state.json")
SYNC_PID_FILE    = Path("/root/licitmap/data/sync_pid.txt")
VENV_PYTHON      = Path("/root/licitmap/.venv/bin/python")
SYNC_SCRIPT_PY   = Path("/root/licitmap/scripts/sync.py")


def _sync_running() -> bool:
    if not SYNC_PID_FILE.exists():
        return False
    try:
        pid = int(SYNC_PID_FILE.read_text().strip())
        os.kill(pid, 0)
        # os.kill(pid, 0) succeeds for zombie processes too; check /proc stat
        stat = Path(f"/proc/{pid}/stat").read_text()
        if " Z " in stat or stat.split()[2] == "Z":
            SYNC_PID_FILE.unlink(missing_ok=True)
            return False
        return True
    except (ValueError, ProcessLookupError, PermissionError, FileNotFoundError):
        SYNC_PID_FILE.unlink(missing_ok=True)
        return False

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
    total_lics = db.query(Licitacion).count()

    sync_state = {}
    if SYNC_STATE_FILE.exists():
        try:
            sync_state = json.loads(SYNC_STATE_FILE.read_text())
        except Exception:
            pass

    last_sync   = sync_state.get("last_sync", "—")
    sync_nuevas = sync_state.get("nuevas", "—")
    sync_act    = sync_state.get("actualizadas", "—")
    sync_feeds  = sync_state.get("feeds", "—")

    return HTMLResponse(_render(request, "admin_dashboard.html", "dashboard", {
        "total_users":    str(total_users),
        "active_users":   str(active_users),
        "export_limit":   get_setting(db, "export_limit", "5000"),
        "total_lics":     f"{total_lics:,}".replace(",", "."),
        "sync_last":      last_sync,
        "sync_nuevas":    str(sync_nuevas),
        "sync_act":       str(sync_act),
        "sync_feeds":     str(sync_feeds),
    }))


@router.post("/sync")
async def admin_sync_now(request: Request):
    if not _require_admin(request):
        return JSONResponse({"error": "no autorizado"}, status_code=403)
    if _sync_running():
        return JSONResponse({"error": "Sync ya en curso"}, status_code=409)
    try:
        env = os.environ.copy()
        env["PYTHONPATH"] = "/root/licitmap"
        proc = subprocess.Popen(
            [str(VENV_PYTHON), str(SYNC_SCRIPT_PY), "--max-pages", "5"],
            stdout=open("/var/log/licitmap_sync.log", "a"),
            stderr=subprocess.STDOUT,
            cwd="/root/licitmap",
            start_new_session=True,
            env=env,
        )
        SYNC_PID_FILE.parent.mkdir(exist_ok=True)
        SYNC_PID_FILE.write_text(str(proc.pid))
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/sync/status")
async def admin_sync_status(request: Request):
    if not _require_admin(request):
        return JSONResponse({"error": "no autorizado"}, status_code=403)
    running = _sync_running()
    state = {}
    if SYNC_STATE_FILE.exists():
        try:
            state = json.loads(SYNC_STATE_FILE.read_text())
        except Exception:
            pass
    return JSONResponse({"running": running, **state})


@router.post("/sync/cancel")
async def admin_sync_cancel(request: Request):
    if not _require_admin(request):
        return JSONResponse({"error": "no autorizado"}, status_code=403)
    if not SYNC_PID_FILE.exists():
        return JSONResponse({"ok": False, "error": "Sin proceso activo"})
    try:
        pid = int(SYNC_PID_FILE.read_text().strip())
        os.kill(pid, signal.SIGTERM)
        SYNC_PID_FILE.unlink(missing_ok=True)
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


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


@router.post("/usuarios/{user_id}/email")
async def admin_cambiar_email(
    user_id: int,
    request: Request,
    email: str = Form(...),
    db: Session = Depends(get_db),
):
    if not _require_admin(request):
        return RedirectResponse("/login", status_code=303)
    user = db.query(User).filter_by(id=user_id).first()
    if not user or user.username == "admin":
        return RedirectResponse("/admin/usuarios", status_code=303)
    email = email.strip().lower()
    if not email:
        return HTMLResponse(_render(request, "admin_usuarios.html", "usuarios", {
            "users_rows": _users_rows(db),
            "error_block": '<div class="alert alert-danger mt-2">El correo no puede estar vacío.</div>',
        }))
    existing = db.query(User).filter(User.email == email, User.id != user_id).first()
    if existing:
        return HTMLResponse(_render(request, "admin_usuarios.html", "usuarios", {
            "users_rows": _users_rows(db),
            "error_block": f'<div class="alert alert-danger mt-2">El correo <strong>{email}</strong> ya está en uso por otro usuario.</div>',
        }))
    user.email = email
    db.commit()
    return RedirectResponse("/admin/usuarios?ok=Correo+actualizado", status_code=303)


@router.post("/usuarios/{user_id}/eliminar")
def admin_eliminar_usuario(user_id: int, request: Request, db: Session = Depends(get_db)):
    if not _require_admin(request):
        return RedirectResponse("/login", status_code=303)
    from app.models import Alerta, LicitacionSeguida
    user = db.query(User).filter_by(id=user_id).first()
    if user and user.username != "admin":
        db.query(Alerta).filter_by(user_id=user_id).delete()
        db.query(LicitacionSeguida).filter_by(user_id=user_id).delete()
        db.delete(user)
        db.commit()
        return RedirectResponse(f"/admin/usuarios?ok=Usuario+eliminado", status_code=303)
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
        "ok_block":   f'<div class="alert alert-success mb-3">{ok}</div>' if ok else "",
        "test_block": "",
    }))


@router.post("/config/correo/test")
async def admin_config_correo_test(
    request: Request,
    db: Session = Depends(get_db),
):
    if not _require_admin(request):
        return RedirectResponse("/login", status_code=303)

    def _correo_page(test_block: str) -> str:
        return _render(request, "admin_config_correo.html", "config", {
            "smtp_host":      get_setting(db, "smtp_host", ""),
            "smtp_port":      get_setting(db, "smtp_port", "587"),
            "smtp_user":      get_setting(db, "smtp_user", ""),
            "smtp_from":      get_setting(db, "smtp_from", ""),
            "smtp_pass_hint": "(ya configurada)" if get_setting(db, "smtp_pass", "") else "(no configurada)",
            "test_block":     test_block,
        })

    dest = get_setting(db, "smtp_user", "").strip()
    if not dest:
        block = (
            f'<div class="alert alert-warning d-flex align-items-center gap-2 mb-3">'
            f'No hay usuario SMTP configurado. Guarda la configuración primero.</div>'
        )
        return HTMLResponse(_correo_page(block))

    try:
        send_test_email(dest, db)
        block = (
            f'<div class="alert alert-success d-flex align-items-center gap-2 mb-3">'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24"'
            f' stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            f'<polyline points="20 6 9 17 4 12"/></svg>'
            f'Correo de prueba enviado a <strong>{dest}</strong></div>'
        )
    except Exception as e:
        block = (
            f'<div class="alert alert-danger d-flex align-items-center gap-2 mb-3">'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24"'
            f' stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            f'<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/>'
            f'<line x1="12" y1="16" x2="12.01" y2="16"/></svg>'
            f'Error al enviar: {e}</div>'
        )
    return HTMLResponse(_correo_page(block))


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
        is_admin = u.username == "admin"
        if is_admin:
            email_cell = '<span style="color:var(--tx-muted);font-size:0.8rem">—</span>'
        else:
            display = u.email or '<span style="color:var(--co-red);font-size:0.8rem">sin correo</span>'
            email_cell = f"""<span id="email-disp-{u.id}" style="font-size:0.85rem">{display}</span>
              <button type="button" onclick="lmEditEmail({u.id})" title="Cambiar correo"
                style="background:none;border:none;padding:0 0.3rem;cursor:pointer;color:var(--tx-faint);vertical-align:middle">
                <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" fill="none" viewBox="0 0 24 24"
                  stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                </svg>
              </button>
              <form id="email-form-{u.id}" method="post" action="/admin/usuarios/{u.id}/email"
                    style="display:none;margin-top:0.35rem">
                <div class="input-group input-group-sm">
                  <input type="email" name="email" value="{u.email or ''}"
                         class="form-control form-control-sm" required placeholder="nuevo@correo.com">
                  <button type="submit" class="btn btn-sm btn-primary">Guardar</button>
                  <button type="button" class="btn btn-sm btn-outline-secondary"
                          onclick="lmEditEmail({u.id})">✕</button>
                </div>
              </form>"""
        disabled = "disabled" if is_admin else ""
        confirm_js = f"return confirm('¿Eliminar al usuario {u.username}? Esta acción no se puede deshacer.')"
        rows += f"""
        <tr>
          <td style="padding-left:1rem;color:var(--tx-faint)">{u.id}</td>
          <td style="font-weight:500">{u.username}</td>
          <td style="font-size:0.85rem">{email_cell}</td>
          <td><span class="badge {'bg-success' if u.is_active else 'bg-secondary'}">{estado}</span></td>
          <td style="white-space:nowrap">
            <form method="post" action="/admin/usuarios/{u.id}/toggle" style="display:inline">
              <button class="btn btn-sm btn-outline-secondary" type="submit" {disabled}>{toggle_label}</button>
            </form>
            <form method="post" action="/admin/usuarios/{u.id}/eliminar" style="display:inline"
                  onsubmit="{confirm_js}">
              <button class="btn btn-sm btn-outline-danger" type="submit" {disabled}>Eliminar</button>
            </form>
          </td>
        </tr>"""
    return rows
