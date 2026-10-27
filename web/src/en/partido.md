---
title: Match
toc: false
---
<!-- GENERADO por `rma traducir` a partir de ../partido.md: no editar a mano -->

```js
import {num, pct, ent, fecha, fechaHora, tickNum, puestoTxt, t as tr} from "../components/formato.js";
import {mapaTiros} from "../components/campo.js";
import {resultadoMerecido, probAlMenos} from "../components/probabilidad.js";
import {barraPartido} from "../components/ui.js";
import {cronologia, alineaciones, banquillo, estadisticas, escudoDe} from "../components/eventos.js";
import {selectorPartidos, COMPETICION} from "../components/selector.js";
import {nombre, corto} from "../equipos/equipos.js";

const estado = FileAttachment("../data/estado.json").json();
const partidos = FileAttachment("../data/rm_partidos.csv").csv({typed: true});
const tiros = FileAttachment("../data/tiros_rm.csv").csv({typed: true});
const jugadores = FileAttachment("../data/jugadores_rm.csv").csv({typed: true});
const todas = FileAttachment("../data/partidos_todas.csv").csv({typed: true});
const eventos = FileAttachment("../data/eventos.json").json();
```

```js
// Todos los partidos jugados de la temporada, de cualquier competición (ESPN), con su fila de
// Understat cuando es de Liga (tiros, xG, jugadores). Si ESPN faltara, quedan los de Liga.
const liga = partidos.filter((d) => d.temporada === estado.temporada && d.jugado);
const deLiga = (e) => liga.find((u) => u.rival === e.rival && Math.abs(u.fecha - e.fecha) < 2 * 864e5);
const lista = todas.filter((d) => d.jugado).map((e) => {
  const u = e.liga === "esp.1" ? deLiga(e) : null;
  return {...e, clave: `e${e.id}`, u, jornada: u?.jornada, det: eventos[String(e.id)] ?? null};
});
for (const u of liga) {
  if (lista.some((x) => x.u === u)) continue;
  const casa = u.condicion === "Local";
  lista.push({clave: `u${u.game_id}`, fecha: u.fecha, liga: "esp.1", jornada: u.jornada, u, det: null,
    local: casa ? "Real Madrid" : u.rival, visitante: casa ? u.rival : "Real Madrid",
    goles_local: casa ? u.gf : u.gc, goles_visitante: casa ? u.gc : u.gf, resultado: u.resultado});
}
lista.sort((a, b) => b.fecha - a.fecha);
const pedido = new URLSearchParams(location.search).get("p");
const elegido = view(selectorPartidos(lista, {value: lista.find((d) => d.clave === pedido) ?? lista[0]}));
```

```js
history.replaceState(null, "", `?p=${elegido.clave}`);
const P = elegido;           // el partido (cualquier competición)
const p = P.u;               // su fila de Understat, solo en Liga
const det = P.det;           // su ficha de ESPN, si la hay
const local = P.local, visitante = P.visitante;
const rival = local === "Real Madrid" ? visitante : local;
const R = nombre(rival);
const t = p ? tiros.filter((d) => d.game_id === p.game_id) : [];
const tRM = t.filter((d) => d.equipo === "Real Madrid");
const tRiv = t.filter((d) => d.equipo !== "Real Madrid");
const comp = COMPETICION[P.liga]?.corto ?? P.competicion;
const FASES = {"League Phase": tr("Fase liga", "League phase"), "Round of 16": tr("Octavos", "Round of 16"), "Quarterfinals": tr("Cuartos", "Quarter-finals"),
  "Semifinals": tr("Semifinales", "Semi-finals"), "Final": tr("Final", "Final"), "Knockout Round Playoffs": tr("Eliminatoria previa", "Play-offs")};
const subtitulo = p ? `${tr("Jornada", "Matchday")} ${p.jornada}` : FASES[P.fase] ?? P.fase ?? "";
// goleadores: de la cronología de ESPN si la hay (incluye autogoles); si no, de los tiros de Understat
const golesDe = (eq) => det
  ? det.eventos.filter((e) => (e.tipo === "gol" && e.equipo === eq) || (e.tipo === "autogol" && e.equipo !== eq))
      .map((e) => `${e.jugador} ${e.reloj}${e.tipo === "autogol" ? tr(" (p.p.)", " (o.g.)") : ""}${e.subtipo?.includes("penalty") ? tr(" (pen.)", " (pen)") : ""}`)
  : t.filter((d) => d.resultado === "gol" && (eq === "Real Madrid" ? d.equipo === eq : d.equipo !== "Real Madrid"))
      .sort((a, b) => a.minuto - b.minuto).map((d) => `${d.jugador} ${d.minuto}'`);
