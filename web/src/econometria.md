---
title: Econometría
---

```js
import {num, ent, tickNum, t} from "./components/formato.js";
const eco = FileAttachment("data/econometria.json").json();
```

```js
// ---------- lectura automática de cada resultado: nada de cifras escritas a mano
const NIVEL = eco.metodo?.nivel ?? 0.05;
// texto propio con <b> y <i>: se pinta como HTML (nunca se usa con datos de fuera)
const H = (s) => Object.assign(document.createElement("span"), {innerHTML: s});
const signo = (v, d = 2) => (v == null ? "–" : `${v > 0 ? "+" : ""}${num(v, d)}`);
const pTxt = (p) => (p < 0.001 ? "p < 0,001" : `p = ${num(p, 3)}`).replace(/,/g, t(",", "."));
const esSig = (e) => e && e.p < NIVEL;
const veredicto = (e) => !e ? "" : esSig(e)
  ? html`<span class="sello sello-si">${t("Distinto de cero al 5 %", "Different from zero at 5%")}</span>`
  : html`<span class="sello sello-no">${t("No se distingue de cero", "Not distinguishable from zero")}</span>`;
const intervalo = (e, d = 2) => `[${signo(e.ci95[0], d)}, ${signo(e.ci95[1], d)}]`;
const param = (res, nombre) => res?.parametros?.find((p) => p.param === nombre);

const bernabeu = param(eco.localia?.regresion, "local");
const corto = param(eco.descanso?.regresion, "corto");
const champions = param(eco.descanso?.champions, "tras_champions");
const ausencias = eco.ausencias ?? [];
const benzema = ausencias.find((a) => a.jugador === "Karim Benzema");
```

# ${t("Econometría", "Econometrics")}

<p class="nota" style="margin:0.2rem 0 1rem">${t("Regresiones con efectos fijos de rival y temporada y errores estándar agrupados por rival.", "Regressions with opponent and season fixed effects and standard errors clustered by opponent.")}</p>

<p>${H(t("Las medias simples engañan. Un equipo puede generar más xG sin su estrella no porque juegue mejor sin ella, sino porque el entrenador la deja descansar contra los rivales más flojos. Aquí cada comparación se hace <b>contra el mismo rival y dentro de la misma temporada</b>, que es la forma estándar de quitar ese sesgo.", "Simple averages mislead. A team may create more xG without its star not because it plays better without him, but because the coach rests him against weaker opponents. Here every comparison is made <b>against the same opponent and within the same season</b>, the standard way to remove that bias."))}</p>

<div class="aviso aviso-obras">${H(t("Son <b>asociaciones ajustadas</b>, no efectos causales garantizados: que un jugador no sea titular no es aleatorio (lesiones, sanciones, rotaciones en partidos sin nada en juego) y eso no lo arregla ningún control. Léelo como «lo que queda después de quitar el efecto del rival y de la temporada».", "These are <b>adjusted associations</b>, not guaranteed causal effects: whether a player starts is not random (injuries, suspensions, rotation in dead rubbers) and no control fixes that. Read it as “what is left after removing the effect of the opponent and the season”."))}</div>

<div class="grid grid-cols-4">
  <div class="card kpi">
    <div class="etiqueta">${t("Jugar en el Bernabéu", "Playing at the Bernabéu")}</div>
    <div class="cifra">${signo(bernabeu?.coef)}<small>xG</small></div>
    <div class="nota">${t("de diferencia de xG frente al mismo rival fuera", "xG difference vs the same opponent away")} · ${bernabeu ? pTxt(bernabeu.p) : ""}</div>
    ${veredicto(bernabeu)}
  </div>
  <div class="card kpi">
    <div class="etiqueta">${t("Sin Benzema de titular", "Without Benzema starting")}</div>
    <div class="cifra">${signo(benzema?.efecto.coef)}<small>xG</small></div>
    <div class="nota">${t("diferencia de xG por partido", "xG difference per match")} · ${benzema ? pTxt(benzema.efecto.p) : ""}</div>
    ${veredicto(benzema?.efecto)}
  </div>
  <div class="card kpi">
    <div class="etiqueta">${t("Con 3 días o menos de descanso", "With 3 days' rest or less")}</div>
    <div class="cifra">${signo(corto?.coef)}<small>xG</small></div>
    <div class="nota">${t("frente a una semana normal", "vs a normal week")} · ${corto ? pTxt(corto.p) : ""}</div>
    ${veredicto(corto)}
  </div>
  <div class="card kpi">
    <div class="etiqueta">${t("Justo después de Champions", "Right after a Champions League game")}</div>
    <div class="cifra">${signo(champions?.coef)}<small>xG</small></div>
    <div class="nota">${ent(eco.descanso?.n_tras_champions)} ${t("partidos", "matches")} · ${champions ? pTxt(champions.p) : ""}</div>
    ${veredicto(champions)}
  </div>
