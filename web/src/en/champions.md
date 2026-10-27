---
title: Champions League
toc: false
---
<!-- GENERADO por `rma traducir` a partir de ../champions.md: no editar a mano -->

```js
import {fecha, fechaHora, diaLargo, hora, ordinal, letra, t} from "../components/formato.js";
import {pildoras} from "../components/ui.js";
import {cronologia, alineaciones, banquillo, estadisticas, escudoDe, conEscudoDe} from "../components/eventos.js";
import {nombre} from "../equipos/equipos.js";

const todas = FileAttachment("../data/partidos_todas.csv").csv({typed: true});
const eventos = FileAttachment("../data/eventos.json").json();
const tabla = FileAttachment("../data/champions_tabla.csv").csv({typed: true});
```

```js
const FASES = {
  "League Phase": t("Fase liga", "League phase"), "Knockout Round Playoffs": t("Eliminatoria previa", "Knockout play-offs"),
  "Round of 16": t("Octavos de final", "Round of 16"), "Quarterfinals": t("Cuartos de final", "Quarter-finals"),
  "Semifinals": t("Semifinales", "Semi-finals"), "Final": t("Final", "Final")
};
const fase = (f) => FASES[f] ?? f;
const ucl = todas.filter((d) => d.liga === "uefa.champions");
const jugados = ucl.filter((d) => d.jugado);
const pendientes = ucl.filter((d) => !d.jugado);
const rm = tabla.find((d) => d.equipo === "Real Madrid");
const marcador = (d) => `${d.goles_local}–${d.goles_visitante}${d.penaltis_local != null ? ` (${d.penaltis_local}–${d.penaltis_visitante} ${t("pen.", "pens")})` : ""}`;
const goleadores = (d, equipo) => (eventos[String(d.id)]?.eventos ?? [])
  .filter((e) => (e.tipo === "gol" && e.equipo === equipo) || (e.tipo === "autogol" && e.equipo !== equipo))
  .map((e) => `${e.jugador} ${e.reloj}${e.tipo === "autogol" ? t(" (p.p.)", " (o.g.)") : ""}`);
const zona = (p) => (p <= 8 ? "directo" : p <= 24 ? "playoff" : "fuera");
```

# Champions League

<div class="nota" style="margin:0.2rem 0 1.2rem">${t("Solo descriptivo: resultados, cronologías y tabla. Datos de ESPN.", "Descriptive only: results, timelines and table. Data from ESPN.")}</div>

<div class="grid grid-cols-4">
  <div class="card kpi">
    <div class="etiqueta">${t("Puesto en la fase liga", "League phase position")}</div>
    <div class="cifra">${rm ? ordinal(rm.puesto) : "–"}<small>${t("de", "of")} ${tabla.length}</small></div>
    <div class="nota">${rm ? (rm.puesto <= 8 ? t("Ahora mismo, a octavos directo", "Right now, straight into the last 16") : rm.puesto <= 24 ? t("Ahora mismo, a la eliminatoria previa", "Right now, into the play-offs") : t("Ahora mismo, fuera", "Right now, out")) : ""}</div>
  </div>
  <div class="card kpi">
    <div class="etiqueta">${t("Puntos", "Points")}</div>
    <div class="cifra">${rm?.puntos ?? "–"}<small>${t("en", "in")} ${rm?.pj ?? 0} ${t("partidos", "matches")}</small></div>
    <div class="nota">${rm ? `${rm.v} ${letra("V")} · ${rm.e} ${letra("E")} · ${rm.d} ${letra("D")}` : ""}</div>
  </div>
  <div class="card kpi">
    <div class="etiqueta">${t("Goles a favor – en contra", "Goals for – against")}</div>
    <div class="cifra">${rm ? `${rm.gf}–${rm.gc}` : "–"}</div>
    <div class="nota">${rm ? `${t("Diferencia", "Difference")} ${rm.dg > 0 ? "+" : ""}${rm.dg}` : ""}</div>
  </div>
  <div class="card kpi">
    <div class="etiqueta">${t("Racha en Europa", "European form")}</div>
    <div style="margin-top:0.6rem">${pildoras(jugados.slice(-5).map((d) => ({resultado: d.resultado, titulo: `${nombre(d.local)} ${marcador(d)} ${nombre(d.visitante)}`})))}</div>
    <div class="nota">${t("Últimos partidos de Champions", "Latest Champions League matches")}</div>
  </div>
</div>

```js
const sig = pendientes[0];
const ladoUcl = (eq, url) => html`<div class="lado"><div class="escudo-grande">${escudoDe(eq, url, 48)}</div><div class="nombre">${nombre(eq)}</div></div>`;
if (sig) display(html`<div class="card destacada">
  <div class="etiqueta">${t("Próximo partido de Champions", "Next Champions League match")} · ${fase(sig.fase)}</div>
  <div class="cuando">${diaLargo(sig.fecha)}, ${hora(sig.fecha)}</div>
  <div class="duelo">${ladoUcl(sig.local, sig.escudo_local)}<div class="centro">VS</div>${ladoUcl(sig.visitante, sig.escudo_visitante)}</div>
  <div class="nota" style="text-align:center">${sig.estadio ?? ""}</div>
