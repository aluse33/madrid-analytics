---
title: Player profile
toc:
  label: "On this page"
---
<!-- GENERADO por `rma traducir` a partir de ../jugador.md: no editar a mano -->

```js
import {num, pct, ent, fecha, tickNum, puestoTxt, t, LOC} from "../components/formato.js";
import {mapaTirosMedio} from "../components/campo.js";
import {nombre, escudoUrl} from "../equipos/equipos.js";

const estado = FileAttachment("../data/estado.json").json();
const partidos = FileAttachment("../data/rm_partidos.csv").csv({typed: true});
const tiros = FileAttachment("../data/tiros_rm.csv").csv({typed: true});
const jugRM = FileAttachment("../data/jugadores_rm.csv").csv({typed: true});
const liga = FileAttachment("../data/jugadores_liga.csv").csv({typed: true});
const historico = FileAttachment("../data/jugadores_historico.csv").csv({typed: true});
const eb = FileAttachment("../data/jugadores_eb.csv").csv({typed: true});
const fotos = FileAttachment("../data/jugadores_fotos.csv").csv({typed: true});
```

```js
// plantilla ordenada por minutos; ?j=Nombre abre directamente a ese jugador
const plantilla = d3.rollups(jugRM, (v) => d3.sum(v, (d) => d.minutos), (d) => d.jugador)
  .sort((a, b) => b[1] - a[1]).map((d) => d[0]);
const pedido = new URLSearchParams(location.search).get("j");
const jugador = view(Inputs.select(plantilla, {label: t("Jugador", "Player"), value: plantilla.includes(pedido) ? pedido : plantilla[0]}));
```

```js
// actualiza la dirección para poder compartir el enlace de este jugador
history.replaceState(null, "", `?j=${encodeURIComponent(jugador)}`);
const porId = new Map(partidos.map((d) => [d.game_id, d]));
const pj = jugRM.filter((d) => d.jugador === jugador).map((d) => ({...d, p: porId.get(d.game_id)})).sort((a, b) => a.p.fecha - b.p.fecha);
const total = (k) => d3.sum(pj, (d) => d[k]);
const minutos = total("minutos");
const puesto = d3.greatest(d3.rollups(pj, (v) => v.length, (d) => d.puesto), (d) => d[1])[0];
const titular = pj.filter((d) => d.minutos >= 60).length;
const p90 = (k) => (minutos ? (90 * total(k)) / minutos : null);
const fila = liga.find((d) => d.jugador === jugador && d.equipo === "Real Madrid");
const ebDe = (m) => eb.find((d) => d.jugador === jugador && d.metrica === m);
const rotulo = (p) => `J${p.jornada} · ${p.condicion === "Local" ? "vs" : "@"} ${nombre(p.rival)}`;
```

```js
// foto de ESPN: mismo nombre sin tildes ni mayúsculas; si no, mismo apellido
const llano = (s) => String(s).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
const fotoDe = (n) => fotos.find((f) => llano(f.nombre) === llano(n))
  ?? fotos.find((f) => llano(f.nombre).split(" ").at(-1) === llano(n).split(" ").at(-1) && llano(n).split(" ").length > 1);
const fila_foto = fotoDe(jugador);
const iniciales = jugador.split(" ").filter(Boolean).map((x) => x[0]).slice(0, 2).join("");
function retrato() {
  const caja = html`<div class="retrato"><span>${iniciales}</span></div>`;
  if (fila_foto?.foto) {
    const img = html`<img src=${fila_foto.foto} alt="${jugador}" loading="lazy">`;
    img.onload = () => caja.classList.add("con-foto");
    img.onerror = () => img.remove();
    caja.prepend(img);
  }
  return caja;
}
```

<div class="card destacada ficha">
  <div class="ficha-cab">
    ${retrato()}
    <div>
      <div class="etiqueta">${puestoTxt(puesto)} · Real Madrid · LaLiga ${estado.temporada}${fila_foto?.dorsal ? ` · ${fila_foto.dorsal}` : ""}</div>
      <h1 style="margin:0.2rem 0 0.8rem">${jugador}</h1>
    </div>
  </div>
  <div class="cifras-ficha">
    <div><b>${pj.length}</b><span>${t("partidos", "matches")}</span></div>
    <div><b>${ent(minutos)}</b><span>${t("minutos", "minutes")}</span></div>
    <div><b>${titular}</b><span>${t("con 60′ o más", "with 60′ or more")}</span></div>
    <div><b>${total("goles")}</b><span>${t("goles", "goals")}</span></div>
    <div><b>${total("asistencias")}</b><span>${t("asistencias", "assists")}</span></div>
    <div><b>${num(total("npxg"), 1)}</b><span>npxG</span></div>
    <div><b>${num(total("xa"), 1)}</b><span>xA</span></div>
  </div>
