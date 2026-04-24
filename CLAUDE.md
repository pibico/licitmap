# LicitMap — Contexto para Claude Code

App de licitaciones del Estado (España) sincronizada por feed ATOM. Este fichero da contexto mínimo a futuras sesiones de Claude. **El contexto completo vive en `.claude/memory/`** (indexado por `.claude/memory/MEMORY.md`).

## Stack

- **Backend**: Python 3.11+ / FastAPI / SQLAlchemy
- **BD**: PostgreSQL 17 (nativo en prod, `ENCODING 'UTF8' TEMPLATE template0 LC_COLLATE 'C' LC_CTYPE 'C'`)
- **Front**: Bootstrap 5 + JS vanilla + Leaflet (mapa)
- **Deploy**: systemd en LXC Proxmox (`install.sh` / `uninstall.sh` en la raíz)
- **i18n**: sistema propio — `{{t.key.subkey}}` reemplazado por `I18nMiddleware` (ver gotchas abajo)

## Estructura rápida

```
main.py                         FastAPI + I18nMiddleware + routers
app/
  i18n.py                       TRANSLATIONS ES/EN + middleware + translate_html
  models.py                     User (language VARCHAR 2), Licitacion, Alerta, LicitacionSeguida, Setting
  routes/{home,mapa,analisis,alertas,admin,auth,lang,redirects}.py
  email_utils.py                EMAIL_STRINGS ES/EN, send_*_email(..., lang=...)
  utils.py                      _nav_context() + lang_selector_html()
scripts/{licitmap,sync.py,check_alertas.py,run_sync.sh}
deploy/{licitmap.service,licitmap.nginx.conf,licitmap.cron}
static/{js,css,data/{ccaa,provincias,municipios}.geojson,cpv_es.json,municipios_coords.json}
templates/*.html                Sistema propio: Path.read_text() + .replace("{{key}}", value), NO Jinja2
```

## Gotchas críticos (i18n)

1. **f-strings + placeholders**: `{{t.xxx}}` dentro de f-string se convierte en `{t.xxx}` literal. Usar **`{{{{t.xxx}}}}`** (4 llaves) o asignar a variable `x="{{t.xxx}}"` y `f"...{x}..."`.
2. **JSON responses** no pasan por el middleware. Los endpoints que devuelven HTML dentro de JSON (ej. `/?partial=1`) deben llamar `translate_html(frag, lang)` a mano.
3. **Regex del middleware**: `{{t.[a-zA-Z0-9_.]+}}`, **sin `+`**. Claves tipo `1m+` deben mapearse a `1mplus`.
4. **JS**: `window.I18N` en `base.html` expone strings frecuentes (mapa tooltips/legend, confirms).
5. **BD encoding**: sin `LC_COLLATE 'C' LC_CTYPE 'C'` PostgreSQL arranca en SQL_ASCII en LXC minimal y explota con ñ/acentos.

## URLs

Inglés primario con redirects 301 desde español:
`/map` ← `/mapa`, `/analytics` ← `/analisis`, `/alerts` ← `/alertas`, `/admin/users` ← `/admin/usuarios`, `/admin/settings/*` ← `/admin/config/*`, `/api/{map,alerts,analytics}/*` ← viejas APIs.

## Comandos

```bash
licitmap status | doctor | logs [sync|alertas] | sync --full | migrate | update
licitmap admin reset-password
# Reinstalación limpia:
bash /opt/licitmap/uninstall.sh -y && rm -rf ~/licitmap-dev && git clone https://github.com/Ivisor/licitmap-dev.git ~/licitmap-dev && bash ~/licitmap-dev/install.sh
```

## Preferencias del autor

- **Commits sin co-author de Claude**. Solo `ivisor` como autor.
- **Granularidad**: un commit por feature/fix significativo, no acumular.
- **Paleta**: Stone/Slate propia. **NO Catppuccin** (descartado). Light `#f9f7f4`, dark `#20232b`.
- Sensibilidad a saturación: fondos neutros > expresivos.

## Repos

- **Dev (este)**: `git@github.com:Ivisor/licitmap-dev.git` — privado, incluye `.claude/` y `CLAUDE.md`.
- **Público** (pendiente): `Ivisor/licitmap` — se excluirán `.claude/`, `CLAUDE.md`, `.planning/` del `.gitignore` cuando se cree.

## Dónde mirar

- `.claude/memory/project_state.md` — features, auth, tareas pendientes (fuente de verdad)
- `.claude/memory/project_tech.md` — arquitectura, modelos, placeholders, infraestructura
- `.claude/memory/feedback_*.md` — diseño y workflow