</div>

## ${t("1. El efecto Bernabéu", "1. The Bernabéu effect")}

```js
const L = eco.localia;
display(L?.regresion ? html`<div class="grid grid-cols-2">
  <div class="card">
    <h3>${t("En bruto", "Raw")}</h3>
    <table class="mini">
      <tr><td>${t("En casa", "Home")} (${L.n_local})</td><td>${num(L.local_xgf, 2)} – ${num(L.local_xgc, 2)} xG · <b>${signo(L.local_dif)}</b></td></tr>
      <tr><td>${t("Fuera", "Away")} (${L.n_visitante})</td><td>${num(L.visit_xgf, 2)} – ${num(L.visit_xgc, 2)} xG · <b>${signo(L.visit_dif)}</b></td></tr>
      <tr><td>${t("Diferencia", "Difference")}</td><td><b>${signo(L.local_dif - L.visit_dif)}</b></td></tr>
    </table>
    <div class="nota">${t("xG a favor – en contra por partido de Liga, desde 2019/20.", "xG for – against per league match, since 2019/20.")}</div>
  </div>
  <div class="card">
    <h3>${t("Contra el mismo rival y en la misma temporada", "Against the same opponent, in the same season")}</h3>
    <div class="cifra">${signo(bernabeu.coef, 2)}<small>xG</small></div>
    <p>${t("Intervalo del 95 %", "95% interval")}: <b>${intervalo(bernabeu)}</b> · ${pTxt(bernabeu.p)}</p>
    ${veredicto(bernabeu)}
    <p class="nota">${esSig(bernabeu)
      ? t(`Jugando en casa, el Madrid saca de media ${num(bernabeu.coef, 2)} xG más de diferencia que contra el mismo rival a domicilio. Es el resultado más sólido de la página: el calendario reparte casa y fuera casi al azar.`,
          `At home, Madrid's xG difference is on average ${num(bernabeu.coef, 2)} higher than against the same opponent away. It is the most robust result on this page: the fixture list assigns home and away almost at random.`)
      : t("Con los partidos disponibles no se distingue de cero.", "With the matches available it cannot be told apart from zero.")}</p>
  </div>
</div>` : html`<p>${t("Todavía no hay datos suficientes.", "Not enough data yet.")}</p>`);
```

## ${t("2. Descanso y «resaca europea»", "2. Rest and the “European hangover”")}

```js
const D = eco.descanso;
const NOMBRE_CAT = {corto: t("≤ 3 días", "≤ 3 days"), medio: t("4–5 días", "4–5 days"), normal: t("6–8 días (referencia)", "6–8 days (reference)"), largo: t("9–30 días", "9–30 days")};
const NOMBRE_PAR = {corto: t("≤ 3 días", "≤ 3 days"), medio: t("4–5 días", "4–5 days"), largo: t("9–30 días", "9–30 days"), local: t("En casa", "At home"), tras_champions: t("Tras Champions", "After Champions League")};
```

<p>${H(t("Días desde el partido oficial anterior, <b>de cualquier competición</b>: un partido de Liga el sábado después de jugar Champions el miércoles cuenta como 3 días de descanso, no como una semana. El primer partido de cada temporada no cuenta.", "Days since the previous official match <b>in any competition</b>: a Saturday league game after a Wednesday Champions League game counts as 3 days' rest, not a week. The first match of each season is left out."))}</p>

