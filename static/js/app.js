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

  document.addEventListener('DOMContentLoaded', function () {
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

        // Desactivar todos los items del mismo grupo
        sidebar.querySelectorAll('.lm-sidebar-item[data-field="' + field + '"]')
          .forEach(function (el) { el.classList.remove('lm-active'); });

        if (field === 'pais') {
          // Territorio: comportamiento radio — siempre activa el ítem, nunca deselecciona
          input.value = value;
          item.classList.add('lm-active');

          var esEspana = !value || value === 'España';

          // Actualizar título inmediatamente
          var titleEl = document.getElementById('sidebar-territorio-title');
          if (titleEl) titleEl.textContent = esEspana ? 'Comunidad autónoma' : 'País';

          // Limpiar CCAA si salimos de España/Todos
          var ccaaInput = document.getElementById('h-ccaa');
          if (!esEspana && ccaaInput) {
            ccaaInput.value = '';
            sidebar.querySelectorAll('.lm-sidebar-item[data-field="ccaa"]')
              .forEach(function (el) { el.classList.remove('lm-active'); });
          }

          // País concreto → marcar Internacional como activo visualmente
          if (!esEspana && value !== '__intl__') {
            sidebar.querySelectorAll('.lm-sidebar-item[data-field="pais"]')
              .forEach(function (el) { el.classList.remove('lm-active'); });
            var intlItem = sidebar.querySelector('.lm-sidebar-item[data-value="__intl__"]');
            if (intlItem) intlItem.classList.add('lm-active');
          }

        } else {
          // Resto de campos: toggle normal
          if (isActive) {
            input.value = '';
          } else {
            input.value = value;
            item.classList.add('lm-active');
          }

          // Al seleccionar una CCAA: auto-activar España si el territorio no lo está
          if (field === 'ccaa' && !isActive) {
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
