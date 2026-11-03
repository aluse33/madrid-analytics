---
title: Next opponent
toc: false
---
<!-- GENERADO por `rma traducir` a partir de ../rival.md: no editar a mano -->

```js
import {num, pct, ent, fecha, fechaHora, letra, ordinal, tickNum, t} from "../components/formato.js";
import {nombre, escudo} from "../equipos/equipos.js";
import {barraPartido, pildoras} from "../components/ui.js";
import {densidadTiros} from "../components/rival.js";

const R = FileAttachment("../data/rivales.json").json();
const liga = FileAttachment("../data/liga_temporada.csv").csv({typed: true});
const ratings = FileAttachment("../data/ratings.csv").csv({typed: true});
const jugLiga = FileAttachment("../data/jugadores_liga.csv").csv({typed: true});
const rmp = FileAttachment("../data/rm_partidos.csv").csv({typed: true});
const prediccion = FileAttachment("../data/prediccion.json").json();
const todas = FileAttachment("../data/partidos_todas.csv").csv({typed: true});
const estado = FileAttachment("../data/estado.json").json();
```

```js
// el próximo rival de Liga: el primer partido que el modelo predice y que ESPN no da por jugado
const enEspn = (m) => todas.find((d) => d.liga === "esp.1" && d.rival === m.rival && Math.abs(d.fecha - new Date(m.fecha)) < 3 * 864e5);
const proxLiga = prediccion.partidos.find((m) => !enEspn(m)?.jugado);
const proxOficial = todas.find((d) => !d.jugado);
const equipos = Object.keys(R.equipos).filter((e) => e !== "Real Madrid").sort((a, b) => nombre(a).localeCompare(nombre(b)));
const pedido = new URLSearchParams(location.search).get("e");
const porDefecto = equipos.includes(pedido) ? pedido : proxLiga && equipos.includes(proxLiga.rival) ? proxLiga.rival : equipos[0];
const E = view(Inputs.select(equipos, {label: t("Equipo", "Team"), format: nombre, value: porDefecto}));
```

```js
history.replaceState(null, "", `?e=${encodeURIComponent(E)}`);
const info = R.equipos[E];
const jugados = liga.filter((d) => d.jugado);

// tabla de la Liga (y en casa / fuera) para todos, para poder dar el puesto de cada métrica
function filasDe(eq, filtro = () => true) {
  return jugados.filter((d) => (d.local === eq || d.visitante === eq) && filtro(d)).sort((a, b) => a.fecha - b.fecha).map((d) => {
    const casa = d.local === eq;
    const gf = casa ? d.goles_local : d.goles_visitante, gc = casa ? d.goles_visitante : d.goles_local;
    return {fecha: d.fecha, casa, rival: casa ? d.visitante : d.local, gf, gc, xgf: casa ? d.xg_local : d.xg_visitante, xgc: casa ? d.xg_visitante : d.xg_local,
      resultado: gf > gc ? "V" : gf === gc ? "E" : "D", puntos: gf > gc ? 3 : gf === gc ? 1 : 0,
      titulo: `${casa ? "vs" : "@"} ${nombre(casa ? d.visitante : d.local)} ${gf}–${gc}`};
  });
}
const resumir = (f) => ({pj: f.length, puntos: d3.sum(f, (d) => d.puntos), gf: d3.sum(f, (d) => d.gf), gc: d3.sum(f, (d) => d.gc),
  xgf: d3.mean(f, (d) => d.xgf), xgc: d3.mean(f, (d) => d.xgc), ppp: f.length ? d3.sum(f, (d) => d.puntos) / f.length : null});
const todos = [...new Set(jugados.flatMap((d) => [d.local, d.visitante]))];
const tabla = d3.sort(todos.map((e) => ({equipo: e, ...resumir(filasDe(e))})), (a, b) => b.puntos - a.puntos || (b.gf - b.gc) - (a.gf - a.gc) || b.gf - a.gf)
  .map((d, i) => ({...d, puesto: i + 1}));
const fila = tabla.find((d) => d.equipo === E);
const puestoEn = (k, asc = false) => 1 + tabla.filter((d) => (asc ? d[k] < fila[k] : d[k] > fila[k])).length;
const partidos = filasDe(E);
const casa = resumir(partidos.filter((d) => d.casa)), fuera = resumir(partidos.filter((d) => !d.casa));

// ¿es el próximo rival? entonces, el partido y la predicción
const P = proxLiga && proxLiga.rival === E ? {...proxLiga, fecha: enEspn(proxLiga)?.fecha ?? new Date(proxLiga.fecha)} : null;
const rivalJuegaEnCasa = P ? P.local === E : null;
function marcadores(p, k = 3) {
  const out = [];
  p.matriz.forEach((fila, i) => fila.forEach((v, j) => out.push({i, j, v})));
  return out.sort((a, b) => b.v - a.v).slice(0, k);
}
const otraAntes = proxOficial && P && proxOficial.liga !== "esp.1" && proxOficial.fecha < P.fecha ? proxOficial : null;
```

