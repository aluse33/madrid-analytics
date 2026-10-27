---
title: Histórico
---

```js
import {num, pct, ent, ordinal, tickNum, t, LOC} from "./components/formato.js";
const H = FileAttachment("data/historia.json").json();
const europaGeo = FileAttachment("mapas/europa.geo.json").json();
const estado = FileAttachment("data/estado.json").json();
const partidos = FileAttachment("data/rm_partidos.csv").csv({typed: true});
```

```js
// ---------- utilidades
const anio = (temp) => {
  const m = String(temp).match(/^(\d{4})(?:[–-](\d{2,4}))?/);
  if (!m) return null;
  if (!m[2]) return +m[1];
  return m[2].length === 4 ? +m[2] : +m[1].slice(0, 2) * 100 + +m[2] + (+m[2] < +m[1].slice(2) ? 100 : 0);
};
const GRUPO = (c) => /Champions/.test(c) ? "champions" : c === "LaLiga" ? "liga" : c === "Copa del Rey" ? "copa" : "otros";
const COLOR = {champions: "var(--rm)", liga: "var(--oro)", copa: "var(--modelo)", otros: "var(--empate)"};
const NOMBRE_GRUPO = {champions: t("Copa de Europa / Champions", "European Cup / Champions League"), liga: "LaLiga", copa: "Copa del Rey", otros: t("Otros oficiales", "Other official")};
const COMP_EN = {"Copa de Europa / Champions League": "European Cup / Champions League", "Copa de la UEFA": "UEFA Cup", "Supercopa de Europa": "UEFA Super Cup",
  "Supercopa de España": "Spanish Super Cup", "Mundial de Clubes": "Club World Cup", "Copa Intercontinental": "Intercontinental Cup",
  "Copa Intercontinental de la FIFA": "FIFA Intercontinental Cup", "Copa Latina": "Latin Cup", "Copa Iberoamericana": "Ibero-American Cup",
  "Copa de la Liga": "League Cup", "Campeonato Regional": "Regional championship"};
const comp = (c) => t(c, COMP_EN[c] ?? c);
const RONDAS = {"Final": t("Final", "Final"), "Semi-final": t("Semifinal", "Semi-final"), "Quarter-final": t("Cuartos", "Quarter-final"),
  "Round of 16": t("Octavos", "Round of 16"), "First round": t("Primera ronda", "First round"), "Second round": t("Segunda ronda", "Second round"),
  "Preliminary round": t("Ronda previa", "Preliminary round"), "League phase": t("Fase liga", "League phase"),
  "Knockout phase play-off": t("Eliminatoria previa", "Knockout play-off"), "Third qualifying round": t("Tercera previa", "Third qualifying round")};
const ronda = (r) => RONDAS[r] ?? r.replace(/^Group /, t("Grupo ", "Group ")).replace(/^First group stage/, t("Primera fase de grupos", "First group stage")).replace(/^Second group stage/, t("Segunda fase de grupos", "Second group stage"));
const marcadorTxt = (s) => t(s.replaceAll("(H)", "(C)").replaceAll("(A)", "(F)").replaceAll("a.e.t.", "pr.").replaceAll("pen.", "pen."), s);
const RES = {W: t("Campeón", "Winners"), RU: t("Final", "Runners-up"), SF: t("Semifinal", "Semi-final"), QF: t("Cuartos", "Quarter-final"),
  R16: t("Octavos", "Round of 16"), R32: t("Dieciseisavos", "Round of 32"), R64: t("Treintaidosavos", "Round of 64"), "3rd": t("Tercero", "Third")};

// ---------- títulos
const oficiales = (H.palmares ?? []).filter((d) => d.tipo !== "Regional");
const titulos = oficiales.flatMap((d) => d.temporadas.map((s) => ({temporada: s, anio: anio(s), competicion: d.competicion, grupo: GRUPO(d.competicion)})));
const totalTitulos = d3.sum(oficiales, (d) => d.titulos);
```

# ${t("Histórico del Real Madrid", "Real Madrid history")}