const lado = (e, url) => html`<div class="lado"><div class="escudo-grande">${escudoDe(e, url, 48)}</div><div class="nombre">${nombre(e)}</div></div>`;
```

<div class="card destacada">
  <div class="etiqueta">${comp} · ${subtitulo}</div>
  <div class="cuando">${fechaHora(P.fecha)}</div>
  <div class="duelo">
    ${lado(local, P.escudo_local)}
    <div class="marcador">${P.goles_local} – ${P.goles_visitante}</div>
    ${lado(visitante, P.escudo_visitante)}
  </div>
  <div class="duelo" style="margin-top:0;align-items:start;font-size:0.85rem">
    <div>${golesDe(local).map((g) => html`<div>⚽ ${g}</div>`)}</div><div></div><div>${golesDe(visitante).map((g) => html`<div>⚽ ${g}</div>`)}</div>
  </div>
  <div class="nota" style="text-align:center">${p
    ? `xG ${num(p.condicion === "Local" ? p.xgf : p.xgc)} – ${num(p.condicion === "Local" ? p.xgc : p.xgf)} · ${tr("tiros", "shots")} ${local === "Real Madrid" ? tRM.length : tRiv.length} – ${local === "Real Madrid" ? tRiv.length : tRM.length}`
    : P.estadio ?? ""}</div>
</div>

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
if (!p) display(html`<div class="aviso">${tr("Los mapas de tiros, el xG y los datos por jugador salen de Understat, que solo cubre LaLiga. Para este partido se ve lo que da ESPN: alineaciones, cronología y estadísticas.",
  "Shot maps, xG and player data come from Understat, which only covers LaLiga. For this match you see what ESPN provides: line-ups, timeline and stats.")}</div>`);
```

