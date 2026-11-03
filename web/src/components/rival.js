// Densidad de tiros en medio campo (vertical, la portería arriba): de dónde tira un equipo o desde
// dónde le tiran. Viene ya suavizada de Python (rivales.json).
import * as Plot from "npm:@observablehq/plot";
import * as d3 from "npm:d3";
import {lineasMedio} from "./campo.js";

const L = 105, A = 68;
const PALETAS = {
  favor: d3.piecewise(d3.interpolateRgb, ["#6250d6", "#8a5cd8", "#eb6834", "#ffd166"]),
  contra: d3.piecewise(d3.interpolateRgb, ["#eb6834", "#f08a3a", "#ffd166"])
};
const OPACIDAD = (v) => Math.min(0.9, Math.max(0, (v - 4) / 32));

export function densidadTiros(valores, {width = 420, rejilla = [14, 11], tipo = "favor"} = {}) {
  const [nu, nv] = rejilla;
  const w = Math.min(width, 520);
  const campo = lineasMedio();
  const color = PALETAS[tipo] ?? PALETAS.favor;
  return Plot.plot({
    width: w, height: Math.round((w * (L / 2 + 2.5)) / A), margin: 0, inset: 0,
    x: {domain: [0, A], axis: null}, y: {domain: [L / 2, L + 2.5], axis: null},
    marks: [
      campo[0],
      valores?.length ? Plot.raster(valores, {width: nu, height: nv, x1: 0, x2: A, y1: L, y2: L / 2,
        fill: (v) => color(Math.max(0, v) / 100), fillOpacity: OPACIDAD}) : null,
      ...campo.slice(1)
    ]
  });
}
