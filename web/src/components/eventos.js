// Cronología, alineaciones y estadísticas de un partido (datos de ESPN, en data/eventos.json).
import * as Plot from "npm:@observablehq/plot";
import * as d3 from "npm:d3";
import {html} from "npm:htl";
import {EN, LOC, t} from "./formato.js";
import {lineas} from "./campo.js";
import {EQUIPOS, escudo, nombre} from "../equipos/equipos.js";

const L = 105, A = 68;
const colorDe = (equipo) => (equipo === "Real Madrid" ? "var(--rm)" : "var(--rival)");

const ICONO = {gol: "⚽", autogol: "⚽", penalti_fallado: "❌", amarilla: "🟨", roja: "🟥", cambio: "🔁"};

// ---------------------------------------------------------------- cronología
export function cronologia(det, local, visitante, nombre = (x) => x) {
  const evs = det.eventos.filter((e) => e.tipo !== "cambio" || e.equipo);
  if (!evs.length) return html`<p>${t("Sin eventos registrados.", "No events recorded.")}</p>`;
  const texto = (e) => {
    switch (e.tipo) {
      case "gol": return html`<b>${e.jugador}</b>${e.subtipo.includes("penalty") ? t(" (penalti)", " (penalty)") : ""}${e.otro ? html`<span class="sub-ev">${t("asist.", "assist")} ${e.otro}</span>` : ""}`;
      case "autogol": return html`<b>${e.jugador}</b> ${t("(en propia)", "(own goal)")}`;
      case "penalti_fallado": return html`${e.jugador} ${t("falla un penalti", "misses a penalty")}`;
      case "cambio": return html`<span class="entra">▲ ${e.jugador}</span><span class="sale">▼ ${e.otro ?? ""}</span>`;
      default: return html`${e.jugador ?? ""}`;
    }
  };
  // el autogol suma al rival del que lo marca
  const ladoDe = (e) => (e.tipo === "autogol" ? (e.equipo === local ? visitante : local) : e.equipo);
  let mi = 0, su = 0;
  const filas = [];
  let descanso = false;
  for (const e of evs) {
    if (!descanso && e.parte === 2) {
      descanso = true;
      filas.push(html`<div class="crono-descanso">${t("Descanso", "Half time")} · ${mi}–${su}</div>`);
    }
    const lado = ladoDe(e);
    if (e.tipo === "gol" || e.tipo === "autogol") lado === local ? mi++ : su++;
    const izq = lado === local;
    const contenido = html`<div class="crono-ev ${e.tipo}">${ICONO[e.tipo]} <span>${texto(e)}</span>${e.tipo === "gol" || e.tipo === "autogol" ? html`<span class="crono-marcador">${mi}–${su}</span>` : ""}</div>`;
    filas.push(html`<div class="crono-fila"><div class="izq">${izq ? contenido : ""}</div><div class="min">${e.reloj}</div><div class="der">${izq ? "" : contenido}</div></div>`);
  }
  return html`<div class="cronologia">
    <div class="crono-fila crono-cab"><div class="izq">${nombre(local)}</div><div class="min"></div><div class="der">${nombre(visitante)}</div></div>
    ${filas}
    <div class="crono-descanso">${t("Final", "Full time")} · ${mi}–${su}</div>
  </div>`;
}

// ---------------------------------------------------------------- alineaciones
// línea táctica según la posición de ESPN (G, CD-L, LB, DM, CM-R, LM, AM, AM-L, F, CF-R...)
const rango = (p = "") =>
  p === "G" ? 0 : /^(CD|LB|RB|LWB|RWB|SW)/.test(p) ? 1 : /^DM/.test(p) ? 2 : /^(CM|LM|RM)/.test(p) ? 3 : /^(AM|LW|RW)/.test(p) ? 4 : 5;
// de izquierda (−) a derecha (+) desde el punto de vista del propio equipo
const lateral = (p = "") => (/-L$/.test(p) ? -1 : /-R$/.test(p) ? 1 : /^L/.test(p) ? -2 : /^R/.test(p) ? 2 : 0);

function colocar(once, formacion) {
  const portero = once.filter((j) => j.pos === "G");
  const campo = once.filter((j) => j.pos !== "G").sort((a, b) => rango(a.pos) - rango(b.pos) || lateral(a.pos) - lateral(b.pos));
  let lineasF = (formacion ?? "").split("-").map(Number).filter((n) => n > 0);
  if (d3.sum(lineasF) !== campo.length) lineasF = d3.groups(campo, (j) => rango(j.pos)).map(([, v]) => v.length);
  const filas = [];
  let i = 0;
  for (const n of lineasF) { filas.push(campo.slice(i, i + n)); i += n; }
  const out = portero.map((j) => ({...j, x: 5, y: A / 2}));
  filas.forEach((fila, k) => {
    const x = filas.length === 1 ? 30 : 16 + (k * 32) / (filas.length - 1);
    fila.sort((a, b) => lateral(a.pos) - lateral(b.pos)).forEach((j, m) => out.push({...j, x, y: (A * (fila.length - m)) / (fila.length + 1)}));
  });
  return out;
}

const apellido = (j) => (j.corto ?? j.nombre).replace(/^[A-ZÁÉÍÓÚ]\. /, "");

