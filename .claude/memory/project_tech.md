---
name: Detalles técnicos LicitMap
description: Arquitectura, i18n, URLs, instalador, deploy systemd — actualizado 2026-04-24
type: project
originSessionId: 79a1f941-20f8-4d17-9a34-944531e2e52e
---

## Arquitectura de ficheros

```
main.py                              FastAPI app + I18nMiddleware + SessionMiddleware + routers
install.sh                           Instalador interactivo (defaults seguros)
uninstall.sh                         Desinstalador (-y para no-interactivo)
app/
  database.py                        SQLAlchemy + connect_args={"client_encoding":"utf8"}
  models.py                          User(tiene language VARCHAR(2)), Setting, Licitacion, Alerta, LicitacionSeguida
  i18n.py                            TRANSLATIONS dict ES/EN + I18nMiddleware + translate_html + get_lang_from_request
  utils.py                           _nav_context() devuelve (auth_block, busqueda_display, lang_selector); lang_selector_html()
  email_utils.py                     Emails con EMAIL_STRINGS ES/EN + param lang
  routes/
    home.py       GET / + APIs (ESTADOS/TIPOS/PRANGES usan placeholders {{t.x.y}})
    mapa.py       GET /map + APIs /api/map/* (sidebar items aún en español — PENDIENTE)
    analisis.py   GET /analytics + /api/analytics/data
    alertas.py    GET /alerts + /api/alerts/* (_build_* generan HTML español — PENDIENTE traducir)
    admin.py      /admin/* (prefix), /admin/users, /admin/settings/{export,email,security}
    auth.py       /login (email o usuario), /login/password, /login/codigo
    lang.py       GET/POST /lang/{es|en} — cookie lm_lang + actualiza user.language
    redirects.py  301 desde URLs españolas (/mapa → /map, /alertas → /alerts, etc.)
scripts/
  licitmap            CLI (bash, i18n ES/EN, runuser no sudo)
  sync.py             Flag --since-date + --max-pages, HISTORY_YEARS env var
  run_sync.sh         PYTHONPATH derivado de dirname
  check_alertas.py    sys.path relativo, pasa user.language a emails
deploy/
  licitmap.service    systemd unit con LANG=C.UTF-8, {{HOST}} placeholder (0.0.0.0 si no nginx)
  licitmap.nginx.conf Plantilla nginx
  licitmap.cron       Cron con LANG=C.UTF-8
static/data/
  ccaa.geojson, provincias.geojson, municipios.geojson (tracked, !important: .gitignore "/data/" no "data/")
  cpv_es.json, municipios_coords.json, world.geojson
```

## Sistema de templates (CRÍTICO)
- `Path("templates/X.html").read_text()` + `str.replace("{{key}}", value)`. NO Jinja2 (bug Py 3.13+).
- `re.sub(r"\{\{[a-z_]+\}\}", "", html)` al final de algunos renders (NO afecta a `{{t.x.y}}` porque tiene puntos).
- Middleware i18n reemplaza `{{t.key}}` con regex `[a-zA-Z0-9_.]+` (no admite `+`, por eso `prange.1m+` → key `prange.1mplus`).

## i18n — Gotchas críticos

1. **f-strings Python**: `{{t.xxx}}` en f-string produce `{t.xxx}` literal. Solución: `{{{{t.xxx}}}}` (4 llaves) o usar variable `x="{{t.xxx}}"` y `f"...{x}..."`.
2. **JSON responses** bypass middleware. Endpoints partial deben llamar `translate_html(frag, lang)` manualmente antes de meter en JSON.
3. **window.I18N** en base.html expone strings frecuentes para JS (mapa.map.tenders/active/legend, confirm.deleteUser/deleteAlert/unfollow, follow/unfollow).
4. **BD encoding**: `CREATE DATABASE ... ENCODING 'UTF8' TEMPLATE template0 LC_COLLATE 'C' LC_CTYPE 'C'` para evitar SQL_ASCII en LXC minimal.

## URLs (inglés con redirects 301)
```
/ /map /analytics /alerts /login /lang/{es|en}
/admin /admin/users /admin/settings/{export,email,security}
/api/map/{nombres,provincias,municipios} /api/map (con filtros)
/api/analytics/data /api/alerts/{seguidos,seguir,nueva,...}
```

Redirects viejos → nuevos en `app/routes/redirects.py` (301 para GET, 307 para APIs/POST preservando método).

## Infraestructura (instalación nueva 2026-04-24)

- **systemd**: `/etc/systemd/system/licitmap.service` — Environment LANG/LC_ALL/PYTHONIOENCODING=utf8, 2 workers uvicorn, bind 0.0.0.0 si no hay nginx
- **PostgreSQL**: nativo (default), Docker o externo. Siempre `ENCODING 'UTF8'`.
- **Logs**: `/var/log/licitmap.log` (app), `/var/log/licitmap_sync.log`, `/var/log/licitmap_alertas.log` — chown al user del servicio
- **Cron**: `/etc/cron.d/licitmap` con LANG=C.UTF-8
- **CLI**: `/usr/local/bin/licitmap` + symlink `/usr/bin/licitmap` (always in PATH — fix LXC Proxmox)
- **Config CLI**: `/etc/default/licitmap` con INSTALL_DIR, SYS_USER, APP_PORT

## Comandos frecuentes (nueva instalación)
```bash
licitmap status           # BD + servicio + último sync + URL
licitmap doctor           # diagnóstico completo
licitmap logs [sync]      # /var/log/licitmap.log o /var/log/licitmap_sync.log
licitmap sync --full      # sync completo (manual)
licitmap migrate          # ALTER TABLE idempotente (fallback si alguien no tiene users.language)
licitmap update           # git pull + pip install + restart
licitmap admin reset-password
# Reinstalación limpia completa:
bash /opt/licitmap/uninstall.sh -y && rm -rf ~/licitmap-dev && git clone https://github.com/Ivisor/licitmap-dev.git ~/licitmap-dev && bash ~/licitmap-dev/install.sh
```

## Modelos (resumen)

- **User**: id, username, hashed_password, email, otp_code, otp_expires_at, is_active, **language(VARCHAR 2, default "es")**
- **Licitacion**: id, atom_id, expediente, titulo, organo_contratacion, estado, presupuesto, fecha_publicacion, fecha_limite, tipo_contrato, comunidad_autonoma, pais, url, cpv, municipio, codigo_postal, provincia
- **Alerta**: user_id, nombre, tipo (newsletter|alerta|suscripcion), keywords (pipe), cpv_codes, tipo_contrato, comunidades, provincias, presupuesto_min/max, solo_activas, entidad_tipo/valor, frecuencia, dia_semana, hora_envio, activa
- **Setting**: key/value (SMTP, export limit, etc.)
- **LicitacionSeguida**: user_id, licitacion_id, notif_cambio_estado, notif_dias_vencimiento, last_estado
