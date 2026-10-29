"""Econometría aplicada al Madrid: localía, descanso entre partidos y ausencias de jugadores clave.

Todas las regresiones explican la diferencia de xG de un partido de Liga (o los goles evitados,
en el caso del portero) con:

- **efectos fijos de rival y de temporada**, metidos como variables ficticias. El panel rival ×
  temporada está muy desequilibrado (ascensos y descensos, uno o dos partidos por rival y año),
  así que restar medias de rival y de temporada NO da el estimador de efectos fijos;
- **errores estándar agrupados por rival** (unos 30 grupos). Agrupar por temporada dejaría 8
  grupos, demasiado pocos para que el error sándwich sea fiable.

Son asociaciones ajustadas, no efectos causales limpios: las ausencias no son aleatorias
(lesiones, rotaciones en partidos sin nada en juego) y el descanso depende del calendario, que
a su vez depende de cómo le va al equipo en las otras competiciones. Lo que sí controlan es la
calidad del rival y el nivel de cada temporada.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
import scipy.stats as st

log = logging.getLogger(__name__)

NIVEL = 0.05


# ------------------------------------------------------------------ estimación
def ols_cluster(
    y: np.ndarray, X: np.ndarray, clusters: np.ndarray, nombres: list[str] | None = None
) -> dict[str, Any]:
    """MCO con errores estándar sándwich agrupados (Liang-Zeger) y corrección de muestra finita."""
    y = np.asarray(y, dtype=float)
    X = np.asarray(X, dtype=float)
    if X.ndim == 1:
        X = X.reshape(-1, 1)
    N, K = X.shape

    # columnas sin variación (p. ej. una ficticia que no aparece en la muestra) fuera
    validas = np.var(X, axis=0) > 1e-12
    if not np.any(validas) or N <= K:
        return {"parametros": [], "n": int(N), "clusters": int(len(np.unique(clusters))), "r2": 0.0, "rmse": 0.0}
    X = X[:, validas]
    if nombres:
        nombres = [n for i, n in enumerate(nombres) if validas[i]]
    N, K = X.shape

    # pseudoinversa: tolera colinealidad exacta (p. ej. un rival que solo aparece una vez)
    pan = np.linalg.pinv(X.T @ X)
    beta = pan @ (X.T @ y)
    e = y - X @ beta
    K_ef = int(np.linalg.matrix_rank(X))

    grupos = np.unique(clusters)
    G = len(grupos)
    carne = np.zeros((K, K))
    for g in grupos:
        m = clusters == g
        s = X[m].T @ e[m]
        carne += np.outer(s, s)
    # corrección de Cameron y Miller (2015)
    c = (G / max(G - 1, 1)) * ((N - 1) / max(N - K_ef, 1))
    cov = c * (pan @ carne @ pan)
    se = np.sqrt(np.maximum(np.diag(cov), 1e-12))

    t = np.where(se > 1e-9, beta / se, 0.0)
    gl = max(G - 1, 1)
    p = 2 * st.t.sf(np.abs(t), df=gl)
    tc = st.t.ppf(1 - NIVEL / 2, df=gl)

    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - float(np.sum(e**2)) / ss_tot if ss_tot > 1e-12 else 0.0
    return {
        "parametros": [{
            "param": nombres[i] if nombres and i < len(nombres) else f"x{i}",
            "coef": round(float(beta[i]), 4), "se": round(float(se[i]), 4), "t": round(float(t[i]), 3),
            "p": round(float(p[i]), 4),
            "ci95": [round(float(beta[i] - tc * se[i]), 4), round(float(beta[i] + tc * se[i]), 4)],
        } for i in range(K)],
        "n": int(N), "clusters": int(G), "r2": round(float(r2), 4), "rmse": round(float(np.sqrt(np.mean(e**2))), 4),
    }


def regresion_fe(df: pd.DataFrame, y: str, regresores: list[str],
                 efectos: tuple[str, ...] = ("rival", "temporada"), cluster: str = "rival") -> dict[str, Any]:
    """y ~ regresores + efectos fijos (ficticias), con errores agrupados. Devuelve solo los regresores.

    Las ficticias del primer efecto entran completas (hacen de constante) y las del resto sin su
    primera categoría, para que la matriz tenga rango completo.
    """
    d = df.dropna(subset=[y, *regresores]).copy()
    bloques = [d[regresores].astype(float)]
    for i, ef in enumerate(efectos):
        bloques.append(pd.get_dummies(d[ef], prefix=f"fe_{ef}", drop_first=i > 0, dtype=float))
    X = pd.concat(bloques, axis=1)
    res = ols_cluster(d[y].to_numpy(), X.to_numpy(), d[cluster].to_numpy(), nombres=list(X.columns))
    res["parametros"] = [p for p in res["parametros"] if p["param"] in regresores]
    res["efectos"] = list(efectos)
    res["cluster"] = cluster
    return res


def bootstrap_ci(x: np.ndarray, n_boot: int = 2000, nivel: float = NIVEL) -> list[float]:
    """Intervalo bootstrap percentil para la media."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    if len(x) < 2:
        v = float(x[0]) if len(x) else 0.0
        return [round(v, 3), round(v, 3)]
    rng = np.random.default_rng(42)
    medias = rng.choice(x, size=(n_boot, len(x)), replace=True).mean(axis=1)
    return [round(float(np.quantile(medias, nivel / 2)), 3), round(float(np.quantile(medias, 1 - nivel / 2)), 3)]


