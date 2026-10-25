---
title: Match
toc:
  label: "On this page"
---
<!-- GENERADO por `rma traducir` a partir de ../partido.md: no editar a mano -->

```js
import {num, pct, fecha, fechaHora, tickNum, puestoTxt} from "../components/formato.js";
import {mapaTiros} from "../components/campo.js";
import {resultadoMerecido, probAlMenos} from "../components/probabilidad.js";
import {barraPartido} from "../components/ui.js";
import {escudo, nombre, corto} from "../equipos/equipos.js";

const estado = FileAttachment("../data/estado.json").json();
const partidos = FileAttachment("../data/rm_partidos.csv").csv({typed: true});
const tiros = FileAttachment("../data/tiros_rm.csv").csv({typed: true});
const jugadores = FileAttachment("../data/jugadores_rm.csv").csv({typed: true});
```

```js
const jugados = partidos.filter((d) => d.temporada === estado.temporada && d.jugado).reverse();
const elegido = view(Inputs.select(jugados, {
  label: "Match",
  format: (d) => `J${d.jornada} · ${fecha(d.fecha)} · ${d.condicion === "Local" ? `Real Madrid ${d.gf}–${d.gc} ${nombre(d.rival)}` : `${nombre(d.rival)} ${d.gc}–${d.gf} Real Madrid`}`
}));
```

```js
const p = elegido;
const ORDEN = {POR: 0, DEF: 1, MED: 2, DEL: 3};
// with 0 goals, "0 o más" es siempre el 100 %: lo informativo es la probabilidad de quedarse a cero
const frase = (quien, ts, goles) => goles === 0
  ? html`Probability that ${quien} would fail <b>to score</b> with their ${ts.length} shots: <b>${pct(1 - probAlMenos(ts.map((d) => d.xg_understat), 1))}</b>.`
  : html`Probability that ${quien} would score <b>${goles} or more</b> with their ${ts.length} shots: <b>${pct(probAlMenos(ts.map((d) => d.xg_understat), goles))}</b>.`;
const t = tiros.filter((d) => d.game_id === p.game_id);
const tRM = t.filter((d) => d.equipo === "Real Madrid");
const tRiv = t.filter((d) => d.equipo !== "Real Madrid");
const merecido = resultadoMerecido(tRM.map((d) => d.xg_understat), tRiv.map((d) => d.xg_understat));
const merecidoPropio = resultadoMerecido(tRM.map((d) => d.xg_propio), tRiv.map((d) => d.xg_propio));
const local = p.condicion === "Local" ? "Real Madrid" : p.rival;
const visitante = p.condicion === "Local" ? p.rival : "Real Madrid";
const marcador = p.condicion === "Local" ? `${p.gf} – ${p.gc}` : `${p.gc} – ${p.gf}`;
const R = nombre(p.rival);
const lado = (e) => html`<div class="lado"><div class="escudo-grande">${escudo(e, 48)}</div><div class="nombre">${nombre(e)}</div></div>`;
// goleadores de cada equipo (los autogoles no son tiros y no aparecen)
const goles = (eq) => t.filter((d) => d.resultado === "gol" && (eq === "Real Madrid" ? d.equipo === eq : d.equipo !== "Real Madrid"))
  .sort((a, b) => a.minuto - b.minuto).map((d) => `${d.jugador} ${d.minuto}'`);
