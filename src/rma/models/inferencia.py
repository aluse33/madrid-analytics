"""Inferencia sencilla pero honesta: Poisson-binomial para goles vs xG y bootstrap.

¿Un jugador 'está enchufado' o ha tenido suerte? Si cada tiro i es gol con probabilidad
xG_i, de forma independiente, los goles siguen una Poisson-binomial. Con ella se calcula
cuán raro es marcar g goles con esos tiros, en vez de mirar solo 'goles − xG'.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np


def poisson_binomial_pmf(p) -> np.ndarray:
    """Distribución exacta del número de éxitos de Bernoullis independientes (O(n²))."""
    pmf = np.zeros(len(p) + 1)
    pmf[0] = 1.0
    for k, pi in enumerate(np.asarray(p, float), start=1):
        pmf[1:k + 1] = pmf[1:k + 1] * (1 - pi) + pmf[:k] * pi
        pmf[0] *= 1 - pi
    return pmf


def goles_vs_xg(xg_tiros, goles: int) -> dict[str, float]:
    """P(G ≥ goles) y P(G ≤ goles) bajo la Poisson-binomial de sus tiros, y el percentil medio."""
    pmf = poisson_binomial_pmf(xg_tiros)
    g = int(goles)
    p_mayor_igual = float(pmf[g:].sum()) if g < len(pmf) else 0.0
    p_menor_igual = float(pmf[:g + 1].sum()) if g < len(pmf) else 1.0
    return {
        "goles": g,
        "xg": float(np.sum(xg_tiros)),
        "p_al_menos": p_mayor_igual,     # pequeño: marcó más de lo que 'tocaba'
        "p_como_mucho": p_menor_igual,   # pequeño: marcó menos de lo que 'tocaba'
        "percentil": float(pmf[:g].sum() + 0.5 * (pmf[g] if g < len(pmf) else 0)),
    }


def bootstrap_ci(
    x, estadistico: Callable = np.mean, B: int = 5000, nivel: float = 0.9, semilla: int = 1
) -> tuple[float, float, float]:
    """Estimación puntual e intervalo bootstrap de percentiles."""
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    rng = np.random.default_rng(semilla)
    idx = rng.integers(0, len(x), size=(B, len(x)))
    stats = np.apply_along_axis(estadistico, 1, x[idx])
    cola = (1 - nivel) / 2
    return float(estadistico(x)), float(np.quantile(stats, cola)), float(np.quantile(stats, 1 - cola))


def bootstrap_diferencia(
    a, b, estadistico: Callable = np.mean, B: int = 5000, nivel: float = 0.9, semilla: int = 1
) -> dict[str, float]:
    """Diferencia estadistico(a) − estadistico(b) con remuestreo independiente de cada grupo."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    rng = np.random.default_rng(semilla)
    da = np.array([estadistico(rng.choice(a, len(a))) for _ in range(B)])
    db = np.array([estadistico(rng.choice(b, len(b))) for _ in range(B)])
    d = da - db
    cola = (1 - nivel) / 2
    return {
        "diferencia": float(estadistico(a) - estadistico(b)),
        "inf": float(np.quantile(d, cola)),
        "sup": float(np.quantile(d, 1 - cola)),
        "p_mayor_que_cero": float((d > 0).mean()),
    }
