#!/bin/bash
# LicitMap — instalador interactivo
# Compatible con Debian 12+ y Ubuntu 22.04+
set -euo pipefail

# ─── Helpers ────────────────────────────────────────────────────────────
C_RESET="\033[0m"; C_BOLD="\033[1m"; C_RED="\033[31m"; C_GREEN="\033[32m"; C_YELLOW="\033[33m"; C_BLUE="\033[34m"
log()   { echo -e "${C_BLUE}▶${C_RESET} $*"; }
ok()    { echo -e "${C_GREEN}✓${C_RESET} $*"; }
warn()  { echo -e "${C_YELLOW}⚠${C_RESET} $*"; }
err()   { echo -e "${C_RED}✗${C_RESET} $*" >&2; }
die()   { err "$*"; exit 1; }

ask() {
    local prompt="$1"; local default="${2:-}"; local reply
    if [ -n "$default" ]; then
        read -r -p "$(echo -e "${C_BOLD}?${C_RESET} $prompt [$default]: ")" reply
        echo "${reply:-$default}"
    else
        read -r -p "$(echo -e "${C_BOLD}?${C_RESET} $prompt: ")" reply
        echo "$reply"
    fi
}

ask_secret() {
    local prompt="$1"; local reply
    read -r -s -p "$(echo -e "${C_BOLD}?${C_RESET} $prompt: ")" reply
    echo >&2
    echo "$reply"
}

ask_yn() {
    local prompt="$1"; local default="${2:-n}"; local reply
    local hint="[y/N]"; [ "$default" = "y" ] && hint="[Y/n]"
    read -r -p "$(echo -e "${C_BOLD}?${C_RESET} $prompt $hint: ")" reply
    reply="${reply:-$default}"
    [[ "$reply" =~ ^[YySs]$ ]]
}

ask_choice() {
    local prompt="$1"; shift
    local default="$1"; shift
    local -a options=("$@")
    local i=1
    echo -e "${C_BOLD}?${C_RESET} $prompt" >&2
    for opt in "${options[@]}"; do
        echo "   $i) $opt" >&2
        ((i++))
    done
    local reply
    read -r -p "   Elige [1-${#options[@]}] [$default]: " reply
    echo "${reply:-$default}"
}

# ─── Checks previos ─────────────────────────────────────────────────────
[ "$EUID" -eq 0 ] || die "El instalador debe ejecutarse como root (sudo)."

if [ -f /etc/os-release ]; then
    . /etc/os-release
    case "$ID" in
        debian|ubuntu) ok "Sistema detectado: $PRETTY_NAME" ;;
        *) warn "Sistema no probado ($PRETTY_NAME). Continúo bajo tu responsabilidad." ;;
    esac
else
    warn "No se pudo identificar el sistema operativo."
fi

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
log "Repositorio origen: $REPO_DIR"
echo

# ─── Preguntas ──────────────────────────────────────────────────────────
echo -e "${C_BOLD}=== Configuración de la instalación ===${C_RESET}"
INSTALL_DIR=$(ask "Ruta de instalación" "/opt/licitmap")
SYS_USER=$(ask "Usuario del sistema que ejecutará el servicio" "licitmap")
APP_PORT=$(ask "Puerto interno de la app (detrás de nginx)" "8000")
HISTORY_YEARS=$(ask "Años de histórico a mantener (la purga diaria borra lo anterior)" "5")

echo
echo -e "${C_BOLD}=== Credenciales del administrador ===${C_RESET}"
ADMIN_USER=$(ask "Usuario admin" "admin")
ADMIN_EMAIL=$(ask "Correo del admin (para notificaciones y recuperación)" "")
DEFAULT_PASS=0
while true; do
    ADMIN_PASS=$(ask_secret "Contraseña del admin (enter para usar '$ADMIN_USER')")
    if [ -z "$ADMIN_PASS" ]; then
        ADMIN_PASS="$ADMIN_USER"
        DEFAULT_PASS=1
        break
    fi
    ADMIN_PASS2=$(ask_secret "Repite la contraseña")
    [ "$ADMIN_PASS" = "$ADMIN_PASS2" ] && break
    warn "Las contraseñas no coinciden. Inténtalo de nuevo."