```js
display(html`<div class="card destacada">
  <div class="cab-rival">
    <div class="escudo-grande">${escudo(E, 64)}</div>
    <div>
      <div class="etiqueta">${P ? t("Próximo rival en Liga", "Next league opponent") : t("Informe de rival", "Opponent report")} · LaLiga ${estado.temporada}</div>
      <h1 style="color:#fff">${nombre(E)}</h1>
      <div class="fila-forma"><span class="etiqueta">${fila ? `${ordinal(fila.puesto)} · ${fila.puntos} ${t("puntos", "points")}` : ""}</span>${pildoras(partidos.slice(-5))}</div>
    </div>
  </div>
  ${P ? html`<div style="margin-top:0.8rem">
    <div class="etiqueta">${P.local === "Real Madrid" ? `Real Madrid – ${nombre(E)}` : `${nombre(E)} – Real Madrid`} · ${fechaHora(P.fecha)}</div>
    ${barraPartido(P, nombre)}
    <div class="nota">${t("Goles esperados", "Expected goals")}: Madrid ${num(P.goles_esperados_rm, 1)} · ${nombre(E)} ${num(P.goles_esperados_rival, 1)} ·
      ${t("marcadores más probables", "most likely scores")}: ${marcadores(P).map((m) => `${m.i}–${m.j} (${pct(m.v)})`).join(", ")} ·
      <a href="./prediccion">${t("Predicción completa", "Full forecast")}</a></div>
    ${otraAntes ? html`<div class="nota">${t("Antes hay partido de", "Before that there is a")} ${otraAntes.competicion}: ${nombre(otraAntes.local)} – ${nombre(otraAntes.visitante)}, ${fecha(otraAntes.fecha)}.</div>` : ""}
  </div>` : ""}
</div>`);
```

```js
display(!fila ? html`<span></span>` : html`<div class="grid grid-cols-4">
  <div class="card kpi"><div class="etiqueta">${t("Goles por partido", "Goals per match")}</div>
    <div class="cifra">${num(fila.gf / fila.pj, 1)}<small>${t("a favor", "for")}</small></div>
    <div class="nota">${num(fila.gc / fila.pj, 1)} ${t("en contra", "against")} · ${fila.pj} ${t("partidos", "matches")}</div></div>
  <div class="card kpi"><div class="etiqueta">${t("xG a favor por partido", "xG for per match")}</div>
    <div class="cifra">${num(fila.xgf)}<small>${ordinal(puestoEn("xgf"))}</small></div>
    <div class="nota">${t("Puesto en LaLiga: cuánto peligro genera", "LaLiga rank: how much danger it creates")}</div></div>
  <div class="card kpi"><div class="etiqueta">${t("xG en contra por partido", "xG against per match")}</div>
    <div class="cifra">${num(fila.xgc)}<small>${ordinal(puestoEn("xgc", true))}</small></div>
    <div class="nota">${t("Puesto en LaLiga: 1.º = el que menos concede", "LaLiga rank: 1st = concedes the least")}</div></div>
  <div class="card kpi"><div class="etiqueta">${t("Goles frente a xG", "Goals vs xG")}</div>
    <div class="cifra">${(fila.gf - fila.xgf * fila.pj) >= 0 ? "+" : ""}${num(fila.gf - fila.xgf * fila.pj, 1)}</div>
    <div class="nota">${t("Goles marcados menos los esperados: positivo = está rindiendo por encima de sus ocasiones", "Goals scored minus expected: positive = finishing above its chances")}</div></div>
</div>`);
```

