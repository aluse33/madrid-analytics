// Configuración de Observable Framework: https://observablehq.com/framework/config
export default {
  title: "Real Madrid Analytics",
  root: "src",
  lang: "es",
  pages: [
    {name: "Resumen", path: "/"},
    {name: "Partido", path: "/partido"},
    {name: "Jugadores", path: "/jugadores"},
    {name: "Predicción", path: "/prediccion"},
    {name: "Laboratorio de modelos", path: "/modelos"},
    {name: "Metodología", path: "/metodologia"}
  ],
  // Tema propio encima del de Framework: claro/oscuro según el sistema
  style: "style.css",
  head: `<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><circle cx='16' cy='16' r='14' fill='%236250d6'/><path d='M9 21l3-10 4 6 4-6 3 10' stroke='white' stroke-width='2.4' fill='none' stroke-linejoin='round'/></svg>">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=Inter:wght@400;500;600&display=swap">`,
  footer: "Datos: Understat (vía soccerdata). Modelos propios: Dixon-Coles, shrinkage empírico-bayesiano y xG con gradient boosting. Proyecto personal, sin relación con el Real Madrid C.F.",
  toc: {label: "En esta página"},
  pager: false,
  search: true,
  cleanUrls: true
};
