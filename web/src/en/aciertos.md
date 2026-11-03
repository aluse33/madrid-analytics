---
title: Track record
toc: false
---
<!-- GENERADO por `rma traducir` a partir de ../aciertos.md: no editar a mano -->

```js
import {num, pct, ent, fecha, fechaHora, letra, t, LOC} from "../components/formato.js";
import {nombre} from "../equipos/equipos.js";
import {barraPartido, pildoras} from "../components/ui.js";

const A = FileAttachment("../data/aciertos.json").json();
```

```js
const H = (s) => Object.assign(document.createElement("span"), {innerHTML: s});
const NIVEL = 0.05;
const pTxt = (p) => (p < 0.001 ? "p < 0,001" : `p = ${num(p, 3)}`).replace(/,/g, t(",", "."));
const signo = (v, d = 3) => (v == null ? "–" : `${v > 0 ? "+" : ""}${num(v, d)}`);
const vivo = A.en_vivo ?? {n: 0, pendientes: 0};
const partidosVivo = (A.en_vivo_partidos ?? []).map((d) => ({...d, fecha: new Date(d.fecha)}));
const jugadosVivo = partidosVivo.filter((d) => d.jugado).sort((a, b) => b.fecha - a.fecha);
const pendientesVivo = partidosVivo.filter((d) => !d.jugado).sort((a, b) => a.fecha - b.fecha);
const M = A.madrid, LIGA = A.liga;

// frase según el contraste (diferencia de RPS modelo − referencia: negativa = el modelo acierta más)
function veredicto(c, contra) {
  if (!c || c.p == null) return "";
  const mejor = c.dif < 0;
  const ic = `${t("diferencia de RPS", "RPS difference")} ${signo(c.dif)} [${signo(c.inf)}, ${signo(c.sup)}], ${pTxt(c.p)}, n = ${ent(c.n)}`;
  if (c.p < NIVEL) return H(mejor
    ? t(`El modelo predice <b>mejor que ${contra}</b>, y la diferencia es estadísticamente significativa (${ic}).`, `The model forecasts <b>better than ${contra}</b>, and the difference is statistically significant (${ic}).`)
    : t(`El modelo predice <b>peor que ${contra}</b>, y la diferencia es estadísticamente significativa (${ic}).`, `The model forecasts <b>worse than ${contra}</b>, and the difference is statistically significant (${ic}).`));
  return H(t(`No se puede distinguir al modelo de ${contra}: la diferencia no es significativa (${ic}).`, `The model cannot be told apart from ${contra}: the difference is not significant (${ic}).`));
}
const sello = (c) => c?.p == null ? "" : c.p < NIVEL
  ? html`<span class="sello sello-si">${c.dif < 0 ? t("Mejor, significativo", "Better, significant") : t("Peor, significativo", "Worse, significant")}</span>`
  : html`<span class="sello sello-no">${t("Sin diferencia clara", "No clear difference")}</span>`;
const MERCADO = t("el mercado de apuestas", "the betting market");
const INGENUO = t("el modelo ingenuo", "the naive model");
```

<div class="card destacada">
  <div class="etiqueta">${t("Transparencia", "Transparency")}</div>
  <h1 style="margin:0.2rem 0 0.4rem;color:#fff">${t("¿Acierta el modelo?", "Is the model any good?")}</h1>
  <p style="max-width:62rem;margin:0">${H(t("Antes de cada partido de Liga del Madrid se <b>guarda la predicción</b> y se congela al empezar el partido. Después se compara con lo que pasó. El historial vive en el repositorio público, así que nadie puede retocar una predicción a posteriori.", "Before each Madrid league match the <b>forecast is saved</b> and frozen at kick-off. Afterwards it is scored against what happened. The record lives in the public repository, so no forecast can be edited after the fact."))}</p>
</div>

## ${t("En tiempo real", "Live record")}