```js
function graficoDescanso(width) {
  const filas = D.categorias.map((c) => ({...c, nombre: NOMBRE_CAT[c.categoria]}));
  return Plot.plot({
    width, height: 50 * filas.length + 50, marginLeft: 150, marginRight: 90,
    x: {label: t("Diferencia de xG media por partido (intervalo bootstrap del 95 %)", "Mean xG difference per match (95% bootstrap interval)"), grid: true, tickFormat: tickNum},
    y: {domain: filas.map((d) => d.nombre), label: null},
    marks: [
      Plot.ruleY(filas, {y: "nombre", x1: (d) => d.ci95_dif[0], x2: (d) => d.ci95_dif[1], stroke: "var(--rm)", strokeWidth: 2.5, strokeOpacity: 0.6}),
      Plot.dot(filas, {y: "nombre", x: "dif_xg_medio", fill: "var(--rm)", r: 6, stroke: "var(--theme-background)", strokeWidth: 2}),
      Plot.text(filas, {y: "nombre", x: (d) => d.ci95_dif[1], text: (d) => `${d.n} ${t("partidos", "matches")}`, dx: 8, textAnchor: "start", fontSize: 11, fill: "var(--texto-suave)"}),
      Plot.tip(filas, Plot.pointerY({y: "nombre", x: "dif_xg_medio",
        title: (d) => `${d.nombre} · ${d.n} ${t("partidos", "matches")} (${t("media", "mean")} ${num(d.dias_medio, 1)} ${t("días", "days")})\nxG ${num(d.xgf_medio, 2)} – ${num(d.xgc_medio, 2)}`}))
    ]
  });
}
const tablaReg = (res) => html`<table class="mini tabla-reg">
  <tr><th></th><th>${t("Coef.", "Coef.")}</th><th>${t("Intervalo 95 %", "95% interval")}</th><th>p</th><th></th></tr>
  ${res.parametros.map((p) => html`<tr><td>${NOMBRE_PAR[p.param] ?? p.param}</td><td>${signo(p.coef, 3)}</td><td>${intervalo(p)}</td><td>${p.p < 0.001 ? "< 0,001".replace(",", t(",", ".")) : num(p.p, 3)}</td><td>${esSig(p) ? "✓" : ""}</td></tr>`)}
</table>`;
```

```js
display(D?.categorias ? html`<div class="card">
  <h3>${t("En bruto, por días de descanso", "Raw, by days of rest")}</h3>
  ${resize((width) => graficoDescanso(width))}
  ${D.calendario_completo ? "" : html`<div class="aviso">${t("Falta el calendario de las otras competiciones: el descanso solo cuenta partidos de Liga.", "The other competitions' fixtures are missing: rest only counts league matches.")}</div>`}
</div>
<div class="grid grid-cols-2">
  <div class="card">
    <h3>${t("Ajustado por rival y temporada", "Adjusted for opponent and season")}</h3>
    ${tablaReg(D.regresion)}
    <p class="nota">${t("Diferencia frente a una semana normal (6–8 días). ✓ = distinto de cero al 5 %.", "Difference vs a normal week (6–8 days). ✓ = different from zero at 5%.")} ${D.regresion.n} ${t("partidos", "matches")}, ${D.regresion.clusters} ${t("rivales", "opponents")}.</p>
    <p>${esSig(corto)
      ? t(`Con 3 días o menos de descanso, la diferencia de xG cambia en ${signo(corto.coef)} por partido, y el cambio es distinto de cero.`, `With 3 days' rest or less, the xG difference changes by ${signo(corto.coef)} per match, and the change is different from zero.`)
      : t(`Con 3 días o menos de descanso, la diferencia de xG cambia en ${signo(corto.coef)} por partido, pero el intervalo ${intervalo(corto)} incluye el cero: no hay pruebas de que el cansancio se note en las ocasiones.`, `With 3 days' rest or less, the xG difference changes by ${signo(corto.coef)} per match, but the interval ${intervalo(corto)} includes zero: there is no evidence that fatigue shows in the chances.`)}</p>
  </div>
  <div class="card">
    <h3>${t("Justo después de jugar Champions", "Right after a Champions League game")}</h3>
    ${D.champions?.parametros?.length ? tablaReg(D.champions) : ""}
    <p>${!champions ? t("No hay datos suficientes.", "Not enough data.") : D.n_tras_champions < 20
      ? t(`Solo hay ${D.n_tras_champions} partidos de Liga justo después de Champions: demasiado pocos para concluir nada.`, `There are only ${D.n_tras_champions} league matches right after a Champions League game: too few to conclude anything.`)
      : esSig(champions)
        ? t(`En los ${D.n_tras_champions} partidos de Liga que siguen a uno de Champions, la diferencia de xG cambia en ${signo(champions.coef)} y el cambio es distinto de cero.`, `In the ${D.n_tras_champions} league matches that follow a Champions League game, the xG difference changes by ${signo(champions.coef)}, and the change is different from zero.`)
        : t(`En los ${D.n_tras_champions} partidos de Liga que siguen a uno de Champions, la diferencia de xG cambia en ${signo(champions.coef)}, con un intervalo ${intervalo(champions)} que incluye el cero: no se ve «resaca europea».`, `In the ${D.n_tras_champions} league matches that follow a Champions League game, the xG difference changes by ${signo(champions.coef)}, with an interval ${intervalo(champions)} that includes zero: no “European hangover” is visible.`)}</p>
  </div>