<div class="nota" style="margin:0.2rem 0 1.2rem">${t("Desde 1902. Datos de Wikipedia (CC BY-SA), revisados el", "Since 1902. Data from Wikipedia (CC BY-SA), checked on")} ${H.actualizado}.</div>

## ${t("La vitrina", "The trophy cabinet")}

```js
const vitrina = oficiales.slice().sort((a, b) => b.titulos - a.titulos);
display(html`<div class="vitrina">
  <div class="card destacada trofeo-total"><div class="etiqueta">${t("Títulos oficiales", "Official trophies")}</div><div class="cifra-grande">${totalTitulos}</div>
    <div class="nota">${t("Sin contar los campeonatos regionales", "Not counting regional championships")}</div></div>
  ${vitrina.map((d) => html`<div class="card trofeo" style="border-top-color:${COLOR[GRUPO(d.competicion)]}">
    <div class="cifra">${d.titulos}</div>
    <div class="trofeo-nombre">${comp(d.competicion)}</div>
    <div class="nota">${t("Último", "Latest")}: ${d.temporadas.at(-1)}${d.compartido ? t(" · récord", " · record") : ""}</div>
  </div>`)}
</div>`);
```

```js
function lineaTitulos(width) {
  const datos = titulos.filter((d) => d.anio);
  return Plot.plot({
    width, height: 230, marginLeft: 10, marginRight: 10,
    x: {label: null, domain: [1900, new Date().getFullYear() + 1], tickFormat: (d) => String(d)},
    y: {axis: null},
    color: {domain: Object.keys(COLOR), range: Object.values(COLOR)},
    marks: [
      Plot.ruleY([0], {stroke: "var(--borde)"}),
      Plot.dot(datos, Plot.dodgeY({x: "anio", fill: "grupo", r: 4.5, padding: 1, anchor: "bottom",
        title: (d) => `${d.temporada} · ${comp(d.competicion)}`, tip: true}))
    ]
  });
}
```

<div class="card">
  <h3>${t("Cada título, en el tiempo", "Every trophy, over time")}</h3>
  <div class="leyenda">${Object.entries(NOMBRE_GRUPO).map(([k, v]) => html`<span class="g-${k}">${v}</span>`)}</div>
  ${resize((width) => lineaTitulos(width))}
  <div class="nota">${t("Cada punto es un título, apilado en el año en que se ganó. Se ven las dos edades de oro europeas (1956–1966 y 2014–2024).", "Each dot is a trophy, stacked on the year it was won. The two golden European eras stand out (1956–1966 and 2014–2024).")}</div>
</div>

## ${t("Temporada a temporada en Liga", "Season by season in the league")}

```js
const ligas = (H.temporadas ?? []).filter((d) => d.division === "La Liga" && d.puesto).map((d) => ({...d, anio: anio(d.temporada)}));
const europeos = new Set(titulos.filter((d) => d.grupo === "champions").map((d) => d.temporada));
function posiciones(width) {
  return Plot.plot({
    width, height: 300,
    x: {label: null, tickFormat: (d) => String(d)},
    y: {label: t("Puesto en Liga", "League position"), reverse: true, domain: [1, d3.max(ligas, (d) => d.puesto)], ticks: [1, 2, 3, 5, 7, 9, 11], grid: true},
    marks: [
      Plot.line(ligas, {x: "anio", y: "puesto", stroke: "var(--theme-foreground-faint)", curve: "step"}),
      Plot.dot(ligas, {x: "anio", y: "puesto", r: (d) => (d.puesto === 1 ? 5 : 3),
        fill: (d) => (d.puesto === 1 ? "var(--oro)" : "var(--theme-foreground-muted)"), stroke: "var(--theme-background)"}),
      Plot.text(ligas.filter((d) => europeos.has(d.temporada)), {x: "anio", y: 1, text: () => "★", dy: -14, fill: "var(--rm)", fontSize: 13}),
      Plot.tip(ligas, Plot.pointerX({x: "anio", y: "puesto",
        title: (d) => `${d.temporada}: ${ordinal(d.puesto)}${d.puntos != null ? ` · ${d.puntos} ${t("puntos", "points")}` : ""}` +
          `${d.copa && RES[d.copa] ? `\nCopa: ${RES[d.copa]}` : ""}${d.europa_ronda && RES[d.europa_ronda] ? `\n${t("Europa", "Europe")}: ${RES[d.europa_ronda]}` : ""}` +
          `${d.goleador && d.goleador !== "—" ? `\n${t("Máximo goleador", "Top scorer")}: ${d.goleador} (${d.goles_goleador})` : ""}`}))
    ]
  });
}
```

