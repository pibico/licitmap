---
name: Estado del proyecto LicitMap
description: Stack actual, repo dev/público, instalador, i18n en curso — actualizado 2026-04-24
type: project
originSessionId: 0a24a54b-07be-4428-9146-e319cc5ab3d6
---

## Repos (abril 2026)

- **Dev (privado)**: `git@github.com:Ivisor/licitmap-dev.git`
- **Público** (pendiente de crear): `Ivisor/licitmap` en GitHub. El usuario renombró el antiguo privado `licitmap` → `licitmap-dev`. Aún no existe el público.
- Último commit: `87a013a` · `main`

Stack: FastAPI + PostgreSQL 17 + Bootstrap 5. Prod antigua en `https://ivan.pibico.es` (usa supervisor). La producción NUEVA es un LXC de Proxmox (`10.20.0.90:8000` o similar) instalado con `install.sh` bajo systemd.

## Instalación nueva (2026-04-24)

- **`install.sh`** en la raíz del repo: instalador interactivo con defaults seguros. PostgreSQL nativo por defecto, sin nginx, contraseña admin = `admin` si se deja vacía (aviso al final).
- **`uninstall.sh -y`** en la raíz: desinstalación no-interactiva (para reinstalación limpia scriptable). Borra systemd unit, cron, /etc/default/licitmap, CLI (both /usr/local/bin y /usr/bin), /opt/licitmap, BD (nativa/docker), usuario del sistema, nginx si estaba.
- **Ruta de instalación**: `/opt/licitmap`, usuario del sistema `licitmap`.
- **Proceso administra**: systemd (`licitmap.service`), no supervisor. Logs en `/var/log/licitmap.log` via `StandardOutput=append:` en el unit.
- **CLI `licitmap`**: se instala en `/usr/local/bin/licitmap` + symlink `/usr/bin/licitmap` (siempre en PATH, incluso en shells LXC sin bash.bashrc). Comandos: status, start, stop, restart, logs [app|sync|alertas], sync [--full|--since], url, stats, config, admin reset-password, update, version, help, doctor, migrate.
- **Config del CLI**: `/etc/default/licitmap` con INSTALL_DIR, SYS_USER, APP_PORT.
- **`licitmap doctor`** hace diagnóstico completo de la instalación (BD, servicio, puerto, locales UTF-8 en systemd, CLI en PATH, errores recientes).

### Bugs del LXC minimal (Proxmox) ya parcheados en install.sh

- **UTF-8**: `deploy/licitmap.service` tiene `Environment=LANG=C.UTF-8`, `LC_ALL=C.UTF-8`, `PYTHONIOENCODING=utf-8`. `deploy/licitmap.cron` también. `app/database.py` fuerza `connect_args={"client_encoding": "utf8"}`.
- **BD UTF-8**: `CREATE DATABASE ... ENCODING 'UTF8' TEMPLATE template0 LC_COLLATE 'C' LC_CTYPE 'C'` (sin esto PostgreSQL inicia con encoding SQL_ASCII si el locale no está generado, explota con ñ/acentos).
- **Idempotencia**: si el rol PG existe, hace `ALTER USER WITH PASSWORD` (no falla). Docker: si el container existe, extrae la password del env y sincroniza `.env`.
- **git safe.directory** + **curl** añadidos al apt install.

## Idioma (i18n) — en curso

### Arquitectura

- **`app/i18n.py`**: `TRANSLATIONS` dict `{es, en}`, función `t(key, lang)`, regex `{{t.xxx.yyy}}` (chars `[a-zA-Z0-9_.]`, **sin `+`** — `1m+` debe mapearse a key `1mplus`).
- **`I18nMiddleware`** en `main.py`: procesa respuestas HTML y traduce placeholders.
- **Selector en navbar**: `{{lang_selector}}` en base.html → `utils.lang_selector_html()`. Botones ES/EN, ruta `/lang/{lang}` setea cookie `lm_lang` y actualiza `user.language`.
- **Detección de idioma**: cookie `lm_lang` > `Accept-Language` > default `es`.
- **Modelo `User`** tiene columna `language` (`VARCHAR(2)`, default `"es"`).
- **Templates**: `{{t.key}}` placeholders, middleware reemplaza.
- **En JS**: `window.I18N` inyectado en base.html con traducciones frecuentes (mapa tooltips/legend, confirms). mapa.js usa `window.I18N.map.tenders/active/legend`.
- **Emails**: `app/email_utils.py` reescrito con `EMAIL_STRINGS` dict (keys ES/EN), cada `send_*_email` acepta `lang` param. Callers pasan `user.language`.

### GOTCHA crítico — Python f-strings y placeholders

`{{t.xxx}}` dentro de un f-string Python se convierte en `{t.xxx}` (escape de llaves). Solución: usar **`{{{{t.xxx}}}}`** (4 llaves) en f-strings, o (mejor) asignar a variable y usar `{variable}` — la sustitución de variable no reprocesa llaves.