```js
function partidoAPartido(width) {
  const datos = partidos.map((d, i) => ({...d, i}));
  const tope = Math.max(2.5, d3.max(datos, (d) => Math.max(d.xgf, d.xgc)) ?? 0) * 1.1;
  return Plot.plot({
    width, height: 250,
    x: {domain: datos.map((d) => d.i), axis: null, padding: 0.2},
    y: {domain: [-tope, tope], label: t("xG (arriba, a favor; abajo, en contra)", "xG (up, for; down, against)"), grid: true, tickFormat: (v) => tickNum(Math.abs(v))},
    marks: [
      Plot.barY(datos, {x: "i", y: "xgf", fill: "var(--rival)", rx: 2}),
      Plot.barY(datos, {x: "i", y: (d) => -d.xgc, fill: "var(--empate)", rx: 2}),
      Plot.ruleY([0], {stroke: "var(--theme-foreground-muted)"}),
      Plot.dot(datos, {x: "i", y: tope * 0.93, r: 5, fill: (d) => ({V: "var(--victoria)", E: "var(--empate)", D: "var(--derrota)"})[d.resultado]}),
      Plot.tip(datos, Plot.pointerX({x: "i", y: 0, title: (d) => `${fecha(d.fecha)} · ${d.casa ? "vs" : "@"} ${nombre(d.rival)}\n${t("Resultado", "Result")} ${d.gf}–${d.gc} (${letra(d.resultado)})\nxG ${num(d.xgf)} – ${num(d.xgc)}`}))
    ]
  });
}
const lado = (titulo, r, resaltar) => html`<tr class=${resaltar ? "resaltada" : ""}><td>${titulo}${resaltar ? html` <span class="sello sello-si">${t("así jugará", "this fixture")}</span>` : ""}</td>
  <td>${r.pj}</td><td>${r.ppp == null ? "–" : num(r.ppp, 2)}</td><td>${r.gf}–${r.gc}</td><td>${r.xgf == null ? "–" : num(r.xgf)}</td><td>${r.xgc == null ? "–" : num(r.xgc)}</td></tr>`;
```

<div class="grid grid-cols-2" style="grid-template-columns: minmax(0, 3fr) minmax(0, 2fr)">
  <div class="card">
    <h3>${t("Partido a partido", "Match by match")}</h3>
    <div class="leyenda"><span class="rival">${t("xG a favor", "xG for")}</span><span class="empate">${t("xG en contra", "xG against")}</span><span class="sin">${t("Punto = resultado", "Dot = result")}</span></div>
    ${resize((width) => partidoAPartido(width))}
  </div>
  <div class="card">
    <h3>${t("En casa y fuera", "Home and away")}</h3>
    <table class="perfil" style="width:100%;max-width:none">
      <tr><th></th><th>PJ</th><th>${t("Pts/p", "Pts/g")}</th><th>${t("Goles", "Goals")}</th><th>xGF</th><th>xGC</th></tr>
      ${lado(t("En casa", "Home"), casa, rivalJuegaEnCasa === true)}
      ${lado(t("Fuera", "Away"), fuera, rivalJuegaEnCasa === false)}
    </table>
    <div class="nota">${t("xGF y xGC, por partido.", "xGF and xGC, per match.")}</div>
  </div>
</div>

## ${t("Cómo ataca y cómo defiende", "How it attacks and defends")}

```js
// medias de LaLiga para comparar el perfil de tiro
const media = (lado, k) => d3.mean(Object.values(R.equipos), (d) => d[lado][k]);
const METRICAS = [["tiros_pp", t("Tiros por partido", "Shots per match"), 1], ["npxg_pp", t("npxG por partido", "npxG per match"), 2],
  ["xg_por_tiro", t("xG por tiro (calidad de ocasión)", "xG per shot (chance quality)"), 3], ["pct_fuera_area", t("Tiros desde fuera del área", "Shots from outside the box"), "%"],
  ["pct_cabeza", t("Remates de cabeza", "Headers"), "%"], ["pct_balon_parado", t("Tiros a balón parado", "Set-piece shots"), "%"]];
function perfil(ladoK, mejorSiAlto) {
  return html`<table class="perfil" style="width:100%;max-width:none">
    <tr><th></th><th>${nombre(E)}</th><th>${t("Media LaLiga", "LaLiga avg")}</th></tr>
    ${METRICAS.map(([k, txt, d]) => {
      const v = info[ladoK][k], m = media(ladoK, k);
      const fmt = (x) => (x == null ? "–" : d === "%" ? pct(x) : num(x, d));
      const destaca = v != null && m && Math.abs(v - m) / m > 0.15 && ["tiros_pp", "npxg_pp", "xg_por_tiro"].includes(k);
      const bueno = destaca && ((v > m) === mejorSiAlto);
      return html`<tr><td>${txt}</td><td>${fmt(v)} ${destaca ? html`<span class=${bueno ? "flecha-mejor" : "flecha-peor"}>${v > m ? "▲" : "▼"}</span>` : ""}</td><td>${fmt(m)}</td></tr>`;
    })}
    <tr><td>${t("Goles a balón parado", "Set-piece goals")}</td><td>${info[ladoK].goles_balon_parado} ${t("de", "of")} ${info[ladoK].goles}</td><td></td></tr>
  </table>`;
}
```

