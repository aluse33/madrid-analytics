---
title: Players
toc:
  label: "On this page"
---
<!-- GENERADO por `rma traducir` a partir de ../jugadores.md: no editar a mano -->

```js
import {num, pct, tickNum, LOC, puestoTxt} from "../components/formato.js";
const estado = FileAttachment("../data/estado.json").json();
const eb = FileAttachment("../data/jugadores_eb.csv").csv({typed: true});
const finalizacion = FileAttachment("../data/finalizacion.csv").csv({typed: true});
```

# Players: signal and noise

Early in the season, the xG per 90 minutes of someone who has barely played is mostly noise. Each player shows **two estimates**: the raw one (their numbers as they are) and the **empirical Bayes** one, which pulls them towards the LaLiga average for their position, the more so the fewer minutes they have. Bars are 90% credible intervals. The model is explained in [Methodology](./metodologia).

```js
const metrica = view(Inputs.radio(new Map([["Non-penalty expected goals (npxG)", "npxg"], ["Expected assists (xA)", "xa"]]),
  {label: "Metric", value: "npxg"}));
const verTodos = view(Inputs.toggle({label: `Include players with under 270 minutes`, value: false}));
```

```js
const filas = eb.filter((d) => d.metrica === metrica && (verTodos || d.minimo_web)).sort((a, b) => b.eb_p90 - a.eb_p90);
const priores = d3.rollups(filas, (v) => v[0].prior_media_p90, (d) => d.puesto);
```

```js
function bosque(width) {
  return Plot.plot({
    width, height: 28 * filas.length + 60, marginLeft: 150, marginRight: 30,
    x: {label: `${metrica === "npxg" ? "npxG" : "xA"} per 90 minutes`, grid: true, tickFormat: tickNum, nice: true},
    y: {label: null, domain: filas.map((d) => d.jugador)},
    marks: [
      Plot.ruleY(filas, {y: "jugador", x1: "eb_inf", x2: "eb_sup", stroke: "var(--rm)", strokeWidth: 2, strokeOpacity: 0.55}),
      // bruto: aro; EB: punto sólido
      Plot.dot(filas, {y: "jugador", x: "bruto_p90", r: 5, stroke: "var(--theme-foreground-muted)", strokeWidth: 2, fill: "var(--theme-background)"}),
      Plot.dot(filas, {y: "jugador", x: "eb_p90", r: 6, fill: "var(--rm)", stroke: "var(--theme-background)", strokeWidth: 2}),
      Plot.tip(filas, Plot.pointerY({y: "jugador", x: "eb_p90",
        title: (d) => `${d.jugador} · ${puestoTxt(d.puesto)} · ${d.minutos.toLocaleString(LOC)} min\nRaw: ${num(d.bruto_p90)} per 90'\nEB estimate: ${num(d.eb_p90)} [${num(d.eb_inf)}, ${num(d.eb_sup)}]\nLeague average for the position: ${num(d.prior_media_p90)}\nWeight of the position average: ${pct(d.peso_prior)}`}))
    ]
  });
}
```

<div class="card">
  <div class="leyenda"><span class="sin">○ Raw</span><span class="rm">Empirical Bayes estimate (dot) and its 90% interval (line)</span></div>
  ${resize((width) => bosque(width))}
  <div class="nota">LaLiga averages by position (the value estimates are shrunk towards): ${priores.map(([p, v]) => `${puestoTxt(p)} ${num(v)}`).join(" · ")}.</div>
</div>

## Finishing: hot streak or luck?

Non-penalty goals against what their shots were worth. The last column is the probability of scoring **at least** that many goals with those shots if each one goes in with probability equal to its xG (Poisson-binomial distribution). Below 10% is an unusual hot streak; above 90% in the other column, a cold one.

```js
function finalizar(width) {
  const d = finalizacion.map((x) => ({...x, dif: x.goles - x.xg})).sort((a, b) => b.dif - a.dif);
  return Plot.plot({
    width, height: 30 * d.length + 50, marginLeft: 150, marginRight: 20,
    x: {label: "Non-penalty goals − npxG", inset: 90, grid: true, tickFormat: (v) => (v > 0 ? "+" : "") + v.toLocaleString(LOC)},
    y: {label: null, domain: d.map((x) => x.jugador)},
    marks: [
      Plot.ruleX([0], {stroke: "var(--theme-foreground-muted)"}),
      Plot.barX(d, {y: "jugador", x: "dif", fill: "var(--rm)", rx: 3, insetTop: 5, insetBottom: 5}),
      Plot.text(d.filter((x) => x.dif >= 0), {y: "jugador", x: "dif", text: (x) => `${x.goles} G / ${num(x.xg, 1)} npxG`, dx: 6, textAnchor: "start", fontSize: 11}),
      Plot.text(d.filter((x) => x.dif < 0), {y: "jugador", x: "dif", text: (x) => `${x.goles} G / ${num(x.xg, 1)} npxG`, dx: -6, textAnchor: "end", fontSize: 11}),
      Plot.tip(d, Plot.pointerY({y: "jugador", x: "dif",
        title: (x) => `${x.jugador}\n${x.goles} goals from ${num(x.xg)} npxG in ${x.tiros} shots\nP(≥ ${x.goles} goals) = ${pct(x.p_al_menos)}\nP(≤ ${x.goles} goals) = ${pct(x.p_como_mucho)}`}))
    ]
  });
}
```

<div class="card">
  ${resize((width) => finalizar(width))}
  <div class="nota">Right of zero: more goals than their shots were worth; left: fewer. The table says whether the gap is rare or normal.</div>
</div>

```js
Inputs.table(finalizacion, {
  columns: ["jugador", "tiros", "goles", "xg", "p_al_menos", "p_como_mucho"],
  header: {jugador: "Player", tiros: "Shots", goles: "Goals", xg: "npxG", p_al_menos: "P(≥ goals)", p_como_mucho: "P(≤ goals)"},
  format: {xg: (d) => num(d), p_al_menos: (d) => pct(d, 1), p_como_mucho: (d) => pct(d, 1)},
  width: {jugador: 170}, layout: "auto",
  select: false
})
```
