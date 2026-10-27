// Configuración de Observable Framework: https://observablehq.com/framework/config
export default {
  title: "Minuto 90",
  root: "src",
  lang: "es",
  pages: [
    {name: "Resumen", path: "/"},
    {name: "Partidos", path: "/partido"},
    {name: "Champions League", path: "/champions"},
    {name: "Histórico", path: "/historico"},
    {name: "Jugadores", path: "/jugadores"},
    {name: "Ficha de jugador", path: "/jugador"},
    {name: "Predicción", path: "/prediccion"},
    {name: "Simulación Monte Carlo", path: "/montecarlo"},
    {name: "Laboratorio de modelos", path: "/modelos"},
    {name: "Metodología", path: "/metodologia"}
  ],
  // Tema propio (style.css): claro/oscuro según el sistema, o el que elija el botón
  style: "style.css",
  head: `<script>
  // tema guardado, antes de pintar para que no parpadee
  try { const t = localStorage.getItem("rm-tema"); if (t) document.documentElement.dataset.theme = t; } catch (e) {}
  // idioma: las páginas en inglés viven bajo /en/
  window.RM_EN = /\\/en(\\/|$)/.test(location.pathname);
  if (window.RM_EN) document.documentElement.lang = "en";
  document.addEventListener("DOMContentLoaded", () => {
    const titulo = document.querySelector("#observablehq-sidebar > ol:first-child a");
    // raíz de la web (vale también si se publica en una subcarpeta, p. ej. GitHub Pages)
    const raiz = titulo ? new URL(titulo.getAttribute("href"), location.href).href.replace(/en\\/?$/, "") : location.origin + "/";
    window.RM_RAIZ = raiz;
    const boton = document.getElementById("boton-idioma");
    if (boton) boton.textContent = window.RM_EN ? "🇪🇸 Español" : "🇬🇧 English";
    const tema = document.getElementById("boton-tema");
    if (tema && window.RM_EN) tema.textContent = "🌓 Theme";
    if (!window.RM_EN) return;
    // en inglés: barra lateral, pie y enlaces apuntando a las páginas /en/
    const T = {"Resumen": "Summary", "Partidos": "Matches", "Jugadores": "Players", "Ficha de jugador": "Player profile", "Histórico": "History", "Predicción": "Prediction",
      "Simulación Monte Carlo": "Monte Carlo simulation", "Laboratorio de modelos": "Model lab", "Metodología": "Methodology"};
    const aqui = location.href.split(/[?#]/)[0].replace(/\\/$/, "");
    for (const a of document.querySelectorAll("#observablehq-sidebar a[href]")) {
      const url = new URL(a.getAttribute("href"), location.href).href;
      if (!url.startsWith(raiz) || url.startsWith(raiz + "en/")) continue;
      const destino = raiz + "en/" + url.slice(raiz.length);
      a.setAttribute("href", destino);
      if (T[a.textContent.trim()]) a.textContent = T[a.textContent.trim()];
      const li = a.closest("li");
      if (li && li.classList.contains("observablehq-link")) {
        li.classList.toggle("observablehq-link-active", destino.replace(/\\/$/, "") === aqui);
      }
    }
    const pie = document.querySelector("#observablehq-footer");
    if (pie) pie.textContent = "Data: Understat (via soccerdata), ESPN and Wikipedia (CC BY-SA). Crests: luukhopman/football-logos; trademarks of each club. Personal project, not affiliated with Real Madrid C.F.";
    const fuente = document.getElementById("fuente-datos");
    if (fuente) fuente.textContent = "Data: Understat";
  });
  // ES <-> EN manteniendo la página
  window.rmIdioma = () => {
    const raiz = window.RM_RAIZ || location.origin + "/";
    const actual = location.href;
    location.href = window.RM_EN ? raiz + actual.slice((raiz + "en/").length) : raiz + "en/" + actual.slice(raiz.length);
  };
</script>
<link rel="icon" type="image/png" href="./marca/favicon.png">
<link rel="apple-touch-icon" href="./marca/apple-touch-icon.png">
<meta name="theme-color" content="#000000">
<meta name="description" content="Análisis de datos del Real Madrid en LaLiga: xG, modelos de predicción y estadística bayesiana. Se actualiza tras cada jornada.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=Inter:wght@400;500;600;700&display=swap">`,
  header: `<span id="fuente-datos">Datos: Understat</span>
<button id="boton-idioma" class="boton-tema" type="button" onclick="rmIdioma()">🇬🇧 English</button>
<button id="boton-tema" class="boton-tema" type="button" onclick="(function(b){
  const r = document.documentElement;
  const oscuro = r.dataset.theme ? r.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
  r.dataset.theme = oscuro ? 'light' : 'dark';
  try { localStorage.setItem('rm-tema', r.dataset.theme); } catch (e) {}
  b.textContent = window.RM_EN ? (oscuro ? '🌙 Dark mode' : '☀️ Light mode') : (oscuro ? '🌙 Modo oscuro' : '☀️ Modo claro');
})(this)">🌓 Cambiar tema</button>`,
  footer: "Datos: Understat (vía soccerdata), ESPN y Wikipedia (CC BY-SA). Escudos: luukhopman/football-logos; son marcas de cada club. Proyecto personal, sin relación con el Real Madrid C.F.",
  toc: {label: "En esta página"},
  pager: false,
  search: true,
  cleanUrls: true
};
