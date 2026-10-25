r"""Shrinkage empírico-bayesiano Gamma-Poisson (con sobredispersión) para tasas por 90'.

Con pocas jornadas, el xG/90 de un jugador con 200 minutos es casi todo ruido. El
modelo jerárquico

    θ_i ~ Gamma(α, β)                         (tasa por 90' del jugador; prior del puesto)
    E[X_i | θ_i] = θ_i e_i,  Var[X_i | θ_i] = φ θ_i e_i      (e_i = minutos / 90)

se trata reescalando por la dispersión φ: X_i/φ ~ Poisson(θ_i e_i/φ). La posterior es
conjugada, θ_i | X_i ~ Gamma(α + X_i/φ, β + e_i/φ), con media

    E[θ_i | X_i] = B_i · (α/β) + (1 − B_i) · X_i/e_i,     B_i = β / (β + e_i/φ)

una media ponderada entre la tasa observada y la del puesto.

¿Por qué φ? El xG es una suma de probabilidades pequeñas: su varianza es Σ xG_k² ≪ Σ xG_k,
muy por debajo de una Poisson (en LaLiga, φ ≈ 0,3 para el xG de un delantero). Sin
corregirlo, el modelo cree que todo es ruido y encoge muchísimo de más.

- φ: dispersión de Pearson DENTRO de cada jugador, con los datos partido a partido.
- (α, β): máxima verosimilitud marginal (binomial negativa sobre X/φ) con todos los
  jugadores de la liga del mismo puesto: el 'empírico' de empírico-bayesiano.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import gammaln
from scipy.stats import gamma


def dispersion(partidos_jugador: pd.DataFrame, metrica: str, id_col: str = "jugador_id",
               minutos: str = "minutos") -> float:
    """φ de Pearson: Σ (x_ij − θ̂_i e_ij)² / (θ̂_i e_ij) / (N − n_jugadores)."""
    d = partidos_jugador[partidos_jugador[minutos] > 0]
    e = d[minutos] / 90
    tot = d.groupby(id_col).agg(x=(metrica, "sum"), m=(minutos, "sum"))
    theta = (tot.x / (tot.m / 90)).rename("theta")
    mu = d[id_col].map(theta) * e
    ok = mu > 1e-9
    gl = ok.sum() - theta.size
    if gl <= 0:
        return 1.0
    return float((((d[metrica] - mu)[ok]) ** 2 / mu[ok]).sum() / gl)


def ajustar_prior(x: np.ndarray, e: np.ndarray) -> tuple[float, float]:
    """(α, β) por máxima verosimilitud de la binomial negativa marginal."""
    x, e = np.asarray(x, float), np.asarray(e, float)
    ok = e > 0
    x, e = x[ok], e[ok]

    def nll(p):
        a, b = np.exp(p)
        ll = gammaln(x + a) - gammaln(a) + a * np.log(b / (b + e)) + x * np.log(e / (b + e))
        return -ll.sum()

    media = x.sum() / e.sum()
    p0 = np.log([2.0, 2.0 / max(media, 1e-3)])
    res = minimize(nll, p0, method="Nelder-Mead",
                   options={"xatol": 1e-7, "fatol": 1e-9, "maxiter": 5000})
    a, b = np.exp(res.x)
    return float(a), float(b)


def posterior(x, e, a: float, b: float, phi: float = 1.0, nivel: float = 0.9) -> pd.DataFrame:
    x, e = np.asarray(x, float), np.asarray(e, float)
    a_post, b_post = a + x / phi, b + e / phi
    cola = (1 - nivel) / 2
    return pd.DataFrame({
        "bruto_p90": np.where(e > 0, x / np.where(e > 0, e, 1), np.nan),
        "eb_p90": a_post / b_post,
        "eb_inf": gamma.ppf(cola, a_post, scale=1 / b_post),
        "eb_sup": gamma.ppf(1 - cola, a_post, scale=1 / b_post),
        "peso_prior": b / b_post,  # B_i: cuánto pesa la media del puesto en la estimación
    })


def shrink(
    partidos_jugador: pd.DataFrame,
    metrica: str,
    grupo: str = "puesto",
    claves: tuple[str, ...] = ("jugador_id", "jugador", "equipo"),
    nivel: float = 0.9,
) -> pd.DataFrame:
    """Recibe filas jugador-partido; devuelve una fila por jugador con tasa bruta y EB.

    El prior y φ se estiman por grupo (puesto) con todos los jugadores de la liga.
    """
    out = []
    for g, d in partidos_jugador.groupby(grupo):
        tot = d.groupby(list(claves), as_index=False).agg(minutos=("minutos", "sum"),
                                                          partidos=("game_id", "nunique"),
                                                          x=(metrica, "sum"))
        tot = tot[tot.minutos > 0]
        if len(tot) < 10:
            continue
        phi = max(dispersion(d, metrica), 1e-3)
        e = tot.minutos.to_numpy(float) / 90
        a, b = ajustar_prior(tot.x.to_numpy(float) / phi, e / phi)
        post = posterior(tot.x, e, a, b, phi, nivel)
        post.index = tot.index
        tot = pd.concat([tot, post], axis=1).rename(columns={"x": f"{metrica}_total"})
        tot[grupo] = g
        tot["prior_media_p90"] = a / b
        tot["dispersion"] = phi
        out.append(tot)
    r = pd.concat(out, ignore_index=True)
    r["metrica"] = metrica
    return r
