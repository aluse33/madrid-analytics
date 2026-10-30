// Gráficos con datos de Sofascore (todas las competiciones): mapa de calor, posiciones medias,
// tiros con xG a puerta, portería y dominio. Todo en la orientación del Madrid: ataca hacia la
// derecha (x = 105) y el rival hacia la izquierda.
import * as Plot from "npm:@observablehq/plot";
import * as d3 from "npm:d3";
import {lineas} from "./campo.js";
import {EN, LOC, t} from "./formato.js";

const L = 105, A = 68;
const n2 = (v) => (v == null ? "–" : (+v).toLocaleString(LOC, {maximumFractionDigits: 2, minimumFractionDigits: 2}));

// del morado al naranja y al amarillo; la transparencia va aparte (el raster de Plot la toma de fillOpacity)
const CALOR = d3.piecewise(d3.interpolateRgb, ["#6250d6", "#8a5cd8", "#eb6834", "#ffd166"]);
const OPACIDAD = (v) => Math.min(0.92, Math.max(0, (v - 4) / 30));

export function mapaCalor(valores, {width = 720, rejilla = [21, 14], titulo} = {}) {
  const [nx, ny] = rejilla;
  const height = Math.round((width * A) / L);
  const campo = lineas();
  return Plot.plot({
    width, height, margin: 0, inset: 0, title: titulo,
    x: {domain: [0, L], axis: null}, y: {domain: [0, A], axis: null},
    marks: [
      campo[0],
      // fila 0 = la de arriba; el navegador suaviza al ampliar la imagen
      Plot.raster(valores, {width: nx, height: ny, x1: 0, x2: L, y1: A, y2: 0, fill: (v) => CALOR(Math.max(0, v) / 100), fillOpacity: OPACIDAD}),
      ...campo.slice(1),
      Plot.rect([{}], {x1: 0, x2: L, y1: 0, y2: A, fill: "none", stroke: "var(--campo-linea)", strokeWidth: 1.2}),
      Plot.text([t("Ataca → ", "Attacking → ")], {frameAnchor: "top-right", dx: -8, dy: 8, fill: "var(--campo-linea)", fontSize: 11, opacity: 0.8})
    ]
  });
}

// posiciones medias: tamaño = balones tocados; los suplentes, con borde discontinuo
export function posicionesMedias(filas, {width = 720, rival = "Rival", conRival = false} = {}) {
  const datos = filas.filter((d) => conRival || d.equipo === "rm");
  const height = Math.round((width * A) / L);
  const color = (d) => (d.equipo === "rm" ? "var(--rm)" : "var(--rival)");
  return Plot.plot({
    width, height, margin: 0, inset: 0,
    x: {domain: [0, L], axis: null}, y: {domain: [0, A], axis: null},
    r: {domain: [0, d3.max(filas, (d) => d.toques) || 100], range: [5, width < 500 ? 15 : 22]},
    marks: [
      ...lineas(),
      Plot.dot(datos, {x: "x", y: "y", r: "toques", fill: color, fillOpacity: (d) => (d.titular ? 0.95 : 0.55),
        stroke: "var(--campo-fondo)", strokeWidth: 1.5, strokeDasharray: (d) => (d.titular ? null : "3,2")}),
      Plot.text(datos, {x: "x", y: "y", text: "dorsal", fill: "white", fontWeight: 700, fontSize: width < 500 ? 9 : 11}),
      width < 500 ? null : Plot.text(datos, {x: "x", y: "y", text: (d) => d.nombre.split(" ").at(-1), dy: 24, fill: "var(--texto)", fontSize: 10, stroke: "var(--campo-fondo)", strokeWidth: 3}),
      Plot.tip(datos, Plot.pointer({x: "x", y: "y",
        title: (d) => `${d.nombre} (${d.equipo === "rm" ? "Real Madrid" : rival})\n${d.toques} ${t("acciones registradas", "recorded actions")}${d.titular ? "" : t(" · suplente", " · substitute")}`}))
    ]
  });
}

const RES = EN
  ? {goal: "goal", save: "saved", miss: "off target", post: "woodwork", block: "blocked", "blocked-off-line": "cleared off the line"}
  : {goal: "gol", save: "parado", miss: "fuera", post: "palo", block: "bloqueado", "blocked-off-line": "salvado bajo palos"};
const SIT = EN
  ? {regular: "open play", assisted: "assisted", "fast-break": "counter-attack", corner: "corner", "set-piece": "set piece", penalty: "penalty", "free-kick": "free kick", "throw-in-set-piece": "throw-in"}
  : {regular: "jugada", assisted: "con asistencia", "fast-break": "contragolpe", corner: "córner", "set-piece": "balón parado", penalty: "penalti", "free-kick": "falta directa", "throw-in-set-piece": "saque de banda"};
const CUERPO = EN ? {"right-foot": "right foot", "left-foot": "left foot", head: "header", other: "other"}
  : {"right-foot": "pie derecho", "left-foot": "pie izquierdo", head: "cabeza", other: "otra"};
const tipTiro = (rival) => (d) =>
  `${d.jugador} (${d.equipo === "rm" ? "Real Madrid" : rival}) · ${d.minuto}′\nxG ${n2(d.xg)}${d.xgot ? ` · xGOT ${n2(d.xgot)}` : ""}\n` +
  `${SIT[d.situacion] ?? d.situacion ?? ""} · ${CUERPO[d.cuerpo] ?? d.cuerpo ?? ""}\n${RES[d.resultado] ?? d.resultado}`;

