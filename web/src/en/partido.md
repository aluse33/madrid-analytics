---
title: Match
toc:
  label: "On this page"
---
<!-- GENERADO por `rma traducir` a partir de ../partido.md: no editar a mano -->

```js
import {num, pct, ent, fecha, fechaHora, tickNum, puestoTxt, t as tr} from "../components/formato.js";
import {mapaTiros} from "../components/campo.js";
import {resultadoMerecido, probAlMenos} from "../components/probabilidad.js";
import {barraPartido} from "../components/ui.js";
import {cronologia, alineaciones, banquillo, estadisticas} from "../components/eventos.js";
import {escudo, nombre, corto} from "../equipos/equipos.js";

const estado = FileAttachment("../data/estado.json").json();
const partidos = FileAttachment("../data/rm_partidos.csv").csv({typed: true});
const tiros = FileAttachment("../data/tiros_rm.csv").csv({typed: true});
const jugadores = FileAttachment("../data/jugadores_rm.csv").csv({typed: true});
const todas = FileAttachment("../data/partidos_todas.csv").csv({typed: true});
const eventos = FileAttachment("../data/eventos.json").json();
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

```js
// la ficha de ESPN del mismo partido (misma jornada de Liga, mismo rival, ±2 días)
const espnP = todas.find((d) => d.liga === "esp.1" && d.rival === p.rival && Math.abs(d.fecha - p.fecha) < 2 * 864e5);
const det = espnP ? eventos[String(espnP.id)] : null;
```

```js
if (det) display(html`<h2>${tr("Lo que pasó", "What happened")}</h2>
<div class="card"><h3>${tr("Alineaciones", "Line-ups")}</h3>
  ${banquillo(det, local)}
  ${resize((width) => alineaciones(det, {width}))}
  ${banquillo(det, visitante)}
  <div class="nota">${nombre(local)} ${tr("ataca hacia la derecha", "attacks to the right")}. ▼ ${tr("minuto del cambio", "minute subbed off")}.${det.arbitro ? ` ${tr("Árbitro", "Referee")}: ${det.arbitro}.` : ""}${det.asistencia ? ` ${tr("Público", "Attendance")}: ${ent(det.asistencia)}.` : ""}</div>
</div>
<div class="grid grid-cols-2">
  <div class="card"><h3>${tr("Cronología", "Timeline")}</h3>${cronologia(det, local, visitante, nombre)}</div>
  <div class="card"><h3>${tr("Estadísticas", "Stats")}</h3>${estadisticas(det, local, visitante)}</div>
</div>`);
```

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

## ${tr("Dominio del partido, cada 5 minutos", "Match momentum, every 5 minutes")}

```js
function momentum(width) {
  // xG por tramo de 5 minutos: el Madrid hacia arriba, el rival hacia abajo; el añadido entra en el último tramo
  const tramo = (m) => Math.min(Math.floor(m / 5), 18) * 5;
  const filas = d3.rollups(t, (v) => d3.sum(v, (d) => d.xg_understat), (d) => d.equipo === "Real Madrid", (d) => tramo(d.minuto))
    .flatMap(([rm, v]) => v.map(([desde, xg]) => ({desde, xg: rm ? xg : -xg, rm})));
  const golesT = t.filter((d) => d.resultado === "gol").map((d) => ({...d, desde: tramo(d.minuto), rm: d.equipo === "Real Madrid"}));
  const tope = Math.max(0.6, d3.max(filas, (d) => Math.abs(d.xg)) ?? 0) * 1.25;
  return Plot.plot({
    width, height: 260,
    x: {domain: [0, 95], label: tr("Minuto", "Minute"), ticks: [0, 15, 30, 45, 60, 75, 90]},
    y: {domain: [-tope, tope], label: tr("xG en el tramo", "xG in the window"), grid: true, tickFormat: (v) => tickNum(Math.abs(v))},
    marks: [
      Plot.rectY(filas, {x1: "desde", x2: (d) => d.desde + 5, y: "xg", fill: (d) => (d.rm ? "var(--rm)" : "var(--rival)"), inset: 1, rx: 2}),
      Plot.ruleY([0], {stroke: "var(--theme-foreground-muted)"}),
      Plot.ruleX([45], {stroke: "var(--theme-foreground-faint)", strokeDasharray: "3,3"}),
      Plot.text(golesT, {x: (d) => d.desde + 2.5, y: (d) => (d.rm ? tope * 0.9 : -tope * 0.9), text: () => "⚽", fontSize: 14}),
      Plot.tip(filas, Plot.pointer({x: (d) => d.desde + 2.5, y: "xg",
        title: (d) => `${d.desde}′–${d.desde === 90 ? "" : d.desde + 5 + "′"}${d.desde === 90 ? tr("final", "end") : ""}\n${d.rm ? "Real Madrid" : nombre(p.rival)}: ${num(Math.abs(d.xg))} xG`}))
    ]
  });
}
```

<div class="card">
  <div class="leyenda"><span class="rm">${tr("Real Madrid (arriba)", "Real Madrid (up)")}</span><span class="rival">${R} ${tr("(abajo)", "(down)")}</span><span class="sin">⚽ ${tr("= gol en ese tramo", "= goal in that window")}</span></div>
  ${resize((width) => momentum(width))}
  <div class="nota">${tr("Suma del xG de los tiros de cada equipo en cada tramo de cinco minutos. El tiempo añadido de la segunda parte cuenta en el último tramo.", "Sum of each team's shot xG in each five-minute window. Second-half stoppage time goes into the last window.")}</div>
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
const delPartido = jugadores.filter((d) => d.game_id === p.game_id);
const impacto = delPartido.filter((d) => d.npxg + d.xa + d.goles + d.asistencias > 0)
  .sort((a, b) => b.npxg + b.xa - (a.npxg + a.xa));
function rankingImpacto(width) {
  const filas = impacto.flatMap((d) => [{jugador: d.jugador, tipo: "npxG", v: d.npxg, d}, {jugador: d.jugador, tipo: "xA", v: d.xa, d}]);
  return Plot.plot({
    width, height: 30 * impacto.length + 50, marginLeft: 150, marginRight: 60,
    x: {label: tr("npxG + xA en el partido", "npxG + xA in the match"), grid: true, tickFormat: tickNum},
    y: {domain: impacto.map((d) => d.jugador), label: null},
    color: {domain: ["npxG", "xA"], range: ["var(--rm)", "var(--modelo)"]},
    marks: [
      Plot.barX(filas, {y: "jugador", x: "v", fill: "tipo", insetTop: 5, insetBottom: 5}),
      Plot.dot(impacto, {y: "jugador", x: "xg_chain", r: 4, stroke: "var(--texto)", fill: "var(--theme-background)", strokeWidth: 1.5}),
      Plot.text(impacto.filter((d) => d.goles + d.asistencias > 0), {y: "jugador", x: (d) => Math.max(d.npxg + d.xa, d.xg_chain),
        text: (d) => [d.goles ? `${d.goles}G` : "", d.asistencias ? `${d.asistencias}A` : ""].filter(Boolean).join(" "), dx: 10, textAnchor: "start", fontWeight: 700}),
      Plot.tip(impacto, Plot.pointerY({y: "jugador", x: (d) => d.npxg + d.xa,
        title: (d) => `${d.jugador} · ${d.minutos}′\nnpxG ${num(d.npxg)} · xA ${num(d.xa)}\nxGChain ${num(d.xg_chain)} · ${tr("tiros", "shots")} ${d.tiros} · ${tr("pases clave", "key passes")} ${d.pases_clave}`}))
    ]
  });
}
```

