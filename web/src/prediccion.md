---
title: Predicción
---

```js
import {num, pct, ent, fecha, fechaHora, tickNum, tickPct, ordinal} from "./components/formato.js";
import {escudo, escudoUrl, nombre, conEscudo} from "./equipos/equipos.js";
const prediccion = FileAttachment("data/prediccion.json").json();
const simulacion = FileAttachment("data/simulacion.json").json();
const ratings = FileAttachment("data/ratings.csv").csv({typed: true});
```

# Predicción

Un modelo de **Dixon-Coles** estima la capacidad ofensiva y la fragilidad defensiva de cada equipo de LaLiga con los partidos de los últimos tres años, dando más peso a los recientes (semivida de ${prediccion.modelo.semivida_dias} días). Aprende de una mezcla de xG y goles: el xG es mucho menos ruidoso que el marcador. Ventaja de campo estimada: ${pct(Math.exp(prediccion.modelo.campo) - 1)} más de goles esperados para el local.

## Próximos partidos

```js
Inputs.table(prediccion.partidos, {
  columns: ["fecha", "local", "visitante", "p_victoria", "p_empate", "p_derrota", "goles_esperados_rm", "goles_esperados_rival"],
  header: {fecha: "Fecha", local: "Local", visitante: "Visitante", p_victoria: "V Madrid", p_empate: "E", p_derrota: "D Madrid",
    goles_esperados_rm: "Goles esp. Madrid", goles_esperados_rival: "Goles esp. rival"},
  format: {fecha: (d) => fecha(d), local: (d) => conEscudo(d), visitante: (d) => conEscudo(d), p_victoria: (d) => pct(d), p_empate: (d) => pct(d), p_derrota: (d) => pct(d),
    goles_esperados_rm: (d) => num(d), goles_esperados_rival: (d) => num(d)},
  width: {local: 190, visitante: 190}, layout: "auto",
  select: false
})
```

```js
const elegido = view(Inputs.select(prediccion.partidos, {label: "Marcadores probables", format: (d) => `${nombre(d.local)} – ${nombre(d.visitante)}`}));
```

```js
function matriz(width) {
  const m = elegido.matriz;
  const celdas = m.flatMap((fila, i) => fila.map((p, j) => ({local: i, visitante: j, p})));
  const top = celdas.slice().sort((a, b) => b.p - a.p).slice(0, 5);
  const lado = Math.min(width, 520);
  return Plot.plot({
    width: lado, height: lado * 0.9, padding: 0.06,
    x: {label: `Goles de ${nombre(elegido.visitante)}`, axis: "top", domain: d3.range(7)},
    y: {label: `Goles de ${nombre(elegido.local)}`, domain: d3.range(7)},
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
  <div class="nota">Cada casilla es la probabilidad de un marcador exacto; la diagonal son los empates. La corrección de Dixon-Coles (ρ = ${num(prediccion.modelo.rho, 3)}) ajusta los resultados con pocos goles.</div>
</div>

## Simulación del resto de la Liga

${simulacion ? html`${ent(simulacion.n)} temporadas simuladas a partir de los ${simulacion.pendientes} partidos que faltan, teniendo en cuenta que la fuerza de cada equipo es incierta y cambia con el tiempo. Trayectorias, distribuciones y el detalle del método, en <a href="./montecarlo">Simulación Monte Carlo</a>.` : "La temporada ha terminado."}

```js
function puestos(width) {
  const d = simulacion.rm_dist_puesto.map((p, i) => ({puesto: i + 1, p})).filter((d) => d.p > 0.0005);
  return Plot.plot({
    width, height: 240, marginTop: 34,
    x: {label: "Puesto final del Real Madrid", domain: d.map((x) => x.puesto), tickFormat: ordinal},
    y: {label: "Probabilidad", grid: true, tickFormat: tickPct},
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
  header: {equipo: "Equipo", puntos_actuales: "Puntos hoy", puntos_media: "Puntos finales (media)", puntos_p05: "P5", puntos_p95: "P95",
    p_campeon: "Campeón", p_top4: "Top 4", p_descenso: "Descenso"},
  format: {equipo: (d) => conEscudo(d), puntos_media: (d) => num(d, 1), puntos_p05: ent, puntos_p95: ent, puntos_actuales: ent,
    p_campeon: (d) => pct(d, 1), p_top4: (d) => pct(d, 1), p_descenso: (d) => pct(d, 1)},
  width: {equipo: 210}, layout: "auto",
  select: false, rows: 21
})
```

## Fuerza de los equipos

```js
function fuerzas(width) {
  const enLiga = new Set(simulacion.tabla.map((d) => d.equipo));
  const actuales = ratings.filter((d) => enLiga.has(d.equipo));
  return Plot.plot({
    width, height: 440, inset: 20, marginRight: 90,
    x: {label: "Ataque: goles generados frente a la media (×) →", grid: true, tickFormat: tickNum},
    y: {label: "↑ Defensa: goles concedidos frente a la media (×), menos es mejor", grid: true, reverse: true, tickFormat: tickNum},
    marks: [
      Plot.ruleX([1], {stroke: "var(--theme-foreground-faint)"}),
      Plot.ruleY([1], {stroke: "var(--theme-foreground-faint)"}),
      // el Madrid con un halo para encontrarlo de un vistazo
      Plot.dot(actuales.filter((d) => d.equipo === "Real Madrid"), {x: "ataque", y: "defensa", r: 22, fill: "var(--rm)", fillOpacity: 0.18, stroke: "var(--rm)"}),
      Plot.image(actuales, {x: "ataque", y: "defensa", src: (d) => escudoUrl(d.equipo), width: 26, height: 30}),
      Plot.tip(actuales, Plot.pointer({x: "ataque", y: "defensa",
        title: (d) => `${nombre(d.equipo)}\nAtaque ×${num(d.ataque)} · Defensa ×${num(d.defensa)}`}))
    ]
  });
}
```

<div class="card">
  ${resize((width) => fuerzas(width))}
  <div class="nota">Arriba a la derecha, los mejores: generan más y conceden menos que un equipo medio de LaLiga. Los valores incluyen shrinkage hacia la media (penalización L2), así que los extremos están algo encogidos a propósito.</div>
</div>