```js
display(html`<div>
<div class="grid grid-cols-4">
  <div class="card kpi"><div class="etiqueta">${t("Predicciones evaluadas", "Forecasts scored")}</div><div class="cifra">${vivo.n}</div>
    <div class="nota">${vivo.pendientes} ${t("guardadas, a la espera del partido", "saved, waiting for the match")}</div></div>
  <div class="card kpi"><div class="etiqueta">${t("RPS medio del modelo", "Model mean RPS")}</div><div class="cifra">${vivo.n ? num(vivo.rps_modelo, 3) : "–"}</div>
    <div class="nota">${t("Cuanto más bajo, mejor", "Lower is better")}</div></div>
  <div class="card kpi"><div class="etiqueta">${t("Frente al ingenuo", "Vs naive model")}</div><div class="cifra">${vivo.rps_base != null ? num(vivo.rps_base, 3) : "–"}</div>
    <div class="nota">${vivo.vs_base ? sello(vivo.vs_base) : t("RPS medio de la referencia", "Benchmark mean RPS")}</div></div>
  <div class="card kpi"><div class="etiqueta">${t("Favorito acertado", "Favourite called")}</div><div class="cifra">${vivo.n ? pct(vivo.acierto) : "–"}</div>
    <div class="nota">${t("El resultado más probable fue el que pasó", "The most likely outcome happened")}</div></div>
</div>
${vivo.n < 10 ? html`<div class="aviso">${t(`El registro en tiempo real arrancó en noviembre de 2026 y aún tiene muy pocos partidos: con ${vivo.n} evaluados, cualquier diferencia es ruido. Mientras crece, la evidencia sólida está más abajo, en la reconstrucción.`, `The live record started in November 2026 and still has very few matches: with ${vivo.n} scored, any difference is noise. While it grows, the solid evidence is below, in the reconstruction.`)}</div>` : ""}
${pendientesVivo.length ? html`<div class="card"><h3>${t("Guardadas, a la espera", "Saved, waiting")}</h3>
  ${pendientesVivo.map((d) => html`<div class="fila-pred">
    <div class="fila-pred-cab"><b>${d.condicion === "Local" ? `Real Madrid – ${nombre(d.rival)}` : `${nombre(d.rival)} – Real Madrid`}</b><span>${fechaHora(d.fecha)}</span></div>
    ${barraPartido({local: d.condicion === "Local" ? "Real Madrid" : d.rival, visitante: d.condicion === "Local" ? d.rival : "Real Madrid", p_victoria: d.p_victoria, p_empate: d.p_empate, p_derrota: d.p_derrota}, nombre)}
    <div class="nota">${t("Guardada", "Saved")}: ${fechaHora(new Date(d.guardada))} · ${t("goles esperados", "expected goals")} ${num(d.goles_esperados_rm, 1)} – ${num(d.goles_esperados_rival, 1)}</div>
  </div>`)}</div>` : ""}
${jugadosVivo.length ? html`<div class="card"><h3>${t("Ya evaluadas", "Already scored")}</h3>
  <table class="tabla-pred"><thead><tr><th>${t("Partido", "Match")}</th><th>${t("Predicción (V · E · D)", "Forecast (W · D · L)")}</th><th>${t("Resultado", "Result")}</th><th>RPS</th></tr></thead>
  <tbody>${jugadosVivo.map((d) => html`<tr>
    <td>${fecha(d.fecha)} · ${d.condicion === "Local" ? "vs" : "@"} ${nombre(d.rival)}</td>
    <td>${pct(d.p_victoria)} · ${pct(d.p_empate)} · ${pct(d.p_derrota)}</td>
    <td><span class="res-marcador res-${d.resultado}">${d.gf}–${d.gc}</span></td>
    <td>${num(d.rps, 3)}</td></tr>`)}</tbody></table></div>` : ""}
</div>`);
```

## ${t("Reconstruido: lo que habría dicho cada semana", "Reconstructed: what it would have said each week")}

<p>${H(t(`Mientras el registro en tiempo real crece, la prueba seria es el <b>backtest con origen móvil</b>: desde ${fecha(new Date(A.desde), true)}, cada semana se reajusta el modelo solo con los partidos ya jugados y se predice la jornada siguiente. Son ${ent(LIGA.n)} partidos de LaLiga, ${ent(M.n)} del Madrid.`, `While the live record grows, the serious test is the <b>rolling-origin backtest</b>: since ${fecha(new Date(A.desde), true)}, every week the model is refitted using only matches already played and forecasts the next round. That is ${ent(LIGA.n)} LaLiga matches, ${ent(M.n)} of them Madrid's.`))}</p>