```

<div class="card destacada">
  <div class="etiqueta">Matchday ${p.jornada} · LaLiga ${p.temporada}</div>
  <div class="cuando">${fechaHora(p.fecha)}</div>
  <div class="duelo">
    ${lado(local)}
    <div class="marcador">${marcador}</div>
    ${lado(visitante)}
  </div>
  <div class="duelo" style="margin-top:0;align-items:start;font-size:0.85rem">
    <div>${goles(local).map((g) => html`<div>⚽ ${g}</div>`)}</div><div></div><div>${goles(visitante).map((g) => html`<div>⚽ ${g}</div>`)}</div>
  </div>
  <div class="nota" style="text-align:center">xG ${num(p.condicion === "Local" ? p.xgf : p.xgc)} – ${num(p.condicion === "Local" ? p.xgc : p.xgf)} · shots ${p.condicion === "Local" ? tRM.length : tRiv.length} – ${p.condicion === "Local" ? tRiv.length : tRM.length}</div>
</div>

## Shot map

<div class="card">
  <div class="leyenda"><span class="rm">Real Madrid, attacking to the right</span><span class="rival">${R}, to the left</span><span class="sin">Filled = goal · size = xG</span></div>
  ${resize((width) => mapaTiros(t, {width}))}
</div>

## How the match unfolded

```js
function xgAcumulado(width) {
  const serie = (arr, nombre) => {
    let acc = 0;
    const filas = [{minuto: 0, xg: 0, equipo: nombre}];
    for (const d of arr.slice().sort((a, b) => a.minuto - b.minuto)) {
      acc += d.xg_understat;
      filas.push({minuto: d.minuto, xg: acc, equipo: nombre, jugador: d.jugador, gol: d.resultado === "gol", tiro: d.xg_understat});
    }
    filas.push({minuto: 95, xg: acc, equipo: nombre});
    return filas;
  };
  const datos = [...serie(tRM, "Real Madrid"), ...serie(tRiv, p.rival)];
  const color = {domain: ["Real Madrid", p.rival], range: ["var(--rm)", "var(--rival)"]};
  return Plot.plot({
    width, height: 280, color,
    x: {label: "Minute", domain: [0, 95], ticks: [0, 15, 30, 45, 60, 75, 90]},
    y: {label: "Cumulative xG", grid: true, tickFormat: tickNum},
    marks: [
      Plot.ruleX([45], {stroke: "var(--theme-foreground-faint)", strokeDasharray: "3,3"}),
      Plot.line(datos, {x: "minuto", y: "xg", stroke: "equipo", strokeWidth: 2, curve: "step-after"}),
      Plot.dot(datos.filter((d) => d.gol), {x: "minuto", y: "xg", fill: "equipo", r: 6, stroke: "var(--theme-background)", strokeWidth: 2}),
      Plot.tip(datos.filter((d) => d.jugador), Plot.pointer({x: "minuto", y: "xg",
        title: (d) => `${d.minuto}' · ${d.jugador}\nShot worth ${num(d.tiro)} xG${d.gol ? " · GOAL" : ""}\nCumulative ${d.equipo}: ${num(d.xg)}`}))
    ]
  });
}
```

<div class="card">
  <div class="leyenda"><span class="rm">Real Madrid</span><span class="rival">${R}</span><span class="sin">Dot = goal</span></div>
  ${resize((width) => xgAcumulado(width))}
  <div class="nota">Goals: ${t.filter((d) => d.resultado === "gol").sort((a, b) => a.minuto - b.minuto).map((d) => `${d.minuto}' ${d.jugador} (${d.equipo === "Real Madrid" ? "RMA" : corto(p.rival)})`).join(" · ") || "none"}. Own goals are not shots and are not shown.</div>
</div>

## What did the chances deserve?

<div class="grid grid-cols-2">
  <div class="card">
    <h3>Result according to the shots</h3>
    <p>If the match were replayed with exactly the same chances and each shot went in with probability equal to its xG:</p>
    ${barraPartido({local, visitante, p_victoria: merecido.victoria, p_empate: merecido.empate, p_derrota: merecido.derrota}, nombre)}
    <p class="nota">Expected points: <b>${num(merecido.puntosEsperados)}</b> (actual: ${p.puntos}). With our own xG model: ${num(merecidoPropio.puntosEsperados)}.</p>
  </div>
  <div class="card">
    <h3>Skill or luck?</h3>
    <p>${frase("Madrid", tRM, p.gf)}</p>
    <p>${frase(R, tRiv, p.gc)}</p>
    <p class="nota">Low values (below 10%) mean unusual finishing; they do not say whether it was talent or luck, only that it was rare.</p>
  </div>
</div>

## Madrid players

```js
Inputs.table(jugadores.filter((d) => d.game_id === p.game_id).sort((a, b) => ORDEN[a.puesto] - ORDEN[b.puesto] || b.minutos - a.minutos), {
  columns: ["jugador", "puesto", "minutos", "goles", "asistencias", "tiros", "xg", "npxg", "xa", "pases_clave", "xg_chain"],
  header: {jugador: "Player", puesto: "Pos", minutos: "Min", goles: "G", asistencias: "A", tiros: "Shots",
    xg: "xG", npxg: "npxG", xa: "xA", pases_clave: "Key passes", xg_chain: "xGChain"},
  format: {puesto: puestoTxt, xg: (d) => num(d), npxg: (d) => num(d), xa: (d) => num(d), xg_chain: (d) => num(d)},
  width: {jugador: 170}, layout: "auto",
  select: false, rows: 16
})
```