export function mapaTirosSofa(tiros, {width = 720, rival = "Rival"} = {}) {
  const height = Math.round((width * A) / L);
  const color = (d) => (d.equipo === "rm" ? "var(--rm)" : "var(--rival)");
  const gol = tiros.filter((d) => d.resultado === "goal"), resto = tiros.filter((d) => d.resultado !== "goal");
  return Plot.plot({
    width, height, margin: 0, inset: 0,
    x: {domain: [0, L], axis: null}, y: {domain: [0, A], axis: null},
    r: {domain: [0, 0.8], range: [3, 18]},
    marks: [
      ...lineas(),
      Plot.dot(resto, {x: "x", y: "y", r: "xg", fill: "var(--campo-fondo)", fillOpacity: 0.85, stroke: color, strokeWidth: 2}),
      Plot.dot(gol, {x: "x", y: "y", r: "xg", fill: color, stroke: "var(--campo-fondo)", strokeWidth: 2}),
      Plot.tip(tiros, Plot.pointer({x: "x", y: "y", title: tipTiro(rival)}))
    ]
  });
}

// la portería vista de frente: dónde fue cada tiro que llegó a la línea (sin los bloqueados)
const PALO1 = 44.6, PALO2 = 55.4, LARGUERO = 38;
export function porteria(tiros, {width = 360, rival = "Rival", equipo = "rm"} = {}) {
  const datos = tiros.filter((d) => d.equipo === equipo && d.py != null && !String(d.resultado).startsWith("block"))
    .map((d) => ({...d, py: Math.max(37, Math.min(63, d.py)), pz: Math.min(58, d.pz)}));
  const height = Math.round(width * 0.62);
  const color = equipo === "rm" ? "var(--rm)" : "var(--rival)";
  return Plot.plot({
    width, height, marginTop: 6, marginBottom: 10, marginLeft: 6, marginRight: 6,
    x: {domain: [37, 63], axis: null}, y: {domain: [-3, 60], axis: null},
    r: {domain: [0, 1], range: [3, 13]},
    marks: [
      Plot.ruleY([0], {stroke: "var(--theme-foreground-faint)", strokeWidth: 1.5}),
      Plot.line([[PALO1, 0], [PALO1, LARGUERO], [PALO2, LARGUERO], [PALO2, 0]], {stroke: "var(--texto)", strokeWidth: 4, strokeLinejoin: "round"}),
      // red
      Plot.ruleX(d3.range(PALO1 + 1.2, PALO2, 1.2), {y1: 0, y2: LARGUERO, stroke: "var(--theme-foreground-faintest)"}),
      Plot.ruleY(d3.range(4, LARGUERO, 4), {x1: PALO1, x2: PALO2, stroke: "var(--theme-foreground-faintest)"}),
      Plot.dot(datos.filter((d) => d.resultado !== "goal"), {x: "py", y: "pz", r: (d) => d.xgot || d.xg, fill: "var(--theme-background)", stroke: color, strokeWidth: 2}),
      Plot.dot(datos.filter((d) => d.resultado === "goal"), {x: "py", y: "pz", r: (d) => d.xgot || d.xg, fill: color, stroke: "var(--theme-background)", strokeWidth: 1.5}),
      Plot.tip(datos, Plot.pointer({x: "py", y: "pz", title: tipTiro(rival)}))
    ]
  });
}

// dominio de Sofascore: presión ofensiva minuto a minuto (arriba, el Madrid)
export function dominioSofa(puntos, {width = 720, rival = "Rival", goles = []} = {}) {
  const datos = puntos.map(([minuto, v]) => ({minuto, v}));
  const fin = Math.max(95, d3.max(datos, (d) => d.minuto) ?? 90);
  return Plot.plot({
    width, height: 230,
    x: {domain: [0, fin], label: t("Minuto", "Minute"), ticks: [0, 15, 30, 45, 60, 75, 90]},
    y: {domain: [-100, 100], label: null, ticks: []},
    marks: [
      Plot.rectY(datos, {x1: (d) => d.minuto - 1, x2: "minuto", y: "v", fill: (d) => (d.v >= 0 ? "var(--rm)" : "var(--rival)"), inset: 0.3}),
      Plot.ruleY([0], {stroke: "var(--theme-foreground-muted)"}),
      Plot.ruleX([45], {stroke: "var(--theme-foreground-faint)", strokeDasharray: "3,3"}),
      Plot.text(goles, {x: "minuto", y: (d) => (d.equipo === "rm" ? 92 : -92), text: () => "⚽", fontSize: 13}),
      Plot.text([t("Real Madrid", "Real Madrid")], {frameAnchor: "top-left", dx: 4, dy: 2, fill: "var(--rm)", fontWeight: 600}),
      Plot.text([rival], {frameAnchor: "bottom-left", dx: 4, dy: -24, fill: "var(--rival)", fontWeight: 600}),
      Plot.tip(datos, Plot.pointerX({x: "minuto", y: "v", title: (d) => `${d.minuto}′ · ${d.v >= 0 ? "Real Madrid" : rival}`}))
    ]
  });
}
