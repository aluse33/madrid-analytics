---
title: Laboratorio de modelos
---

```js
import {num, pct, tickNum, tickPct} from "./components/formato.js";
const xg = FileAttachment("data/xg_modelo.json").json();
const backtest = FileAttachment("data/backtest.json").json();
```

# Laboratorio de modelos

Aquí se evalúan los modelos con honestidad: siempre **fuera de muestra** y siempre frente a una referencia sencilla. Un modelo que no bate a la referencia no merece estar en la web.

## Modelo xG propio

Entrenado con ${xg.n_tiros.toLocaleString("es-ES")} tiros de LaLiga (sin penaltis, que reciben su tasa empírica: ${pct(xg.tasa_penalti, 1)}). Validación cruzada en ${5} bloques **agrupados por partido**, para que los tiros de un mismo partido no estén a la vez en entrenamiento y en test.

```js
const nombres = {logistico: "Regresión logística", boosting: "Gradient boosting", understat: "xG de Understat", tasa_base: "Tasa media (referencia)"};
const metricas = Object.entries(xg.metricas_cv).map(([k, v]) => ({modelo: nombres[k] ?? k, ...v}));
```

```js
Inputs.table(metricas, {
  columns: ["modelo", "log_loss", "brier", "auc", "ece"],
  header: {modelo: "Modelo", log_loss: "Log-loss ↓", brier: "Brier ↓", auc: "AUC ↑", ece: "ECE ↓"},
  format: {log_loss: (d) => num(d, 4), brier: (d) => num(d, 4), auc: (d) => num(d, 3), ece: (d) => num(d, 4)},
  select: false
})
```

<div class="nota">Log-loss y Brier miden calibración y discriminación a la vez; AUC solo discriminación (¿ordena bien los tiros?); ECE solo calibración (¿un 0,20 entra el 20 % de las veces?).</div>

```js
const serieFiab = Object.entries(xg.fiabilidad)
  .filter(([k]) => ["boosting", "understat"].includes(k))
  .flatMap(([k, v]) => v.map((d) => ({...d, modelo: nombres[k]})));
function fiabilidad(width) {
  return Plot.plot({
    width, height: 360,
    x: {label: "xG predicho (medio del tramo)", type: "sqrt", domain: [0, 0.8], grid: true, tickFormat: tickNum},
    y: {label: "Tasa de gol observada", type: "sqrt", domain: [0, 0.8], grid: true, tickFormat: tickNum},
    color: {domain: [nombres.boosting, nombres.understat], range: ["var(--modelo)", "var(--rival)"]},
    marks: [
      Plot.line([[0, 0], [0.8, 0.8]], {stroke: "var(--theme-foreground-faint)", strokeDasharray: "4,4"}),
      Plot.line(serieFiab, {x: "predicho", y: "observado", stroke: "modelo", strokeWidth: 2}),
      Plot.dot(serieFiab, {x: "predicho", y: "observado", fill: "modelo", r: 4.5, stroke: "var(--theme-background)", strokeWidth: 2}),
      Plot.tip(serieFiab, Plot.pointer({x: "predicho", y: "observado",
        title: (d) => `${d.modelo}\nPredicho ${num(d.predicho, 3)} · observado ${num(d.observado, 3)}\n${d.n.toLocaleString("es-ES")} tiros`}))
    ]
  });
}
```

<div class="card">
  <h3>Diagrama de fiabilidad</h3>
  <div class="leyenda"><span class="modelo">Nuestro modelo (gradient boosting)</span><span class="rival">Understat</span><span class="sin">Diagonal = calibración perfecta</span></div>
  ${resize((width) => fiabilidad(width))}
  <div class="nota">Cada punto agrupa un décimo de los tiros. Ejes en raíz cuadrada para ver bien la zona de xG bajo, donde están la mayoría.</div>
</div>