export function alineaciones(det, {width = 720} = {}) {
  const cambios = det.eventos.filter((e) => e.tipo === "cambio");
  const puntos = det.alineaciones.flatMap((al) => {
    const once = colocar(al.jugadores.filter((j) => j.titular), al.formacion);
    return once.map((j) => {
      const sale = cambios.find((c) => c.equipo === al.equipo && c.otro === j.nombre);
      const local = al.lado === "local";
      return {...j, equipo: al.equipo, x: local ? j.x : L - j.x, y: local ? j.y : A - j.y,
        etiqueta: apellido(j), sale: sale?.reloj,
        iconos: "⚽".repeat(j.goles) + (j.rojas ? "🟥" : j.amarillas ? "🟨" : "")};
    });
  });
  const h = Math.round((width * A) / L);
  const r = Math.max(8, Math.min(13, width / 60));
  return Plot.plot({
    width, height: h, margin: 0, inset: 0,
    x: {domain: [0, L], axis: null}, y: {domain: [0, A], axis: null},
    marks: [
      ...lineas(),
      Plot.dot(puntos, {x: "x", y: "y", r, fill: (d) => colorDe(d.equipo), stroke: "var(--campo-fondo)", strokeWidth: 1.5}),
      Plot.text(puntos, {x: "x", y: "y", text: "dorsal", fill: "white", fontWeight: 700, fontSize: Math.round(r * 0.95)}),
      Plot.text(puntos, {x: "x", y: "y", text: "etiqueta", dy: r + 8, fontSize: width < 600 ? 9 : 11, fill: "var(--texto)", stroke: "var(--campo-fondo)", strokeWidth: 3}),
      Plot.text(puntos.filter((d) => d.iconos), {x: "x", y: "y", text: "iconos", dy: -r - 7, fontSize: 11}),
      Plot.text(puntos.filter((d) => d.sale), {x: "x", y: "y", text: (d) => `▼${d.sale}`, dx: r + 4, dy: -r + 2, textAnchor: "start", fontSize: 9, fill: "var(--derrota)"}),
      Plot.tip(puntos, Plot.pointer({x: "x", y: "y", title: (d) => `${d.dorsal} · ${d.nombre}\n${d.pos} · ${d.equipo}${d.sale ? `\n${t("Sustituido en el", "Subbed off at")} ${d.sale}` : ""}`}))
    ]
  });
}

// suplentes que entraron, con el minuto
export function banquillo(det, equipo) {
  const al = det.alineaciones.find((a) => a.equipo === equipo);
  if (!al) return "";
  const cambios = det.eventos.filter((e) => e.tipo === "cambio" && e.equipo === equipo);
  const entran = al.jugadores.filter((j) => j.entra).map((j) => ({j, c: cambios.find((c) => c.jugador === j.nombre)}))
    .sort((a, b) => (a.c?.minuto ?? 99) - (b.c?.minuto ?? 99));
  return html`<div class="banquillo"><b>${al.formacion ?? ""}</b> · ${t("Entraron", "Came on")}: ${entran.length
    ? entran.map(({j, c}, i) => html`${i ? ", " : ""}${j.dorsal} ${apellido(j)}${c ? ` (${c.reloj})` : ""}${"⚽".repeat(j.goles)}`)
    : t("nadie", "nobody")}</div>`;
}

// ---------------------------------------------------------------- estadísticas
const STATS = [
  ["possessionPct", t("Posesión", "Possession"), (v) => `${(+v).toLocaleString(LOC, {maximumFractionDigits: 0})}${EN ? "%" : " %"}`],
  ["totalShots", t("Tiros", "Shots")],
  ["shotsOnTarget", t("A puerta", "On target")],
  ["wonCorners", t("Córners", "Corners")],
  ["totalPasses", t("Pases", "Passes")],
  ["accuratePasses", t("Pases buenos", "Accurate passes")],
  ["interceptions", t("Intercepciones", "Interceptions")],
  ["effectiveTackles", t("Entradas ganadas", "Tackles won")],
  ["saves", t("Paradas", "Saves")],
  ["foulsCommitted", t("Faltas", "Fouls")],
  ["offsides", t("Fueras de juego", "Offsides")],
  ["yellowCards", t("Amarillas", "Yellow cards")],
  ["redCards", t("Rojas", "Red cards")]
];

export function estadisticas(det, local, visitante) {
  const a = det.estadisticas[local] ?? {}, b = det.estadisticas[visitante] ?? {};
  const filas = STATS.filter(([k]) => a[k] != null && b[k] != null && !(+a[k] === 0 && +b[k] === 0));
  if (!filas.length) return html`<p>${t("Sin estadísticas.", "No stats.")}</p>`;
  return html`<div class="stats-duelo">${filas.map(([k, nombre, fmt = (v) => (+v).toLocaleString(LOC)]) => {
    const x = +a[k], y = +b[k], tot = x + y || 1;
    return html`<div class="stat">
      <div class="stat-cab"><b>${fmt(x)}</b><span>${nombre}</span><b>${fmt(y)}</b></div>
      <div class="stat-barra"><div style="width:${(100 * x) / tot}%;background:${colorDe(local)}"></div><div style="width:${(100 * y) / tot}%;background:${colorDe(visitante)}"></div></div>
    </div>`;
  })}</div>`;
}

// escudo propio si lo tenemos (equipos de LaLiga); si no, el que da ESPN
export const escudoDe = (equipo, url, size = 22) =>
  EQUIPOS[equipo] || !url ? escudo(equipo, size)
    : html`<img class="escudo" src=${url} alt="" width=${size} height=${size} style="height:${size}px;width:auto" loading="lazy">`;
export const conEscudoDe = (equipo, url, size = 18) =>
  html`<span class="con-escudo">${escudoDe(equipo, url, size)}<span>${nombre(equipo)}</span></span>`;