```js
const tarjeta = (titulo, B) => html`<div class="card">
  <h3>${titulo}</h3>
  <table class="mini">
    <tr><td>${t("RPS del modelo", "Model RPS")}</td><td><b>${num(B.rps_modelo, 3)}</b></td></tr>
    <tr><td>${t("RPS del modelo ingenuo", "Naive model RPS")}</td><td>${num(B.rps_base, 3)}</td></tr>
    ${B.rps_mercado != null ? html`<tr><td>${t("RPS del mercado (cuotas de cierre)", "Market RPS (closing odds)")}</td><td>${num(B.rps_mercado, 3)}</td></tr>` : ""}
    <tr><td>${t("Favorito acertado: modelo", "Favourite called: model")}</td><td>${pct(B.acierto)}</td></tr>
    ${B.acierto_mercado != null ? html`<tr><td>${t("Favorito acertado: mercado", "Favourite called: market")}</td><td>${pct(B.acierto_mercado)}</td></tr>` : ""}
    <tr><td>Log-loss</td><td>${num(B.logloss_modelo, 3)}</td></tr>
  </table>
  <p style="margin-bottom:0.3rem">${veredicto(B.vs_base, INGENUO)} ${sello(B.vs_base)}</p>
  ${B.vs_mercado ? html`<p style="margin:0.3rem 0 0">${veredicto(B.vs_mercado, MERCADO)} ${sello(B.vs_mercado)}</p>` : ""}
</div>`;
display(html`<div class="grid grid-cols-2">${tarjeta(t("Partidos del Madrid", "Madrid matches"), M)}${tarjeta(t("Toda LaLiga", "All of LaLiga"), LIGA)}</div>`);
display(A.hay_mercado ? html`<span></span>` : html`<div class="nota">${t("Aún no hay cuotas descargadas: la comparación con el mercado aparecerá tras la próxima actualización.", "No odds downloaded yet: the market comparison will appear after the next update.")}</div>`);
```