<div class="card">
  <div class="leyenda"><span class="g-liga">${t("Campeón de Liga", "League champions")}</span><span class="sin">★ ${t("= ese año, también campeón de Europa", "= that year, also European champions")}</span></div>
  ${resize((width) => posiciones(width))}
  <div class="nota">${t("Nunca ha bajado de categoría: es, junto a Athletic y Barcelona, uno de los tres clubes que han jugado todas las temporadas de Primera.", "Never relegated: with Athletic and Barcelona, one of the three clubs that have played every top-flight season.")}</div>
</div>

## ${t("Esta temporada frente a las de título", "This season against the title-winning ones")}

```js
// puntos por partido con 3 por victoria, para comparar épocas (antes de 1995 la victoria valía 2)
const ppp = (d) => (3 * d.v + d.e) / d.pj;
const campeonas = ligas.filter((d) => d.puesto === 1 && d.pj).map((d) => ({...d, ppp: ppp(d), gfp: d.gf / d.pj, gcp: d.gc / d.pj}));
const actual = partidos.filter((d) => d.temporada === estado.temporada && d.jugado);
const hoy = actual.length ? {ppp: d3.mean(actual, (d) => d.puntos), gfp: d3.mean(actual, (d) => d.gf), gcp: d3.mean(actual, (d) => d.gc), pj: actual.length} : null;
const METRICAS_T = [
  ["ppp", t("Puntos por partido (3 por victoria)", "Points per match (3 for a win)")],
  ["gfp", t("Goles a favor por partido", "Goals for per match")],
  ["gcp", t("Goles en contra por partido", "Goals against per match")]
];
function comparaTitulo(width, [k, rot]) {
  const peor = k === "gcp";
  const orden = campeonas.slice().sort((a, b) => (peor ? a[k] - b[k] : b[k] - a[k]));
  const puesto = hoy ? orden.filter((d) => (peor ? d[k] < hoy[k] : d[k] > hoy[k])).length + 1 : null;
  return html`<div><div class="etiqueta">${rot}</div>${Plot.plot({
    width, height: 90, marginTop: 10, marginBottom: 30,
    x: {label: null, grid: true, tickFormat: tickNum},
    marks: [
      Plot.dot(campeonas, Plot.dodgeY({x: k, r: 4, fill: "var(--oro)", fillOpacity: 0.75, anchor: "middle",
        title: (d) => `${d.temporada}: ${num(d[k])}`, tip: true})),
      hoy ? Plot.ruleX([hoy[k]], {stroke: "var(--rm)", strokeWidth: 3}) : null
    ]
  })}${hoy ? html`<div class="nota">${t("Ahora", "Now")}: <b>${num(hoy[k])}</b> · ${t("sería la", "would rank")} ${ordinal(puesto)} ${t("de", "of")} ${campeonas.length} ${t("temporadas campeonas", "title-winning seasons")}</div>` : ""}</div>`;
}
```

<div class="card">
  <div class="leyenda"><span class="g-liga">${t("Cada una de las Ligas ganadas", "Each league title season")}</span><span class="rm">${t("Esta temporada", "This season")} ${hoy ? `(${hoy.pj} ${t("partidos", "matches")})` : ""}</span></div>
  ${resize((width) => html`<div class="grid grid-cols-1" style="gap:0.6rem">${METRICAS_T.map((m) => comparaTitulo(width, m))}</div>`)}
  <div class="nota">${t("Con pocas jornadas, la línea se moverá mucho: es una foto, no una predicción. Para comparar épocas, todas las temporadas se cuentan con 3 puntos por victoria.", "Early in the season the line will move a lot: it is a snapshot, not a forecast. To compare eras, every season is counted with 3 points for a win.")}</div>
