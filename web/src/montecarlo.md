---
title: Simulación Monte Carlo
toc: false
---

```js
import {num, pct, ent, fecha, tickNum, tickPct, LOC, letra, ordinal} from "./components/formato.js";
import {escudo, escudoUrl, nombre, conEscudo} from "./equipos/equipos.js";

const sim = FileAttachment("data/simulacion.json").json();
```

```js
const seguidos = sim.trayectorias.equipos;
const COLOR = {domain: seguidos, range: ["var(--rm)", "var(--rival)", "var(--modelo)"].slice(0, seguidos.length)};
const fechas = sim.trayectorias.fechas.map((f) => new Date(f));
const rmSim = sim.tabla.find((d) => d.equipo === "Real Madrid");
```

# Simulación Monte Carlo

La Liga se juega ${ent(sim.n)} veces en el ordenador. En cada simulación, los ${sim.pendientes} partidos que faltan se deciden con un marcador aleatorio sacado del modelo Dixon-Coles, y al final se ordena la clasificación. La probabilidad de que pase algo es simplemente la proporción de simulaciones en las que pasa.

<div class="grid grid-cols-3">
  <div class="card kpi">
    <div class="etiqueta">Real Madrid campeón</div>
    <div class="cifra">${pct(rmSim.p_campeon, 1)}</div>
    <div class="nota">en ${ent(sim.n * rmSim.p_campeon)} de ${ent(sim.n)} simulaciones</div>
  </div>
  <div class="card kpi">
    <div class="etiqueta">Puntos finales del Madrid</div>
    <div class="cifra">${ent(rmSim.puntos_media)}</div>
    <div class="nota">90 % de las simulaciones entre ${ent(rmSim.puntos_p05)} y ${ent(rmSim.puntos_p95)}</div>
  </div>
  <div class="card kpi">
    <div class="etiqueta">Favorito</div>
    <div class="cifra" style="display:flex;align-items:center;gap:0.5rem">${escudo(sim.tabla[0].equipo, 40)} ${pct(d3.max(sim.tabla, (d) => d.p_campeon))}</div>
    <div class="nota">${nombre(d3.greatest(sim.tabla, (d) => d.p_campeon).equipo)}</div>
  </div>
</div>

## Lo que se juega en el próximo partido

```js
const clave = sim.clave;
const ETIQ = {V: "Si gana el Madrid", E: "Si empatan", D: "Si pierde el Madrid"};
```

```js
display(clave ? html`<p>Las mismas simulaciones, separadas según cómo acaba <b>${nombre(clave.local)} – ${nombre(clave.visitante)}</b>. Como el resto de la temporada se juega igual, la diferencia entre columnas es lo que vale este partido.</p>
<div class="grid grid-cols-3">${clave.condicionado.map((c) => html`<div class="card ${c.resultado === "V" ? "destacada" : ""}">
  <div class="etiqueta"><span class="res res-${c.resultado}">${letra(c.resultado)}</span> ${ETIQ[c.resultado]}</div>
  <div class="nota">Pasa en el ${pct(c.p_resultado)} de las simulaciones</div>
  <div class="cifra">${pct(c.p_campeon_rm, 1)}</div>
  <div class="nota">probabilidad de título del Madrid${clave.lider && clave.lider !== "Real Madrid" ? html` · ${nombre(clave.lider)}: ${pct(c.p_campeon_lider)}` : ""}</div>
</div>`)}</div>` : html`<p class="nota">No quedan partidos.</p>`);
```

## Puntos jornada a jornada

```js
function abanico(width) {
  const q = sim.trayectorias.cuantiles.map((d) => ({...d, fecha: new Date(d.fecha), equipoN: nombre(d.equipo)}));
  const lineas = sim.trayectorias.muestra.flatMap((s) => s.puntos.map((p, t) => ({sim: s.sim, equipo: s.equipo, equipoN: nombre(s.equipo), fecha: fechas[t], puntos: p})));
  return Plot.plot({
    width, height: 240 * seguidos.length, marginLeft: 50, marginRight: 20,
    x: {label: null, type: "utc"},
    y: {label: "Puntos", grid: true, tickFormat: tickNum},
    fy: {label: null, domain: seguidos.map(nombre), axis: null},
    color: COLOR,
    marks: [
      Plot.frame({stroke: "var(--borde)"}),
      Plot.text(seguidos.map(nombre), {fy: (d) => d, text: (d) => d, frameAnchor: "top-left", dx: 10, dy: 10, fontWeight: 700, fontSize: 13}),
      // 50 simulaciones concretas, finas: cada una es una temporada posible
      Plot.line(lineas, {x: "fecha", y: "puntos", z: "sim", fy: "equipoN", stroke: "equipo", strokeWidth: 0.6, strokeOpacity: 0.25, curve: "step-after"}),
      Plot.areaY(q, {x: "fecha", y1: "p05", y2: "p95", fy: "equipoN", fill: "equipo", fillOpacity: 0.12, curve: "step-after"}),
      Plot.areaY(q, {x: "fecha", y1: "p25", y2: "p75", fy: "equipoN", fill: "equipo", fillOpacity: 0.22, curve: "step-after"}),
      Plot.line(q, {x: "fecha", y: "p50", fy: "equipoN", stroke: "equipo", strokeWidth: 2.5, curve: "step-after"}),
      Plot.text(q.filter((d, i, a) => i === a.length - 1 || a[i + 1].equipo !== d.equipo),
        {x: "fecha", y: "p50", fy: "equipoN", text: (d) => `${ent(d.p50)} pts`, dx: -4, dy: -12, textAnchor: "end", fontWeight: 700}),
      Plot.tip(q, Plot.pointer({x: "fecha", y: "p50", fy: "equipoN",
        title: (d) => `${d.equipoN} · ${fecha(d.fecha)}\nMediana ${ent(d.p50)} puntos\n50 %: ${ent(d.p25)}–${ent(d.p75)} · 90 %: ${ent(d.p05)}–${ent(d.p95)}`}))
    ]
  });
}
```