done

echo
echo -e "${C_BOLD}=== PostgreSQL ===${C_RESET}"
DB_CHOICE=$(ask_choice "¿Cómo quieres la base de datos?" "2" \
    "Docker (aislado en contenedor, requiere docker.io)" \
    "Nativo (apt install postgresql, corre en el host)" \
    "Externo (conexión a un PostgreSQL ya existente)")

case "$DB_CHOICE" in
    1) DB_MODE="docker" ;;
    2) DB_MODE="nativo" ;;
    3) DB_MODE="externo" ;;
    *) die "Opción inválida." ;;
esac

if [ "$DB_MODE" = "externo" ]; then
    DB_URL=$(ask "DATABASE_URL completa (postgresql://user:pass@host:port/dbname)" "")
    [ -z "$DB_URL" ] && die "DATABASE_URL es obligatoria."
else
    DB_NAME=$(ask "Nombre de la base de datos" "licitmap")
    DB_USER=$(ask "Usuario de la base de datos" "licitmap")
    DB_PASS=$(ask_secret "Contraseña de la base de datos (enter para autogenerar)")
    [ -z "$DB_PASS" ] && DB_PASS="$(openssl rand -base64 24 | tr -d '/=+' | cut -c1-24)" && ok "Generada automáticamente."
    if [ "$DB_MODE" = "docker" ]; then
        DB_URL="postgresql://${DB_USER}:${DB_PASS}@127.0.0.1:5432/${DB_NAME}"
    else
        DB_URL="postgresql://${DB_USER}:${DB_PASS}@127.0.0.1:5432/${DB_NAME}"
    fi
fi

echo
echo -e "${C_BOLD}=== Nginx ===${C_RESET}"
if ask_yn "¿Configurar nginx como proxy inverso?" "n"; then
    USE_NGINX=1
    DOMAIN=$(ask "Dominio (ej. licitmap.example.com, deja vacío para usar IP)" "")
    USE_SSL=0
    if [ -n "$DOMAIN" ] && ask_yn "¿Obtener certificado SSL con Let's Encrypt (certbot)?" "y"; then
        USE_SSL=1
    fi
else
    USE_NGINX=0
fi

echo
echo -e "${C_BOLD}=== SMTP (opcional) ===${C_RESET}"
USE_SMTP=0
SMTP_HOST=""; SMTP_PORT=""; SMTP_USER=""; SMTP_PASS=""; SMTP_FROM=""
if ask_yn "¿Configurar correo SMTP ahora? (se puede hacer luego desde /admin/config)" "n"; then
    USE_SMTP=1
    SMTP_HOST=$(ask "Servidor SMTP" "smtp.gmail.com")
    SMTP_PORT=$(ask "Puerto SMTP (465 SSL, 587 STARTTLS)" "465")
    SMTP_USER=$(ask "Usuario SMTP" "")
    SMTP_PASS=$(ask_secret "Contraseña SMTP")
    SMTP_FROM=$(ask "Dirección remitente (From)" "$SMTP_USER")
fi

echo
echo -e "${C_BOLD}=== Carga inicial de datos ===${C_RESET}"
LOAD_CHOICE=$(ask_choice "¿Cuándo cargar los datos históricos de PLACSP?" "3" \
    "Ahora (al finalizar la instalación, tarda según años)" \
    "En el próximo ciclo de cron (cada 10 min, gradual)" \
    "No cargar nada — solo preparar el servicio")

case "$LOAD_CHOICE" in
    1) LOAD_NOW=1 ;;
    2) LOAD_NOW=0 ;;
    3) LOAD_NOW=0; NO_DATA=1 ;;
    *) die "Opción inválida." ;;
esac

