---
title: Summary
toc: false
---
<!-- GENERADO por `rma traducir` a partir de ../index.md: no editar a mano -->

```js
import {num, pct, ent, fecha, fechaHora, hora as horaDe, diaLargo, letra, condicionTxt, tickNum, ordinal} from "../components/formato.js";
import {barraPartido, pildoras} from "../components/ui.js";
import {escudo, escudoUrl, nombre, corto, conEscudo} from "../equipos/equipos.js";

const estado = FileAttachment("../data/estado.json").json();
const partidos = FileAttachment("../data/rm_partidos.csv").csv({typed: true});
const liga = FileAttachment("../data/liga_temporada.csv").csv({typed: true});
const temporadas = FileAttachment("../data/temporadas.json").json();
const prediccion = FileAttachment("../data/prediccion.json").json();
const simulacion = FileAttachment("../data/simulacion.json").json();
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

// clasificación actual y forma de cualquier equipo, desde los partidos de la Liga
const ligaJugada = liga.filter((d) => d.jugado);
function resultadosDe(equipo) {
  return ligaJugada
    .filter((d) => d.local === equipo || d.visitante === equipo)
    .sort((a, b) => a.fecha - b.fecha)
    .map((d) => {
      const casa = d.local === equipo;
      const gf = casa ? d.goles_local : d.goles_visitante, gc = casa ? d.goles_visitante : d.goles_local;
      return {resultado: gf > gc ? "V" : gf === gc ? "E" : "D", puntos: gf > gc ? 3 : gf === gc ? 1 : 0, dg: gf - gc, gf,
        titulo: `${nombre(casa ? equipo : d.local)} ${d.goles_local}–${d.goles_visitante} ${nombre(casa ? d.visitante : equipo)}`};
    });
}
const clasificacion = d3.sort(
  [...new Set(ligaJugada.flatMap((d) => [d.local, d.visitante]))].map((e) => {
    const r = resultadosDe(e);
    return {equipo: e, puntos: d3.sum(r, (x) => x.puntos), dg: d3.sum(r, (x) => x.dg), gf: d3.sum(r, (x) => x.gf)};
  }),
  (a, b) => b.puntos - a.puntos || b.dg - a.dg || b.gf - a.gf
).map((d, i) => ({...d, puesto: i + 1}));
const puestoDe = (e) => clasificacion.find((d) => d.equipo === e);

// cuándo: "Hoy, a las 21:00", "Mañana, a las 18:30" o la fecha
function cuando(f) {
  const d = new Date(f), hoy = new Date();
  const dias = Math.round((new Date(d.toDateString()) - new Date(hoy.toDateString())) / 864e5);
  const hora = horaDe(d);
  if (dias === 0) return `Today, ${hora}`;
  if (dias === 1) return `Tomorrow, ${hora}`;
  return `${diaLargo(d)}, ${hora}`;
}
```

${estado.muestra ? html`<div class="aviso"><b>Sample data.</b> Everything here is synthetic, for developing the site. Run <code>rma todo</code> to download the real data from Understat.</div>` : ""}

# Season ${temp}

<div class="nota" style="margin:0.2rem 0 1.2rem">LaLiga · updated ${fechaHora(estado.actualizado)}</div>