<div class="grid grid-cols-2">
  <div class="card">
    <h3>${t("Desde dónde tira", "Where it shoots from")}</h3>
    <div style="max-width:420px;margin:0 auto">${resize((width) => densidadTiros(info.favor.rejilla, {width, rejilla: R.rejilla, tipo: "favor"}))}</div>
    ${perfil("favor", true)}
    <div class="nota">${info.favor.n} ${t("tiros sin contar penaltis. La portería, arriba. ▲▼ = más de un 15 % por encima o por debajo de la media (verde, bueno para", "shots excluding penalties. Goal at the top. ▲▼ = more than 15% above or below average (green, good for")} ${nombre(E)}).</div>
  </div>
  <div class="card">
    <h3>${t("Desde dónde le tiran", "Where it concedes shots from")}</h3>
    <div style="max-width:420px;margin:0 auto">${resize((width) => densidadTiros(info.contra.rejilla, {width, rejilla: R.rejilla, tipo: "contra"}))}</div>
    ${perfil("contra", false)}
    <div class="nota">${info.contra.n} ${t("tiros de sus rivales, sin penaltis. Aquí, verde = concede menos que la media.", "shots by its opponents, excluding penalties. Here, green = concedes less than average.")}</div>
  </div>
</div>

```js
function tramos(width) {
  const etiquetas = R.tramos.map((d, i) => (i === R.tramos.length - 1 ? `${d}′+` : `${d}–${R.tramos[i + 1]}′`));
  const filas = etiquetas.flatMap((tr, i) => [
    {tr, v: info.tramos_favor.goles[i], xg: info.tramos_favor.xg[i], quien: "favor"},
    {tr, v: -info.tramos_contra.goles[i], xg: -info.tramos_contra.xg[i], quien: "contra"}]);
  const tope = Math.max(3, d3.max(filas, (d) => Math.max(Math.abs(d.v), Math.abs(d.xg)))) * 1.15;
  return Plot.plot({
    width, height: 250,
    x: {domain: etiquetas, label: null},
    y: {domain: [-tope, tope], label: t("Goles (arriba, marcados; abajo, encajados)", "Goals (up, scored; down, conceded)"), grid: true, tickFormat: (v) => tickNum(Math.abs(v))},
    marks: [
      // una marca por serie: dentro de una misma marca, Plot apilaría a favor y en contra
      ...["favor", "contra"].flatMap((q) => {
        const f = filas.filter((d) => d.quien === q), color = q === "favor" ? "var(--rival)" : "var(--empate)";
        return [Plot.barY(f, {x: "tr", y: "xg", fill: color, fillOpacity: 0.25, insetLeft: 6, insetRight: 6}),
          Plot.barY(f, {x: "tr", y: "v", fill: color, insetLeft: 14, insetRight: 14, rx: 2})];
      }),
      Plot.ruleY([0], {stroke: "var(--theme-foreground-muted)"}),
      Plot.tip(filas, Plot.pointer({x: "tr", y: "v", title: (d) => `${d.tr} · ${d.quien === "favor" ? t("marcados", "scored") : t("encajados", "conceded")}: ${Math.abs(d.v)}\nxG ${num(Math.abs(d.xg))}`}))
    ]
  });
}
const peligro = jugLiga.filter((d) => d.equipo === E && d.minutos >= 180).sort((a, b) => (b.npxg + b.xa) - (a.npxg + a.xa)).slice(0, 6);
```