```js
function porTemporada(width) {
  const series = [["rps_modelo", t("Modelo", "Model"), "var(--modelo)"], ["rps_base", t("Ingenuo", "Naive"), "var(--empate)"], ["rps_mercado", t("Mercado", "Market"), "var(--rival)"]];
  const filas = A.por_temporada.flatMap((d) => series.filter(([k]) => d[k] != null).map(([k, s]) => ({temporada: d.temporada, serie: s, rps: d[k], n: d.n})));
  return Plot.plot({
    width, height: 260, marginLeft: 50,
    x: {label: null, domain: A.por_temporada.map((d) => d.temporada)},
    y: {label: t("RPS medio (más bajo, mejor)", "Mean RPS (lower is better)"), grid: true, zero: false},
    color: {domain: series.map((s) => s[1]), range: series.map((s) => s[2]), legend: true},
    marks: [
      Plot.line(filas, {x: "temporada", y: "rps", stroke: "serie", strokeWidth: 2}),
      Plot.dot(filas, {x: "temporada", y: "rps", fill: "serie", r: 5, stroke: "var(--theme-background)", strokeWidth: 1.5}),
      Plot.tip(filas, Plot.pointer({x: "temporada", y: "rps", title: (d) => `${d.temporada} · ${d.serie}\nRPS ${num(d.rps, 4)} · ${d.n} ${t("partidos", "matches")}`}))
    ]
  });
}

function calibracionPlot(width) {
  const m = A.calibracion.map((d) => ({...d, quien: t("Modelo", "Model")}));
  const k = (A.calibracion_mercado ?? []).map((d) => ({...d, quien: t("Mercado", "Market")}));
  const datos = [...m, ...k];
  return Plot.plot({
    width, height: Math.min(width, 420), marginLeft: 50, marginBottom: 40,
    x: {domain: [0, 1], label: t("Probabilidad dicha →", "Stated probability →"), tickFormat: (v) => pct(v)},
    y: {domain: [0, 1], label: t("↑ Frecuencia real", "↑ Actual frequency"), tickFormat: (v) => pct(v), grid: true},
    r: {domain: [0, d3.max(datos, (d) => d.n)], range: [3, 13]},
    color: {domain: [t("Modelo", "Model"), t("Mercado", "Market")], range: ["var(--modelo)", "var(--rival)"], legend: k.length > 0},
    marks: [
      Plot.line([[0, 0], [1, 1]], {stroke: "var(--theme-foreground-faint)", strokeDasharray: "4,4"}),
      Plot.ruleX(m, {x: "predicho", y1: "inf", y2: "sup", stroke: "var(--modelo)", strokeOpacity: 0.5, strokeWidth: 2}),
      Plot.dot(datos, {x: "predicho", y: "observado", r: "n", fill: "quien", fillOpacity: (d) => (d.quien === t("Mercado", "Market") ? 0.45 : 0.95), stroke: "var(--theme-background)", strokeWidth: 1.5}),
      Plot.tip(m, Plot.pointer({x: "predicho", y: "observado",
        title: (d) => `${t("Cuando dijo", "When it said")} ${pct(d.desde)}–${pct(d.hasta)} (${t("media", "mean")} ${pct(d.predicho)})\n${t("pasó el", "it happened")} ${pct(d.observado)} ${t("de las veces", "of the time")}\nIC 95 %: ${pct(d.inf)}–${pct(d.sup)} · n = ${ent(d.n)}`}))
    ]
  });
}

// partidos del Madrid reconstruidos (los últimos 38): probabilidad de cada resultado y lo que pasó
const recientes = A.madrid_partidos.map((d) => ({...d, fecha: new Date(d.fecha)})).slice(-38);
function franjas(width) {
  const filas = recientes.flatMap((d, i) => [["V", d.p_victoria], ["E", d.p_empate], ["D", d.p_derrota]].map(([r, p]) => ({i, r, p, d})));
  return Plot.plot({
    width, height: 240, marginBottom: 30,
    x: {domain: d3.range(recientes.length), axis: null, padding: 0.12},
    y: {domain: [0, 1.12], label: t("Probabilidad", "Probability"), tickFormat: (v) => (v <= 1 ? pct(v) : ""), ticks: [0, 0.25, 0.5, 0.75, 1]},
    color: {domain: ["V", "E", "D"], range: ["var(--victoria)", "var(--empate)", "var(--derrota)"]},
    marks: [
      Plot.barY(filas, Plot.stackY({x: "i", y: "p", fill: "r", order: ["V", "E", "D"], fillOpacity: (d) => (d.r === d.d.resultado ? 1 : 0.28)})),
      Plot.dot(recientes, {x: (_, i) => i, y: 1.07, r: 4.5, fill: (d) => ({V: "var(--victoria)", E: "var(--empate)", D: "var(--derrota)"})[d.resultado]}),
      Plot.tip(recientes, Plot.pointerX({x: (_, i) => i, y: 0.5,
        title: (d) => `${fecha(d.fecha, true)} · ${d.condicion === "Local" ? "vs" : "@"} ${nombre(d.rival)}\n${t("Victoria", "Win")} ${pct(d.p_victoria)} · ${t("empate", "draw")} ${pct(d.p_empate)} · ${t("derrota", "loss")} ${pct(d.p_derrota)}\n${t("Resultado", "Result")}: ${letra(d.resultado)} · RPS ${num(d.rps, 3)}`}))
    ]
  });
}
```

