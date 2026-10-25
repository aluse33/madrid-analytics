---
title: Monte Carlo simulation
toc: false
---
<!-- GENERADO por `rma traducir` a partir de ../montecarlo.md: no editar a mano -->

```js
import {num, pct, ent, fecha, tickNum, tickPct, LOC, letra, ordinal} from "../components/formato.js";
import {escudo, escudoUrl, nombre, conEscudo} from "../equipos/equipos.js";

const sim = FileAttachment("../data/simulacion.json").json();
```

```js
const seguidos = sim.trayectorias.equipos;
const COLOR = {domain: seguidos, range: ["var(--rm)", "var(--rival)", "var(--modelo)"].slice(0, seguidos.length)};
const fechas = sim.trayectorias.fechas.map((f) => new Date(f));
const rmSim = sim.tabla.find((d) => d.equipo === "Real Madrid");
```

# Monte Carlo simulation

The league is played ${ent(sim.n)} times on the computer. In each simulation the ${sim.pendientes} remaining matches are decided by a random scoreline drawn from the Dixon-Coles model, and the final table is sorted. The probability of something is simply the share of simulations in which it happens.

<div class="grid grid-cols-3">
  <div class="card kpi">
    <div class="etiqueta">Real Madrid champions</div>
    <div class="cifra">${pct(rmSim.p_campeon, 1)}</div>
    <div class="nota">in ${ent(sim.n * rmSim.p_campeon)} of ${ent(sim.n)} simulations</div>
  </div>
  <div class="card kpi">
    <div class="etiqueta">Madrid final points</div>
    <div class="cifra">${ent(rmSim.puntos_media)}</div>
    <div class="nota">90% of simulations between ${ent(rmSim.puntos_p05)} and ${ent(rmSim.puntos_p95)}</div>
  </div>
  <div class="card kpi">
    <div class="etiqueta">Favourite</div>
    <div class="cifra" style="display:flex;align-items:center;gap:0.5rem">${escudo(sim.tabla[0].equipo, 40)} ${pct(d3.max(sim.tabla, (d) => d.p_campeon))}</div>
    <div class="nota">${nombre(d3.greatest(sim.tabla, (d) => d.p_campeon).equipo)}</div>
  </div>
</div>

## What is at stake in the next match

```js
const clave = sim.clave;
const ETIQ = {V: "If Madrid win", E: "If it is a draw", D: "If Madrid lose"};
```

```js
display(clave ? html`<p>The same simulations, split by how <b>${nombre(clave.local)} – ${nombre(clave.visitante)}</b> ends. Since the rest of the season is played the same way, the gap between columns is what this match is worth.</p>
<div class="grid grid-cols-3">${clave.condicionado.map((c) => html`<div class="card ${c.resultado === "V" ? "destacada" : ""}">
  <div class="etiqueta"><span class="res res-${c.resultado}">${letra(c.resultado)}</span> ${ETIQ[c.resultado]}</div>
  <div class="nota">Happens in ${pct(c.p_resultado)} of simulations</div>
  <div class="cifra">${pct(c.p_campeon_rm, 1)}</div>
  <div class="nota">Madrid title probability${clave.lider && clave.lider !== "Real Madrid" ? html` · ${nombre(clave.lider)}: ${pct(c.p_campeon_lider)}` : ""}</div>
</div>`)}</div>` : html`<p class="nota">No matches left.</p>`);
```

## Points matchday by matchday

```js
function abanico(width) {
  const q = sim.trayectorias.cuantiles.map((d) => ({...d, fecha: new Date(d.fecha), equipoN: nombre(d.equipo)}));
  const lineas = sim.trayectorias.muestra.flatMap((s) => s.puntos.map((p, t) => ({sim: s.sim, equipo: s.equipo, equipoN: nombre(s.equipo), fecha: fechas[t], puntos: p})));
  return Plot.plot({
    width, height: 240 * seguidos.length, marginLeft: 50, marginRight: 20,
    x: {label: null, type: "utc"},
    y: {label: "Points", grid: true, tickFormat: tickNum},
    fy: {label: null, domain: seguidos.map(nombre), axis: null},
    color: COLOR,
    marks: [
      Plot.frame({stroke: "var(--borde)"}),
      Plot.text(seguidos.map(nombre), {fy: (d) => d, text: (d) => d, frameAnchor: "top-left", dx: 10, dy: 10, fontWeight: 700, fontSize: 13}),
      // 50 individual simulations, finas: cada una es una temporada posible
      Plot.line(lineas, {x: "fecha", y: "puntos", z: "sim", fy: "equipoN", stroke: "equipo", strokeWidth: 0.6, strokeOpacity: 0.25, curve: "step-after"}),
      Plot.areaY(q, {x: "fecha", y1: "p05", y2: "p95", fy: "equipoN", fill: "equipo", fillOpacity: 0.12, curve: "step-after"}),
      Plot.areaY(q, {x: "fecha", y1: "p25", y2: "p75", fy: "equipoN", fill: "equipo", fillOpacity: 0.22, curve: "step-after"}),
      Plot.line(q, {x: "fecha", y: "p50", fy: "equipoN", stroke: "equipo", strokeWidth: 2.5, curve: "step-after"}),
      Plot.text(q.filter((d, i, a) => i === a.length - 1 || a[i + 1].equipo !== d.equipo),
        {x: "fecha", y: "p50", fy: "equipoN", text: (d) => `${ent(d.p50)} pts`, dx: -4, dy: -12, textAnchor: "end", fontWeight: 700}),
      Plot.tip(q, Plot.pointer({x: "fecha", y: "p50", fy: "equipoN",
        title: (d) => `${d.equipoN} · ${fecha(d.fecha)}\nMedian ${ent(d.p50)} points\n50%: ${ent(d.p25)}–${ent(d.p75)} · 90%: ${ent(d.p05)}–${ent(d.p95)}`}))
    ]
  });
}
```