</div>

## ${t("Frente a los de su puesto en LaLiga", "Against LaLiga players in his position")}

```js
const METRICAS = [
  ["npxg_p90", t("npxG", "npxG"), t("Goles esperados sin penaltis", "Non-penalty expected goals")],
  ["goles_p90", t("Goles", "Goals"), t("Goles (con penaltis)", "Goals (incl. penalties)")],
  ["tiros_p90", t("Tiros", "Shots"), t("Tiros", "Shots")],
  ["xa_p90", "xA", t("Asistencias esperadas: xG de los tiros que deja a un compañero", "Expected assists: xG of the shots he sets up")],
  ["asistencias_p90", t("Asistencias", "Assists"), t("Asistencias", "Assists")],
  ["pases_clave_p90", t("Pases clave", "Key passes"), t("Pases que acaban en tiro", "Passes that lead to a shot")],
  ["xg_chain_p90", "xGChain", t("xG de las jugadas en las que participa", "xG of the possessions he is involved in")],
  ["xg_buildup_p90", "xGBuildup", t("Lo mismo sin contar el tiro ni el último pase", "The same, leaving out the shot and the final pass")]
];
// percentil: proporción de jugadores de su puesto (con los minutos mínimos) por debajo de él
const grupo = fila ? liga.filter((d) => d.puesto === fila.puesto) : [];
const percentiles = fila ? METRICAS.map(([k, corto, largo]) => {
  const otros = grupo.filter((d) => d !== fila);
  const menos = otros.filter((d) => d[k] < fila[k]).length, iguales = otros.filter((d) => d[k] === fila[k]).length;
  return {k, corto, largo, valor: fila[k], p: (menos + iguales / 2) / otros.length, mediana: d3.median(grupo, (d) => d[k])};
}) : [];

function barrasPercentil(width) {
  return Plot.plot({
    width, height: 34 * percentiles.length + 40, marginLeft: 100, marginRight: 70,
    x: {domain: [0, 1], label: t("Percentil en su puesto", "Percentile in his position"), tickFormat: (d) => pct(d), grid: true},
    y: {domain: percentiles.map((d) => d.corto), label: null},
    marks: [
      Plot.barX(percentiles, {y: "corto", x: 1, fill: "var(--theme-foreground-faintest)", insetTop: 6, insetBottom: 6, rx: 4}),
      Plot.barX(percentiles, {y: "corto", x: "p", fill: "var(--rm)", insetTop: 6, insetBottom: 6, rx: 4}),
      Plot.ruleX([0.5], {stroke: "var(--theme-foreground-muted)", strokeDasharray: "3,3"}),
      Plot.text(percentiles, {y: "corto", x: 1, text: (d) => `${num(d.valor)} /90`, dx: 8, textAnchor: "start", fontSize: 12}),
      Plot.tip(percentiles, Plot.pointerY({y: "corto", x: "p",
        title: (d) => `${d.largo}\n${num(d.valor)} ${t("por 90′", "per 90′")} · ${t("mediana del puesto", "position median")} ${num(d.mediana)}\n${t("Percentil", "Percentile")} ${pct(d.p)}`}))
    ]
  });
}
```

<div class="card">
${fila
  ? html`${resize((width) => barrasPercentil(width))}
    <div class="nota">${t(`Por 90 minutos, frente a los ${grupo.length} jugadores de LaLiga que juegan de ${puestoTxt(fila.puesto)} y llevan al menos 270 minutos esta temporada. La línea discontinua es la mediana. Con pocas jornadas, el ruido es grande: mira también la estimación empírico-bayesiana de abajo.`,
      `Per 90 minutes, against the ${grupo.length} LaLiga players who play as ${puestoTxt(fila.puesto)} and have at least 270 minutes this season. The dashed line is the median. Early in the season the noise is large: see also the empirical Bayes estimate below.`)}</div>`
  : html`<p>${puesto === "POR"
    ? t("Para porteros estas métricas de ataque no dicen gran cosa; llegarán métricas propias cuando tengamos datos de eventos.", "These attacking metrics say little about goalkeepers; specific metrics will come with event data.")
    : t("Todavía no llega a los 270 minutos que hacen falta para compararlo con fiabilidad.", "He has not yet reached the 270 minutes needed for a reliable comparison.")}</p>`}
</div>