<div class="card">
  <h3>${tr("Quién generó más peligro", "Who created the most danger")}</h3>
  <div class="leyenda"><span class="rm">${tr("npxG: sus tiros", "npxG: his shots")}</span><span class="modelo">${tr("xA: los tiros que dio a otros", "xA: the shots he set up")}</span><span class="sin">○ xGChain · ${tr("G/A = goles y asistencias", "G/A = goals and assists")}</span></div>
  ${impacto.length ? resize((width) => rankingImpacto(width)) : html`<p>${tr("Sin datos de jugadores para este partido.", "No player data for this match.")}</p>`}
  <div class="nota">${tr("xGChain (aro) suma el xG de todas las jugadas en las que participó, aunque no diera el último pase: premia a los que construyen. Pulsa un nombre en la tabla para ver su ficha.", "xGChain (ring) adds up the xG of every possession he took part in, even without the final pass: it rewards build-up players. Click a name in the table to open his profile.")}</div>
</div>

```js
Inputs.table(delPartido.slice().sort((a, b) => ORDEN[a.puesto] - ORDEN[b.puesto] || b.minutos - a.minutos), {
  columns: ["jugador", "puesto", "minutos", "goles", "asistencias", "tiros", "xg", "npxg", "xa", "pases_clave", "xg_chain"],
  header: {jugador: "Player", puesto: "Pos", minutos: "Min", goles: "G", asistencias: "A", tiros: "Shots",
    xg: "xG", npxg: "npxG", xa: "xA", pases_clave: "Key passes", xg_chain: "xGChain"},
  format: {jugador: (j) => html`<a href="./jugador?j=${encodeURIComponent(j)}">${j}</a>`, puesto: puestoTxt, xg: (d) => num(d), npxg: (d) => num(d), xa: (d) => num(d), xg_chain: (d) => num(d)},
  width: {jugador: 170}, layout: "auto",
  select: false, rows: 16
})
```