</div>

## ${t("El camino a cada Copa de Europa", "The road to every European Cup")}

```js
const europaPorTemp = d3.group(H.europa ?? [], (d) => d.temporada);
const ganadas = (H.finales ?? []).filter((d) => d.gano).reverse();
const tempElegida = view(Inputs.select(ganadas.map((d) => d.temporada), {label: t("Temporada", "Season")}));
```

```js
const final = (H.finales ?? []).find((d) => d.temporada === tempElegida);
const camino = europaPorTemp.get(tempElegida) ?? [];
const ganador = (s) => {
  // ¿pasó el Madrid? suma de goles de la eliminatoria (las finales a partido único: el ganador ya se sabe)
  const goles = [...s.matchAll(/(\d+)–(\d+)/g)].map((m) => [+m[1], +m[2]]);
  const a = d3.sum(goles, (g) => g[0]), b = d3.sum(goles, (g) => g[1]);
  return a > b ? "V" : a < b ? "D" : "E";
};
display(html`<div class="grid grid-cols-2" style="grid-template-columns: minmax(0, 3fr) minmax(0, 2fr)">
  <div class="card"><h3>${tempElegida}</h3>
    <div class="camino">${camino.map((d) => html`<div class="paso ${d.ronda === "Final" ? "paso-final" : ""}">
      <div class="paso-ronda">${ronda(d.ronda)}</div>
      <div class="paso-rival">${d.rival}</div>
      <div class="paso-marcador"><span class="res-marcador res-${d.ronda === "Final" ? "V" : ganador(d.marcador)}">${marcadorTxt(d.marcador)}</span></div>
    </div>`)}</div>
    <div class="nota">${t("(C) en casa · (F) fuera · (N) campo neutral · pr. prórroga. En las eliminatorias a doble partido se ven los dos resultados.", "(H) home · (A) away · (N) neutral venue · a.e.t. after extra time. Two-legged ties show both results.")}</div>
  </div>
  ${final ? html`<div class="card destacada">
    <div class="etiqueta">${t("La final", "The final")}</div>
    <div class="cifra-grande" style="color:#fff">${final.marcador}</div>
    <div style="font-size:1.1rem;color:#fff"><b>Real Madrid</b> – ${final.rival}</div>
    <p style="color:rgba(255,255,255,0.8)">${final.estadio}, ${final.ciudad}${final.publico ? html`<br>${ent(final.publico)} ${t("espectadores", "spectators")}` : ""}</p>
    <div class="nota">${t("Copa de Europa número", "European Cup number")} ${ganadas.length - ganadas.indexOf(final)}</div>
  </div>` : ""}
</div>`);
```

## ${t("Dónde se ganaron", "Where they were won")}