```js
// ------------------------------------------------------------ solo Liga (Understat)
const ORDEN = {POR: 0, DEF: 1, MED: 2, DEL: 3};
const merecido = p ? resultadoMerecido(tRM.map((d) => d.xg_understat), tRiv.map((d) => d.xg_understat)) : null;
const merecidoPropio = p ? resultadoMerecido(tRM.map((d) => d.xg_propio), tRiv.map((d) => d.xg_propio)) : null;
// con 0 goles, "0 o más" es siempre el 100 %: lo informativo es la probabilidad de quedarse a cero
const frase = (quien, ts, goles) => goles === 0
  ? html`${tr("Probabilidad de que", "Probability that")} ${quien} ${tr("se quedara", "would be held")} <b>${tr("sin marcar", "scoreless")}</b> ${tr("con sus", "with their")} ${ts.length} ${tr("tiros", "shots")}: <b>${pct(1 - probAlMenos(ts.map((d) => d.xg_understat), 1))}</b>.`
  : html`${tr("Probabilidad de que", "Probability that")} ${quien} ${tr("marcara", "would score")} <b>${goles} ${tr("o más", "or more")}</b> ${tr("con sus", "with their")} ${ts.length} ${tr("tiros", "shots")}: <b>${pct(probAlMenos(ts.map((d) => d.xg_understat), goles))}</b>.`;

function xgAcumulado(width) {
  const serie = (arr, quien) => {
    let acc = 0;
    const filas = [{minuto: 0, xg: 0, equipo: quien}];
    for (const d of arr.slice().sort((a, b) => a.minuto - b.minuto)) {
      acc += d.xg_understat;
      filas.push({minuto: d.minuto, xg: acc, equipo: quien, jugador: d.jugador, gol: d.resultado === "gol", tiro: d.xg_understat});
    }
    filas.push({minuto: 95, xg: acc, equipo: quien});
    return filas;
  };
  const datos = [...serie(tRM, "Real Madrid"), ...serie(tRiv, rival)];
  return Plot.plot({
    width, height: 280, color: {domain: ["Real Madrid", rival], range: ["var(--rm)", "var(--rival)"]},
    x: {label: tr("Minuto", "Minute"), domain: [0, 95], ticks: [0, 15, 30, 45, 60, 75, 90]},
    y: {label: tr("xG acumulado", "Cumulative xG"), grid: true, tickFormat: tickNum},
    marks: [
      Plot.ruleX([45], {stroke: "var(--theme-foreground-faint)", strokeDasharray: "3,3"}),
      Plot.line(datos, {x: "minuto", y: "xg", stroke: "equipo", strokeWidth: 2, curve: "step-after"}),
      Plot.dot(datos.filter((d) => d.gol), {x: "minuto", y: "xg", fill: "equipo", r: 6, stroke: "var(--theme-background)", strokeWidth: 2}),
      Plot.tip(datos.filter((d) => d.jugador), Plot.pointer({x: "minuto", y: "xg",
        title: (d) => `${d.minuto}' · ${d.jugador}\n${tr("Tiro de", "Shot worth")} ${num(d.tiro)} xG${d.gol ? tr(" · GOL", " · GOAL") : ""}\n${tr("Acumulado", "Cumulative")} ${nombre(d.equipo)}: ${num(d.xg)}`}))
    ]
  });
}

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
        title: (d) => `${d.desde}′–${d.desde === 90 ? tr("final", "end") : d.desde + 5 + "′"}\n${d.rm ? "Real Madrid" : R}: ${num(Math.abs(d.xg))} xG`}))
    ]
  });
}

const delPartido = p ? jugadores.filter((d) => d.game_id === p.game_id) : [];
const impacto = delPartido.filter((d) => d.npxg + d.xa + d.goles + d.asistencias > 0).sort((a, b) => b.npxg + b.xa - (a.npxg + a.xa));
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

```js
if (p) display(html`
<h2>${tr("Mapa de tiros", "Shot map")}</h2>
<div class="card">
  <div class="leyenda"><span class="rm">${tr("Real Madrid, atacando hacia la derecha", "Real Madrid, attacking to the right")}</span><span class="rival">${R}, ${tr("hacia la izquierda", "to the left")}</span><span class="sin">${tr("Relleno = gol · tamaño = xG", "Filled = goal · size = xG")}</span></div>
  ${resize((width) => mapaTiros(t, {width}))}
</div>

<h2>${tr("Cómo se fue construyendo el partido", "How the match unfolded")}</h2>
<div class="card">
  <div class="leyenda"><span class="rm">Real Madrid</span><span class="rival">${R}</span><span class="sin">${tr("Punto = gol", "Dot = goal")}</span></div>
  ${resize((width) => xgAcumulado(width))}
  <div class="nota">${tr("Los autogoles no son tiros y no aparecen.", "Own goals are not shots and do not appear.")}</div>
</div>

<h2>${tr("Dominio del partido, cada 5 minutos", "Match momentum, every 5 minutes")}</h2>
<div class="card">
  <div class="leyenda"><span class="rm">${tr("Real Madrid (arriba)", "Real Madrid (up)")}</span><span class="rival">${R} ${tr("(abajo)", "(down)")}</span><span class="sin">⚽ ${tr("= gol en ese tramo", "= goal in that window")}</span></div>
  ${resize((width) => momentum(width))}
  <div class="nota">${tr("Suma del xG de los tiros de cada equipo en cada tramo de cinco minutos. El tiempo añadido de la segunda parte cuenta en el último tramo.", "Sum of each team's shot xG in each five-minute window. Second-half stoppage time goes into the last window.")}</div>