<div class="card">
  <div class="leyenda"><span class="sin">Línea gruesa: mediana · banda oscura: 50 % central · banda clara: 90 % · líneas finas: 50 temporadas simuladas</span></div>
  ${resize((width) => abanico(width))}
</div>

## Distribución de los puntos finales

```js
function histogramas(width) {
  const d = sim.distribucion_puntos.map((x) => ({...x, equipoN: nombre(x.equipo)}));
  const medias = seguidos.map((e) => ({equipoN: nombre(e), media: sim.tabla.find((t) => t.equipo === e).puntos_media}));
  return Plot.plot({
    width, height: 130 * seguidos.length + 40, marginLeft: 50,
    x: {label: "Puntos al final de la Liga", grid: true, tickFormat: tickNum},
    y: {label: null, axis: null},
    fy: {label: null, domain: seguidos.map(nombre), axis: null},
    color: COLOR,
    marks: [
      Plot.text(seguidos.map(nombre), {fy: (d) => d, text: (d) => d, frameAnchor: "top-left", dy: 4, fontWeight: 700, fontSize: 13}),
      Plot.rectY(d, {x1: (x) => x.puntos - 0.45, x2: (x) => x.puntos + 0.45, y: "prob", fy: "equipoN", fill: "equipo", rx: 1}),
      Plot.ruleX(medias, {x: "media", fy: "equipoN", stroke: "var(--texto)", strokeDasharray: "3,3"}),
      Plot.text(medias, {x: "media", fy: "equipoN", frameAnchor: "top", text: (m) => `media ${num(m.media, 1)}`, dy: 22, dx: 4, textAnchor: "start", fontSize: 11}),
      Plot.tip(d, Plot.pointerX({x: "puntos", y: "prob", fy: "equipoN", title: (x) => `${x.equipoN}: ${x.puntos} puntos en el ${pct(x.prob, 1)} de las simulaciones`}))
    ]
  });
}
```

<div class="card">${resize((width) => histogramas(width))}</div>

## ¿Quién acaba dónde?

```js
const orden = sim.tabla.map((d) => d.equipo);
function matrizPuestos(width) {
  const d = sim.puestos.filter((x) => x.prob > 0).map((x) => ({...x, equipoN: nombre(x.equipo)}));
  return Plot.plot({
    width, height: 28 * orden.length + 60, marginLeft: 160, padding: 0.06,
    x: {label: "Puesto final", axis: "top", domain: d3.range(1, orden.length + 1), tickFormat: ordinal},
    y: {label: null, domain: orden.map(nombre)},
    marks: [
      // intensidad = probabilidad (transparencia sobre el color del Madrid: vale en claro y en oscuro)
      Plot.cell(d, {x: "puesto", y: "equipoN", fill: "var(--rm)", fillOpacity: (x) => 0.06 + 0.94 * Math.min(1, x.prob / 0.6), rx: 3}),
      // etiquetas solo donde hay probabilidad apreciable
      Plot.text(d.filter((x) => x.prob >= 0.1), {x: "puesto", y: "equipoN", text: (x) => Math.round(100 * x.prob),
        fill: (x) => (x.prob > 0.3 ? "white" : "var(--texto)"), fontSize: 11, fontWeight: 600}),
      Plot.tip(d, Plot.pointer({x: "puesto", y: "equipoN", title: (x) => `${x.equipoN}: ${ordinal(x.puesto)} en el ${pct(x.prob, 1)} de las simulaciones`}))
    ]
  });
}
```

<div class="card">
  ${resize((width) => matrizPuestos(width))}
  <div class="nota">Cada fila suma 100 %. Números: porcentaje de simulaciones (solo a partir del 10 %). Equipos ordenados por puntos esperados.</div>
</div>

## Por qué no basta con fijar la fuerza de cada equipo

```js
const comp = sim.comparacion.filter((d) => d.p_campeon > 0.001 || d.p_ingenua > 0.001)
  .flatMap((d) => [{equipo: d.equipo, tipo: "Fuerzas fijas y conocidas", p: d.p_ingenua}, {equipo: d.equipo, tipo: "Con incertidumbre", p: d.p_campeon}]);
const der = sim.deriva;
```

