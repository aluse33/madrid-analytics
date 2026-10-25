r"""Modelo de Dixon y Coles (1997) con ponderación temporal, penalización L2 y objetivo en xG.

Goles (o xG) del local y del visitante:

    log λ = μ + h + a_local + d_visitante
    log ν = μ     + a_visit + d_local

`a` es la capacidad ofensiva y `d` la fragilidad defensiva (d alto = concede más).
La corrección τ(x, y; λ, ν, ρ) de Dixon-Coles reajusta la masa de 0-0, 1-0, 0-1 y 1-1.

Estimación en dos pasos:
1. (μ, h, a, d) por cuasi-verosimilitud de Poisson ponderada con penalización L2:
       max Σ_k w_k [y_k log λ_k − λ_k]  −  (l2/2)(‖a‖² + ‖d‖²)
   El objetivo y puede ser goles, xG o una mezcla. La cuasi-verosimilitud de Poisson
   es consistente para la media con y continuo, así que usar xG es legítimo y reduce
   mucho el ruido (los goles son una realización muy ruidosa de la calidad de las ocasiones).
   La penalización identifica el modelo (fija la constante que se puede pasar de `a` a `d`)
   y hace shrinkage hacia la media de la liga, útil para recién ascendidos.
2. ρ por máxima verosimilitud sobre los goles reales, dados λ̂ y ν̂ (τ solo tiene
   sentido con conteos).

Ponderación temporal: w = 0.5 ** (antigüedad_en_días / semivida).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import pairwise

import numpy as np
import pandas as pd
from scipy.optimize import minimize, minimize_scalar
from scipy.stats import poisson


@dataclass
class DixonColes:
    equipos: list[str]
    mu: float
    campo: float
    ataque: np.ndarray
    defensa: np.ndarray
    rho: float
    fecha_ref: pd.Timestamp
    info: dict = field(default_factory=dict)
    # covarianza de (mu, campo, ataque..., defensa...) por el estimador sándwich
    cov: np.ndarray | None = None

    def muestrear(self, k: int, rng: np.random.Generator) -> np.ndarray:
        """k vectores de parámetros de su distribución aproximada N(θ̂, Σ) (Laplace/sándwich)."""
        theta = np.r_[self.mu, self.campo, self.ataque, self.defensa]
        if self.cov is None:
            return np.tile(theta, (k, 1))
        return rng.multivariate_normal(theta, self.cov, size=k, method="eigh")

    def _idx(self, equipo: str) -> int:
        try:
            return self.equipos.index(equipo)
        except ValueError:
            return -1  # equipo nuevo: se queda en la media de la liga (a = d = 0)

    def tasas(self, local: str, visitante: str) -> tuple[float, float]:
        i, j = self._idx(local), self._idx(visitante)
        a = lambda k: self.ataque[k] if k >= 0 else 0.0
        d = lambda k: self.defensa[k] if k >= 0 else 0.0
        lam = np.exp(self.mu + self.campo + a(i) + d(j))
        nu = np.exp(self.mu + a(j) + d(i))
        return float(lam), float(nu)

    def matriz(self, local: str, visitante: str, max_goles: int = 10) -> np.ndarray:
        """P(goles_local = i, goles_visitante = j), i, j = 0..max_goles."""
        lam, nu = self.tasas(local, visitante)
        g = np.arange(max_goles + 1)
        m = np.outer(poisson.pmf(g, lam), poisson.pmf(g, nu))
        m[0, 0] *= 1 - lam * nu * self.rho
        m[0, 1] *= 1 + lam * self.rho
        m[1, 0] *= 1 + nu * self.rho
        m[1, 1] *= 1 - self.rho
        return m / m.sum()

    def prob_1x2(self, local: str, visitante: str) -> dict[str, float]:
        m = self.matriz(local, visitante)
        return {
            "local": float(np.tril(m, -1).sum()),
            "empate": float(np.trace(m)),
            "visitante": float(np.triu(m, 1).sum()),
        }

    def ratings(self) -> pd.DataFrame:
        """Ataque y defensa en escala multiplicativa respecto a la media de la liga."""
        return pd.DataFrame({
            "equipo": self.equipos,
            "ataque": np.exp(self.ataque),       # >1: genera más que la media
            "defensa": np.exp(self.defensa),     # <1: concede menos que la media
            "goles_esperados_vs_medio": np.exp(self.mu + self.ataque),
            "goles_concedidos_vs_medio": np.exp(self.mu + self.defensa),
        }).sort_values("ataque", ascending=False, ignore_index=True)


def _tau(x, y, lam, nu, rho):
    t = np.ones_like(lam)
    t = np.where((x == 0) & (y == 0), 1 - lam * nu * rho, t)
    t = np.where((x == 0) & (y == 1), 1 + lam * rho, t)
    t = np.where((x == 1) & (y == 0), 1 + nu * rho, t)
    t = np.where((x == 1) & (y == 1), 1 - rho, t)
    return t


def objetivo(df: pd.DataFrame, tipo: str = "mix", peso_xg: float = 0.6) -> tuple[np.ndarray, np.ndarray]:
    if tipo == "goals":
        return df.goles_local.to_numpy(float), df.goles_visitante.to_numpy(float)
    if tipo == "xg":
        return df.xg_local.to_numpy(float), df.xg_visitante.to_numpy(float)
    if tipo == "mix":
        yl = peso_xg * df.xg_local + (1 - peso_xg) * df.goles_local
        yv = peso_xg * df.xg_visitante + (1 - peso_xg) * df.goles_visitante
        return yl.to_numpy(float), yv.to_numpy(float)
    raise ValueError(f"objetivo desconocido: {tipo}")


def ajustar(
    partidos: pd.DataFrame,
    fecha_ref: pd.Timestamp | None = None,
    semivida_dias: float = 180,
    l2: float = 1.0,
    tipo: str = "mix",
    peso_xg: float = 0.6,
    anios: float | None = 3,
) -> DixonColes:
    """Ajusta con los partidos jugados ANTES de `fecha_ref` (sin mirar el futuro)."""
    df = partidos[partidos.jugado].copy()
    fecha_ref = pd.Timestamp(fecha_ref) if fecha_ref is not None else df.fecha.max() + pd.Timedelta(days=1)
    df = df[df.fecha < fecha_ref]
    if anios:
        df = df[df.fecha >= fecha_ref - pd.Timedelta(days=365 * anios)]
    df = df.dropna(subset=["goles_local", "goles_visitante", "xg_local", "xg_visitante"])
    if len(df) < 30:
        raise ValueError("Muy pocos partidos para ajustar el modelo")

    equipos = sorted(set(df.local) | set(df.visitante))
    n = len(equipos)
    pos = {e: k for k, e in enumerate(equipos)}
    hi = df.local.map(pos).to_numpy()
    ai = df.visitante.map(pos).to_numpy()
    edad = (fecha_ref - df.fecha).dt.total_seconds().to_numpy() / 86400
    w = 0.5 ** (edad / semivida_dias)
    yl, yv = objetivo(df, tipo, peso_xg)

    def f(theta):
        mu, h = theta[0], theta[1]
        a, d = theta[2:2 + n], theta[2 + n:]
        eta_l = mu + h + a[hi] + d[ai]
        eta_v = mu + a[ai] + d[hi]
        lam, nu = np.exp(eta_l), np.exp(eta_v)
        ll = np.sum(w * (yl * eta_l - lam + yv * eta_v - nu))
        pen = 0.5 * l2 * (a @ a + d @ d)
        rl, rv = w * (yl - lam), w * (yv - nu)  # derivadas respecto a eta
        g = np.empty_like(theta)
        g[0] = rl.sum() + rv.sum()
        g[1] = rl.sum()
        g[2:2 + n] = np.bincount(hi, rl, n) + np.bincount(ai, rv, n) - l2 * a
        g[2 + n:] = np.bincount(ai, rl, n) + np.bincount(hi, rv, n) - l2 * d
        return -(ll - pen), -g

    x0 = np.zeros(2 + 2 * n)
    x0[0] = np.log(max(np.mean(np.r_[yl, yv]), 0.1))
    res = minimize(f, x0, jac=True, method="L-BFGS-B")
    mu, h = res.x[0], res.x[1]
    a, d = res.x[2:2 + n], res.x[2 + n:]

    # Paso 2: rho con los goles reales
    lam = np.exp(mu + h + a[hi] + d[ai])
    nu = np.exp(mu + a[ai] + d[hi])
    gl, gv = df.goles_local.to_numpy(int), df.goles_visitante.to_numpy(int)
    cota = float(min(1.0, 1 / np.max(lam * nu))) * 0.99

    def nll_rho(r):
        t = _tau(gl, gv, lam, nu, r)
        return -np.sum(w * np.log(np.clip(t, 1e-12, None)))

    rho = minimize_scalar(nll_rho, bounds=(-0.3, min(0.3, cota)), method="bounded").x

    cov = _covarianza_sandwich(hi, ai, n, w, yl, yv, lam, nu, l2)

    return DixonColes(
        equipos=equipos, mu=float(mu), campo=float(h), ataque=a, defensa=d, rho=float(rho),
        fecha_ref=fecha_ref,
        info={"partidos": len(df), "convergio": bool(res.success), "tipo": tipo,
              "semivida_dias": semivida_dias, "l2": l2},
        cov=cov,
    )


def _covarianza_sandwich(hi, ai, n, w, yl, yv, lam, nu, l2) -> np.ndarray:
    """Σ = H⁻¹ B H⁻¹ para el estimador de cuasi-verosimilitud ponderada y penalizada.

    H = Σ w λ x xᵀ + l2·I (pendiente de la ecuación de estimación),
    B = Σ (w (y − λ))² x xᵀ (varianza empírica de los scores, agrupando los dos
    marcadores de cada partido). No supone que y sea Poisson, así que vale para xG
    (infradisperso) y para la mezcla con goles.
    """
    p = 2 + 2 * n
    m = len(hi)
    filas = np.arange(m)
    xl = np.zeros((m, p))
    xl[:, 0] = 1
    xl[:, 1] = 1
    xl[filas, 2 + hi] = 1
    xl[filas, 2 + n + ai] = 1
    xv = np.zeros((m, p))
    xv[:, 0] = 1
    xv[filas, 2 + ai] = 1
    xv[filas, 2 + n + hi] = 1
    H = (xl * (w * lam)[:, None]).T @ xl + (xv * (w * nu)[:, None]).T @ xv
    H[2:, 2:] += l2 * np.eye(2 * n)
    s = xl * (w * (yl - lam))[:, None] + xv * (w * (yv - nu))[:, None]  # score de cada partido
    B = s.T @ s
    Hi = np.linalg.inv(H)
    cov = Hi @ B @ Hi
    return (cov + cov.T) / 2


# ---------------------------------------------------------------- evaluación

def rps(p: np.ndarray, resultado: np.ndarray) -> np.ndarray:
    """Ranked Probability Score para (local, empate, visitante). Menor es mejor.

    `p` tiene forma (n, 3); `resultado` es 0 = local, 1 = empate, 2 = visitante.
    """
    o = np.zeros_like(p)
    o[np.arange(len(p)), resultado] = 1
    cp, co = np.cumsum(p, 1)[:, :2], np.cumsum(o, 1)[:, :2]
    return 0.5 * np.sum((cp - co) ** 2, axis=1)


def backtest(
    partidos: pd.DataFrame,
    desde: pd.Timestamp,
    cada_dias: int = 7,
    **kw,
) -> pd.DataFrame:
    """Predicción fuera de muestra con origen móvil: se reajusta cada `cada_dias` y se
    predice la semana siguiente con lo sabido hasta entonces. Incluye como referencia
    las frecuencias históricas de 1X2 (el 'modelo' que no sabe nada de los equipos)."""
    jug = partidos[partidos.jugado].dropna(subset=["goles_local", "goles_visitante"])
    fechas = pd.date_range(pd.Timestamp(desde).normalize(), jug.fecha.max() + pd.Timedelta(days=1),
                           freq=f"{cada_dias}D")
    filas = []
    for ini, fin in pairwise(fechas):
        bloque = jug[(jug.fecha >= ini) & (jug.fecha < fin)]
        if bloque.empty:
            continue
        m = ajustar(partidos, fecha_ref=ini, **kw)
        pasado = jug[(jug.fecha < ini) & (jug.fecha >= ini - pd.Timedelta(days=365 * 3))]
        base = np.array([
            (pasado.goles_local > pasado.goles_visitante).mean(),
            (pasado.goles_local == pasado.goles_visitante).mean(),
            (pasado.goles_local < pasado.goles_visitante).mean(),
        ])
        for r in bloque.itertuples():
            p = m.prob_1x2(r.local, r.visitante)
            res = 0 if r.goles_local > r.goles_visitante else 1 if r.goles_local == r.goles_visitante else 2
            filas.append({
                "game_id": r.game_id, "fecha": r.fecha, "temporada": r.temporada,
                "local": r.local, "visitante": r.visitante,
                "p_local": p["local"], "p_empate": p["empate"], "p_visitante": p["visitante"],
                "b_local": base[0], "b_empate": base[1], "b_visitante": base[2],
                "resultado": res,
            })
    bt = pd.DataFrame(filas)
    if len(bt):
        P = bt[["p_local", "p_empate", "p_visitante"]].to_numpy()
        B = bt[["b_local", "b_empate", "b_visitante"]].to_numpy()
        y = bt.resultado.to_numpy()
        bt["rps_modelo"] = rps(P, y)
        bt["rps_base"] = rps(B, y)
        bt["logloss_modelo"] = -np.log(np.clip(P[np.arange(len(P)), y], 1e-12, None))
        bt["logloss_base"] = -np.log(np.clip(B[np.arange(len(B)), y], 1e-12, None))
    return bt
