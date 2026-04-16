// LicitMap JS

(function () {
  var THEME_KEY = 'licitmap-theme';

  function applyTheme(theme) {
    if (theme === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
    } else {
      document.documentElement.removeAttribute('data-theme');
    }
    localStorage.setItem(THEME_KEY, theme);
  }

  var SIDEBAR_STATE_KEY = 'lm-sidebar-open';

  function getSidebarState() {
    try { return JSON.parse(localStorage.getItem(SIDEBAR_STATE_KEY)) || {}; } catch(e) { return {}; }
  }

  function setupSidebarToggles() {
    var state = getSidebarState();
    // Secciones a forzar abiertas: las que vienen del param ?open= (desde mapa)
    var openParam = new URLSearchParams(window.location.search).get('open');
    var forceOpen = openParam ? openParam.split(',') : [];

    document.querySelectorAll('.lm-sidebar-toggle').forEach(function(btn) {
      var section = btn.dataset.section;
      var body = document.getElementById('sc-' + section);
      if (!body) return;

      // Abre si: estaba abierto en localStorage, viene forzado desde mapa,
      // o tiene ítems activos, o tiene inputs de fecha con valor
      var hasActive = body.querySelector('.lm-active');
      var hasDate = Array.from(body.querySelectorAll('input[type="date"], input[type="text"]')).some(function(i) { return i.value; });
      if (state[section] || forceOpen.indexOf(section) >= 0 || hasActive || hasDate) {
        btn.classList.add('open');
        body.classList.add('open');
      }

      // Auto-scroll al ítem activo si la sección es scrollable
      if (hasActive && body.classList.contains('lm-scrollable')) {
        setTimeout(function() {
          var activeEl = body.querySelector('.lm-active');
          if (activeEl) activeEl.scrollIntoView({ block: 'nearest' });
        }, 300);
      }

      btn.addEventListener('click', function() {
        var open = btn.classList.toggle('open');
        body.classList.toggle('open', open);
        var s = getSidebarState();
        if (open) s[section] = 1; else delete s[section];
        localStorage.setItem(SIDEBAR_STATE_KEY, JSON.stringify(s));
      });
    });
  }

  // ─── Autocomplete con posición fija (escapa overflow:hidden del sidebar) ──
  function stripAccents(s) {
    return s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  }

  function setupAutocomplete(inputId, listId, getOptions, onSelect) {
    var input = document.getElementById(inputId);
    var list  = document.getElementById(listId);
    if (!input || !list) return;
    list.style.position = 'fixed';
    list.style.zIndex   = '9999';

    var activeIdx = -1;

    function updatePos() {
      var r = input.getBoundingClientRect();
      list.style.top   = r.bottom + 'px';
      list.style.left  = r.left + 'px';
      list.style.width = r.width + 'px';
    }

    function showList(items) {
      if (!items.length) { list.classList.remove('open'); return; }
      list.innerHTML = items.slice(0, 10).map(function(item) {
        return '<div class="lm-autocomplete-item" data-val="' + item + '">' + item + '</div>';
      }).join('');
      updatePos();
      list.classList.add('open');
      activeIdx = -1;
      list.querySelectorAll('.lm-autocomplete-item').forEach(function(el) {
        el.addEventListener('mousedown', function(e) {
          e.preventDefault();
          input.value = el.dataset.val;
          list.classList.remove('open');
          onSelect(el.dataset.val);
        });
      });
    }

    function setActive(idx) {
      var items = list.querySelectorAll('.lm-autocomplete-item');
      items.forEach(function(el) { el.classList.remove('lm-ac-active'); });
      if (idx >= 0 && idx < items.length) { items[idx].classList.add('lm-ac-active'); activeIdx = idx; }
    }

    input.addEventListener('input', function() {
      var val = stripAccents(input.value.trim());
      if (!val) { list.classList.remove('open'); onSelect(''); return; }
      var matches = getOptions().filter(function(o) { return stripAccents(o).includes(val); });
      showList(matches);
    });

    input.addEventListener('keydown', function(e) {
      var items = list.querySelectorAll('.lm-autocomplete-item');
      if (e.key === 'ArrowDown')  { e.preventDefault(); setActive(Math.min(activeIdx + 1, items.length - 1)); }
      else if (e.key === 'ArrowUp')   { e.preventDefault(); setActive(Math.max(activeIdx - 1, 0)); }
      else if (e.key === 'Enter' && activeIdx >= 0 && items[activeIdx]) {
        input.value = items[activeIdx].dataset.val;
        list.classList.remove('open');
        onSelect(input.value);
      } else if (e.key === 'Escape') { list.classList.remove('open'); }
    });

    document.addEventListener('click', function(e) {
      if (!input.contains(e.target) && !list.contains(e.target)) list.classList.remove('open');
    });
    window.addEventListener('scroll', updatePos, true);
    window.addEventListener('resize', updatePos);
  }

  document.addEventListener('DOMContentLoaded', function () {
    setupSidebarToggles();

    // Theme toggle
    var btn = document.getElementById('theme-toggle');
    if (btn) {
      btn.addEventListener('click', function () {
        var current = document.documentElement.getAttribute('data-theme');
        applyTheme(current === 'dark' ? 'light' : 'dark');
      });
    }

    // ─── Panel de detalle ─────────────────────────────────────────────────
    var detailPanel    = document.getElementById('lm-detail-panel');
    var detailBackdrop = document.getElementById('lm-detail-backdrop');
    var detailIds = [];
    var detailIdx = -1;

    function escHtml(s) {
      return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    }

    function updateNavButtons() {
      var prevBtn = document.getElementById('lm-detail-prev');
      var nextBtn = document.getElementById('lm-detail-next');
      if (prevBtn) prevBtn.style.display = detailIdx > 0 ? '' : 'none';
      if (nextBtn) nextBtn.style.display = (detailIdx >= 0 && detailIdx < detailIds.length - 1) ? '' : 'none';
    }

    function loadDetailContent(licId) {
      document.getElementById('lm-detail-title').textContent = '';
      document.getElementById('lm-detail-organo').textContent = '';
      var estadoEl = document.getElementById('lm-detail-estado');
      estadoEl.textContent = ''; estadoEl.className = 'badge';
      document.getElementById('lm-detail-body').innerHTML = '<div class="lm-detail-skeleton">Cargando...</div>';

      fetch('/api/licitacion/' + licId)
        .then(function(r) { return r.json(); })
        .then(function(d) {
          document.getElementById('lm-detail-title').textContent = d.titulo;
          document.getElementById('lm-detail-organo').textContent = d.organo_contratacion || '';
          estadoEl.textContent = d.estado_label; estadoEl.className = 'badge badge-' + d.estado;
          var urlBtn = document.getElementById('lm-detail-url');
          if (urlBtn) urlBtn.href = d.url || '#';

          // ── Stats: presupuesto + fechas ──
          var statsItems = [
            d.presupuesto ? ['Presupuesto', '<span class="lm-stat-price">' + escHtml(d.presupuesto) + '</span>'] : null,
            d.fecha_publicacion ? ['Publicación', escHtml(d.fecha_publicacion)] : null,
            d.fecha_limite ? ['Fecha límite', escHtml(d.fecha_limite)] : null,
          ].filter(Boolean);
          var statsHtml = statsItems.length
            ? '<div class="lm-detail-stats">' + statsItems.map(function(s) {
                return '<div class="lm-detail-stat">' +
                  '<span class="lm-detail-stat-label">' + escHtml(s[0]) + '</span>' +
                  '<span class="lm-detail-stat-value">' + s[1] + '</span>' +
                  '</div>';
              }).join('') + '</div>'
            : '';

          // ── Info grid (expediente incluido) ──
          var fieldDefs = [
            d.expediente ? ['Expediente', d.expediente] : null,
            d.tipo_contrato ? ['Tipo', d.tipo_contrato] : null,
            d.comunidad_autonoma ? ['CCAA', d.comunidad_autonoma] : null,
            d.provincia ? ['Provincia', d.provincia] : null,
            d.municipio ? ['Municipio', d.municipio] : null,
            d.codigo_postal ? ['C.P.', d.codigo_postal] : null,
            (d.pais && d.pais !== 'España') ? ['País', d.pais] : null,
          ].filter(Boolean);
          var fieldsHtml = fieldDefs.length
            ? '<div class="lm-detail-fields">' + fieldDefs.map(function(r) {
                return '<div class="lm-detail-field">' +
                  '<span class="lm-detail-label">' + escHtml(r[0]) + '</span>' +
                  '<span class="lm-detail-value">' + escHtml(r[1]) + '</span>' +
                  '</div>';
              }).join('') + '</div>'
            : '';

          // ── CPV tags ──
          var cpvHtml = '';
          if (d.cpv && d.cpv.trim()) {
            var codes = d.cpv.trim().split(/\s+/);
            var shown = codes.slice(0, 6);
            var extra = codes.length - shown.length;
            cpvHtml = '<div class="lm-detail-cpv-section">' +
              '<span class="lm-detail-label">Códigos CPV</span>' +
              '<div class="lm-detail-cpv-tags">' +
              shown.map(function(c) { return '<span class="lm-cpv-tag">' + escHtml(c) + '</span>'; }).join('') +
              (extra > 0 ? '<span class="lm-cpv-tag lm-cpv-more">+' + extra + ' más</span>' : '') +
              '</div></div>';
          }

          document.getElementById('lm-detail-body').innerHTML = statsHtml + fieldsHtml + cpvHtml;
        })
        .catch(function() {
          document.getElementById('lm-detail-body').innerHTML = '<div class="lm-detail-skeleton">Error al cargar los datos.</div>';
        });
    }

    function openDetailPanel(licId) {
      if (!detailPanel) return;
      detailIds = Array.from(document.querySelectorAll('.lm-card[data-lic-id]')).map(function(c) { return c.dataset.licId; });
      detailIdx = detailIds.indexOf(String(licId));
      updateNavButtons();
      loadDetailContent(licId);
      detailPanel.classList.add('open');
      detailBackdrop.classList.add('open');
      document.body.style.overflow = 'hidden';
    }

    function closeDetailPanel() {
      if (!detailPanel || !detailPanel.classList.contains('open')) return;
      detailPanel.classList.remove('open');
      detailBackdrop.classList.remove('open');
      document.body.style.overflow = '';
    }

    document.addEventListener('click', function(e) {
      if (e.target.closest('.lm-detail-panel')) return;
      var card = e.target.closest('.lm-card[data-lic-id]');
      if (card) { openDetailPanel(card.dataset.licId); return; }
      if (detailBackdrop && detailBackdrop.contains(e.target)) closeDetailPanel();
    });

    var detailCloseBtn = document.getElementById('lm-detail-close');
    if (detailCloseBtn) detailCloseBtn.addEventListener('click', closeDetailPanel);

    var prevBtn = document.getElementById('lm-detail-prev');
    var nextBtn = document.getElementById('lm-detail-next');
    if (prevBtn) prevBtn.addEventListener('click', function() {
      if (detailIdx > 0) { detailIdx--; loadDetailContent(detailIds[detailIdx]); updateNavButtons(); }
    });
    if (nextBtn) nextBtn.addEventListener('click', function() {
      if (detailIdx < detailIds.length - 1) { detailIdx++; loadDetailContent(detailIds[detailIdx]); updateNavButtons(); }
    });

    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') closeDetailPanel();
    });
    // ──────────────────────────────────────────────────────────────────────

    // ─── Buscador CPV ─────────────────────────────────────────────────────
    var cpvHelpBtn    = document.getElementById('cpv-help-btn');
    var cpvPopup      = document.getElementById('cpv-popup');
    var cpvSearchInput = document.getElementById('cpv-search-input');
    var cpvResults    = document.getElementById('cpv-results');
    var cpvQInput     = document.getElementById('cpv-q-input');
    var cpvTimer      = null;

    function openCpvPopup() {
      if (!cpvPopup) return;
      cpvPopup.classList.add('open');
      cpvHelpBtn.classList.add('active');
      if (cpvSearchInput) { cpvSearchInput.focus(); cpvSearchInput.select(); }
    }

    function closeCpvPopup() {
      if (!cpvPopup) return;
      cpvPopup.classList.remove('open');
      cpvHelpBtn.classList.remove('active');
    }

    function renderCpvResults(items) {
      if (!items.length) {
        cpvResults.innerHTML = '<div class="lm-cpv-hint">Sin resultados para esta búsqueda</div>';
        return;
      }
      cpvResults.innerHTML = items.map(function(item) {
        return '<div class="lm-cpv-result-item" data-code="' + item.code + '">' +
          '<span class="lm-cpv-result-code">' + item.code + '</span>' +
          '<span class="lm-cpv-result-label">' + item.label + '</span>' +
          '</div>';
      }).join('');
    }

    function doCpvSearch(q) {
      if (!q.trim()) {
        cpvResults.innerHTML = '<div class="lm-cpv-hint">Escribe para buscar en el vocabulario CPV</div>';
        return;
      }
      cpvResults.innerHTML = '<div class="lm-cpv-hint">Buscando...</div>';
      fetch('/api/cpv/buscar?q=' + encodeURIComponent(q))
        .then(function(r) { return r.json(); })
        .then(renderCpvResults)
        .catch(function() {
          cpvResults.innerHTML = '<div class="lm-cpv-hint">Error al buscar</div>';
        });
    }

    if (cpvHelpBtn) {
      cpvHelpBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        cpvPopup.classList.contains('open') ? closeCpvPopup() : openCpvPopup();
      });
    }

    if (cpvSearchInput) {
      cpvSearchInput.addEventListener('input', function() {
        clearTimeout(cpvTimer);
        cpvTimer = setTimeout(function() { doCpvSearch(cpvSearchInput.value); }, 280);
      });
      cpvSearchInput.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') { e.stopPropagation(); closeCpvPopup(); }
      });
    }

    if (cpvResults) {
      cpvResults.addEventListener('click', function(e) {
        var item = e.target.closest('.lm-cpv-result-item');
        if (!item) return;
        var code = item.dataset.code;
        if (cpvQInput) cpvQInput.value = code;
        closeCpvPopup();
        // Disparar búsqueda automáticamente
        var form = document.getElementById('filtros-form');
        if (form) form.dispatchEvent(new Event('submit', {bubbles: true}));
      });
    }

    document.addEventListener('click', function(e) {
      if (cpvPopup && cpvPopup.classList.contains('open')) {
        if (!cpvPopup.contains(e.target) && e.target !== cpvHelpBtn) {
          closeCpvPopup();
        }
      }
    });
    // ──────────────────────────────────────────────────────────────────────

    // ─── Panel lateral: búsqueda por organismo ────────────────────────────
    var orgSearchBtn  = document.getElementById('org-search-btn');
    var orgPanel      = document.getElementById('lm-org-panel');
    var orgBackdrop   = document.getElementById('lm-org-backdrop');
    var orgClose      = document.getElementById('lm-org-close');
    var orgInput      = document.getElementById('lm-org-input');
    var orgResults    = document.getElementById('lm-org-results');
    var orgClearBtn   = document.getElementById('lm-org-clear-btn');
    var orgActiveEl   = document.getElementById('lm-org-active');
    var orgActiveName = document.getElementById('lm-org-active-name');
    var hOrganismo    = document.getElementById('h-organismo');
    var orgTimer      = null;
    var orgItemsCache = [];

    function openOrgPanel() {
      if (!orgPanel) return;
      orgPanel.classList.add('open');
      if (orgBackdrop) orgBackdrop.classList.add('open');
      document.body.style.overflow = 'hidden';
      if (orgInput) { orgInput.focus(); }
      doOrgSearch(orgInput ? orgInput.value : '');
    }

    function closeOrgPanel() {
      if (!orgPanel) return;
      orgPanel.classList.remove('open');
      if (orgBackdrop) orgBackdrop.classList.remove('open');
      document.body.style.overflow = '';
    }

    function updateOrgActive() {
      var val = hOrganismo ? hOrganismo.value : '';
      if (val) {
        if (orgActiveEl)   orgActiveEl.style.display = '';
        if (orgActiveName) orgActiveName.textContent = val;
        if (orgSearchBtn)  orgSearchBtn.classList.add('active');
      } else {
        if (orgActiveEl)   orgActiveEl.style.display = 'none';
        if (orgSearchBtn)  orgSearchBtn.classList.remove('active');
      }
    }

    function doOrgSearch(q) {
      if (!orgResults) return;
      clearTimeout(orgTimer);
      orgTimer = setTimeout(function() {
        fetch('/api/organismos/buscar?q=' + encodeURIComponent(q || ''))
          .then(function(r) { return r.json(); })
          .then(function(items) {
            orgItemsCache = items;
            if (!items.length) {
              orgResults.innerHTML = '<div class="lm-org-hint">Sin resultados para esta búsqueda</div>';
              return;
            }
            var currentOrg = hOrganismo ? hOrganismo.value : '';
            orgResults.innerHTML = items.map(function(item, idx) {
              var isActive = item.nombre === currentOrg;
              return '<div class="lm-org-item' + (isActive ? ' lm-active' : '') + '" data-idx="' + idx + '">' +
                '<span class="lm-org-item-name">' + escHtml(item.nombre) + '</span>' +
                '<span class="lm-org-item-count">' + item.count + '</span>' +
                '</div>';
            }).join('');
          })
          .catch(function() {
            orgResults.innerHTML = '<div class="lm-org-hint">Error al buscar</div>';
          });
      }, 280);
    }

    if (orgSearchBtn) {
      orgSearchBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        orgPanel && orgPanel.classList.contains('open') ? closeOrgPanel() : openOrgPanel();
      });
    }
    if (orgClose)    orgClose.addEventListener('click', closeOrgPanel);
    if (orgBackdrop) orgBackdrop.addEventListener('click', closeOrgPanel);

    if (orgInput) {
      orgInput.addEventListener('input', function() { doOrgSearch(orgInput.value); });
      orgInput.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') { e.stopPropagation(); closeOrgPanel(); }
      });
    }

    if (orgResults) {
      orgResults.addEventListener('click', function(e) {
        var item = e.target.closest('.lm-org-item');
        if (!item) return;
        var idx = parseInt(item.dataset.idx, 10);
        var entry = orgItemsCache[idx];
        if (!entry) return;
        if (hOrganismo) hOrganismo.value = entry.nombre;
        updateOrgActive();
        closeOrgPanel();
        fetchResultados();
      });
    }

    if (orgClearBtn) {
      orgClearBtn.addEventListener('click', function() {
        if (hOrganismo) hOrganismo.value = '';
        updateOrgActive();
        fetchResultados();
      });
    }

    // Init: mostrar chip si viene del servidor con organismo activo
    updateOrgActive();
    // ──────────────────────────────────────────────────────────────────────

    var form = document.getElementById('filtros-form');
    if (!form) return;

    function fetchResultados() {
      var formData = new FormData(form);
      var params = new URLSearchParams(formData);
      params.set('partial', '1');

      // Mantener URL sincronizada para que el reload restaure los filtros actuales
      var urlParams = new URLSearchParams();
      formData.forEach(function(v, k) { if (v) urlParams.set(k, v); });
      history.replaceState(null, '', urlParams.toString() ? '/?' + urlParams.toString() : '/');

      fetch('/?' + params.toString())
        .then(function (r) { return r.json(); })
        .then(function (data) {
          document.getElementById('cards-container').innerHTML = data.filas;
          document.getElementById('paginacion-top').innerHTML = data.paginacion;
          document.getElementById('paginacion-bottom').innerHTML = data.paginacion;
          document.getElementById('resultados-count').textContent = data.resultados;
          if (data.en_plazo !== undefined) {
            document.getElementById('en-plazo-count').textContent = data.en_plazo;
          }

          // Actualizar conteos del sidebar
          var s = data.sidebar;
          if (s) {
            document.getElementById('sidebar-tipo-items').innerHTML = s.sidebar_tipo;
            document.getElementById('sidebar-prange-items').innerHTML = s.sidebar_prange;
            document.getElementById('sidebar-territorio-items').innerHTML = s.sidebar_pais;

            // Actualizar ccaa/paises con su contenido Y mostrar/ocultar juntos
            // (evita layout shift al hacerlo en el mismo frame que el resto del sidebar)
            var ccaaItems = document.getElementById('sidebar-ccaa-items');
            var paisesItems = document.getElementById('sidebar-paises-items');
            var currentPais = document.getElementById('h-pais').value;
            var esEspana = !currentPais || currentPais === 'España';
            if (ccaaItems) {
              ccaaItems.innerHTML = s.sidebar_ccaa;
              ccaaItems.style.display = esEspana ? '' : 'none';
            }
            if (paisesItems) {
              paisesItems.innerHTML = s.sidebar_paises_ext;
              paisesItems.style.display = esEspana ? 'none' : '';
            }

            document.getElementById('sidebar-estado-items').innerHTML = s.sidebar_estado;
          }
        });
    }

    // Salto de página — delegado en document para cubrir paginación top y bottom
    document.addEventListener('keydown', function(e) {
      if (e.key !== 'Enter') return;
      var input = e.target.closest('.lm-page-input');
      if (!input) return;
      e.preventDefault();
      var p = parseInt(input.value, 10);
      var total = parseInt(input.dataset.total, 10);
      if (!p || p < 1 || p > total) { input.value = input.defaultValue; return; }
      var params = new URLSearchParams(window.location.search);
      params.set('page', p);
      window.location.href = '/?' + params.toString();
    });

    // Cargar nombres para autocomplete
    var nombresProvincias = [], nombresMunicipios = [];
    fetch('/api/mapa/nombres').then(function(r) { return r.json(); }).then(function(data) {
      nombresProvincias = data.provincias || [];
      nombresMunicipios = data.municipios || [];

      setupAutocomplete('sidebar-provincia-input', 'sidebar-provincia-list',
        function() { return nombresProvincias; },
        function(val) {
          var h = document.getElementById('h-provincia');
          if (h) { h.value = val; fetchResultados(); }
        }
      );

      setupAutocomplete('sidebar-municipio-input', 'sidebar-municipio-list',
        function() { return nombresMunicipios; },
        function(val) {
          var h = document.getElementById('h-municipio');
          if (h) { h.value = val; fetchResultados(); }
        }
      );
    });

    // Búsqueda de texto: debounce 600ms (cubre barra principal, CPV y municipio)
    var debounceTimer;
    form.querySelectorAll('input[type="text"]').forEach(function (textInput) {
      textInput.addEventListener('input', function () {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(fetchResultados, 600);
      });
    });

    // Fecha: fetch inmediato al cambiar (ambos inputs desde/hasta)
    form.querySelectorAll('input[type="date"]').forEach(function (input) {
      input.addEventListener('change', fetchResultados);
    });

    // Delegación de eventos para el sidebar (sobrevive a reemplazos de innerHTML)
    var sidebar = document.querySelector('.lm-sidebar');
    if (!sidebar) return;

    // Botón de orden
    var btnOrden = document.getElementById('btn-orden');
    var ordenInput = document.getElementById('h-orden');
    if (btnOrden && ordenInput) {
      btnOrden.addEventListener('click', function() {
        var current = ordenInput.value || 'asc';
        var next = current === 'asc' ? 'desc' : 'asc';
        ordenInput.value = next;
        document.getElementById('orden-label').textContent = next === 'asc' ? 'Pronta finalización' : 'Más tiempo';
        var iconDesc = document.getElementById('orden-icon-desc');
        var iconAsc  = document.getElementById('orden-icon-asc');
        if (iconDesc) iconDesc.style.display = next === 'desc' ? '' : 'none';
        if (iconAsc)  iconAsc.style.display  = next === 'asc'  ? '' : 'none';
        fetchResultados();
      });
    }

    // Per-page buttons: init active state and bind clicks
    var perPageInput = document.getElementById('h-per_page');
    document.querySelectorAll('.lm-per-page-btn').forEach(function(btn) {
      if (perPageInput && btn.dataset.value === perPageInput.value) {
        btn.classList.add('active');
      }
      btn.addEventListener('click', function() {
        document.querySelectorAll('.lm-per-page-btn').forEach(function(b) { b.classList.remove('active'); });
        btn.classList.add('active');
        if (perPageInput) perPageInput.value = btn.dataset.value;
        fetchResultados();
      });
    });

    var MULTI_FIELDS = ['tipo', 'estado', 'prange', 'ccaa'];

    sidebar.addEventListener('click', function (e) {
      // Clic en item de filtro
      var item = e.target.closest('.lm-sidebar-item[data-field]');
      if (item) {
        e.preventDefault();
        var field = item.dataset.field;
        var value = item.dataset.value;
        var input = document.getElementById('h-' + field);
        if (!input) return;

        var isActive = item.classList.contains('lm-active');

        if (field === 'pais') {
          // Territorio: comportamiento radio — desactiva todo el grupo, activa el ítem
          sidebar.querySelectorAll('.lm-sidebar-item[data-field="pais"]')
            .forEach(function (el) { el.classList.remove('lm-active'); });
          input.value = value;
          item.classList.add('lm-active');

          var esEspana = !value || value === 'España';

          var titleEl = document.getElementById('sidebar-territorio-title');
          if (titleEl) titleEl.textContent = esEspana ? 'Comunidad autónoma' : 'País';

          var ccaaInput = document.getElementById('h-ccaa');
          if (!esEspana && ccaaInput) {
            ccaaInput.value = '';
            sidebar.querySelectorAll('.lm-sidebar-item[data-field="ccaa"]')
              .forEach(function (el) { el.classList.remove('lm-active'); });
          }
          // Reset provincia y municipio al salir de España
          if (!esEspana) {
            var hProv = document.getElementById('h-provincia');
            var hMun  = document.getElementById('h-municipio');
            var inProv = document.getElementById('sidebar-provincia-input');
            var inMun  = document.getElementById('sidebar-municipio-input');
            if (hProv) hProv.value = '';
            if (hMun)  hMun.value  = '';
            if (inProv) inProv.value = '';
            if (inMun)  inMun.value  = '';
          }
          // Mostrar/ocultar secciones España-only
          var secProv = document.getElementById('sidebar-provincia-section');
          var secMun  = document.getElementById('sidebar-municipio-section');
          if (secProv) secProv.style.display = esEspana ? '' : 'none';
          if (secMun)  secMun.style.display  = esEspana ? '' : 'none';

          if (!esEspana && value !== '__intl__') {
            sidebar.querySelectorAll('.lm-sidebar-item[data-field="pais"]')
              .forEach(function (el) { el.classList.remove('lm-active'); });
            var intlItem = sidebar.querySelector('.lm-sidebar-item[data-value="__intl__"]');
            if (intlItem) intlItem.classList.add('lm-active');
          }

        } else if (MULTI_FIELDS.indexOf(field) >= 0) {
          // Multiselección: toggle este valor en lista separada por |
          var current = input.value ? input.value.split('|').filter(Boolean) : [];
          var idx = current.indexOf(value);
          if (idx >= 0) {
            current.splice(idx, 1);
            item.classList.remove('lm-active');
          } else {
            current.push(value);
            item.classList.add('lm-active');
          }
          input.value = current.join('|');

          // Al seleccionar una CCAA: auto-activar España si el territorio no lo está
          if (field === 'ccaa' && idx < 0) {
            var paisInput = document.getElementById('h-pais');
            if (paisInput && paisInput.value !== 'España') {
              paisInput.value = 'España';
              sidebar.querySelectorAll('.lm-sidebar-item[data-field="pais"]')
                .forEach(function (el) { el.classList.remove('lm-active'); });
              var espanaItem = sidebar.querySelector('.lm-sidebar-item[data-value="España"]');
              if (espanaItem) espanaItem.classList.add('lm-active');
              var titleEl2 = document.getElementById('sidebar-territorio-title');
              if (titleEl2) titleEl2.textContent = 'Comunidad autónoma';
            }
          }

        } else {
          // Resto (paises individuales): toggle normal
          sidebar.querySelectorAll('.lm-sidebar-item[data-field="' + field + '"]')
            .forEach(function (el) { el.classList.remove('lm-active'); });
          if (isActive) {
            input.value = '';
          } else {
            input.value = value;
            item.classList.add('lm-active');
          }
        }

        fetchResultados();
        return;
      }

      // Clic en "Ver todas / Ver menos"
      var verLink = e.target.closest('.lm-sidebar-ver-todas');
      if (verLink) {
        e.preventDefault();
        if (verLink.classList.contains('lm-sidebar-ver-menos')) {
          var extra = verLink.closest('.lm-sidebar-extra');
          if (extra) {
            extra.style.display = 'none';
            var verTodas = extra.previousElementSibling;
            if (verTodas) verTodas.style.display = '';
          }
        } else {
          var extraNext = verLink.nextElementSibling;
          if (extraNext) {
            extraNext.style.display = 'block';
            verLink.style.display = 'none';
          }
        }
      }
    });
  });
})();