</div>` : html`<p>${t("Todavía no hay datos suficientes.", "Not enough data yet.")}</p>`);
```

## ${t("3. Cuando un jugador clave no es titular", "3. When a key player does not start")}

```js
const ROL = {"Karim Benzema": t("delantero centro, eje del ataque", "centre-forward, focal point of the attack"),
  "Vinícius Júnior": t("extremo, desequilibrio y finalización", "winger, dribbling and finishing"),
  "Thibaut Courtois": t("portero", "goalkeeper")};
const VARIABLE = {dif_xg: t("diferencia de xG por partido", "xG difference per match"),
  goles_evitados: t("goles evitados por partido (xG en contra − goles en contra)", "goals prevented per match (xG against − goals against)")};
const elegido = ausencias.length ? view(Inputs.radio(ausencias.map((a) => a.jugador), {label: t("Jugador", "Player"), value: ausencias[0].jugador})) : null;
```

```js
const A = ausencias.find((a) => a.jugador === elegido);
const periodo = (a) => a.temporadas.length > 1 ? `${a.temporadas[0]} – ${a.temporadas.at(-1)}` : a.temporadas[0];
function bosqueAusencias(width) {
  const filas = ausencias.map((a) => ({jugador: a.jugador, coef: a.efecto.coef, inf: a.efecto.ci95[0], sup: a.efecto.ci95[1], bruto: a.diferencia_bruta, variable: a.variable}));
  return Plot.plot({
    width, height: 60 * filas.length + 50, marginLeft: 130, marginRight: 30,
    x: {label: t("Cambio al no ser titular (intervalo del 95 %)", "Change when not starting (95% interval)"), grid: true, tickFormat: tickNum},
    y: {domain: filas.map((d) => d.jugador), label: null},
    marks: [
      Plot.ruleX([0], {stroke: "var(--theme-foreground-muted)", strokeDasharray: "4,4"}),
      Plot.ruleY(filas, {y: "jugador", x1: "inf", x2: "sup", stroke: "var(--rm)", strokeWidth: 2.5}),
      Plot.dot(filas, {y: "jugador", x: "bruto", r: 5, stroke: "var(--texto-suave)", strokeWidth: 1.5, fill: "var(--theme-background)"}),
      Plot.dot(filas, {y: "jugador", x: "coef", r: 6, fill: "var(--rm)", stroke: "var(--theme-background)", strokeWidth: 2}),
      Plot.tip(filas, Plot.pointerY({y: "jugador", x: "coef", title: (d) => `${d.jugador}\n${t("Ajustado", "Adjusted")}: ${signo(d.coef, 2)} [${signo(d.inf, 2)}, ${signo(d.sup, 2)}]\n${t("En bruto", "Raw")}: ${signo(d.bruto, 2)}\n${VARIABLE[d.variable]}`}))
    ]
  });
}
display(A ? html`<div class="grid grid-cols-2">
  <div class="card">
    <div class="etiqueta">${A.jugador} · ${ROL[A.jugador] ?? ""}</div>
    <p>${t("Temporadas", "Seasons")}: <b>${periodo(A)}</b><br><span class="nota">${t("solo las que fue titular al menos 5 veces", "only those in which he started at least 5 times")}</span></p>
    <table class="mini">
      <tr><td>${t("Titular", "Starting")} (${A.n_titular} ${t("partidos", "matches")})</td><td>${signo(A.media_titular)}</td></tr>
      <tr><td>${t("No titular", "Not starting")} (${A.n_no_titular} ${t("partidos", "matches")})</td><td>${signo(A.media_no_titular)}</td></tr>
      <tr><td>${t("Diferencia en bruto", "Raw difference")}</td><td><b>${signo(A.diferencia_bruta)}</b></td></tr>
    </table>
    <div class="nota">${VARIABLE[A.variable]}</div>
  </div>
  <div class="card">
    <div class="etiqueta">${t("Ajustado por rival, temporada y localía", "Adjusted for opponent, season and venue")}</div>
    <div class="cifra">${signo(A.efecto.coef, 2)}</div>
    <p>${t("Intervalo del 95 %", "95% interval")}: <b>${intervalo(A.efecto)}</b> · ${pTxt(A.efecto.p)}</p>
    ${veredicto(A.efecto)}
    <p class="nota">${esSig(A.efecto)
      ? t(`Cuando ${A.jugador} no es titular, la ${VARIABLE[A.variable]} cambia en ${signo(A.efecto.coef)}, incluso comparando contra el mismo rival y en la misma temporada.`, `When ${A.jugador} does not start, the ${VARIABLE[A.variable]} changes by ${signo(A.efecto.coef)}, even comparing against the same opponent and in the same season.`)
      : t(`Una vez se compara contra el mismo rival y en la misma temporada, no se puede distinguir de cero lo que cambia la ${VARIABLE[A.variable]} sin ${A.jugador} de titular.`, `Once the comparison is made against the same opponent and in the same season, the change in ${VARIABLE[A.variable]} without ${A.jugador} starting cannot be told apart from zero.`)}
    ${Math.sign(A.diferencia_bruta) !== Math.sign(A.efecto.coef) || Math.abs(A.diferencia_bruta - A.efecto.coef) > 0.15
      ? t(" El ajuste mueve bastante la cifra en bruto: parte de la diferencia simple venía de contra quién jugaba.", " The adjustment moves the raw figure noticeably: part of the simple difference came from who the opponent was.")
      : ""}</p>
  </div>