<div class="grid grid-cols-2">
  <div class="card">
    <h3>${t("Temporada a temporada", "Season by season")}</h3>
    ${resize((width) => porTemporada(width))}
    <div class="nota">${t("Toda LaLiga. El modelo ingenuo da a cada partido las frecuencias históricas de victoria local, empate y victoria visitante.", "All of LaLiga. The naive model gives every match the historical frequencies of home win, draw and away win.")}</div>
  </div>
  <div class="card">
    <h3>${t("Calibración: ¿cuando dice 60 %, pasa el 60 %?", "Calibration: when it says 60%, does it happen 60%?")}</h3>
    ${resize((width) => calibracionPlot(width))}
    <div class="nota">${t("Las tres probabilidades de cada partido (victoria local, empate, victoria visitante), agrupadas en tramos de 10 puntos. Un modelo bien calibrado cae sobre la diagonal. Las barras son el intervalo de confianza del 95 % (Wilson); el tamaño, cuántas predicciones hay en el tramo.", "The three probabilities of each match (home win, draw, away win), grouped in 10-point bins. A well-calibrated model sits on the diagonal. Bars are 95% confidence intervals (Wilson); size is how many forecasts fall in the bin.")}</div>
  </div>
</div>

<div class="card">
  <h3>${t("Los últimos partidos del Madrid, como los habría visto el modelo", "Madrid's latest matches, as the model would have seen them")}</h3>
  <div class="leyenda"><span class="victoria">${t("Victoria", "Win")}</span><span class="empate">${t("Empate", "Draw")}</span><span class="derrota">${t("Derrota", "Loss")}</span><span class="sin">${t("Color fuerte = lo que pasó · punto = resultado", "Solid colour = what happened · dot = result")}</span></div>
  ${resize((width) => franjas(width))}
  <div class="nota">${t("Una columna por partido, del más antiguo al más reciente. Una columna casi toda de color fuerte es una predicción acertada y segura; mucho color claro, una sorpresa.", "One column per match, oldest to newest. A column that is mostly solid colour is a confident, correct forecast; lots of pale colour, a surprise.")}</div>
</div>

## ${t("Cómo se mide", "How it is measured")}

<div class="card">
<p>${H(t("La métrica principal es el <b>RPS</b> (<i>ranked probability score</i>, Epstein 1969), la estándar para predecir resultados de fútbol. Compara la probabilidad acumulada que se dio (victoria; victoria o empate) con lo que pasó, así que respeta el orden de los resultados: decir 60 % de victoria y que acabe en empate penaliza menos que si acaba en derrota. Va de 0 (acierto perfecto) a 1. Como referencia, un modelo que no sabe nada de los equipos ronda 0,22, y las casas de apuestas, 0,19-0,20.", "The main metric is the <b>RPS</b> (ranked probability score, Epstein 1969), the standard for football result forecasts. It compares the cumulative probability given (win; win or draw) with what happened, so it respects the order of outcomes: saying 60% win and getting a draw is penalised less than getting a loss. It runs from 0 (perfect) to 1. For reference, a model that knows nothing about the teams scores around 0.22, and bookmakers around 0.19–0.20."))}</p>
<p>${H(t("Para comparar con otra referencia se usa un <b>contraste de Diebold y Mariano</b>: la diferencia de RPS partido a partido, su media y su intervalo de confianza. Si el intervalo no toca el cero, la diferencia es significativa al 5 %.", "To compare against a benchmark, a <b>Diebold–Mariano test</b> is used: the match-by-match RPS difference, its mean and confidence interval. If the interval does not cross zero, the difference is significant at 5%."))}</p>
<p>${H(t("El <b>mercado</b> son las cuotas de cierre de Pinnacle (o la media de las casas si no las hay), de <a href='https://www.football-data.co.uk' target='_blank' rel='noopener'>football-data.co.uk</a>, con el margen de la casa quitado. Es el listón más difícil: las cuotas resumen la información de miles de apostantes, incluidas lesiones y alineaciones que el modelo no ve.", "The <b>market</b> is Pinnacle's closing odds (or the bookmakers' average if missing), from <a href='https://www.football-data.co.uk' target='_blank' rel='noopener'>football-data.co.uk</a>, with the bookmaker margin removed. It is the hardest benchmark: odds pool the information of thousands of bettors, including injuries and line-ups the model does not see."))}</p>
<p class="nota">${t("La predicción en tiempo real es la de la web (con la incertidumbre de los parámetros incluida); la reconstruida usa el modelo puntual, así que no son exactamente iguales.", "The live forecast is the website's (including parameter uncertainty); the reconstructed one uses the point estimate, so they are not exactly identical.")}</p>
</div>