</div>

<h2>${tr("¿Qué merecían las ocasiones?", "What did the chances deserve?")}</h2>
<div class="grid grid-cols-2">
  <div class="card">
    <h3>${tr("Resultado según los tiros", "Result according to the shots")}</h3>
    <p>${tr("Si se repitiera el partido con exactamente las mismas ocasiones y cada tiro entrara con probabilidad igual a su xG:", "If the match were replayed with exactly the same chances and each shot went in with probability equal to its xG:")}</p>
    ${barraPartido({local, visitante, p_victoria: merecido.victoria, p_empate: merecido.empate, p_derrota: merecido.derrota}, nombre)}
    <p class="nota">${tr("Puntos esperados", "Expected points")}: <b>${num(merecido.puntosEsperados)}</b> (${tr("obtenidos", "won")}: ${p.puntos}). ${tr("Con el xG de nuestro modelo", "With our own xG model")}: ${num(merecidoPropio.puntosEsperados)}.</p>
  </div>
  <div class="card">
    <h3>${tr("¿Acierto o suerte?", "Skill or luck?")}</h3>
    <p>${frase(tr("el Madrid", "Madrid"), tRM, p.gf)}</p>
    <p>${frase(R, tRiv, p.gc)}</p>
    <p class="nota">${tr("Valores bajos (por debajo del 10 %) indican una eficacia fuera de lo normal; no dicen si fue talento o suerte, solo que fue poco habitual.", "Low values (below 10%) mean unusual finishing; they do not say whether it was talent or luck, only that it was rare.")}</p>
  </div>
</div>

<h2>${tr("Jugadores del Madrid", "Madrid players")}</h2>
<div class="card">
  <h3>${tr("Quién generó más peligro", "Who created the most danger")}</h3>
  <div class="leyenda"><span class="rm">${tr("npxG: sus tiros", "npxG: his shots")}</span><span class="modelo">${tr("xA: los tiros que dio a otros", "xA: the shots he set up")}</span><span class="sin">○ xGChain · ${tr("G/A = goles y asistencias", "G/A = goals and assists")}</span></div>
  ${impacto.length ? resize((width) => rankingImpacto(width)) : html`<p>${tr("Sin datos de jugadores para este partido.", "No player data for this match.")}</p>`}
  <div class="nota">${tr("xGChain (aro) suma el xG de todas las jugadas en las que participó, aunque no diera el último pase: premia a los que construyen. Pulsa un nombre en la tabla para ver su ficha.", "xGChain (ring) adds up the xG of every possession he took part in, even without the final pass: it rewards build-up players. Click a name in the table to open his profile.")}</div>
</div>
${Inputs.table(delPartido.slice().sort((a, b) => ORDEN[a.puesto] - ORDEN[b.puesto] || b.minutos - a.minutos), {
  columns: ["jugador", "puesto", "minutos", "goles", "asistencias", "tiros", "xg", "npxg", "xa", "pases_clave", "xg_chain"],
  header: {jugador: tr("Jugador", "Player"), puesto: tr("Puesto", "Pos."), minutos: "Min", goles: "G", asistencias: "A", tiros: tr("Tiros", "Shots"),
    xg: "xG", npxg: "npxG", xa: "xA", pases_clave: tr("Pases clave", "Key passes"), xg_chain: "xGChain"},
  format: {jugador: (j) => html`<a href="./jugador?j=${encodeURIComponent(j)}">${j}</a>`, puesto: puestoTxt, xg: (d) => num(d), npxg: (d) => num(d), xa: (d) => num(d), xg_chain: (d) => num(d)},
  width: {jugador: 170}, layout: "auto", select: false, rows: 16
})}`);
```
