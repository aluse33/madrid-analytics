---
title: Resumen
toc: false
---

```js
import {num, pct, ent, fecha, fechaHora, tickNum} from "./components/formato.js";
import {barra1x2} from "./components/ui.js";

const estado = FileAttachment("data/estado.json").json();
const partidos = FileAttachment("data/rm_partidos.csv").csv({typed: true});
const temporadas = FileAttachment("data/temporadas.json").json();
const prediccion = FileAttachment("data/prediccion.json").json();
const simulacion = FileAttachment("data/simulacion.json").json();
```

```js
const temp = estado.temporada;
const jugados = partidos.filter((d) => d.temporada === temp && d.jugado);
const V = jugados.filter((d) => d.resultado === "V").length;
const E = jugados.filter((d) => d.resultado === "E").length;
const D = jugados.filter((d) => d.resultado === "D").length;
const sum = (k) => d3.sum(jugados, (d) => d[k]);
const proximo = prediccion.partidos[0];
const rmSim = simulacion?.tabla.find((d) => d.equipo === "Real Madrid");
```

<div class="cabecera">
  <span class="escudo-dot"></span>
  <h1>Temporada ${temp}</h1>
  <span class="sub">LaLiga · actualizado ${fechaHora(estado.actualizado)}</span>
</div>

${estado.muestra ? html`<div class="aviso"><b>Datos de muestra.</b> Todo lo que ves está generado sintéticamente para desarrollar la web. Ejecuta <code>rma todo</code> para descargar los datos reales de Understat.</div>` : ""}

<div class="grid grid-cols-4">
  <div class="card">
    <div class="etiqueta">Puntos</div>
    <div class="cifra">${sum("puntos")}<small>en ${jugados.length} partidos</small></div>
    <div>${jugados.slice(-5).map((d) => html`<span class="res res-${d.resultado}" title="${d.rival}: ${d.gf}–${d.gc}">${d.resultado}</span>`)}</div>
    <div class="nota">${V} V · ${E} E · ${D} D · últimos cinco, de más antiguo a más reciente</div>
  </div>
  <div class="card">
    <div class="etiqueta">Goles a favor – en contra</div>
    <div class="cifra">${sum("gf")}–${sum("gc")}</div>
    <div class="nota">Diferencia ${sum("gf") - sum("gc") > 0 ? "+" : ""}${sum("gf") - sum("gc")}</div>
  </div>
  <div class="card">
    <div class="etiqueta">xG por partido, a favor – en contra</div>
    <div class="cifra">${num(sum("xgf") / jugados.length)}–${num(sum("xgc") / jugados.length)}</div>
    <div class="nota">Goles marcados ${sum("gf") >= sum("xgf") ? "por encima" : "por debajo"} del xG (${num(sum("gf") - sum("xgf"), 1)})</div>
  </div>
  <div class="card">
    <div class="etiqueta">Probabilidad de ganar la Liga</div>
    <div class="cifra">${rmSim ? pct(rmSim.p_campeon) : "–"}</div>
    <div class="nota">${rmSim ? html`Puntos finales: ${ent(rmSim.puntos_media)} (90 %: ${ent(rmSim.puntos_p05)}–${ent(rmSim.puntos_p95)}). ${ent(simulacion.n)} simulaciones.` : "Temporada terminada"}</div>
  </div>
</div>


<div class="grid grid-cols-2">
  <div class="card">
    <h2>Próximo partido</h2>
    ${proximo ? html`
    <h3>${proximo.local} – ${proximo.visitante} · ${fechaHora(proximo.fecha)}</h3>
    ${barra1x2({victoria: proximo.p_victoria, empate: proximo.p_empate, derrota: proximo.p_derrota}, proximo.rival)}
    <div class="nota">Goles esperados: Madrid ${num(proximo.goles_esperados_rm)}, ${proximo.rival} ${num(proximo.goles_esperados_rival)}. Modelo Dixon-Coles con objetivo mixto xG/goles; detalles en <a href="./prediccion">Predicción</a>.</div>` : html`<p>No quedan partidos de Liga.</p>`}
  </div>
  <div class="card">
    <h2>Esta temporada frente a las anteriores</h2>
    ${(() => {
      const c = temporadas.comparativa;
      if (!c) return html`<p class="nota">Hacen falta al menos tres partidos.</p>`;
      const d = c.dif_xg;
      return html`<p>Diferencia de xG por partido respecto a la media de ${c.referencia}:
        <b>${d.diferencia > 0 ? "+" : ""}${num(d.diferencia)}</b>, intervalo bootstrap del 90 %: [${num(d.inf)}, ${num(d.sup)}].</p>
        <p class="nota">${d.inf > 0 ? "El equipo genera claramente más de lo que concede que en años anteriores." : d.sup < 0 ? "El equipo está claramente por debajo de sus temporadas anteriores." : "Con los partidos jugados no se puede distinguir de las temporadas anteriores: el intervalo cruza el cero."}
        Probabilidad bootstrap de que la diferencia sea positiva: ${pct(d.p_mayor_que_cero)}.</p>`;
    })()}
  </div>
