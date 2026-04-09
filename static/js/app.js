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

    // CCAA filter: solo visible cuando país = España
    var paisSel = document.getElementById('filtro-pais');
    var ccaaWrap = document.getElementById('filtro-ccaa-wrap');
    if (paisSel && ccaaWrap) {
      function toggleCCAA() {
        ccaaWrap.style.display = paisSel.value === 'España' ? '' : 'none';
      }
      paisSel.addEventListener('change', toggleCCAA);
      toggleCCAA();
    }
  });
})();