```js
const CIUDADES = {
  Paris: [2.35, 48.86, "París"], Madrid: [-3.69, 40.45, "Madrid"], Brussels: [4.35, 50.85, "Bruselas"], Stuttgart: [9.18, 48.78, "Stuttgart"],
  Glasgow: [-4.25, 55.86, "Glasgow"], Amsterdam: [4.9, 52.37, "Ámsterdam"], Vienna: [16.37, 48.21, "Viena"], "Saint-Denis": [2.36, 48.92, "Saint-Denis"],
  Lisbon: [-9.14, 38.72, "Lisboa"], Milan: [9.19, 45.46, "Milán"], Cardiff: [-3.18, 51.48, "Cardiff"], Kyiv: [30.52, 50.45, "Kiev"], London: [-0.13, 51.51, "Londres"]
};
const enMapa = d3.rollups(H.finales ?? [], (v) => ({ganadas: v.filter((d) => d.gano), perdidas: v.filter((d) => !d.gano)}), (d) => d.ciudad)
  .filter(([c]) => CIUDADES[c])
  .map(([c, v]) => ({ciudad: t(CIUDADES[c][2], c), lon: CIUDADES[c][0], lat: CIUDADES[c][1], ...v, n: v.ganadas.length + v.perdidas.length}));
function mapaFinales(width) {
  return Plot.plot({
    width, height: Math.min(560, width * 0.8),
    r: {domain: [1, 3], range: [6, 14]},
    projection: {type: "conic-conformal", rotate: [-10, 0], parallels: [40, 60], inset: 40,
      domain: {type: "MultiPoint", coordinates: enMapa.map((d) => [d.lon, d.lat])}},
    marks: [
      Plot.geo(europaGeo, {fill: "var(--campo-fondo)", stroke: "var(--campo-linea)", strokeWidth: 0.6}),
      Plot.dot(enMapa, {x: "lon", y: "lat", r: "n", fill: (d) => (d.ganadas.length ? "var(--oro)" : "var(--empate)"),
        stroke: "var(--theme-background)", strokeWidth: 1.5, fillOpacity: 0.9}),
      Plot.text(enMapa, {x: "lon", y: "lat", text: (d) => (d.n > 1 ? String(d.n) : ""), fontWeight: 700, fill: "#1b1530"}),
      // Saint-Denis está pegado a París: su nombre va debajo
      Plot.text(enMapa.filter((d) => d.lat < 48.9 || d.lon > 2.4 || d.lon < 2.3), {x: "lon", y: "lat", text: "ciudad", dy: -18, fontSize: 11, fontWeight: 600, stroke: "var(--theme-background)", strokeWidth: 3, fill: "var(--texto)"}),
      Plot.text(enMapa.filter((d) => !(d.lat < 48.9 || d.lon > 2.4 || d.lon < 2.3)), {x: "lon", y: "lat", text: "ciudad", dy: 20, fontSize: 11, fontWeight: 600, stroke: "var(--theme-background)", strokeWidth: 3, fill: "var(--texto)"}),
      Plot.tip(enMapa, Plot.pointer({x: "lon", y: "lat", title: (d) =>
        `${d.ciudad}\n${d.ganadas.map((f) => `🏆 ${f.temporada} · ${f.marcador} ${f.rival}`).join("\n")}${d.perdidas.length ? "\n" + d.perdidas.map((f) => `✗ ${f.temporada} · ${f.marcador} ${f.rival}`).join("\n") : ""}`}))
    ]
  });
}
```

<div class="card">
  <div class="leyenda"><span class="g-liga">${t("Ciudad con alguna final ganada", "City with a final won")}</span><span class="g-otros">${t("Solo finales perdidas", "Finals lost only")}</span><span class="sin">${t("Tamaño y número = finales jugadas allí", "Size and number = finals played there")}</span></div>
  ${resize((width) => mapaFinales(width))}
  <div class="nota">${(H.finales ?? []).filter((d) => d.gano).length} ${t("finales ganadas y", "finals won and")} ${(H.finales ?? []).filter((d) => !d.gano).length} ${t("perdidas", "lost")}: ${(H.finales ?? []).filter((d) => !d.gano).map((d) => `${d.temporada} (${d.rival}, ${d.marcador})`).join(" · ")}.</div>
</div>

## ${t("Rivales de siempre", "The great rivals")}