# ─── Resumen y confirmación ─────────────────────────────────────────────
echo
echo -e "${C_BOLD}=== Resumen ===${C_RESET}"
echo "  Directorio:       $INSTALL_DIR"
echo "  Usuario sistema:  $SYS_USER"
echo "  Puerto app:       $APP_PORT"
echo "  Años histórico:   $HISTORY_YEARS"
echo "  Admin:            $ADMIN_USER <$ADMIN_EMAIL>"
echo "  PostgreSQL:       $DB_MODE"
echo "  Nginx:            $([ $USE_NGINX -eq 1 ] && echo "sí${DOMAIN:+ (${DOMAIN})}$([ $USE_SSL -eq 1 ] && echo ' + SSL')" || echo 'no')"
echo "  SMTP:             $([ $USE_SMTP -eq 1 ] && echo "sí ($SMTP_HOST:$SMTP_PORT)" || echo 'no')"
echo "  Carga inicial:    $([ $LOAD_NOW -eq 1 ] && echo 'ahora' || echo 'diferida')"
echo
ask_yn "¿Proceder con la instalación?" "y" || { log "Instalación cancelada."; exit 0; }

# ─── Instalación ────────────────────────────────────────────────────────
log "Actualizando índice de paquetes…"
apt-get update -qq

log "Instalando dependencias base…"
PKGS="python3 python3-venv python3-pip git cron openssl"
[ "$DB_MODE" = "docker" ]  && PKGS="$PKGS docker.io"
[ "$DB_MODE" = "nativo" ]  && PKGS="$PKGS postgresql"
[ $USE_NGINX -eq 1 ]       && PKGS="$PKGS nginx"
[ "${USE_SSL:-0}" -eq 1 ]  && PKGS="$PKGS certbot python3-certbot-nginx"
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq $PKGS >/dev/null
ok "Paquetes instalados."

# Usuario del sistema
if ! id "$SYS_USER" &>/dev/null; then
    useradd --system --home-dir "$INSTALL_DIR" --shell /usr/sbin/nologin "$SYS_USER"
    ok "Usuario del sistema '$SYS_USER' creado."
else
    ok "Usuario '$SYS_USER' ya existe."
fi

# Copia del código
if [ "$REPO_DIR" != "$INSTALL_DIR" ]; then
    log "Copiando código a $INSTALL_DIR…"
    mkdir -p "$INSTALL_DIR"
    cp -rT "$REPO_DIR" "$INSTALL_DIR"
fi
mkdir -p "$INSTALL_DIR/data"

# venv + deps
log "Creando entorno virtual y dependencias Python…"
python3 -m venv "$INSTALL_DIR/.venv"
"$INSTALL_DIR/.venv/bin/pip" install -q --upgrade pip
"$INSTALL_DIR/.venv/bin/pip" install -q -r "$INSTALL_DIR/requirements.txt"
ok "Dependencias Python instaladas."

# Base de datos
case "$DB_MODE" in
    docker)
        log "Configurando contenedor Docker licitmap-db…"
        systemctl enable --now docker >/dev/null
        if docker ps -a --format '{{.Names}}' | grep -q '^licitmap-db$'; then
            warn "Contenedor licitmap-db ya existe — no se recrea. Para rehacerlo: docker rm -f licitmap-db"
        else
            docker run -d --name licitmap-db --restart unless-stopped \
                -p 127.0.0.1:5432:5432 \
                -v licitmap-pgdata:/var/lib/postgresql/data \
                -e "POSTGRES_DB=$DB_NAME" \
                -e "POSTGRES_USER=$DB_USER" \
                -e "POSTGRES_PASSWORD=$DB_PASS" \
                postgres:17 >/dev/null
            ok "Contenedor licitmap-db lanzado."
            log "Esperando a que PostgreSQL acepte conexiones…"
            for _ in {1..30}; do
                docker exec licitmap-db pg_isready -U "$DB_USER" -d "$DB_NAME" &>/dev/null && break
                sleep 1
            done
        fi
        ;;
    nativo)
        log "Configurando PostgreSQL nativo…"
        systemctl enable --now postgresql >/dev/null
        sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1 \
            || sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';" >/dev/null
        sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1 \
            || sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" >/dev/null
        ok "PostgreSQL nativo listo."
        ;;
    externo)
        log "Usando PostgreSQL externo — comprobando conexión…"
        "$INSTALL_DIR/.venv/bin/python" -c "from sqlalchemy import create_engine; create_engine('$DB_URL').connect().close()" \
            || die "No se puede conectar a la BD externa. Revisa DATABASE_URL."
        ok "Conexión a BD externa verificada."
        ;;