</div>

## xG a favor y en contra, partido a partido

```js
function graficoXg(width) {
  const filas = jugados.flatMap((d) => [
    {jornada: d.jornada, serie: "Real Madrid", xg: d.xgf, rival: d.rival, res: `${d.gf}–${d.gc}`, resultado: d.resultado},
    {jornada: d.jornada, serie: "Rival", xg: d.xgc, rival: d.rival, res: `${d.gf}–${d.gc}`, resultado: d.resultado}
  ]);
  return Plot.plot({
    width, height: 300, marginBottom: 46,
    x: {label: "Jornada", ticks: jugados.map((d) => d.jornada), tickFormat: tickNum},
    y: {label: "xG", grid: true, tickFormat: tickNum, nice: true},
    color: {domain: ["Real Madrid", "Rival"], range: ["var(--rm)", "var(--rival)"]},
    marks: [
      Plot.ruleY([0], {stroke: "var(--theme-foreground-faint)"}),
      Plot.line(filas, {x: "jornada", y: "xg", stroke: "serie", strokeWidth: 2}),
      Plot.dot(filas, {x: "jornada", y: "xg", fill: "serie", r: 4.5, stroke: "var(--theme-background)", strokeWidth: 2}),
      // resultado bajo el eje: letra + color de estado
      Plot.text(jugados, {x: "jornada", y: 0, dy: 32, text: "resultado", fontWeight: 700,
        fill: (d) => ({V: "var(--victoria)", E: "var(--empate)", D: "var(--derrota)"})[d.resultado]}),
      Plot.tip(filas, Plot.pointerX({x: "jornada", y: "xg", title: (d) => `J${d.jornada} · ${d.rival} (${d.res})\n${d.serie}: ${num(d.xg)} xG`}))
    ]
  });
}
```

<div class="card">
  <div class="leyenda"><span class="rm">xG del Real Madrid</span><span class="rival">xG del rival</span><span class="sin">Bajo el eje: resultado (V/E/D)</span></div>
  ${resize((width) => graficoXg(width))}
</div>

## Temporada a temporada

```js
function graficoTemporadas(width) {
  const t = temporadas.temporadas;
  return Plot.plot({
    width, height: 280, marginLeft: 60,
    x: {label: "Diferencia de xG por partido (a favor − en contra)", grid: true, tickFormat: tickNum},
    y: {label: null, domain: t.map((d) => d.temporada)},
    marks: [
      Plot.ruleX([0], {stroke: "var(--theme-foreground-faint)"}),
      Plot.ruleY(t, {y: "temporada", x1: "dif_xg_inf", x2: "dif_xg_sup", strokeWidth: 2,
        stroke: (d) => (d.temporada === temp ? "var(--rm)" : "var(--theme-foreground-muted)")}),
      Plot.dot(t, {y: "temporada", x: "dif_xg_pp", r: 6, stroke: "var(--theme-background)", strokeWidth: 2,
        fill: (d) => (d.temporada === temp ? "var(--rm)" : "var(--theme-foreground-muted)")}),
      Plot.tip(t, Plot.pointerY({y: "temporada", x: "dif_xg_pp",
        title: (d) => `${d.temporada} · ${d.pj} partidos\nDiferencia de xG: ${num(d.dif_xg_pp)} [${num(d.dif_xg_inf)}, ${num(d.dif_xg_sup)}]\nPuntos por partido: ${num(d.puntos_pp)}`}))
    ]
  });
}
```

<div class="card">
  ${resize((width) => graficoTemporadas(width))}
  <div class="nota">Punto: media por partido. Línea: intervalo bootstrap del 90 %. Con pocos partidos el intervalo es ancho a propósito: el ruido es real.</div>
</div>

## Últimos partidos

```js
Inputs.table(jugados.slice().reverse(), {
  columns: ["jornada", "fecha", "condicion", "rival", "resultado", "gf", "gc", "xgf", "xgc"],
  header: {jornada: "J", fecha: "Fecha", condicion: "", rival: "Rival", resultado: "", gf: "GF", gc: "GC", xgf: "xG", xgc: "xG rival"},
  format: {fecha: (d) => fecha(d), xgf: (d) => num(d), xgc: (d) => num(d),
    resultado: (d) => html`<span class="res res-${d}">${d}</span>`},
  width: {rival: 170, fecha: 80}, layout: "auto",
  rows: 12, select: false
})
```