```js
const coefs = Object.entries(xg.coeficientes_logistico).map(([k, v]) => ({
  rasgo: k.replace("num__", "").replace("cat__situacion_", "situación: ").replace("_", " ").replace("angulo", "ángulo"), coef: v
})).sort((a, b) => a.coef - b.coef);
```

<div class="card">
  <h3>Qué aprende la regresión logística</h3>
  ${resize((width) => Plot.plot({
    width, height: 30 * coefs.length + 40, marginLeft: 190,
    x: {label: "Coeficiente (numéricas estandarizadas; situaciones frente a juego abierto)", grid: true, tickFormat: tickNum},
    y: {label: null, domain: coefs.map((d) => d.rasgo)},
    marks: [
      Plot.ruleX([0], {stroke: "var(--theme-foreground-faint)"}),
      Plot.barX(coefs, {y: "rasgo", x: "coef", fill: (d) => (d.coef > 0 ? "var(--modelo)" : "var(--rival)"), rx: 3, insetTop: 4, insetBottom: 4}),
      Plot.tip(coefs, Plot.pointerY({y: "rasgo", x: "coef", title: (d) => `${d.rasgo}: ${num(d.coef, 3)}`}))
    ]
  }))}
  <div class="nota">Aguamarina: aumenta la probabilidad de gol. Naranja: la reduce.</div>
</div>

## Dixon-Coles: ¿predice mejor que no saber nada?

Predicciones hechas **semana a semana** con lo que se sabía hasta ese momento (origen móvil), para ${backtest.n.toLocaleString("es-ES")} partidos de LaLiga. La referencia asigna a todos los partidos las frecuencias históricas de victoria local, empate y victoria visitante.

```js
const bt = backtest.por_temporada.flatMap((d) => [
  {temporada: d.temporada, modelo: "Dixon-Coles", rps: d.rps_modelo},
  {temporada: d.temporada, modelo: "Referencia (frecuencias)", rps: d.rps_base}
]);
```

<div class="grid grid-cols-2">
  <div class="card">
    <h3>Ranked Probability Score (menos es mejor)</h3>
    <div class="leyenda"><span class="modelo">Dixon-Coles</span><span class="sin">Gris: referencia</span></div>
    ${resize((width) => Plot.plot({
      width, height: 260,
      x: {label: null, domain: backtest.por_temporada.map((d) => d.temporada)},
      y: {label: "RPS medio", grid: true, zero: false, tickFormat: tickNum},
      fx: {label: null},
      color: {domain: ["Dixon-Coles", "Referencia (frecuencias)"], range: ["var(--modelo)", "var(--theme-foreground-muted)"]},
      marks: [
        Plot.dot(bt, {x: "temporada", y: "rps", fill: "modelo", r: 7, stroke: "var(--theme-background)", strokeWidth: 2}),
        Plot.tip(bt, Plot.pointer({x: "temporada", y: "rps", title: (d) => `${d.temporada} · ${d.modelo}\nRPS ${num(d.rps, 4)}`}))
      ]
    }))}
  </div>
  <div class="card">
    <h3>Calibración: victoria local</h3>
    ${resize((width) => Plot.plot({
      width, height: 260,
      x: {label: "Probabilidad predicha", domain: [0, 1], grid: true, tickFormat: tickPct},
      y: {label: "Frecuencia observada", domain: [0, 1], grid: true, tickFormat: tickPct},
      r: {range: [3, 12]},
      marks: [
        Plot.line([[0, 0], [1, 1]], {stroke: "var(--theme-foreground-faint)", strokeDasharray: "4,4"}),
        Plot.dot(backtest.calibracion_local, {x: "predicho", y: "observado", r: "n", fill: "var(--modelo)", stroke: "var(--theme-background)", strokeWidth: 2}),
        Plot.tip(backtest.calibracion_local, Plot.pointer({x: "predicho", y: "observado",
          title: (d) => `Predicho ${pct(d.predicho)} · observado ${pct(d.observado)}\n${d.n} partidos`}))
      ]
    }))}
    <div class="nota">Tamaño del punto: número de partidos en el tramo.</div>
  </div>
</div>