<div class="grid grid-cols-2">
  <div class="card">
    <p>Una simulación ingenua da por buena la fuerza estimada de cada equipo, como si se conociera sin error y no fuera a cambiar hasta mayo. Así sale demasiado segura. Esta simulación añade tres fuentes de incertidumbre:</p>
    <ol>
      <li><b>Error de estimación</b> de las fuerzas (matriz de covarianzas sándwich del ajuste).</li>
      <li><b>Desfase:</b> el modelo promedia partidos de hasta tres años, pero el equipo de hoy no es el de hace dos temporadas. Añade una desviación de ${num(der.sd_desfase_ataque, 3)} en el ataque (escala logarítmica).</li>
      <li><b>Deriva futura:</b> la fuerza sigue moviéndose como un paseo aleatorio, unos ${num(der.sd_200_dias_ataque, 2)} cada 200 días, estimado comparando ${der.pares_ataque} pares de medias temporadas.</li>
    </ol>
    <p class="nota">Detalles y fórmulas en <a href="./metodologia">Metodología</a>.</p>
  </div>
  <div class="card">
    <div class="leyenda"><span class="sin">○ Fuerzas fijas y conocidas</span><span class="rm">Con incertidumbre</span></div>
    ${resize((width) => Plot.plot({
      width, height: 60 + 44 * new Set(comp.map((d) => d.equipo)).size, marginLeft: 150,
      x: {label: "Probabilidad de ganar la Liga", domain: [0, 1], grid: true, tickFormat: tickPct},
      y: {label: null, domain: [...new Set(comp.map((d) => d.equipo))].map(nombre)},
      marks: [
        Plot.link(sim.comparacion.filter((d) => d.p_campeon > 0.001 || d.p_ingenua > 0.001),
          {x1: "p_ingenua", x2: "p_campeon", y1: (d) => nombre(d.equipo), y2: (d) => nombre(d.equipo), stroke: "var(--theme-foreground-faint)", strokeWidth: 2}),
        Plot.dot(comp.filter((d) => d.tipo !== "Con incertidumbre"), {x: "p", y: (d) => nombre(d.equipo), r: 6, stroke: "var(--texto-suave)", strokeWidth: 2, fill: "var(--panel)"}),
        Plot.dot(comp.filter((d) => d.tipo === "Con incertidumbre"), {x: "p", y: (d) => nombre(d.equipo), r: 6, fill: "var(--rm)", stroke: "var(--panel)", strokeWidth: 2}),
        Plot.text(comp.filter((d) => d.tipo === "Con incertidumbre"), {x: "p", y: (d) => nombre(d.equipo), text: (d) => pct(d.p, 1), dy: -14, fontSize: 11, fontWeight: 600}),
        Plot.tip(comp, Plot.pointer({x: "p", y: (d) => nombre(d.equipo), title: (d) => `${nombre(d.equipo)} · ${d.tipo}: ${pct(d.p, 1)}`}))
      ]
    }))}
    <div class="nota">Con incertidumbre, los favoritos bajan y los perseguidores suben: el futuro es menos seguro de lo que dicen las fuerzas estimadas.</div>
  </div>
</div>

## ¿Son suficientes ${ent(sim.n)} simulaciones?

```js
const conv = sim.convergencia.map((d) => ({...d, equipoN: nombre(d.equipo), lo: Math.max(0, d.p - 1.96 * d.se), hi: Math.min(1, d.p + 1.96 * d.se)}));
const finalRM = conv.filter((d) => d.equipo === "Real Madrid").at(-1);
```

<div class="card">
  <div class="leyenda">${seguidos.map((e, i) => html`<span class="${["rm", "rival", "modelo"][i]}">${nombre(e)}</span>`)}<span class="sin">Banda: intervalo del 95 % del error Monte Carlo</span></div>
  ${resize((width) => Plot.plot({
    width, height: 300,
    x: {label: "Número de simulaciones", type: "log", grid: true, tickFormat: (d) => d.toLocaleString(LOC)},
    y: {label: "Probabilidad de ganar la Liga", domain: [0, 1], grid: true, tickFormat: tickPct},
    color: COLOR,
    marks: [
      Plot.areaY(conv, {x: "n", y1: "lo", y2: "hi", fill: "equipo", fillOpacity: 0.15}),
      Plot.line(conv, {x: "n", y: "p", stroke: "equipo", strokeWidth: 2}),
      Plot.tip(conv, Plot.pointerX({x: "n", y: "p", title: (d) => `${d.equipoN} con ${d.n.toLocaleString(LOC)} simulaciones: ${pct(d.p, 1)} ± ${pct(1.96 * d.se, 1)}`}))
    ]
  }))}
  <div class="nota">Con pocas simulaciones la estimación baila; a partir de unos pocos miles se estabiliza. Con ${ent(sim.n)}, el error Monte Carlo de la probabilidad del Madrid es de ±${pct(1.96 * finalRM.se, 1)}: mucho menor que la incertidumbre del propio modelo.</div>
</div>