<div class="card">
  <div class="leyenda"><span class="sin">Thick line: median · dark band: middle 50% · light band: 90% · thin lines: 50 simulated seasons</span></div>
  ${resize((width) => abanico(width))}
</div>

## Distribution of final points

```js
function histogramas(width) {
  const d = sim.distribucion_puntos.map((x) => ({...x, equipoN: nombre(x.equipo)}));
  const medias = seguidos.map((e) => ({equipoN: nombre(e), media: sim.tabla.find((t) => t.equipo === e).puntos_media}));
  return Plot.plot({
    width, height: 130 * seguidos.length + 40, marginLeft: 50,
    x: {label: "Points at the end of the season", grid: true, tickFormat: tickNum},
    y: {label: null, axis: null},
    fy: {label: null, domain: seguidos.map(nombre), axis: null},
    color: COLOR,
    marks: [
      Plot.text(seguidos.map(nombre), {fy: (d) => d, text: (d) => d, frameAnchor: "top-left", dy: 4, fontWeight: 700, fontSize: 13}),
      Plot.rectY(d, {x1: (x) => x.puntos - 0.45, x2: (x) => x.puntos + 0.45, y: "prob", fy: "equipoN", fill: "equipo", rx: 1}),
      Plot.ruleX(medias, {x: "media", fy: "equipoN", stroke: "var(--texto)", strokeDasharray: "3,3"}),
      Plot.text(medias, {x: "media", fy: "equipoN", frameAnchor: "top", text: (m) => `mean ${num(m.media, 1)}`, dy: 22, dx: 4, textAnchor: "start", fontSize: 11}),
      Plot.tip(d, Plot.pointerX({x: "puntos", y: "prob", fy: "equipoN", title: (x) => `${x.equipoN}: ${x.puntos} points in ${pct(x.prob, 1)} of simulations`}))
    ]
  });
}
```

<div class="card">${resize((width) => histogramas(width))}</div>

## Who finishes where?

```js
const orden = sim.tabla.map((d) => d.equipo);
function matrizPuestos(width) {
  const d = sim.puestos.filter((x) => x.prob > 0).map((x) => ({...x, equipoN: nombre(x.equipo)}));
  return Plot.plot({
    width, height: 28 * orden.length + 60, marginLeft: 160, padding: 0.06,
    x: {label: "Final position", axis: "top", domain: d3.range(1, orden.length + 1), tickFormat: ordinal},
    y: {label: null, domain: orden.map(nombre)},
    marks: [
      // intensidad = probabilidad (transparencia sobre el color del Madrid: vale en claro y en oscuro)
      Plot.cell(d, {x: "puesto", y: "equipoN", fill: "var(--rm)", fillOpacity: (x) => 0.06 + 0.94 * Math.min(1, x.prob / 0.6), rx: 3}),
      // etiquetas solo donde hay probabilidad apreciable
      Plot.text(d.filter((x) => x.prob >= 0.1), {x: "puesto", y: "equipoN", text: (x) => Math.round(100 * x.prob),
        fill: (x) => (x.prob > 0.3 ? "white" : "var(--texto)"), fontSize: 11, fontWeight: 600}),
      Plot.tip(d, Plot.pointer({x: "puesto", y: "equipoN", title: (x) => `${x.equipoN}: ${ordinal(x.puesto)} in ${pct(x.prob, 1)} of simulations`}))
    ]
  });
}
```

<div class="card">
  ${resize((width) => matrizPuestos(width))}
  <div class="nota">Each row sums to 100%. Numbers: share of simulations (shown from 10%). Teams sorted by expected points.</div>
</div>

## Why fixing each team's strength is not enough