esac

# .env
log "Generando .env…"
SECRET_KEY="$(openssl rand -base64 48 | tr -d '/=+' | cut -c1-48)"
cat > "$INSTALL_DIR/.env" <<EOF
# Generado por install.sh el $(date -u +%Y-%m-%dT%H:%M:%SZ)
DATABASE_URL=$DB_URL
SECRET_KEY=$SECRET_KEY
HISTORY_YEARS=$HISTORY_YEARS
EOF
chmod 600 "$INSTALL_DIR/.env"
ok ".env creado (permisos 600)."

# Permisos
chown -R "$SYS_USER:$SYS_USER" "$INSTALL_DIR"
chmod +x "$INSTALL_DIR/scripts/run_sync.sh"

# Ficheros de log (writables por el usuario del servicio)
for f in /var/log/licitmap.log /var/log/licitmap_sync.log /var/log/licitmap_alertas.log; do
    touch "$f"
    chown "$SYS_USER:$SYS_USER" "$f"
    chmod 644 "$f"
done

# Inicialización de la BD + admin + settings
log "Creando esquema y usuario admin en la BD…"
"$INSTALL_DIR/.venv/bin/python" - <<PYEOF
import os, sys
sys.path.insert(0, "$INSTALL_DIR")
os.chdir("$INSTALL_DIR")
import bcrypt
from app.database import engine, SessionLocal, Base
from app.models import User, Setting
import app.models  # noqa: registra modelos

Base.metadata.create_all(bind=engine)

db = SessionLocal()
try:
    if not db.query(User).filter_by(username="$ADMIN_USER").first():
        hashed = bcrypt.hashpw("$ADMIN_PASS".encode(), bcrypt.gensalt()).decode()
        admin = User(username="$ADMIN_USER", hashed_password=hashed, email="$ADMIN_EMAIL" or None, is_active=True)
        db.add(admin)

    defaults = {
        "export_max_rows": "10000",
        "otp_ttl_min": "15",
    }
    if $USE_SMTP == 1:
        defaults.update({
            "smtp_host": "$SMTP_HOST",
            "smtp_port": "$SMTP_PORT",
            "smtp_user": "$SMTP_USER",
            "smtp_pass": "$SMTP_PASS",
            "smtp_from": "$SMTP_FROM",
        })
    for k, v in defaults.items():
        if not db.query(Setting).filter_by(key=k).first():
            db.add(Setting(key=k, value=v))
    db.commit()
finally:
    db.close()
print("OK")
PYEOF
ok "BD inicializada, admin creado."

# Config runtime para el CLI
log "Registrando configuración en /etc/default/licitmap…"
cat > /etc/default/licitmap <<EOF
# Generado por install.sh — usado por /usr/local/bin/licitmap
INSTALL_DIR=$INSTALL_DIR
SYS_USER=$SYS_USER
APP_PORT=$APP_PORT
EOF
chmod 644 /etc/default/licitmap

# CLI
log "Instalando CLI en /usr/local/bin/licitmap…"
install -m 755 "$INSTALL_DIR/scripts/licitmap" /usr/local/bin/licitmap
ok "CLI disponible: ejecuta 'licitmap help'."

# systemd
log "Instalando unidad systemd…"
# Si hay nginx delante, la app escucha solo en loopback; si no, en todas las interfaces
BIND_HOST="127.0.0.1"
[ $USE_NGINX -eq 0 ] && BIND_HOST="0.0.0.0"
sed -e "s|{{USER}}|$SYS_USER|g" \
    -e "s|{{INSTALL_DIR}}|$INSTALL_DIR|g" \
    -e "s|{{PORT}}|$APP_PORT|g" \
    -e "s|{{HOST}}|$BIND_HOST|g" \
    "$INSTALL_DIR/deploy/licitmap.service" > /etc/systemd/system/licitmap.service
