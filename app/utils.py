from fastapi import Request


def _nav_context(request: Request) -> tuple[str, str]:
    """Devuelve (nav_auth_block_html, nav_busqueda_display_style)."""
    username = request.session.get("username", "")
    if username:
        admin_link = (
            '<a href="/admin/usuarios" class="lm-nav-logout">Usuarios</a>'
            if username == "admin"
            else ""
        )
        auth_block = (
            f'<div class="lm-nav-user">'
            f'<span class="lm-nav-username">{username}</span>'
            f'{admin_link}'
            f'<a href="/logout" class="lm-nav-logout">Salir</a>'
            f'</div>'
        )
        return auth_block, ""
    return '<a href="/login" class="lm-btn-login">Iniciar sesión</a>', "display:none"