```js
const ebN = ebDe("npxg"), ebA = ebDe("xa");
const tarjetaEB = (x, rot) => html`<div class="card"><div class="etiqueta">${rot}</div>
  <div class="cifra">${num(x.eb_p90)}</div>
  <div class="nota">${t("Intervalo del 90 %", "90% interval")}: ${num(x.eb_inf)} – ${num(x.eb_sup)} · ${t("bruto", "raw")} ${num(x.bruto_p90)} · ${t("media del puesto", "position mean")} ${num(x.prior_media_p90)}</div></div>`;
display(ebN && ebA ? html`<div class="grid grid-cols-2">
  ${tarjetaEB(ebN, t("npxG por 90′ · estimación empírico-bayesiana", "npxG per 90′ · empirical Bayes estimate"))}
  ${tarjetaEB(ebA, t("xA por 90′ · estimación empírico-bayesiana", "xA per 90′ · empirical Bayes estimate"))}
</div>` : html`<span></span>`);
```

## ${t("Mapa de tiros", "Shot map")}

```js
const temporadasTiros = [...new Set(tiros.map((d) => d.temporada))].sort().reverse();
const tempTiros = view(Inputs.radio(temporadasTiros, {label: t("Temporada", "Season"), value: temporadasTiros[0]}));
```

```js
const susTiros = tiros.filter((d) => d.jugador === jugador && d.equipo === "Real Madrid" && d.temporada === tempTiros)
  .map((d) => ({...d, partido: porId.has(d.game_id) ? rotulo(porId.get(d.game_id)) : ""}));
const sinPen = susTiros.filter((d) => d.situacion !== "Penalty");
```

<div class="grid grid-cols-2" style="grid-template-columns: minmax(0, 3fr) minmax(0, 2fr)">
  <div class="card">
    <div class="leyenda"><span class="rm">${t("Relleno = gol · aro = sin gol · tamaño = xG", "Filled = goal · ring = no goal · size = xG")}</span></div>
    ${susTiros.length ? resize((width) => mapaTirosMedio(susTiros, {width})) : html`<p>${t("Sin tiros esta temporada.", "No shots this season.")}</p>`}
  </div>
  <div class="card">
    <div class="etiqueta">${t("Sus tiros", "His shots")} · ${tempTiros}</div>
    <table class="mini">
      <tr><td>${t("Tiros", "Shots")}</td><td>${susTiros.length}</td></tr>
      <tr><td>${t("Goles", "Goals")}</td><td>${susTiros.filter((d) => d.resultado === "gol").length}</td></tr>
      <tr><td>${t("Penaltis tirados", "Penalties taken")}</td><td>${susTiros.length - sinPen.length}</td></tr>
      <tr><td>npxG</td><td>${num(d3.sum(sinPen, (d) => d.xg_understat))}</td></tr>
      <tr><td>${t("npxG por tiro", "npxG per shot")}</td><td>${sinPen.length ? num(d3.mean(sinPen, (d) => d.xg_understat)) : "–"}</td></tr>
      <tr><td>${t("Distancia media", "Average distance")}</td><td>${sinPen.length ? `${num(d3.mean(sinPen, (d) => d.distancia), 1)} m` : "–"}</td></tr>
      <tr><td>${t("Con la cabeza", "Headers")}</td><td>${susTiros.filter((d) => d.parte_cuerpo === "Head").length}</td></tr>
      <tr><td>${t("A puerta (gol o parada)", "On target (goal or save)")}</td><td>${susTiros.length ? pct(susTiros.filter((d) => d.resultado === "gol" || d.resultado === "parado").length / susTiros.length) : "–"}</td></tr>
    </table>
    <div class="nota">${t("El npxG por tiro mide la calidad media de sus ocasiones: alto = remata desde buenas posiciones.", "npxG per shot measures the average quality of his chances: high = he shoots from good positions.")}</div>
  </div>
</div>

## ${t("Partido a partido", "Match by match")}

