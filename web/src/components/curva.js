// Curva de puntos acumulados de todas las Ligas desde 1929 (Resumen e Histórico).
// Tarjeta autónoma: sus controles viven dentro, así que siguen a mano en pantalla completa.
import * as Plot from "npm:@observablehq/plot";
import * as d3 from "npm:d3";
import {html} from "npm:htl";
import {num, ordinal, t} from "./formato.js";

export function tarjetaCurva(curvasLiga, tempActual, invalidation) {
  const porTemp = d3.group(curvasLiga, (d) => d.temporada);
  const actualC = porTemp.get(tempActual) ?? [];
  const nHoy = actualC.length;
  const ptsHoy = actualC.at(-1)?.acumulado ?? 0;
  const esCampeona = (k) => porTemp.get(k)?.[0].campeon;
  const tempsCampeonas = [...porTemp.keys()].filter(esCampeona);
  // media de las Ligas ganadas en cada partido (solo donde llegan al menos la mitad de ellas)
  const mediaCampeonas = [{n: 0, acumulado: 0}, ...d3.range(1, 47).map((n) => {
    const v = tempsCampeonas.map((k) => porTemp.get(k)[n - 1]?.acumulado).filter((x) => x != null);
    return v.length >= tempsCampeonas.length / 2 ? {n, acumulado: d3.mean(v)} : null;
  }).filter(Boolean)];
  // lo que llevaba cada temporada al mismo número de partidos
  const aEstaAltura = [...porTemp].filter(([k, v]) => k !== tempActual && v.length >= nHoy && nHoy > 0)
    .map(([k, v]) => ({temporada: k, pts: v[nHoy - 1].acumulado}));
  const mejores = aEstaAltura.filter((d) => d.pts > ptsHoy).length;
  const empatadas = aEstaAltura.filter((d) => d.pts === ptsHoy).length;
  const mejor = d3.greatest(aEstaAltura, (d) => d.pts);
  const mediaCampHoy = d3.mean(aEstaAltura.filter((d) => esCampeona(d.temporada)), (d) => d.pts);
  const anteriores = [...porTemp.keys()].filter((k) => k !== tempActual).sort().reverse();

  // atajos para comparar
  const finales = anteriores.map((k) => ({k, pts: porTemp.get(k).at(-1).acumulado, pj: porTemp.get(k).length}));
  const record = d3.greatest(finales.filter((d) => d.pj >= 38), (d) => d.pts);
  const atajos = [
    {k: anteriores[0], txt: t("Temporada pasada", "Last season")},
    {k: anteriores.find(esCampeona), txt: t("Última Liga ganada", "Last title")},
    record && {k: record.k, txt: t(`Récord: ${record.pts} puntos`, `Record: ${record.pts} points`)},
    mejor && {k: mejor.temporada, txt: t("Mejor arranque", "Best start")}
  ].filter((a, i, arr) => a?.k && arr.findIndex((b) => b?.k === a.k) === i);

  let zoom = "todo";
  let comparar = null;

  function grafica(width) {
    const fullscreen = tarjeta.classList.contains("pantalla-completa");
    const alto = fullscreen ? Math.max(380, innerHeight - 260) : Math.max(340, Math.min(width * 0.48, 520));
    const xMax = zoom === "hoy" ? Math.max(nHoy + 6, 12) : d3.max(curvasLiga, (d) => d.n);
    const dentro = (d) => d.n <= xMax;
    const resto = curvasLiga.filter((d) => !d.campeon && d.temporada !== tempActual && d.temporada !== comparar && dentro(d));
    const campeonas = curvasLiga.filter((d) => d.campeon && d.temporada !== tempActual && d.temporada !== comparar && dentro(d));
    const conCero = (arr) => [{n: 0, acumulado: 0, temporada: arr[0]?.temporada}, ...arr];
    const actual = conCero(actualC);
    const otra = comparar ? conCero(porTemp.get(comparar).filter(dentro)) : [];
    const yMax = d3.max([...resto, ...campeonas, ...otra, ...actual], (d) => d.acumulado) * 1.04;
    const tip = (d) => `${d.temporada}${esCampeona(d.temporada) ? t(" · campeón", " · champions") : ""}\n${t("Partido", "Match")} ${d.n}: ${d.acumulado} ${t("puntos", "points")}` +
      (d.rival ? `\n${d.rival} ${d.gf}–${d.gc}` : "");
    return Plot.plot({
      width, height: alto, marginRight: 92,
      x: {label: t("partidos de Liga jugados", "league matches played"), domain: [0, xMax]},
      y: {label: t("puntos", "points"), domain: [0, yMax], grid: true},
      marks: [
        Plot.line(resto, {x: "n", y: "acumulado", z: "temporada", stroke: "var(--theme-foreground-faint)", strokeOpacity: 0.45, strokeWidth: 1}),
        Plot.line(campeonas, {x: "n", y: "acumulado", z: "temporada", stroke: "var(--oro)", strokeOpacity: 0.45, strokeWidth: 1.2}),
        Plot.line(mediaCampeonas.filter(dentro), {x: "n", y: "acumulado", stroke: "var(--oro-texto)", strokeWidth: 2.5, strokeDasharray: "6,4"}),
        comparar ? Plot.line(otra, {x: "n", y: "acumulado", stroke: "var(--rival)", strokeWidth: 2.8}) : null,
        comparar ? Plot.text(otra.slice(-1), {x: "n", y: "acumulado", text: (d) => `${comparar}: ${d.acumulado}`, dx: 8, textAnchor: "start",
          fill: "var(--rival)", fontWeight: 700, fontSize: 12, stroke: "var(--theme-background)", strokeWidth: 3, paintOrder: "stroke"}) : null,
        Plot.line(actual, {x: "n", y: "acumulado", stroke: "var(--rm)", strokeWidth: 3.5}),
        Plot.dot(actual.slice(-1), {x: "n", y: "acumulado", r: 6, fill: "var(--rm)", stroke: "var(--theme-background)", strokeWidth: 2}),
        Plot.text(actual.slice(-1), {x: "n", y: "acumulado", text: (d) => `${tempActual}: ${d.acumulado}`, dx: 10, textAnchor: "start",
          fill: "var(--rm)", fontWeight: 700, fontSize: 13, stroke: "var(--theme-background)", strokeWidth: 3, paintOrder: "stroke"}),
        Plot.tip([...resto, ...campeonas, ...otra.slice(1), ...actualC], Plot.pointer({x: "n", y: "acumulado", title: tip, maxRadius: 18}))
      ]
    });
  }

  // ---- controles
  const pastilla = (txt, activo, extra = "") => html`<button type="button" class="pastilla ${extra} ${activo ? "activa" : ""}">${txt}</button>`;
  const zoomBotones = [["todo", t("Temporada completa", "Whole season")], ["hoy", t("Hasta hoy", "Up to today")]].map(([v, txt]) => {
    const b = pastilla(txt, v === zoom);
    b.onclick = () => { zoom = v; marcar(); pintar(); };
    b.valor = v;
    return b;
  });
  const ningunaB = pastilla(t("Ninguna", "None"), true, "pastilla-comp");
  ningunaB.onclick = () => elegir(null);
  const atajoBotones = atajos.map((a) => {
    const b = pastilla(html`${a.txt} <small>${a.k}${esCampeona(a.k) ? " 🏆" : ""}</small>`, false, "pastilla-comp");
    b.onclick = () => elegir(a.k);
    b.valor = a.k;
    return b;
  });
  const lista = html`<select class="selector-pastilla">
    <option value="">${t("Otra temporada…", "Another season…")}</option>
    ${anteriores.map((k) => html`<option value=${k}>${k}${esCampeona(k) ? " 🏆" : ""} · ${porTemp.get(k).at(-1).acumulado} ${t("pts", "pts")}</option>`)}
  </select>`;
  lista.onchange = () => elegir(lista.value || null);

  function elegir(k) { comparar = k; marcar(); pintar(); }
  function marcar() {
    for (const b of zoomBotones) b.classList.toggle("activa", b.valor === zoom);
    ningunaB.classList.toggle("activa", !comparar);
    for (const b of atajoBotones) b.classList.toggle("activa", b.valor === comparar);
    const enAtajos = atajoBotones.some((b) => b.valor === comparar);
    lista.value = comparar && !enAtajos ? comparar : "";
    lista.classList.toggle("activa", Boolean(comparar && !enAtajos));
    leyendaOtra.hidden = !comparar;
    leyendaOtra.textContent = comparar ?? "";
  }

  const grafico = html`<div class="grafico-curva"></div>`;
  const leyendaOtra = html`<span class="rival" hidden></span>`;
  const resumen = nHoy && mejor ? html`${t("Tras", "After")} ${nHoy} ${t("partidos de Liga", "league matches")}, <b>${ptsHoy} ${t("puntos", "points")}</b>: ${t("el", "the")} ${ordinal(mejores + 1)} ${t("mejor arranque de", "best start out of")} ${aEstaAltura.length + 1} ${t("temporadas", "seasons")}${empatadas ? ` (${t("empatado con", "tied with")} ${empatadas} ${empatadas === 1 ? t("otra", "other") : t("otras", "others")})` : ""}. ${t("Las Ligas ganadas llevaban de media", "Title-winning seasons had on average")} ${num(mediaCampHoy, 1)} ${t("a estas alturas; el mejor arranque fue el de", "at this point; the best start was")} ${mejor.temporada}, ${t("con", "with")} ${mejor.pts}.` : "";

  const ampliar = html`<button type="button" class="boton-tema boton-grande">⤢ ${t("Ampliar", "Enlarge")}</button>`;
  const tarjeta = html`<div class="card tarjeta-curva">
    <div class="cab-curva"><h3>${t("Puntos acumulados, Liga a Liga desde 1929", "Cumulative points, every league season since 1929")}</h3>${ampliar}</div>
    <p class="nota" style="margin-top:0">${resumen}</p>
    <div class="controles-curva">
      <div class="grupo-pastillas"><span class="etiqueta">${t("Ver", "Show")}</span><div class="segmentado">${zoomBotones}</div></div>
      <div class="grupo-pastillas"><span class="etiqueta">${t("Comparar con", "Compare with")}</span>${ningunaB}${atajoBotones}${lista}</div>
    </div>
    <div class="leyenda"><span class="rm">${t("Esta temporada", "This season")}</span><span class="g-oro-discontinua">${t("Media de las Ligas ganadas", "Average of title-winning seasons")}</span><span class="g-liga">${t("Temporadas campeonas", "Title-winning seasons")}</span><span class="g-otros">${t("Resto", "Others")}</span>${leyendaOtra}<span class="sin">${t("3 puntos por victoria en todas", "3 points for a win in every season")}</span></div>
    ${grafico}
  </div>`;

  let ancho = 0;
  function pintar() {
    ancho = grafico.clientWidth || 800;
    grafico.replaceChildren(grafica(ancho));
  }
  // se vuelve a dibujar si cambia el ancho (ventana, pantalla completa), no si cambia el alto
  const obs = new ResizeObserver(() => { if (Math.abs(grafico.clientWidth - ancho) > 2) pintar(); });
  obs.observe(grafico);

  // pantalla completa: la tarjeta se saca a <body> para quedar por encima de la barra lateral y la cabecera
  const hueco = document.createComment("curva");
  function alternar() {
    const abierta = tarjeta.classList.toggle("pantalla-completa");
    if (abierta) { tarjeta.replaceWith(hueco); document.body.append(tarjeta); } else { hueco.replaceWith(tarjeta); }
    ampliar.textContent = abierta ? `✕ ${t("Cerrar", "Close")}` : `⤢ ${t("Ampliar", "Enlarge")}`;
    document.body.style.overflow = abierta ? "hidden" : "";
    pintar();
  }
  ampliar.onclick = alternar;
  const esc = (e) => { if (e.key === "Escape" && tarjeta.classList.contains("pantalla-completa")) alternar(); };
  addEventListener("keydown", esc);
  invalidation?.then(() => {
    obs.disconnect();
    removeEventListener("keydown", esc);
    if (tarjeta.classList.contains("pantalla-completa")) alternar();
  });
  requestAnimationFrame(pintar);
  return tarjeta;
}