```js
const COMP_H2H = {"La Liga": t("Liga", "League"), "League": t("Liga", "League"), "Cup": "Copa del Rey", "Copa del Rey": "Copa del Rey",
  "League Cup": t("Copa de la Liga", "League Cup"), "Copa de la Liga": t("Copa de la Liga", "League Cup"),
  "Spanish Super Cup": t("Supercopa de España", "Spanish Super Cup"), "Supercopa de España": t("Supercopa de España", "Spanish Super Cup"),
  "UEFA Champions League": "Champions League", "UEFA Super Cup": t("Supercopa de Europa", "UEFA Super Cup"),
  "Copa de la Coronación": t("Copa de la Coronación (1902)", "Copa de la Coronación (1902)")};
const H2H = d3.sort((H.cara_a_cara ?? []).filter((d) => d.pj > 0 && !/All competitions|Total/i.test(d.competicion))
  .map((d) => ({...d, competicion: COMP_H2H[d.competicion] ?? d.competicion})), (d) => d.rival, (d) => -d.pj);
function caraACara(width) {
  const filas = H2H.flatMap((d) => [
    {rival: d.rival, competicion: d.competicion, tipo: "V", n: d.v, d},
    {rival: d.rival, competicion: d.competicion, tipo: "E", n: d.e, d},
    {rival: d.rival, competicion: d.competicion, tipo: "D", n: d.d, d}
  ]);
  const NOMBRE_RIVAL = {"Barcelona": t("Barcelona (el Clásico)", "Barcelona (El Clásico)"), "Atletico Madrid": t("Atlético (el derbi)", "Atlético (the derby)")};
  return Plot.plot({
    width, height: 34 * H2H.length + 60, marginLeft: Math.min(260, width * 0.4), marginRight: 40,
    x: {label: t("Proporción de partidos", "Share of matches"), percent: true, grid: true},
    y: {domain: H2H.map((d) => `${NOMBRE_RIVAL[d.rival]} · ${d.competicion}`), label: null},
    color: {domain: ["V", "E", "D"], range: ["var(--victoria)", "var(--empate)", "var(--derrota)"]},
    marks: [
      Plot.barX(filas, Plot.stackX({offset: "normalize", y: (d) => `${NOMBRE_RIVAL[d.rival]} · ${d.competicion}`, x: "n", fill: "tipo", insetTop: 4, insetBottom: 4,
        title: (d) => `${d.d.competicion}: ${d.d.pj} ${t("partidos", "matches")}\n${d.d.v} ${letraTxt("V")} · ${d.d.e} ${letraTxt("E")} · ${d.d.d} ${letraTxt("D")}\n${t("Goles", "Goals")} ${d.d.gf}–${d.d.gc}`, tip: true})),
      Plot.text(H2H, {y: (d) => `${NOMBRE_RIVAL[d.rival]} · ${d.competicion}`, x: 1, text: (d) => `${d.pj}`, dx: 14, fontSize: 11, fill: "var(--texto-suave)"})
    ]
  });
}
const letraTxt = (r) => ({V: t("victorias", "wins"), E: t("empates", "draws"), D: t("derrotas", "defeats")})[r];
```

<div class="card">
  <div class="leyenda"><span class="v">${t("Victorias del Madrid", "Madrid wins")}</span><span class="e">${t("Empates", "Draws")}</span><span class="d">${t("Derrotas", "Defeats")}</span><span class="sin">${t("A la derecha: partidos jugados", "On the right: matches played")}</span></div>
  ${resize((width) => caraACara(width))}
  <div class="nota">${t("Partidos oficiales según Wikipedia; puede tardar unos días en recoger el último.", "Official matches according to Wikipedia; it may take a few days to include the latest one.")}</div>
</div>

## ${t("Entrenadores", "Managers")}

```js
const conTitulos = (H.entrenadores_titulos ?? []).slice(0, 12);
function barrasEntrenadores(width) {
  const filas = conTitulos.flatMap((d) => [
    {nombre: d.nombre, tipo: "champions", n: d.champions}, {nombre: d.nombre, tipo: "liga", n: d.liga},
    {nombre: d.nombre, tipo: "copa", n: d.copa}, {nombre: d.nombre, tipo: "otros", n: d.total - d.champions - d.liga - d.copa}]);
  return Plot.plot({
    width, height: 30 * conTitulos.length + 40, marginLeft: 150,
    x: {label: t("Títulos", "Trophies"), grid: true},
    y: {domain: conTitulos.map((d) => d.nombre), label: null},
    color: {domain: Object.keys(COLOR), range: Object.values(COLOR)},
    marks: [
      Plot.barX(filas, Plot.stackX({y: "nombre", x: "n", fill: "tipo", insetTop: 4, insetBottom: 4, title: (d) => `${d.nombre}: ${d.n} · ${NOMBRE_GRUPO[d.tipo]}`, tip: true})),
      Plot.text(conTitulos, {y: "nombre", x: "total", text: "total", dx: 10, fontWeight: 700})
    ]
  });
}
const lista = (H.entrenadores ?? []).filter((d) => d.pj >= 20).map((d) => ({...d, pctv: d.v / d.pj}));
```