```js
function partidoAPartido(width) {
  const filas = pj.flatMap((d) => [
    {jornada: d.p.jornada, tipo: "npxG", valor: d.npxg, d},
    {jornada: d.p.jornada, tipo: "xA", valor: d.xa, d}
  ]);
  const jornadas = pj.map((d) => d.p.jornada);
  return Plot.plot({
    width, height: 280, marginBottom: 46,
    x: {domain: jornadas, label: null, tickFormat: (j) => `J${j}`, padding: 0.25},
    y: {label: t("npxG + xA", "npxG + xA"), grid: true, tickFormat: tickNum},
    color: {domain: ["npxG", "xA"], range: ["var(--rm)", "var(--modelo)"]},
    marks: [
      Plot.barY(filas, {x: "jornada", y: "valor", fill: "tipo", rx: 2}),
      Plot.image(pj, {x: (d) => d.p.jornada, frameAnchor: "bottom", dy: 38, src: (d) => escudoUrl(d.p.rival), width: 18, height: 20}),
      Plot.text(pj.filter((d) => d.goles + d.asistencias > 0), {x: (d) => d.p.jornada, y: (d) => d.npxg + d.xa,
        text: (d) => [d.goles ? `${d.goles}G` : "", d.asistencias ? `${d.asistencias}A` : ""].filter(Boolean).join(" "), dy: -9, fontWeight: 700}),
      Plot.tip(pj, Plot.pointerX({x: (d) => d.p.jornada, y: (d) => d.npxg + d.xa,
        title: (d) => `${rotulo(d.p)} (${d.p.gf}–${d.p.gc})\n${d.minutos}′ · ${d.goles} G · ${d.asistencias} A\nnpxG ${num(d.npxg)} · xA ${num(d.xa)}\n${t("Tiros", "Shots")} ${d.tiros} · ${t("pases clave", "key passes")} ${d.pases_clave}`}))
    ]
  });
}
```

<div class="card">
  <div class="leyenda"><span class="rm">npxG</span><span class="modelo">xA</span><span class="sin">${t("Encima: goles (G) y asistencias (A) · debajo: rival", "Above: goals (G) and assists (A) · below: opponent")}</span></div>
  ${resize((width) => partidoAPartido(width))}
</div>

## ${t("Temporada a temporada", "Season by season")}

```js
const suHistoria = historico.filter((d) => d.jugador === jugador).map((d) => ({...d,
  ga_p90: (90 * (d.goles + d.asistencias)) / d.minutos, esp_p90: (90 * (d.npxg + d.xa)) / d.minutos}));
function historia(width) {
  return Plot.plot({
    width, height: 260,
    x: {domain: suHistoria.map((d) => d.temporada), label: null, padding: 0.35},
    y: {label: t("Por 90 minutos", "Per 90 minutes"), grid: true, tickFormat: tickNum},
    marks: [
      Plot.barY(suHistoria, {x: "temporada", y: "ga_p90", fill: "var(--rm)", fillOpacity: 0.3, rx: 3}),
      Plot.line(suHistoria, {x: "temporada", y: "esp_p90", stroke: "var(--rm)", strokeWidth: 2}),
      Plot.dot(suHistoria, {x: "temporada", y: "esp_p90", fill: "var(--rm)", r: 5, stroke: "var(--theme-background)", strokeWidth: 2}),
      Plot.tip(suHistoria, Plot.pointerX({x: "temporada", y: "esp_p90",
        title: (d) => `${d.temporada} · ${d.partidos} ${t("partidos", "matches")}, ${ent(d.minutos)}′\n${d.goles} G + ${d.asistencias} A = ${num(d.ga_p90)} ${t("por 90′", "per 90′")}\nnpxG + xA = ${num(d.esp_p90)} ${t("por 90′", "per 90′")}`}))
    ]
  });
}
```

<div class="card">
  ${suHistoria.length > 1 ? html`<div class="leyenda"><span class="rm-claro">${t("Barra: goles + asistencias por 90′", "Bar: goals + assists per 90′")}</span><span class="rm">${t("Línea: npxG + xA por 90′", "Line: npxG + xA per 90′")}</span></div>
  ${resize((width) => historia(width))}` : html`<p>${t("Es su primera temporada en el Madrid (desde 2019/20, que es hasta donde llegan los datos).", "This is his first season at Madrid (since 2019/20, as far back as the data goes).")}</p>`}
  ${Inputs.table(suHistoria.slice().reverse(), {
    columns: ["temporada", "partidos", "minutos", "goles", "asistencias", "npxg", "xa", "tiros", "pases_clave"],
    header: {temporada: t("Temporada", "Season"), partidos: t("PJ", "MP"), minutos: "Min", goles: "G", asistencias: "A", npxg: "npxG", xa: "xA", tiros: t("Tiros", "Shots"), pases_clave: t("Pases clave", "Key passes")},
    format: {npxg: (d) => num(d, 1), xa: (d) => num(d, 1), minutos: (d) => ent(d)},
    layout: "auto", select: false
  })}
  <div class="nota">${t("Solo LaLiga. Si la barra queda muy por encima de la línea, ha marcado y asistido más de lo que valían sus ocasiones: suele bajar con el tiempo.", "LaLiga only. If the bar is well above the line, he scored and assisted more than his chances were worth: that usually comes down over time.")}</div>
</div>