Estados/Tipos/Pranges/Territory traducidos vía el diccionario (claves `estado.PUB`, `tipo.1`, `prange.5k`, `territory.spain`...). Los valores en `home.py` y `mapa.py` se definen como strings plano `"{{t.xxx}}"` y son seguros porque NO están en f-strings.

### GOTCHA — JSON responses no pasan por middleware

El endpoint `/?partial=1` devuelve JSON con HTML fragmentos. El middleware i18n solo procesa `text/html`. Por eso los partial endpoints deben llamar `translate_html(frag, lang)` a mano antes de meter en JSON. Ya aplicado en `home.py`.

### URLs en inglés (con redirects 301)

- `/map`, `/analytics`, `/alerts`, `/admin/users`, `/admin/settings/{export,email,security}`
- Redirects desde las españolas (`/mapa`, `/analisis`, `/alertas`, `/admin/usuarios`, `/admin/config/*`) via `app/routes/redirects.py`
- APIs: `/api/map/*`, `/api/alerts/*`, `/api/analytics/*` (redirects desde las viejas)

### Docs bilingües

- **README.md** en inglés (primario, GitHub-friendly)
- **README.es.md** en español (paralelo, igual de completo), cross-link entre ambos

## Pendiente de i18n (BUGS activos + gaps)

### Verificar tras reinstalación con commit 87a013a
- Login password mal → mensaje traducido (era bug de llaves)
- Admin toggle/delete/estado traducidos (usaban f-strings sin escape)
- Flash messages admin (user_created, user_deleted, limit_saved, smtp_saved, password_updated, email_updated) traducidos vía códigos + `_render_ok_block()`

### Pendiente concreto por arreglar
1. **`mapa.py` sidebar items hardcoded en español** (los chips de tipo/estado/presupuesto DENTRO del mapa). Idéntico fix al de `home.py` TIPOS_CONTRATO/ESTADOS/PRANGES con placeholders `"{{t.x.y}}"`.
2. ✅ **HECHO (commit 8aa2502)** — `alertas.py` `_build_nl_section/_build_alertas_list/_build_subs_list/_build_watchlist` traducidos. Constantes `TIPOS_CONTRATO/ESTADOS/DIAS/DIAS_SHORT/ENTIDAD_TIPOS` ahora son placeholders. `_freq_label/_last_label/_alerta_meta` emiten placeholders. `create_suscripcion` usa `t()` para el default name (evita placeholders crudos en BD).
3. **Asistente CPV / Organismo** (popups en `home.html` + strings en `app.js`) sin traducir.
4. ✅ **HECHO (commit f58c007)** — `alertas.js` toasts/confirms via `window.I18N.al.*`. Añadidos helpers `fmt(tmpl, vars)` (sustituye `%(name)s`) y `errMsg(err)`. `base.html` expone `al.toast.*`, `al.sending`, `al.sendTestBtn`, `al.confirmDelete`, `al.entidad.*`, `al.subPh.*`, `al.valorFallback`.
5. **Template `alertas.html` aún con hardcoded**: chips CCAA y labels del form de alerta personalizada ("Nombre *", "Palabras clave en el título", "Tipo de contrato", "Estado", "Presup. mín./máx. (€)", placeholders "Ej:...", "Sin límite"). Reemplazo directo con `{{t.al.*}}` — no hay f-strings, no hay gotcha. Más unos 15 labels.
6. **CCAA desplegable vacío**: NO es bug — se construye desde `ccaa_counts_raw` (query). Con BD vacía no hay nada que mostrar. Cuando haya datos (post `licitmap sync`) aparecerán. Si quieres que siempre muestre las 19 CCAA con count 0, hay que refactorizar `home.py` para que sidebar_ccaa use una lista fija como ESTADOS.
7. **Mapa provincias sin marcar al zoom**: el usuario reportó que `conteos.provincias` no coincide con los nombres del geojson. Requiere verificar que los valores de `licitacion.provincia` en BD coinciden con la propiedad `Texto` del geojson (o añadir mapping). `static/js/mapa.js:1-22` tiene `CCAA_MAP` pero no mapping análogo para provincias.
8. **Asistente CPV / Organismo** en `static/js/app.js:180-227` — labels del panel de detalle hardcoded (`'Presupuesto'`, `'Publicación'`, `'Fecha límite'`, `'Expediente'`, `'Tipo'`, `'CCAA'`, `'Códigos CPV'`). Exponer vía `window.I18N.detail.*`.

## Tareas pendientes estructurales
- Crear repo público `Ivisor/licitmap` y push del `main` limpio (el usuario lo hará manualmente en GitHub UI).
- Ampliar `municipios_coords.json` (~170 coords actualmente).
- Registro público de cuentas.