def _base(rm_partidos: pd.DataFrame) -> pd.DataFrame:
    rm = rm_partidos[rm_partidos.jugado].copy()
    rm["dif_xg"] = rm.xgf - rm.xgc
    rm["local"] = (rm.condicion == "Local").astype(float)
    return rm


# ------------------------------------------------------------------ localía
def analizar_localia(rm_partidos: pd.DataFrame) -> dict[str, Any]:
    """Ventaja de jugar en el Bernabéu: misma comparación contra el mismo rival y en la misma temporada."""
    rm = _base(rm_partidos)
    if len(rm) < 20:
        return {}
    casa, fuera = rm[rm.local == 1], rm[rm.local == 0]
    return {
        "regresion": regresion_fe(rm, "dif_xg", ["local"]),
        "local_xgf": round(float(casa.xgf.mean()), 3), "local_xgc": round(float(casa.xgc.mean()), 3),
        "visit_xgf": round(float(fuera.xgf.mean()), 3), "visit_xgc": round(float(fuera.xgc.mean()), 3),
        "local_dif": round(float(casa.dif_xg.mean()), 3), "visit_dif": round(float(fuera.dif_xg.mean()), 3),
        "n_local": int(len(casa)), "n_visitante": int(len(fuera)),
    }


# ------------------------------------------------------------------ descanso
CATEGORIAS = [  # (clave, desde, hasta) en días; la de referencia es la semana normal
    ("corto", 0, 3.5), ("medio", 3.5, 5.5), ("normal", 5.5, 8.5), ("largo", 8.5, 30)]


def descansos(rm_partidos: pd.DataFrame, oficiales: pd.DataFrame | None) -> pd.DataFrame:
    """Días desde el partido oficial anterior (cualquier competición) para cada partido de Liga.

    El calendario completo sale de ESPN; los partidos de Liga de Understat se añaden por si
    faltara alguno. Si el partido anterior queda a más de 30 días (primer partido de la temporada),
    el descanso no cuenta.
    """
    rm = _base(rm_partidos)
    otros = oficiales if oficiales is not None and len(oficiales) else pd.DataFrame(columns=["fecha", "liga"])
    todas = pd.concat([otros[["fecha", "liga"]], pd.DataFrame({"fecha": rm.fecha, "liga": "esp.1"})], ignore_index=True)
    todas["fecha"] = pd.to_datetime(todas.fecha, utc=True).dt.tz_localize(None)
    todas = todas.sort_values("fecha")
    fechas = todas.fecha.to_numpy()
    ligas = todas.liga.to_numpy()
    previo, comp_previa = [], []
    for f in pd.to_datetime(rm.fecha, utc=True).dt.tz_localize(None):
        # el anterior es el último partido al menos 12 h antes (Understat y ESPN no siempre coinciden en la hora)
        i = np.searchsorted(fechas, np.datetime64(f - pd.Timedelta(hours=12)), side="right") - 1
        if i < 0:
            previo.append(np.nan)
            comp_previa.append(None)
            continue
        dias = (f - pd.Timestamp(fechas[i])).total_seconds() / 86400
        previo.append(dias if dias <= 30 else np.nan)
        comp_previa.append(ligas[i] if dias <= 30 else None)
    rm["descanso"] = previo
    rm["comp_previa"] = comp_previa
    rm["tras_champions"] = (rm.comp_previa == "uefa.champions").astype(float)
    for clave, a, b in CATEGORIAS:
        rm[clave] = ((rm.descanso > a) & (rm.descanso <= b)).astype(float)
    return rm


