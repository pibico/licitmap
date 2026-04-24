#!/bin/bash
# LicitMap — desinstalador interactivo / interactive uninstaller
# Ejecuta 'bash uninstall.sh' como root para limpiar una instalación.
set -euo pipefail

C_RESET=$'\033[0m'; C_BOLD=$'\033[1m'; C_RED=$'\033[31m'; C_GREEN=$'\033[32m'; C_YELLOW=$'\033[33m'; C_BLUE=$'\033[34m'
log()  { echo -e "${C_BLUE}▶${C_RESET} $*"; }
ok()   { echo -e "${C_GREEN}✓${C_RESET} $*"; }
warn() { echo -e "${C_YELLOW}⚠${C_RESET} $*"; }
die()  { echo -e "${C_RED}✗${C_RESET} $*" >&2; exit 1; }

[ "$EUID" -eq 0 ] || die "Debe ejecutarse como root."

# Lee config runtime si existe
INSTALL_DIR="/opt/licitmap"
SYS_USER="licitmap"
if [ -f /etc/default/licitmap ]; then
    # shellcheck source=/dev/null
    . /etc/default/licitmap
fi

ask_yn() {
    local prompt="$1"; local default="${2:-n}"; local reply hint="[y/N]"
    [ "$default" = "y" ] && hint="[Y/n]"
    read -r -p "$(echo -e "${C_BOLD}?${C_RESET} $prompt $hint: ")" reply
    reply="${reply:-$default}"
    [[ "$reply" =~ ^[YySs]$ ]]
}

echo -e "${C_BOLD}=== Desinstalación de LicitMap ===${C_RESET}"
echo "Se eliminará la instalación en: $INSTALL_DIR"
echo "Usuario del sistema: $SYS_USER"
echo
ask_yn "¿Continuar?" "n" || { log "Cancelado."; exit 0; }

# 1. Servicio systemd
log "Parando y deshabilitando el servicio…"
systemctl stop licitmap 2>/dev/null || true
systemctl disable licitmap 2>/dev/null || true
rm -f /etc/systemd/system/licitmap.service
systemctl daemon-reload
ok "Servicio systemd eliminado."

# 2. Ficheros de configuración
log "Eliminando config y cron…"
rm -f /etc/cron.d/licitmap
rm -f /etc/default/licitmap
rm -f /usr/local/bin/licitmap /usr/bin/licitmap
ok "Config, cron y CLI eliminados."

# 3. Base de datos
echo
DB_URL=$(grep -E '^DATABASE_URL=' "$INSTALL_DIR/.env" 2>/dev/null | cut -d= -f2- || true)
echo "DATABASE_URL detectada: ${DB_URL:-(no encontrada)}"
if ask_yn "¿Eliminar la base de datos y el rol PostgreSQL?" "n"; then
    if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -q '^licitmap-db$'; then
        log "Contenedor Docker licitmap-db…"
        docker rm -f licitmap-db 2>/dev/null || true
        docker volume rm licitmap-pgdata 2>/dev/null || true
        ok "Contenedor y volumen Docker eliminados."
    elif systemctl is-active --quiet postgresql 2>/dev/null; then
        log "PostgreSQL nativo…"
        runuser -u postgres -- psql -c "DROP DATABASE IF EXISTS licitmap;" 2>/dev/null || true
        runuser -u postgres -- psql -c "DROP USER IF EXISTS licitmap;" 2>/dev/null || true
        ok "BD y rol nativo eliminados."
    else
        warn "No se detectó Docker ni PostgreSQL nativo. Limpia la BD manualmente si es externa."
    fi
fi

# 4. Logs
if ask_yn "¿Eliminar logs /var/log/licitmap*.log?" "y"; then
    rm -f /var/log/licitmap*.log
    ok "Logs eliminados."
fi

# 5. Usuario del sistema
if id "$SYS_USER" &>/dev/null; then
    if ask_yn "¿Eliminar usuario del sistema '$SYS_USER'?" "y"; then
        userdel -r "$SYS_USER" 2>/dev/null || userdel "$SYS_USER" 2>/dev/null || true
        ok "Usuario '$SYS_USER' eliminado."
    fi
fi

# 6. Directorio de instalación
if [ -d "$INSTALL_DIR" ]; then
    if ask_yn "¿Eliminar directorio de instalación $INSTALL_DIR?" "y"; then
        rm -rf "$INSTALL_DIR"
        ok "Directorio eliminado."
    fi
fi

# 7. Git safe.directory
git config --system --unset-all safe.directory 2>/dev/null || true

# 8. Nginx (si hay sitio)
if [ -f /etc/nginx/sites-enabled/licitmap ]; then
    if ask_yn "¿Eliminar configuración nginx de LicitMap?" "y"; then
        rm -f /etc/nginx/sites-enabled/licitmap /etc/nginx/sites-available/licitmap
        systemctl reload nginx 2>/dev/null || true
        ok "Nginx limpio."
    fi
fi

echo
ok "Desinstalación completada."
echo
echo "Los paquetes del sistema (python, postgresql, docker, nginx, certbot) no se han"
echo "desinstalado para no afectar a otros servicios. Si quieres quitarlos, usa apt remove."