systemctl daemon-reload
systemctl enable --now licitmap >/dev/null
ok "Servicio licitmap iniciado vía systemd (escucha en ${BIND_HOST}:${APP_PORT})."

# Nginx + SSL
if [ $USE_NGINX -eq 1 ]; then
    log "Configurando nginx…"
    SERVER_NAME="${DOMAIN:-_}"
    sed -e "s|{{DOMAIN}}|$SERVER_NAME|g" \
        -e "s|{{INSTALL_DIR}}|$INSTALL_DIR|g" \
        -e "s|{{PORT}}|$APP_PORT|g" \
        "$INSTALL_DIR/deploy/licitmap.nginx.conf" > /etc/nginx/sites-available/licitmap
    ln -sf /etc/nginx/sites-available/licitmap /etc/nginx/sites-enabled/licitmap
    [ -f /etc/nginx/sites-enabled/default ] && rm /etc/nginx/sites-enabled/default
    nginx -t >/dev/null && systemctl reload nginx
    ok "Nginx configurado."

    if [ "${USE_SSL:-0}" -eq 1 ]; then
        log "Obteniendo certificado SSL con certbot…"
        certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$ADMIN_EMAIL" --redirect || warn "Certbot falló — ejecútalo manualmente: certbot --nginx -d $DOMAIN"
    fi
fi

# Cron
log "Instalando cron…"
sed -e "s|{{USER}}|$SYS_USER|g" \
    -e "s|{{INSTALL_DIR}}|$INSTALL_DIR|g" \
    "$INSTALL_DIR/deploy/licitmap.cron" > /etc/cron.d/licitmap
chmod 644 /etc/cron.d/licitmap
ok "Cron instalado en /etc/cron.d/licitmap."

# Carga inicial
if [ $LOAD_NOW -eq 1 ]; then
    log "Lanzando carga inicial ($HISTORY_YEARS años)…"
    SINCE_DATE="$(date -d "$HISTORY_YEARS years ago" +%Y-%m-%d)"
    sudo -u "$SYS_USER" bash -c "cd '$INSTALL_DIR' && PYTHONPATH='$INSTALL_DIR' .venv/bin/python scripts/sync.py --force --since-date $SINCE_DATE" \
        || warn "La carga inicial falló. Revisa /var/log/licitmap_sync.log y lánzala manualmente."
fi

# ─── Final ──────────────────────────────────────────────────────────────
echo
ok "Instalación completada."
echo
echo -e "${C_BOLD}Comandos útiles:${C_RESET}"
echo "  licitmap status       Estado del servicio, BD y último sync"
echo "  licitmap logs         Ver logs en vivo"
echo "  licitmap sync         Lanzar sync manual"
echo "  licitmap help         Lista completa de comandos"
echo
echo -e "${C_BOLD}Acceso:${C_RESET}"
if [ $USE_NGINX -eq 1 ] && [ -n "$DOMAIN" ]; then
    PROTO="http"; [ "$USE_SSL" = "1" ] && PROTO="https"
    echo "  URL:          ${PROTO}://${DOMAIN}"
else
    LAN_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
    echo "  Local:        http://127.0.0.1:$APP_PORT"
    [ -n "$LAN_IP" ] && echo "  LAN:          http://${LAN_IP}:${APP_PORT}"
fi
echo "  Config:       $INSTALL_DIR/.env"
echo
if [ $DEFAULT_PASS -eq 1 ]; then
    echo -e "${C_YELLOW}⚠${C_RESET}  Usuario: ${C_BOLD}$ADMIN_USER${C_RESET}  ·  Contraseña: ${C_BOLD}$ADMIN_USER${C_RESET} (por defecto)"
    echo -e "   ${C_YELLOW}Cámbiala cuanto antes:${C_RESET}"
    echo -e "     · Desde la web:      Inicia sesión y ve a ${C_BOLD}Admin → Configuración → Seguridad${C_RESET}"
    echo -e "     · Desde la terminal: ${C_BOLD}sudo licitmap admin reset-password${C_RESET}"
else
    echo -e "  Accede con usuario ${C_BOLD}$ADMIN_USER${C_RESET} y la contraseña que configuraste."
fi
