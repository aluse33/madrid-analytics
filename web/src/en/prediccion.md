---
title: Prediction
toc:
  label: "On this page"
---
<!-- GENERADO por `rma traducir` a partir de ../prediccion.md: no editar a mano -->

```js
import {num, pct, ent, fecha, fechaHora, tickNum, tickPct, ordinal} from "../components/formato.js";
import {escudo, escudoUrl, nombre, conEscudo} from "../equipos/equipos.js";
const prediccion = FileAttachment("../data/prediccion.json").json();
const simulacion = FileAttachment("../data/simulacion.json").json();
const ratings = FileAttachment("../data/ratings.csv").csv({typed: true});
```

# Prediction

A **Dixon-Coles** model estimates the attacking strength and defensive weakness of every LaLiga team from the last three years of matches, giving more weight to recent ones (half-life of ${prediccion.modelo.semivida_dias} days). It learns from a mix of xG and goals: xG is much less noisy than the scoreline. Estimated home advantage: ${pct(Math.exp(prediccion.modelo.campo) - 1)} more expected goals for the home side.

## Upcoming matches

```js
Inputs.table(prediccion.partidos, {
  columns: ["fecha", "local", "visitante", "p_victoria", "p_empate", "p_derrota", "goles_esperados_rm", "goles_esperados_rival"],
  header: {fecha: "Date", local: "Home", visitante: "Away", p_victoria: "Madrid win", p_empate: "Draw", p_derrota: "Madrid loss",
    goles_esperados_rm: "Madrid exp. goals", goles_esperados_rival: "Opp. exp. goals"},
  format: {fecha: (d) => fecha(d), local: (d) => conEscudo(d), visitante: (d) => conEscudo(d), p_victoria: (d) => pct(d), p_empate: (d) => pct(d), p_derrota: (d) => pct(d),
    goles_esperados_rm: (d) => num(d), goles_esperados_rival: (d) => num(d)},
  width: {local: 190, visitante: 190}, layout: "auto",
  select: false
})
```

```js
const elegido = view(Inputs.select(prediccion.partidos, {label: "Likely scorelines", format: (d) => `${nombre(d.local)} – ${nombre(d.visitante)}`}));
```

```js
function matriz(width) {
  const m = elegido.matriz;
  const celdas = m.flatMap((fila, i) => fila.map((p, j) => ({local: i, visitante: j, p})));
  const top = celdas.slice().sort((a, b) => b.p - a.p).slice(0, 5);
  const lado = Math.min(width, 520);
  return Plot.plot({
    width: lado, height: lado * 0.9, padding: 0.06,
    x: {label: `${nombre(elegido.visitante)} goals`, axis: "top", domain: d3.range(7)},
    y: {label: `${nombre(elegido.local)} goals`, domain: d3.range(7)},
    // secuencial de un solo tono: transparencia sobre el color del Madrid (claro y oscuro)
    marks: [
      Plot.cell(celdas, {x: "visitante", y: "local", fill: "var(--rm)", fillOpacity: (d) => 0.05 + 0.95 * d.p / d3.max(celdas, (c) => c.p), rx: 4}),
      // etiquetas solo en los cinco marcadores más probables (selectivas, no en todas las celdas)
      Plot.text(top, {x: "visitante", y: "local", text: (d) => pct(d.p), fill: "white", fontWeight: 700, fontSize: 12}),
      Plot.tip(celdas, Plot.pointer({x: "visitante", y: "local", title: (d) => `${nombre(elegido.local)} ${d.local} – ${d.visitante} ${nombre(elegido.visitante)}\n${pct(d.p, 1)}`}))
    ]
  });
}
```

<div class="card">
  ${resize((width) => matriz(width))}
  <div class="nota">Each cell is the probability of an exact score; the diagonal is draws. The Dixon-Coles correction (ρ = ${num(prediccion.modelo.rho, 3)}) adjusts low-scoring results.</div>
</div>

