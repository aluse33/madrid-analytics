import * as Plot from "npm:@observablehq/plot";

// Campo de 105 x 68 m dibujado con Plot. El Madrid ataca hacia la derecha (x = 105)
// y el rival hacia la izquierda: sus tiros se reflejan (x -> 105 - x, y -> 68 - y).
const L = 105, A = 68;

function lineas() {
  const c = {stroke: "var(--campo-linea)", strokeWidth: 1.2};
  const area = (x0, w, h) => [[x0, (A - h) / 2], [x0 + w, (A - h) / 2], [x0 + w, (A + h) / 2], [x0, (A + h) / 2]];
  const circulo = (cx, cy, r, a0 = 0, a1 = 2 * Math.PI) =>
    Array.from({length: 61}, (_, i) => {
      const t = a0 + ((a1 - a0) * i) / 60;
      return [cx + r * Math.cos(t), cy + r * Math.sin(t)];
    });
  // arcos del área: la parte del círculo de 9,15 m fuera del área grande
  const arco = Math.acos((16.5 - 11) / 9.15);
  return [
    Plot.rect([{x1: 0, x2: L, y1: 0, y2: A}], {x1: "x1", x2: "x2", y1: "y1", y2: "y2", fill: "var(--campo-fondo)", ...c}),
    Plot.ruleX([L / 2], {...c}),
    Plot.line(circulo(L / 2, A / 2, 9.15), c),
    Plot.line([...area(0, 16.5, 40.3), [0, (A - 40.3) / 2]], c),
    Plot.line([...area(L - 16.5, 16.5, 40.3), [L - 16.5, (A - 40.3) / 2]].map(([x, y], i) => [x, y]), c),
    Plot.line([...area(0, 5.5, 18.32), [0, (A - 18.32) / 2]], c),
    Plot.line([...area(L - 5.5, 5.5, 18.32), [L - 5.5, (A - 18.32) / 2]], c),
    Plot.line(circulo(11, A / 2, 9.15, -arco, arco), c),
    Plot.line(circulo(L - 11, A / 2, 9.15, Math.PI - arco, Math.PI + arco), c),
    Plot.dot([[11, A / 2], [L - 11, A / 2], [L / 2, A / 2]], {r: 1.5, fill: "var(--campo-linea)"})
  ];
}

// tiros: filas de tiros_rm.csv de un partido
export function mapaTiros(tiros, {width = 720, campo = "Real Madrid"} = {}) {
  const datos = tiros.map((t) => {
    const propio = t.equipo === campo;
    return {...t, px: propio ? t.x : L - t.x, py: propio ? t.y : A - t.y, lado: propio ? "Real Madrid" : "Rival", gol: t.resultado === "gol"};
  });
  const height = Math.round((width * A) / L);
  return Plot.plot({
    width, height, margin: 0, inset: 0,
    x: {domain: [0, L], axis: null}, y: {domain: [0, A], axis: null},
    r: {domain: [0, 0.8], range: [3, 18]},
    marks: [
      ...lineas(),
      // los que no fueron gol: aro (2 px) del color del equipo
      Plot.dot(datos.filter((d) => !d.gol), {
        x: "px", y: "py", r: "xg_understat", fill: "var(--campo-fondo)", fillOpacity: 0.85,
        stroke: (d) => (d.lado === "Real Madrid" ? "var(--rm)" : "var(--rival)"), strokeWidth: 2
      }),
      // goles: relleno sólido con anillo del color de la superficie para separarlos
      Plot.dot(datos.filter((d) => d.gol), {
        x: "px", y: "py", r: "xg_understat",
        fill: (d) => (d.lado === "Real Madrid" ? "var(--rm)" : "var(--rival)"),
        stroke: "var(--campo-fondo)", strokeWidth: 2
      }),
      Plot.tip(datos, Plot.pointer({
        x: "px", y: "py",
        title: (d) => `${d.jugador} (${d.equipo})\nMinuto ${d.minuto}\nxG Understat ${(+d.xg_understat).toLocaleString("es-ES", {maximumFractionDigits: 2})}` +
          ` · xG propio ${(+d.xg_propio).toLocaleString("es-ES", {maximumFractionDigits: 2})}\n${d.situacion} · ${d.parte_cuerpo}\nResultado: ${d.resultado}`
      }))
    ]
  });
}