<div class="grid grid-cols-2">
  <div class="card">
    <h3>${t("Cuándo marca y cuándo encaja", "When it scores and concedes")}</h3>
    <div class="leyenda"><span class="rival">${t("Marcados", "Scored")}</span><span class="empate">${t("Encajados", "Conceded")}</span><span class="sin">${t("Barra clara = xG del tramo", "Pale bar = xG in the window")}</span></div>
    ${resize((width) => tramos(width))}
    <div class="nota">${t("Por tramos de 15 minutos; el último incluye el añadido. Sin autogoles.", "In 15-minute windows; the last one includes stoppage time. Own goals excluded.")}</div>
  </div>
  <div class="card">
    <h3>${t("Jugadores a vigilar", "Players to watch")}</h3>
    ${peligro.length ? Inputs.table(peligro, {
      columns: ["jugador", "minutos", "goles", "asistencias", "npxg", "xa"],
      header: {jugador: t("Jugador", "Player"), minutos: "Min", goles: "G", asistencias: "A", npxg: "npxG", xa: "xA", npxg_p90: t("npxG/90", "npxG/90"), xa_p90: t("xA/90", "xA/90")},
      format: {npxg: (v) => num(v, 1), xa: (v) => num(v, 1), npxg_p90: (v) => num(v), xa_p90: (v) => num(v)},
      select: false, layout: "auto", width: {jugador: 150}
    }) : html`<p>${t("Sin datos de jugadores.", "No player data.")}</p>`}
    <div class="nota">${t("Ordenados por npxG + xA: el peligro que genera cada uno con sus tiros y sus pases. Mínimo 180 minutos.", "Sorted by npxG + xA: the danger each one creates with shots and passes. Minimum 180 minutes.")}</div>
  </div>
</div>

## ${t("Frente al Madrid", "Against Madrid")}

```js
const rE = ratings.find((d) => d.equipo === E), rRM = ratings.find((d) => d.equipo === "Real Madrid");
const rankR = (k, asc) => 1 + ratings.filter((d) => (asc ? d[k] < rE[k] : d[k] > rE[k])).length;
const h2h = rmp.filter((d) => d.rival === E && d.jugado).sort((a, b) => b.fecha - a.fecha);
const balance = {V: h2h.filter((d) => d.resultado === "V").length, E: h2h.filter((d) => d.resultado === "E").length, D: h2h.filter((d) => d.resultado === "D").length};
display(html`<div class="grid grid-cols-2">
  <div class="card">
    <h3>${t("Fuerza según el modelo", "Strength according to the model")}</h3>
    ${rE ? html`<table class="mini">
      <tr><td>${t("Goles que marcaría a un rival medio", "Goals vs an average side")}</td><td>${num(rE.goles_esperados_vs_medio)} <span class="nota">(${ordinal(rankR("goles_esperados_vs_medio"))})</span></td></tr>
      <tr><td>${t("Goles que encajaría de un rival medio", "Goals conceded to an average side")}</td><td>${num(rE.goles_concedidos_vs_medio)} <span class="nota">(${ordinal(rankR("goles_concedidos_vs_medio", true))})</span></td></tr>
      <tr><td>${t("El Madrid, en lo mismo", "Madrid, same figures")}</td><td>${num(rRM.goles_esperados_vs_medio)} / ${num(rRM.goles_concedidos_vs_medio)}</td></tr>
    </table>` : html`<p>${t("Sin rating todavía.", "No rating yet.")}</p>`}
    <div class="nota">${t("Del modelo Dixon-Coles, con el último medio año pesando más. Puesto entre los 20 de LaLiga entre paréntesis.", "From the Dixon–Coles model, with the last six months weighted more. LaLiga rank in brackets.")}</div>
  </div>
  <div class="card">
    <h3>${t("Cara a cara en Liga desde 2019/20", "Head to head in LaLiga since 2019/20")}</h3>
    ${h2h.length ? html`<div class="fila-forma"><span class="etiqueta">Madrid: ${balance.V} ${letra("V")} · ${balance.E} ${letra("E")} · ${balance.D} ${letra("D")}</span></div>
    <table class="tabla-pred"><thead><tr><th>${t("Fecha", "Date")}</th><th></th><th>${t("Resultado", "Result")}</th><th>xG</th></tr></thead><tbody>
      ${h2h.slice(0, 8).map((d) => html`<tr><td>${fecha(d.fecha, true)}</td><td>${d.condicion === "Local" ? t("en el Bernabéu", "at the Bernabéu") : t("fuera", "away")}</td>
        <td><span class="res-marcador res-${d.resultado}">${d.condicion === "Local" ? `${d.gf}–${d.gc}` : `${d.gc}–${d.gf}`}</span></td><td>${num(d.xgf, 1)} – ${num(d.xgc, 1)}</td></tr>`)}
    </tbody></table>` : html`<p>${t("No se han enfrentado en Liga desde 2019/20.", "They have not met in LaLiga since 2019/20.")}</p>`}
    <div class="nota">${t("Marcador con el local primero; xG del Madrid primero.", "Score with the home side first; Madrid's xG first.")}</div>
  </div>
</div>`);
```