## Simulating the rest of the season

${simulacion ? html`${ent(simulacion.n)} seasons simulated from the ${simulacion.pendientes} remaining matches, allowing for the fact that each team's strength is uncertain and changes over time. Trajectories, distributions and the method in detail: <a href="./montecarlo">Monte Carlo simulation</a>.` : "The season is over."}

```js
function puestos(width) {
  const d = simulacion.rm_dist_puesto.map((p, i) => ({puesto: i + 1, p})).filter((d) => d.p > 0.0005);
  return Plot.plot({
    width, height: 240, marginTop: 34,
    x: {label: "Real Madrid final position", domain: d.map((x) => x.puesto), tickFormat: ordinal},
    y: {label: "Probability", grid: true, tickFormat: tickPct},
    marks: [
      Plot.barY(d, {x: "puesto", y: "p", fill: "var(--rm)", rx: 4, insetLeft: 1, insetRight: 1}),
      Plot.text(d.filter((x) => x.p >= 0.02), {x: "puesto", y: "p", text: (x) => pct(x.p), dy: -8, fontWeight: 600}),
      Plot.tip(d, Plot.pointerX({x: "puesto", y: "p", title: (x) => `${ordinal(x.puesto)}: ${pct(x.p, 1)}`}))
    ]
  });
}
```

<div class="card">${simulacion ? resize((width) => puestos(width)) : ""}</div>

```js
Inputs.table(simulacion.tabla, {
  columns: ["equipo", "puntos_actuales", "puntos_media", "puntos_p05", "puntos_p95", "p_campeon", "p_top4", "p_descenso"],
  header: {equipo: "Team", puntos_actuales: "Points now", puntos_media: "Final points (mean)", puntos_p05: "P5", puntos_p95: "P95",
    p_campeon: "Title", p_top4: "Top 4", p_descenso: "Relegation"},
  format: {equipo: (d) => conEscudo(d), puntos_media: (d) => num(d, 1), puntos_p05: ent, puntos_p95: ent, puntos_actuales: ent,
    p_campeon: (d) => pct(d, 1), p_top4: (d) => pct(d, 1), p_descenso: (d) => pct(d, 1)},
  width: {equipo: 210}, layout: "auto",
  select: false, rows: 21
})
```

## Team strength

```js
function fuerzas(width) {
  const enLiga = new Set(simulacion.tabla.map((d) => d.equipo));
  const actuales = ratings.filter((d) => enLiga.has(d.equipo));
  return Plot.plot({
    width, height: 440, inset: 20, marginRight: 90,
    x: {label: "Attack: goals created vs average (×) →", grid: true, tickFormat: tickNum},
    y: {label: "↑ Defence: goals conceded vs average (×), lower is better", grid: true, reverse: true, tickFormat: tickNum},
    marks: [
      Plot.ruleX([1], {stroke: "var(--theme-foreground-faint)"}),
      Plot.ruleY([1], {stroke: "var(--theme-foreground-faint)"}),
      // Madrid with a halo para encontrarlo de un vistazo
      Plot.dot(actuales.filter((d) => d.equipo === "Real Madrid"), {x: "ataque", y: "defensa", r: 22, fill: "var(--rm)", fillOpacity: 0.18, stroke: "var(--rm)"}),
      Plot.image(actuales, {x: "ataque", y: "defensa", src: (d) => escudoUrl(d.equipo), width: 26, height: 30}),
      Plot.tip(actuales, Plot.pointer({x: "ataque", y: "defensa",
        title: (d) => `${nombre(d.equipo)}\nAttack ×${num(d.ataque)} · Defence ×${num(d.defensa)}`}))
    ]
  });
}
```

<div class="card">
  ${resize((width) => fuerzas(width))}
  <div class="nota">Top right are the best: they create more and concede less than an average LaLiga team. Values include shrinkage towards the mean (L2 penalty), so extremes are pulled in slightly on purpose.</div>
</div>