<div class="grid grid-cols-2">
  <div class="card">
    <h3>${t("Los que más ganaron", "The most successful")}</h3>
    <div class="leyenda">${Object.entries(NOMBRE_GRUPO).map(([k, v]) => html`<span class="g-${k}">${v}</span>`)}</div>
    ${resize((width) => barrasEntrenadores(width))}
  </div>
  <div class="card">
    <h3>${t("Todos (con 20 partidos o más)", "All of them (20+ matches)")}</h3>
    ${Inputs.table(lista.slice().reverse(), {
      columns: ["nombre", "desde", "hasta", "pj", "v", "e", "d", "pctv"],
      header: {nombre: t("Entrenador", "Manager"), desde: t("Desde", "From"), hasta: t("Hasta", "To"), pj: t("PJ", "P"), v: "V", e: "E", d: "D", pctv: t("% victorias", "Win %")},
      format: {pctv: (d) => pct(d, 0)}, layout: "auto", rows: 14, select: false, sort: "pctv", reverse: true
    })}
  </div>
</div>

## ${t("Récords", "Records")}

```js
function topBarras(datos, campo, etiqueta, width, color = "var(--rm)") {
  return Plot.plot({
    width, height: 30 * datos.length + 40, marginLeft: 150, marginRight: 50,
    x: {label: etiqueta, grid: true},
    y: {domain: datos.map((d) => d.jugador), label: null},
    marks: [
      Plot.barX(datos, {y: "jugador", x: campo, fill: color, insetTop: 4, insetBottom: 4, rx: 3}),
      Plot.text(datos, {y: "jugador", x: campo, text: (d) => ent(d[campo]), dx: 6, textAnchor: "start", fontWeight: 700}),
      Plot.tip(datos, Plot.pointerY({y: "jugador", x: campo, title: (d) => `${d.jugador} (${d.anios})\n${ent(d[campo])}${d.ratio ? ` · ${num(d.ratio)} ${t("por partido", "per match")}` : ""}`}))
    ]
  });
}
```

<div class="grid grid-cols-2">
  <div class="card"><h3>${t("Máximos goleadores", "Top scorers")}</h3>${resize((width) => topBarras(H.records?.goles ?? [], "goles", t("Goles oficiales", "Official goals"), width))}</div>
  <div class="card"><h3>${t("Más partidos", "Most appearances")}</h3>${resize((width) => topBarras(H.records?.partidos ?? [], "total", t("Partidos oficiales", "Official matches"), width, "var(--oro)"))}</div>
</div>

```js
const eu = (H.europa_resumen ?? []).filter((d) => d.competicion !== "Total");
const euTotal = (H.europa_resumen ?? []).find((d) => d.competicion === "Total");
```

<div class="card">
  <h3>${t("En competiciones internacionales", "In international competitions")}</h3>
  ${Inputs.table(eu, {
    columns: ["competicion", "pj", "v", "e", "d", "gf", "gc"],
    header: {competicion: t("Competición", "Competition"), pj: t("PJ", "P"), v: "V", e: "E", d: "D", gf: "GF", gc: t("GC", "GA")},
    layout: "auto", select: false
  })}
  ${euTotal ? html`<div class="nota">${t("En total", "In total")}: ${ent(euTotal.pj)} ${t("partidos", "matches")}, ${pct(euTotal.v / euTotal.pj)} ${t("ganados", "won")}, ${ent(euTotal.gf)} ${t("goles a favor", "goals scored")}.</div>` : ""}
</div>