def analizar_descanso(rm_partidos: pd.DataFrame, oficiales: pd.DataFrame | None) -> dict[str, Any]:
    rm = descansos(rm_partidos, oficiales).dropna(subset=["descanso"])
    if len(rm) < 30:
        return {}
    temporadas_completas = sorted(set(pd.to_datetime(oficiales.fecha).dt.year)) if oficiales is not None and len(oficiales) else []
    categorias = []
    for clave, _a, _b in CATEGORIAS:
        sub = rm[rm[clave] == 1]
        if len(sub):
            categorias.append({"categoria": clave, "n": int(len(sub)), "dias_medio": round(float(sub.descanso.mean()), 1),
                               "xgf_medio": round(float(sub.xgf.mean()), 3), "xgc_medio": round(float(sub.xgc.mean()), 3),
                               "dif_xg_medio": round(float(sub.dif_xg.mean()), 3), "ci95_dif": bootstrap_ci(sub.dif_xg.to_numpy())})
    return {
        "n_total": int(len(rm)),
        "calendario_completo": bool(temporadas_completas),
        "categorias": categorias,
        # categoría de referencia: semana normal (6-8 días)
        "regresion": regresion_fe(rm, "dif_xg", ["corto", "medio", "largo", "local"]),
        # "resaca europea": el partido anterior fue de Champions
        "champions": regresion_fe(rm, "dif_xg", ["tras_champions", "local"]),
        "n_tras_champions": int(rm.tras_champions.sum()),
    }


# ------------------------------------------------------------------ ausencias
JUGADORES = [
    # (jugador, variable que se explica, minutos para contar como titular)
    ("Karim Benzema", "dif_xg", 60),
    ("Vinícius Júnior", "dif_xg", 60),
    ("Thibaut Courtois", "goles_evitados", 60),
]


def analizar_ausencias(rm_partidos: pd.DataFrame, jp_rm: pd.DataFrame) -> list[dict[str, Any]]:
    """Diferencia entre los partidos en que el jugador es titular y en los que no, ajustada por rival y temporada.

    Solo se usan las temporadas en las que el jugador fue titular al menos 5 veces (si no, "no es
    titular" significaría "ya no está en el club").
    """
    rm = _base(rm_partidos)
    rm["goles_evitados"] = rm.xgc - rm.gc
    out = []
    for jugador, y, minimo in JUGADORES:
        mins = jp_rm[jp_rm.jugador == jugador].set_index("game_id").minutos
        if mins.empty:
            continue
        d = rm.copy()
        d["titular"] = (d.game_id.map(mins).fillna(0) >= minimo).astype(float)
        temporadas = [t for t, v in d.groupby("temporada").titular.sum().items() if v >= 5]
        d = d[d.temporada.isin(temporadas)]
        d["no_titular"] = 1.0 - d.titular
        con, sin = d[d.titular == 1], d[d.titular == 0]
        if len(con) < 10 or len(sin) < 10:
            continue
        res = regresion_fe(d, y, ["no_titular", "local"])
        efecto = next((p for p in res["parametros"] if p["param"] == "no_titular"), None)
        if not efecto:
            continue
        out.append({
            "jugador": jugador, "variable": y, "temporadas": temporadas,
            "n_titular": int(len(con)), "n_no_titular": int(len(sin)),
            "media_titular": round(float(con[y].mean()), 3), "media_no_titular": round(float(sin[y].mean()), 3),
            "diferencia_bruta": round(float(sin[y].mean() - con[y].mean()), 3),
            "efecto": efecto, "n": res["n"], "clusters": res["clusters"],
        })
    return out


def analisis_completo(liga_partidos: pd.DataFrame, rm_partidos: pd.DataFrame, jugadores_partido: pd.DataFrame,
                      oficiales: pd.DataFrame | None = None) -> dict[str, Any]:
    """Todo lo que pinta la página Econometría."""
    jp_rm = jugadores_partido[jugadores_partido.equipo == "Real Madrid"]
    return {
        "metodo": {"efectos": ["rival", "temporada"], "cluster": "rival", "nivel": NIVEL},
        "localia": analizar_localia(rm_partidos),
        "descanso": analizar_descanso(rm_partidos, oficiales),
        "ausencias": analizar_ausencias(rm_partidos, jp_rm),
    }