```js
const comp = sim.comparacion.filter((d) => d.p_campeon > 0.001 || d.p_ingenua > 0.001)
  .flatMap((d) => [{equipo: d.equipo, tipo: "Fixed, known strengths", p: d.p_ingenua}, {equipo: d.equipo, tipo: "With uncertainty", p: d.p_campeon}]);
const der = sim.deriva;
```

<div class="grid grid-cols-2">
  <div class="card">
    <p>A naive simulation takes each team's estimated strength as given, as if it were known exactly and would not change until May. That makes it overconfident. This simulation adds three sources of uncertainty:</p>
    <ol>
      <li><b>Estimation error</b> in the strengths (sandwich covariance matrix of the fit).</li>
      <li><b>Lag:</b> the model averages up to three years of matches, but today's team is not the one from two seasons ago. This adds a standard deviation of ${num(der.sd_desfase_ataque, 3)} to attack (log scale).</li>
      <li><b>Future drift:</b> strength keeps moving like a random walk, about ${num(der.sd_200_dias_ataque, 2)} every 200 days, estimated by comparing ${der.pares_ataque} pairs of half-seasons.</li>
    </ol>
    <p class="nota">Details and formulas in <a href="./metodologia">Methodology</a>.</p>
  </div>
  <div class="card">
    <div class="leyenda"><span class="sin">○ Fixed, known strengths</span><span class="rm">With uncertainty</span></div>
    ${resize((width) => Plot.plot({
      width, height: 60 + 44 * new Set(comp.map((d) => d.equipo)).size, marginLeft: 150,
      x: {label: "Chance of winning the league", domain: [0, 1], grid: true, tickFormat: tickPct},
      y: {label: null, domain: [...new Set(comp.map((d) => d.equipo))].map(nombre)},
      marks: [
        Plot.link(sim.comparacion.filter((d) => d.p_campeon > 0.001 || d.p_ingenua > 0.001),
          {x1: "p_ingenua", x2: "p_campeon", y1: (d) => nombre(d.equipo), y2: (d) => nombre(d.equipo), stroke: "var(--theme-foreground-faint)", strokeWidth: 2}),
        Plot.dot(comp.filter((d) => d.tipo !== "With uncertainty"), {x: "p", y: (d) => nombre(d.equipo), r: 6, stroke: "var(--texto-suave)", strokeWidth: 2, fill: "var(--panel)"}),
        Plot.dot(comp.filter((d) => d.tipo === "With uncertainty"), {x: "p", y: (d) => nombre(d.equipo), r: 6, fill: "var(--rm)", stroke: "var(--panel)", strokeWidth: 2}),
        Plot.text(comp.filter((d) => d.tipo === "With uncertainty"), {x: "p", y: (d) => nombre(d.equipo), text: (d) => pct(d.p, 1), dy: -14, fontSize: 11, fontWeight: 600}),
        Plot.tip(comp, Plot.pointer({x: "p", y: (d) => nombre(d.equipo), title: (d) => `${nombre(d.equipo)} · ${d.tipo}: ${pct(d.p, 1)}`}))
      ]
    }))}
    <div class="nota">With uncertainty, favourites drop and chasers rise: the future is less certain than the estimated strengths suggest.</div>
  </div>
</div>

## Are ${ent(sim.n)} simulations enough?

```js
const conv = sim.convergencia.map((d) => ({...d, equipoN: nombre(d.equipo), lo: Math.max(0, d.p - 1.96 * d.se), hi: Math.min(1, d.p + 1.96 * d.se)}));
const finalRM = conv.filter((d) => d.equipo === "Real Madrid").at(-1);
```

<div class="card">
  <div class="leyenda">${seguidos.map((e, i) => html`<span class="${["rm", "rival", "modelo"][i]}">${nombre(e)}</span>`)}<span class="sin">Band: 95% interval of the Monte Carlo error</span></div>
  ${resize((width) => Plot.plot({
    width, height: 300,
    x: {label: "Number of simulations", type: "log", grid: true, tickFormat: (d) => d.toLocaleString(LOC)},
    y: {label: "Chance of winning the league", domain: [0, 1], grid: true, tickFormat: tickPct},
    color: COLOR,
    marks: [
      Plot.areaY(conv, {x: "n", y1: "lo", y2: "hi", fill: "equipo", fillOpacity: 0.15}),
      Plot.line(conv, {x: "n", y: "p", stroke: "equipo", strokeWidth: 2}),
      Plot.tip(conv, Plot.pointerX({x: "n", y: "p", title: (d) => `${d.equipoN} with ${d.n.toLocaleString(LOC)} simulations: ${pct(d.p, 1)} ± ${pct(1.96 * d.se, 1)}`}))
    ]
  }))}
  <div class="nota">With few simulations the estimate jumps around; from a few thousand on it settles. With ${ent(sim.n)}, the Monte Carlo error on Madrid's probability is ±${pct(1.96 * finalRM.se, 1)}: much smaller than the uncertainty of the model itself.</div>
</div>
