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
    document.querySelectorAll('.lm-sidebar-toggle').forEach(function(btn) {
      var section = btn.dataset.section;
      var body = document.getElementById('sc-' + section);
      if (!body) return;
      if (state[section]) {
        btn.classList.add('open');
        body.classList.add('open');
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

    // Búsqueda de texto: debounce 600ms
    var debounceTimer;
    var textInput = form.querySelector('input[type="text"]');
    if (textInput) {
      textInput.addEventListener('input', function () {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(fetchResultados, 600);
      });
    }

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
