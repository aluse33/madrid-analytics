---
title: Jugadores
---

```js
import {num, pct, tickNum, LOC, puestoTxt} from "./components/formato.js";
const estado = FileAttachment("data/estado.json").json();
const eb = FileAttachment("data/jugadores_eb.csv").csv({typed: true});
const finalizacion = FileAttachment("data/finalizacion.csv").csv({typed: true});
```

# Jugadores: lo que dicen los datos y lo que hay de ruido

Con pocas jornadas, el xG por 90 minutos de quien ha jugado poco es casi todo ruido. Aquí cada jugador aparece con **dos estimaciones**: la bruta (sus números tal cual) y la **empírico-bayesiana**, que la acerca a la media de su puesto en toda LaLiga más cuanto menos haya jugado. Las barras son intervalos creíbles del 90 %. El modelo está explicado en [Metodología](./metodologia).

```js
const metrica = view(Inputs.radio(new Map([["Goles esperados sin penaltis (npxG)", "npxg"], ["Asistencias esperadas (xA)", "xa"]]),
  {label: "Métrica", value: "npxg"}));
const verTodos = view(Inputs.toggle({label: `Incluir jugadores con menos de 270 minutos`, value: false}));
```

```js
const filas = eb.filter((d) => d.metrica === metrica && (verTodos || d.minimo_web)).sort((a, b) => b.eb_p90 - a.eb_p90);
const priores = d3.rollups(filas, (v) => v[0].prior_media_p90, (d) => d.puesto);
```

```js
function bosque(width) {
  return Plot.plot({
    width, height: 28 * filas.length + 60, marginLeft: 150, marginRight: 30,
    x: {label: `${metrica === "npxg" ? "npxG" : "xA"} por 90 minutos`, grid: true, tickFormat: tickNum, nice: true},
    y: {label: null, domain: filas.map((d) => d.jugador)},
    marks: [
      Plot.ruleY(filas, {y: "jugador", x1: "eb_inf", x2: "eb_sup", stroke: "var(--rm)", strokeWidth: 2, strokeOpacity: 0.55}),
      // bruto: aro; EB: punto sólido
      Plot.dot(filas, {y: "jugador", x: "bruto_p90", r: 5, stroke: "var(--theme-foreground-muted)", strokeWidth: 2, fill: "var(--theme-background)"}),
      Plot.dot(filas, {y: "jugador", x: "eb_p90", r: 6, fill: "var(--rm)", stroke: "var(--theme-background)", strokeWidth: 2}),
      Plot.tip(filas, Plot.pointerY({y: "jugador", x: "eb_p90",
        title: (d) => `${d.jugador} · ${puestoTxt(d.puesto)} · ${d.minutos.toLocaleString(LOC)} min\nBruto: ${num(d.bruto_p90)} por 90'\nEstimación EB: ${num(d.eb_p90)} [${num(d.eb_inf)}, ${num(d.eb_sup)}]\nMedia del puesto en la liga: ${num(d.prior_media_p90)}\nPeso de la media del puesto: ${pct(d.peso_prior)}`}))
    ]
  });
}
```

<div class="card">
  <div class="leyenda"><span class="sin">○ Bruto</span><span class="rm">Estimación empírico-bayesiana (punto) y su intervalo del 90 % (línea)</span></div>
  ${resize((width) => bosque(width))}
  <div class="nota">Medias de LaLiga por puesto (el valor hacia el que se encoge): ${priores.map(([p, v]) => `${puestoTxt(p)} ${num(v)}`).join(" · ")}.</div>
</div>

## Finalización: ¿enchufados o con suerte?

Goles sin penalti frente a lo que valían sus tiros. La última columna es la probabilidad de marcar **al menos** esos goles con esos tiros si cada uno entra con probabilidad igual a su xG (distribución Poisson-binomial). Por debajo del 10 % es una racha fuera de lo normal; por encima del 90 % en la columna contraria, una mala racha.

```js
function finalizar(width) {
  const d = finalizacion.map((x) => ({...x, dif: x.goles - x.xg})).sort((a, b) => b.dif - a.dif);
  return Plot.plot({
    width, height: 30 * d.length + 50, marginLeft: 150, marginRight: 20,
    x: {label: "Goles sin penalti − npxG", inset: 90, grid: true, tickFormat: (v) => (v > 0 ? "+" : "") + v.toLocaleString(LOC)},
    y: {label: null, domain: d.map((x) => x.jugador)},
    marks: [
      Plot.ruleX([0], {stroke: "var(--theme-foreground-muted)"}),
      Plot.barX(d, {y: "jugador", x: "dif", fill: "var(--rm)", rx: 3, insetTop: 5, insetBottom: 5}),
      Plot.text(d.filter((x) => x.dif >= 0), {y: "jugador", x: "dif", text: (x) => `${x.goles} G / ${num(x.xg, 1)} npxG`, dx: 6, textAnchor: "start", fontSize: 11}),
      Plot.text(d.filter((x) => x.dif < 0), {y: "jugador", x: "dif", text: (x) => `${x.goles} G / ${num(x.xg, 1)} npxG`, dx: -6, textAnchor: "end", fontSize: 11}),
      Plot.tip(d, Plot.pointerY({y: "jugador", x: "dif",
        title: (x) => `${x.jugador}\n${x.goles} goles con ${num(x.xg)} npxG en ${x.tiros} tiros\nP(≥ ${x.goles} goles) = ${pct(x.p_al_menos)}\nP(≤ ${x.goles} goles) = ${pct(x.p_como_mucho)}`}))
    ]
  });
}
```

<div class="card">
  ${resize((width) => finalizar(width))}
  <div class="nota">A la derecha del cero, más goles que los que valían sus tiros; a la izquierda, menos. La tabla dice si la diferencia es rara o normal.</div>
</div>

```js
Inputs.table(finalizacion, {
  columns: ["jugador", "tiros", "goles", "xg", "p_al_menos", "p_como_mucho"],
  header: {jugador: "Jugador", tiros: "Tiros", goles: "Goles", xg: "npxG", p_al_menos: "P(≥ goles)", p_como_mucho: "P(≤ goles)"},
  format: {xg: (d) => num(d), p_al_menos: (d) => pct(d, 1), p_como_mucho: (d) => pct(d, 1)},
  width: {jugador: 170}, layout: "auto",
  select: false
})
```
