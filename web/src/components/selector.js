// Selector de partidos: una tira de tarjetas que se desliza en horizontal, con filtros por competición.
// Funciona como un input de Observable: tiene .value y lanza "input" al elegir (sirve con view()).
import {html} from "npm:htl";
import {fecha, letra, t} from "./formato.js";
import {escudoDe} from "./eventos.js";
import {nombre} from "../equipos/equipos.js";

export const COMPETICION = {
  "esp.1": {corto: "LaLiga", clase: "liga"},
  "uefa.champions": {corto: "Champions", clase: "ucl"},
  "esp.copa_del_rey": {corto: t("Copa", "Copa"), clase: "copa"},
  "esp.super_cup": {corto: t("Supercopa", "Super Cup"), clase: "otra"},
  "uefa.super_cup": {corto: t("Supercopa UEFA", "UEFA Super Cup"), clase: "otra"},
  "fifa.cwc": {corto: t("Mundial", "Club WC"), clase: "otra"},
  "fifa.intercontinental_cup": {corto: t("Intercontinental", "Intercontinental"), clase: "otra"}
};

// partidos: {clave, fecha, liga, local, visitante, escudo_local, escudo_visitante, goles_local, goles_visitante, resultado, jornada}
export function selectorPartidos(partidos, {value} = {}) {
  let actual = value ?? partidos[0];
  let filtro = "todas";
  const ligas = [...new Set(partidos.map((d) => d.liga))];

  const tarjeta = (d) => {
    const c = COMPETICION[d.liga] ?? {corto: d.competicion ?? "", clase: "otra"};
    const el = html`<button type="button" class="chip-partido res-borde-${d.resultado}" title="${nombre(d.local)} ${d.goles_local}–${d.goles_visitante} ${nombre(d.visitante)}">
      <span class="chip-cab"><span class="chip-comp ${c.clase}">${c.corto}${d.jornada ? ` · J${d.jornada}` : ""}</span><span class="chip-fecha">${fecha(d.fecha)}</span></span>
      <span class="chip-marcador">${escudoDe(d.local, d.escudo_local, 26)}<b>${d.goles_local}–${d.goles_visitante}</b>${escudoDe(d.visitante, d.escudo_visitante, 26)}</span>
      <span class="chip-pie"><span class="res res-${d.resultado}">${letra(d.resultado)}</span><span class="chip-rival">${d.local === "Real Madrid" ? t("vs", "vs") : t("en", "at")} ${nombre(d.local === "Real Madrid" ? d.visitante : d.local)}</span></span>
    </button>`;
    el.onclick = () => elegir(d);
    el.dato = d;
    return el;
  };
  const tarjetas = partidos.map(tarjeta);
  const carril = html`<div class="carril-partidos">${tarjetas}</div>`;

  const boton = (k, txt) => {
    const b = html`<button type="button" class="filtro-comp ${k === filtro ? "activo" : ""}">${txt}</button>`;
    b.onclick = () => {
      filtro = k;
      for (const x of filtros.children) x.classList.toggle("activo", x === b);
      for (const el of tarjetas) el.hidden = k !== "todas" && el.dato.liga !== k;
      carril.scrollLeft = 0;
    };
    return b;
  };
  const filtros = html`<div class="filtros-comp">${boton("todas", t("Todos", "All"))}${ligas.map((l) => boton(l, COMPETICION[l]?.corto ?? l))}</div>`;

  const mover = (s) => carril.scrollBy({left: s * carril.clientWidth * 0.8, behavior: "smooth"});
  const izq = html`<button type="button" class="flecha" aria-label="${t("Anteriores", "Previous")}">‹</button>`;
  const der = html`<button type="button" class="flecha" aria-label="${t("Siguientes", "Next")}">›</button>`;
  izq.onclick = () => mover(-1);
  der.onclick = () => mover(1);

  const root = html`<div class="selector-partidos">
    <div class="selector-cab"><span class="etiqueta">${t("Elige partido", "Pick a match")}</span>${filtros}</div>
    <div class="selector-cuerpo">${izq}${carril}${der}</div>
  </div>`;

  function marcar() {
    for (const el of tarjetas) el.classList.toggle("activa", el.dato === actual);
  }
  function elegir(d) {
    actual = d;
    root.value = d;
    marcar();
    root.dispatchEvent(new Event("input", {bubbles: true}));
  }
  root.value = actual;
  marcar();
  return root;
}