</div>
<div class="card">
  <div class="leyenda"><span class="rm">${t("Ajustado, con su intervalo del 95 %", "Adjusted, with its 95% interval")}</span><span class="sin">○ ${t("En bruto", "Raw")}</span></div>
  ${resize((width) => bosqueAusencias(width))}
  <div class="nota">${t("Para Courtois la variable son los goles evitados (xG en contra − goles en contra): depende tanto del portero como de la defensa y de la suerte, porque el xG no tiene en cuenta dónde va el tiro.", "For Courtois the variable is goals prevented (xG against − goals against): it depends on the goalkeeper as much as on the defence and luck, because xG ignores where the shot is placed.")}</div>
</div>` : html`<p>${t("Todavía no hay datos suficientes.", "Not enough data yet.")}</p>`);
```

## ${t("Cómo se estima", "How it is estimated")}

${t("Cada partido de Liga del Madrid desde 2019/20 es una observación. La variable que se explica es la diferencia de xG del partido (a favor − en contra):", "Each Madrid league match since 2019/20 is one observation. The outcome is the match's xG difference (for − against):")}

```tex
\Delta xG_{m} = \beta\, D_{m} + \gamma\, \text{local}_{m} + \alpha_{\text{rival}(m)} + \delta_{\text{temporada}(m)} + \varepsilon_{m}
```

```js
const G = eco.localia?.regresion?.clusters ?? "~30";
display(html`<ul>
  <li>${H(t("<b>Efectos fijos de rival y de temporada</b> (α y δ), metidos como variables ficticias. El panel está muy desequilibrado (ascensos, descensos, uno o dos partidos por rival y año), así que restar a cada partido la media de su rival y la de su temporada no daría el estimador de efectos fijos.", "<b>Opponent and season fixed effects</b> (α and δ), entered as dummy variables. The panel is very unbalanced (promotions, relegations, one or two matches per opponent and year), so subtracting each match's opponent and season means would not give the fixed-effects estimator."))}</li>
  <li>${H(t(`<b>Errores estándar agrupados por rival</b> (${G} grupos), con la corrección de muestra finita de Cameron y Miller (2015) y una t de Student con G − 1 grados de libertad. Agrupar por temporada dejaría solo 8 grupos, demasiado pocos para que el error sándwich sea fiable.`, `<b>Standard errors clustered by opponent</b> (${G} clusters), with the Cameron and Miller (2015) finite-sample correction and a Student t with G − 1 degrees of freedom. Clustering by season would leave only 8 clusters, too few for a reliable sandwich estimator.`))}</li>
  <li>${H(t("<b>Descanso</b>: días desde el partido oficial anterior en cualquier competición (calendario de ESPN), en cuatro tramos; la referencia es la semana normal (6–8 días).", "<b>Rest</b>: days since the previous official match in any competition (ESPN fixtures), in four bands; the reference is a normal week (6–8 days)."))}</li>
  <li>${H(t("<b>Ausencias</b>: «titular» = 60 minutos o más. Solo se usan las temporadas en que el jugador fue titular al menos 5 veces, para no confundir «no es titular» con «ya no está en el club».", "<b>Absences</b>: “starting” = 60 minutes or more. Only seasons in which the player started at least 5 times are used, so “not starting” is not confused with “no longer at the club”."))}</li>
  <li>${t("Todos los textos de esta página se generan a partir de los resultados del día: si un efecto deja de ser distinto de cero con los partidos nuevos, la página lo dirá sola.", "All the text on this page is generated from the day's results: if an effect stops being different from zero with new matches, the page will say so by itself.")}</li>
</ul>`);
```
