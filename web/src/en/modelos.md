---
title: Model lab
toc:
  label: "On this page"
---
<!-- GENERADO por `rma traducir` a partir de ../modelos.md: no editar a mano -->

```js
import {num, pct, tickNum, tickPct, LOC} from "../components/formato.js";
const xg = FileAttachment("../data/xg_modelo.json").json();
const backtest = FileAttachment("../data/backtest.json").json();
```

# Model lab

Models are evaluated honestly here: always **out of sample** and always against a simple baseline. A model that cannot beat the baseline does not deserve to be on the site.

## Our own xG model

Trained on ${xg.n_tiros.toLocaleString(LOC)} LaLiga shots (penalties excluded; they get their empirical rate: ${pct(xg.tasa_penalti, 1)}). Cross-validation in ${5} folds **grouped by match**, so shots from the same match are never in both training and test.

```js
const nombres = {logistico: "Logistic regression", boosting: "Gradient boosting", understat: "Understat xG", tasa_base: "Average rate (baseline)"};
const metricas = Object.entries(xg.metricas_cv).map(([k, v]) => ({modelo: nombres[k] ?? k, ...v}));
```

```js
Inputs.table(metricas, {
  columns: ["modelo", "log_loss", "brier", "auc", "ece"],
  header: {modelo: "Model", log_loss: "Log-loss ↓", brier: "Brier ↓", auc: "AUC ↑", ece: "ECE ↓"},
  format: {log_loss: (d) => num(d, 4), brier: (d) => num(d, 4), auc: (d) => num(d, 3), ece: (d) => num(d, 4)},
  select: false
})
```

<div class="nota">Log-loss and Brier measure calibration and discrimination together; AUC only discrimination (does it rank shots well?); ECE only calibration (does a 0.20 go in 20% of the time?).</div>

```js
const serieFiab = Object.entries(xg.fiabilidad)
  .filter(([k]) => ["boosting", "understat"].includes(k))
  .flatMap(([k, v]) => v.map((d) => ({...d, modelo: nombres[k]})));
function fiabilidad(width) {
  return Plot.plot({
    width, height: 360,
    x: {label: "Predicted xG (bin average)", type: "sqrt", domain: [0, 0.8], grid: true, tickFormat: tickNum},
    y: {label: "Observed goal rate", type: "sqrt", domain: [0, 0.8], grid: true, tickFormat: tickNum},
    color: {domain: [nombres.boosting, nombres.understat], range: ["var(--modelo)", "var(--rival)"]},
    marks: [
      Plot.line([[0, 0], [0.8, 0.8]], {stroke: "var(--theme-foreground-faint)", strokeDasharray: "4,4"}),
      Plot.line(serieFiab, {x: "predicho", y: "observado", stroke: "modelo", strokeWidth: 2}),
      Plot.dot(serieFiab, {x: "predicho", y: "observado", fill: "modelo", r: 4.5, stroke: "var(--theme-background)", strokeWidth: 2}),
      Plot.tip(serieFiab, Plot.pointer({x: "predicho", y: "observado",
        title: (d) => `${d.modelo}\nPredicted ${num(d.predicho, 3)} · observed ${num(d.observado, 3)}\n${d.n.toLocaleString(LOC)} shots`}))
    ]
  });
}
```

<div class="card">
  <h3>Reliability diagram</h3>
  <div class="leyenda"><span class="modelo">Our model (gradient boosting)</span><span class="rival">Understat</span><span class="sin">Diagonal = perfect calibration</span></div>
  ${resize((width) => fiabilidad(width))}
  <div class="nota">Each dot groups a tenth of the shots. Square-root axes to show the low-xG region, where most shots are.</div>
</div>

```js
const coefs = Object.entries(xg.coeficientes_logistico).map(([k, v]) => ({
  rasgo: k.replace("num__", "").replace("cat__situacion_", "situation: ").replace("_", " ").replace("log distancia", "log distance").replace("distancia", "distance").replace("angulo", "angle").replace("cabeza", "header"), coef: v
})).sort((a, b) => a.coef - b.coef);
```

<div class="card">
  <h3>What the logistic regression learns</h3>
  ${resize((width) => Plot.plot({
    width, height: 30 * coefs.length + 40, marginLeft: 190,
    x: {label: "Coefficient (standardised numeric features; situations vs open play)", grid: true, tickFormat: tickNum},
    y: {label: null, domain: coefs.map((d) => d.rasgo)},
    marks: [
      Plot.ruleX([0], {stroke: "var(--theme-foreground-faint)"}),
      Plot.barX(coefs, {y: "rasgo", x: "coef", fill: (d) => (d.coef > 0 ? "var(--modelo)" : "var(--rival)"), rx: 3, insetTop: 4, insetBottom: 4}),
      Plot.tip(coefs, Plot.pointerY({y: "rasgo", x: "coef", title: (d) => `${d.rasgo}: ${num(d.coef, 3)}`}))
    ]
  }))}
  <div class="nota">Aqua: raises the goal probability. Orange: lowers it.</div>
</div>

## Dixon-Coles: does it beat knowing nothing?

Predictions made **week by week** with only what was known at the time (rolling origin), for ${backtest.n.toLocaleString(LOC)} LaLiga matches. The baseline gives every match the historical frequencies of home win, draw and away win.

```js
const bt = backtest.por_temporada.flatMap((d) => [
  {temporada: d.temporada, modelo: "Dixon-Coles", rps: d.rps_modelo},
  {temporada: d.temporada, modelo: "Baseline (frequencies)", rps: d.rps_base}
]);
```

<div class="grid grid-cols-2">
  <div class="card">
    <h3>Ranked Probability Score (lower is better)</h3>
    <div class="leyenda"><span class="modelo">Dixon-Coles</span><span class="sin">Grey: baseline</span></div>
    ${resize((width) => Plot.plot({
      width, height: 260,
      x: {label: null, domain: backtest.por_temporada.map((d) => d.temporada)},
      y: {label: "Mean RPS", grid: true, zero: false, tickFormat: tickNum},
      fx: {label: null},
      color: {domain: ["Dixon-Coles", "Baseline (frequencies)"], range: ["var(--modelo)", "var(--theme-foreground-muted)"]},
      marks: [
        Plot.dot(bt, {x: "temporada", y: "rps", fill: "modelo", r: 7, stroke: "var(--theme-background)", strokeWidth: 2}),
        Plot.tip(bt, Plot.pointer({x: "temporada", y: "rps", title: (d) => `${d.temporada} · ${d.modelo}\nRPS ${num(d.rps, 4)}`}))
      ]
    }))}
  </div>
  <div class="card">
    <h3>Calibration: home win</h3>
    ${resize((width) => Plot.plot({
      width, height: 260,
      x: {label: "Predicted probability", domain: [0, 1], grid: true, tickFormat: tickPct},
      y: {label: "Observed frequency", domain: [0, 1], grid: true, tickFormat: tickPct},
      r: {range: [3, 12]},
      marks: [
        Plot.line([[0, 0], [1, 1]], {stroke: "var(--theme-foreground-faint)", strokeDasharray: "4,4"}),
        Plot.dot(backtest.calibracion_local, {x: "predicho", y: "observado", r: "n", fill: "var(--modelo)", stroke: "var(--theme-background)", strokeWidth: 2}),
        Plot.tip(backtest.calibracion_local, Plot.pointer({x: "predicho", y: "observado",
          title: (d) => `Predicted ${pct(d.predicho)} · observed ${pct(d.observado)}\n${d.n} matches`}))
      ]
    }))}
    <div class="nota">Dot size: number of matches in the bin.</div>
  </div>
</div>
