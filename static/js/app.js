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
      var params = new URLSearchParams(new FormData(form));
      params.set('partial', '1');
      fetch('/?' + params.toString())
        .then(function (r) { return r.json(); })
        .then(function (data) {
          document.getElementById('cards-container').innerHTML = data.filas;
          document.getElementById('paginacion-bottom').innerHTML = data.paginacion;
          document.getElementById('resultados-count').textContent = data.resultados;
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

    // Fecha: fetch inmediato al cambiar
    var dateInput = form.querySelector('input[type="date"]');
    if (dateInput) {
      dateInput.addEventListener('change', fetchResultados);
    }

    // Sidebar: click en item de filtro
    document.querySelectorAll('.lm-sidebar-item[data-field]').forEach(function (item) {
      item.addEventListener('click', function (e) {
        e.preventDefault();
        var field = this.dataset.field;
        var value = this.dataset.value;
        var input = document.getElementById('h-' + field);
        if (!input) return;

        var isActive = this.classList.contains('lm-active');

        // Desactivar todos los items del mismo grupo
        document.querySelectorAll('.lm-sidebar-item[data-field="' + field + '"]')
          .forEach(function (el) { el.classList.remove('lm-active'); });

        if (isActive) {
          input.value = '';
        } else {
          input.value = value;
          this.classList.add('lm-active');
        }

        // País → alternar entre CCAA y lista de países en bloque Territorio
        if (field === 'pais') {
          var newPais = isActive ? 'España' : value;
          var esEspana = newPais === 'España';
          var ccaaItems = document.getElementById('sidebar-ccaa-items');
          var paisesItems = document.getElementById('sidebar-paises-items');
          var ccaaInput = document.getElementById('h-ccaa');
          if (ccaaItems) ccaaItems.style.display = esEspana ? '' : 'none';
          if (paisesItems) paisesItems.style.display = esEspana ? 'none' : '';
          var titleEl = document.getElementById('sidebar-territorio-title');
          if (titleEl) titleEl.textContent = esEspana ? 'Comunidad autónoma' : 'País';
          if (!esEspana && ccaaInput) {
            ccaaInput.value = '';
            document.querySelectorAll('.lm-sidebar-item[data-field="ccaa"]')
              .forEach(function (el) { el.classList.remove('lm-active'); });
          }
          // Si se elige un país concreto, marcar Internacional como activo
          if (!esEspana && value !== '__intl__') {
            document.querySelectorAll('.lm-sidebar-item[data-field="pais"]')
              .forEach(function (el) { el.classList.remove('lm-active'); });
            var intlItem = document.querySelector('.lm-sidebar-item[data-value="__intl__"]');
            if (intlItem) intlItem.classList.add('lm-active');
          }
        }

        fetchResultados();
      });
    });

    // "Ver todas / Ver menos" en CCAA
    document.querySelectorAll('.lm-sidebar-ver-todas').forEach(function (link) {
      link.addEventListener('click', function (e) {
        e.preventDefault();
        // "Ver menos" está dentro del bloque extra — cierra
        if (this.classList.contains('lm-sidebar-ver-menos')) {
          var extra = this.closest('.lm-sidebar-extra');
          if (extra) {
            extra.style.display = 'none';
            var verTodas = extra.previousElementSibling;
            if (verTodas) verTodas.style.display = '';
          }
          return;
        }
        // "Ver todas" — abre el bloque extra
        var extra = this.nextElementSibling;
        if (!extra) return;
        extra.style.display = 'block';
        this.style.display = 'none';
      });
    });
  });
})();