```js
function fichaProximo(p) {
  const rival = p.rival;
  const mia = resultadosDe("Real Madrid").slice(-5);
  const suya = resultadosDe(rival).slice(-5);
  const caraACara = partidos.filter((d) => d.jugado && d.rival === rival).slice(-5)
    .map((d) => ({...d, titulo: `${d.temporada}: ${d.condicion === "Local" ? `Real Madrid ${d.gf}–${d.gc} ${nombre(rival)}` : `${nombre(rival)} ${d.gc}–${d.gf} Real Madrid`}`}));
  const pr = puestoDe(rival), pm = puestoDe("Real Madrid");
  const lado = (e) => html`<div class="lado"><div class="escudo-grande">${escudo(e, 48)}</div><div class="nombre">${nombre(e)}</div></div>`;
  return html`<div class="card destacada grid-colspan-2 grid-rowspan-2">
    <div class="etiqueta">Next match · LaLiga</div>
    <div class="cuando">${cuando(p.fecha)}</div>
    <div class="duelo">${lado(p.local)}<div class="centro">VS</div>${lado(p.visitante)}</div>
    ${barraPartido(p, nombre)}
    <div class="nota">Dixon-Coles model probabilities · expected goals: Madrid ${num(p.goles_esperados_rm)}, ${nombre(rival)} ${num(p.goles_esperados_rival)}. <a href="./prediccion">More details</a></div>
    <div style="margin-top:1rem">
      <div class="fila-forma"><span class="etiqueta">Madrid form</span>${pildoras(mia)}</div>
      <div class="fila-forma"><span class="etiqueta">${corto(rival)} form</span>${pildoras(suya)}</div>
      ${caraACara.length ? html`<div class="fila-forma"><span class="etiqueta">Head to head</span>${pildoras(caraACara)}<span class="nota" style="margin:0">in LaLiga, since ${caraACara[0].temporada}</span></div>` : ""}
    </div>
    ${pr && pm ? html`<div class="nota">${nombre(rival)} are ${ordinal(pr.puesto)} with ${pr.puntos} points; Madrid, ${ordinal(pm.puesto)} with ${pm.puntos}.</div>` : ""}
  </div>`;
}
```

<div class="grid grid-cols-4">
  ${proximo ? fichaProximo(proximo) : html`<div class="card grid-colspan-2 grid-rowspan-2"><p>No league matches left this season.</p></div>`}
  <div class="card kpi">
    <div class="etiqueta">Points</div>
    <div class="cifra">${sum("puntos")}<small>in ${jugados.length} matches</small></div>
    <div class="nota">${V} ${letra("V")} · ${E} ${letra("E")} · ${D} ${letra("D")}</div>
  </div>
  <div class="card kpi">
    <div class="etiqueta">Goals for – against</div>
    <div class="cifra">${sum("gf")}–${sum("gc")}</div>
    <div class="nota">Difference ${sum("gf") - sum("gc") > 0 ? "+" : ""}${sum("gf") - sum("gc")}</div>
  </div>
  <div class="card kpi">
    <div class="etiqueta">xG per match</div>
    <div class="cifra">${num(sum("xgf") / jugados.length)}<small>for</small></div>
    <div class="nota">${num(sum("xgc") / jugados.length)} against · goals ${sum("gf") >= sum("xgf") ? "above" : "below"} xG (${sum("gf") - sum("xgf") > 0 ? "+" : ""}${num(sum("gf") - sum("xgf"), 1)})</div>
  </div>
  <div class="card kpi">
    <div class="etiqueta">Chance of winning LaLiga</div>
    <div class="cifra">${rmSim ? pct(rmSim.p_campeon) : "–"}</div>
    <div class="nota">${rmSim ? html`Final points: ${ent(rmSim.puntos_media)} (90%: ${ent(rmSim.puntos_p05)}–${ent(rmSim.puntos_p95)})` : "Season over"}</div>
  </div>
</div>

## xG for and against, match by match

```js
function graficoXg(width) {
  const filas = jugados.flatMap((d) => [
    {jornada: d.jornada, serie: "Real Madrid", xg: d.xgf, rival: d.rival, res: `${d.gf}–${d.gc}`, resultado: d.resultado},
    {jornada: d.jornada, serie: "Rival", xg: d.xgc, rival: d.rival, res: `${d.gf}–${d.gc}`, resultado: d.resultado}
  ]);
  return Plot.plot({
    width, height: 330, marginBottom: 70,
    x: {label: null, ticks: jugados.map((d) => d.jornada), tickFormat: () => ""},
    y: {label: "xG", grid: true, tickFormat: tickNum, nice: true},
    color: {domain: ["Real Madrid", "Rival"], range: ["var(--rm)", "var(--rival)"]},
    marks: [
      Plot.ruleY([0], {stroke: "var(--theme-foreground-faint)"}),
      Plot.line(filas, {x: "jornada", y: "xg", stroke: "serie", strokeWidth: 2}),
      Plot.dot(filas, {x: "jornada", y: "xg", fill: "serie", r: 4.5, stroke: "var(--theme-background-alt)", strokeWidth: 2}),
      // bajo el eje: escudo del rival y resultado (letra + color de estado)
      Plot.image(jugados, {x: "jornada", y: 0, dy: 22, src: (d) => escudoUrl(d.rival), width: 20, height: 24, title: (d) => nombre(d.rival)}),
      Plot.text(jugados, {x: "jornada", y: 0, dy: 50, text: (d) => letra(d.resultado), fontWeight: 700, fontSize: 12,
        fill: (d) => ({V: "var(--victoria)", E: "var(--empate)", D: "var(--derrota)"})[d.resultado]}),
      Plot.tip(filas, Plot.pointerX({x: "jornada", y: "xg", title: (d) => `J${d.jornada} · ${nombre(d.rival)} (${d.res})\n${d.serie}: ${num(d.xg)} xG`}))
    ]
  });
}
```

