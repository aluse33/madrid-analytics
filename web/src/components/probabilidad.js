// Probabilidades a partir de los tiros de un partido.
// Cada tiro es gol con probabilidad igual a su xG, de forma independiente: los goles de
// cada equipo siguen una Poisson-binomial. Convolucionando las dos se obtiene la
// probabilidad de victoria, empate y derrota "que merecían" las ocasiones.

export function poissonBinomial(ps) {
  let pmf = [1];
  for (const p of ps) {
    const next = new Array(pmf.length + 1).fill(0);
    for (let k = 0; k < pmf.length; k++) {
      next[k] += pmf[k] * (1 - p);
      next[k + 1] += pmf[k] * p;
    }
    pmf = next;
  }
  return pmf;
}

export function resultadoMerecido(xgPropios, xgRival) {
  const a = poissonBinomial(xgPropios);
  const b = poissonBinomial(xgRival);
  let v = 0, e = 0, d = 0;
  for (let i = 0; i < a.length; i++)
    for (let j = 0; j < b.length; j++) {
      const p = a[i] * b[j];
      if (i > j) v += p; else if (i === j) e += p; else d += p;
    }
  return {victoria: v, empate: e, derrota: d, puntosEsperados: 3 * v + e};
}

// P(goles >= g) con esos tiros: cuán "raro" fue marcar tanto
export function probAlMenos(xgs, goles) {
  const pmf = poissonBinomial(xgs);
  return pmf.slice(goles).reduce((s, x) => s + x, 0);
}
