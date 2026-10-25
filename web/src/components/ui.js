import {html} from "npm:htl";
import {EN, letra, pct} from "./formato.js";

// Barra 1X2 apilada: color de estado + porcentaje dentro + etiqueta con letra debajo
// (la identidad nunca depende solo del color).
export function barra1x2({victoria, empate, derrota}, rival) {
  const w = (x) => `flex: ${Math.max(x, 0.0001)} 1 0`;
  return html`<div class="barra-1x2">
      <div style="${w(victoria)};background:var(--victoria)" title="${EN ? "Madrid win" : "Victoria del Madrid"}">${victoria >= 0.12 ? pct(victoria) : ""}</div>
      <div style="${w(empate)};background:var(--empate)" title="Empate">${empate >= 0.12 ? pct(empate) : ""}</div>
      <div style="${w(derrota)};background:var(--derrota)" title="${EN ? `${rival} win` : `Victoria de ${rival}`}">${derrota >= 0.12 ? pct(derrota) : ""}</div>
    </div>
    <div class="leyenda-1x2"><span>${letra("V")} · Madrid ${pct(victoria)}</span><span>${letra("E")} · ${EN ? "draw" : "empate"} ${pct(empate)}</span><span>${letra("D")} · ${rival} ${pct(derrota)}</span></div>`;
}

// Igual, pero en el orden en que se ven los escudos: local a la izquierda, visitante a la derecha.
// El color sigue siendo el del Madrid (verde = gana el Madrid), así que se lee igual en ambos casos.
export function barraPartido(p, nombre = (x) => x) {
  const rmLocal = p.local === "Real Madrid";
  const seg = [
    {p: rmLocal ? p.p_victoria : p.p_derrota, color: rmLocal ? "var(--victoria)" : "var(--derrota)", txt: nombre(p.local)},
    {p: p.p_empate, color: "var(--empate)", txt: EN ? "Draw" : "Empate"},
    {p: rmLocal ? p.p_derrota : p.p_victoria, color: rmLocal ? "var(--derrota)" : "var(--victoria)", txt: nombre(p.visitante)}
  ];
  return html`<div class="barra-1x2">${seg.map((s) => html`<div style="flex:${Math.max(s.p, 0.0001)} 1 0;background:${s.color}" title="${s.txt}">${s.p >= 0.12 ? pct(s.p) : ""}</div>`)}</div>
    <div class="leyenda-1x2">${seg.map((s) => html`<span>${s.txt} ${pct(s.p)}</span>`)}</div>`;
}

// Píldoras de resultados (V/E/D): letra + color, con el partido en el título
export const pildoras = (partidos) =>
  partidos.map((d) => html`<span class="res res-${d.resultado}" title="${d.titulo ?? ""}">${letra(d.resultado)}</span>`);