<div class="card">
  <div class="leyenda"><span class="rm">Real Madrid xG</span><span class="rival">Opponent xG</span><span class="sin">Below the axis: opponent and result (${letra("V")}/${letra("E")}/${letra("D")})</span></div>
  ${resize((width) => graficoXg(width))}
</div>

## This season against previous ones

```js
function graficoTemporadas(width) {
  const t = temporadas.temporadas;
  return Plot.plot({
    width, height: 40 + 30 * t.length, marginLeft: 60,
    x: {label: "xG difference per match (for − against)", grid: true, tickFormat: tickNum},
    y: {label: null, domain: t.map((d) => d.temporada)},
    marks: [
      Plot.ruleX([0], {stroke: "var(--theme-foreground-faint)"}),
      Plot.ruleY(t, {y: "temporada", x1: "dif_xg_inf", x2: "dif_xg_sup", strokeWidth: 2,
        stroke: (d) => (d.temporada === temp ? "var(--rm)" : "var(--theme-foreground-faint)")}),
      Plot.dot(t, {y: "temporada", x: "dif_xg_pp", r: 6, stroke: "var(--theme-background-alt)", strokeWidth: 2,
        fill: (d) => (d.temporada === temp ? "var(--rm)" : "var(--theme-foreground-muted)")}),
      Plot.tip(t, Plot.pointerY({y: "temporada", x: "dif_xg_pp",
        title: (d) => `${d.temporada} · ${d.pj} matches\nxG difference: ${num(d.dif_xg_pp)} [${num(d.dif_xg_inf)}, ${num(d.dif_xg_sup)}]\nPoints per match: ${num(d.puntos_pp)}`}))
    ]
  });
}
```

<div class="grid grid-cols-3">
  <div class="card grid-colspan-2">
    ${resize((width) => graficoTemporadas(width))}
    <div class="nota">Dot: average per match. Line: 90% bootstrap interval. With few matches the interval is wide on purpose: the noise is real.</div>
  </div>
  <div class="card">
    ${(() => {
      const c = temporadas.comparativa;
      if (!c) return html`<p class="nota">At least three matches are needed.</p>`;
      const d = c.dif_xg;
      return html`<div class="etiqueta">Against ${c.referencia}</div>
        <div class="cifra">${d.diferencia > 0 ? "+" : ""}${num(d.diferencia)}<small>xG/match</small></div>
        <p>90% interval: [${num(d.inf)}, ${num(d.sup)}].</p>
        <p class="nota">${d.inf > 0 ? "The team is clearly more dominant than in previous seasons." : d.sup < 0 ? "The team is clearly below its previous seasons." : "With the matches played so far it cannot be told apart from previous seasons: the interval crosses zero."}
        Probability that the difference is positive: ${pct(d.p_mayor_que_cero)}.</p>`;
    })()}
  </div>
</div>

## Latest matches

```js
Inputs.table(jugados.slice().reverse(), {
  columns: ["jornada", "fecha", "condicion", "rival", "resultado", "gf", "gc", "xgf", "xgc"],
  header: {jornada: "MD", fecha: "Date", condicion: "", rival: "Opponent", resultado: "", gf: "GF", gc: "GA", xgf: "xG", xgc: "Opp. xG"},
  format: {fecha: (d) => fecha(d), condicion: condicionTxt, xgf: (d) => num(d), xgc: (d) => num(d), rival: (d) => conEscudo(d),
    resultado: (d) => html`<span class="res res-${d}">${letra(d)}</span>`},
  width: {rival: 200, fecha: 80}, layout: "auto",
  rows: 12, select: false
})
```
