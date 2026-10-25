import {html} from "npm:htl";
import {pct} from "./formato.js";

// Barra 1X2 apilada: color de estado + porcentaje dentro + etiqueta con letra debajo
// (la identidad nunca depende solo del color).
export function barra1x2({victoria, empate, derrota}, rival) {
  const w = (x) => `flex: ${Math.max(x, 0.0001)} 1 0`;
  return html`<div class="barra-1x2">
      <div style="${w(victoria)};background:var(--victoria)" title="Victoria del Madrid">${victoria >= 0.12 ? pct(victoria) : ""}</div>
      <div style="${w(empate)};background:var(--empate)" title="Empate">${empate >= 0.12 ? pct(empate) : ""}</div>
      <div style="${w(derrota)};background:var(--derrota)" title="Victoria de ${rival}">${derrota >= 0.12 ? pct(derrota) : ""}</div>
    </div>
    <div class="leyenda-1x2"><span>V · Madrid ${pct(victoria)}</span><span>E · empate ${pct(empate)}</span><span>D · ${rival} ${pct(derrota)}</span></div>`;
}