</div>`);
```

## ${t("Resultados", "Results")}

```js
display(html`<div class="lista-partidos">${jugados.slice().reverse().map((d) => html`<div class="card partido-ucl res-borde-${d.resultado}">
  <div class="etiqueta">${fase(d.fase)} · ${fecha(d.fecha, true)}</div>
  <div class="fila-ucl">${conEscudoDe(d.local, d.escudo_local, 24)}<b class="marcador-ucl">${marcador(d)}</b>${conEscudoDe(d.visitante, d.escudo_visitante, 24)}</div>
  <div class="goleadores"><div>${goleadores(d, d.local).map((g) => html`<div>⚽ ${g}</div>`)}</div><div>${goleadores(d, d.visitante).map((g) => html`<div>⚽ ${g}</div>`)}</div></div>
</div>`)}</div>`);
```

## ${t("Un partido en detalle", "One match in detail")}

```js
const conDetalle = jugados.filter((d) => eventos[String(d.id)]).reverse();
const elegido = conDetalle.length ? view(Inputs.select(conDetalle, {label: t("Partido", "Match"),
  format: (d) => `${fecha(d.fecha)} · ${nombre(d.local)} ${marcador(d)} ${nombre(d.visitante)}`})) : null;
```

```js
const det = elegido ? eventos[String(elegido.id)] : null;
if (!det) display(html`<p>${t("Todavía no hay fichas de partidos de Champions.", "No Champions League match sheets yet.")}</p>`);
else display(html`<div class="card"><h3>${t("Alineaciones", "Line-ups")}</h3>
    ${banquillo(det, elegido.local)}
    ${resize((width) => alineaciones(det, {width}))}
    ${banquillo(det, elegido.visitante)}
    <div class="nota">${nombre(elegido.local)} ${t("ataca hacia la derecha", "attacks to the right")}. ▼ ${t("minuto del cambio", "minute subbed off")}.${det.arbitro ? ` ${t("Árbitro", "Referee")}: ${det.arbitro}.` : ""}</div>
  </div>
  <div class="grid grid-cols-2">
    <div class="card"><h3>${t("Cronología", "Timeline")}</h3>${cronologia(det, elegido.local, elegido.visitante, nombre)}</div>
    <div class="card"><h3>${t("Estadísticas", "Stats")}</h3>${estadisticas(det, elegido.local, elegido.visitante)}</div>
  </div>`);
```

## ${t("Clasificación de la fase liga", "League phase table")}

```js
display(html`<div class="card" style="overflow-x:auto">
  <div class="leyenda"><span class="z-directo">${t("1–8: octavos directos", "1–8: straight to last 16")}</span><span class="z-playoff">${t("9–24: eliminatoria previa", "9–24: play-offs")}</span><span class="z-fuera">${t("25–36: eliminados", "25–36: eliminated")}</span></div>
  <table class="tabla-ucl">
    <thead><tr><th></th><th>${t("Equipo", "Team")}</th><th>${t("PJ", "P")}</th><th>${letra("V")}</th><th>${letra("E")}</th><th>${letra("D")}</th><th>${t("GF", "GF")}</th><th>${t("GC", "GA")}</th><th>${t("DG", "GD")}</th><th>${t("Pts", "Pts")}</th></tr></thead>
    <tbody>${tabla.map((d) => html`<tr class="${zona(d.puesto)} ${d.equipo === "Real Madrid" ? "rm-fila" : ""}">
      <td><span class="puesto-ucl">${d.puesto}</span></td><td>${conEscudoDe(d.equipo, d.escudo, 18)}</td>
      <td>${d.pj}</td><td>${d.v}</td><td>${d.e}</td><td>${d.d}</td><td>${d.gf}</td><td>${d.gc}</td><td>${d.dg > 0 ? "+" : ""}${d.dg}</td><td><b>${d.puntos}</b></td>
    </tr>`)}</tbody>
  </table>
</div>`);
```

## ${t("Lo que queda", "Still to play")}

```js
display(pendientes.length ? html`<div class="card"><table class="tabla-ucl">${pendientes.map((d) => html`<tr>
  <td>${fecha(d.fecha, true)} · ${hora(d.fecha)}</td><td>${fase(d.fase)}</td>
  <td>${conEscudoDe(d.local, d.escudo_local, 18)}</td><td>–</td><td>${conEscudoDe(d.visitante, d.escudo_visitante, 18)}</td><td class="nota">${d.estadio ?? ""}</td>
</tr>`)}</table></div>` : html`<p>${t("No hay más partidos de Champions programados.", "No more Champions League matches scheduled.")}</p>`);
```
