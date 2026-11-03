"""Registro de aciertos: cada predicción del Madrid se guarda antes del partido y se evalúa después.

Dos fuentes de evidencia, que la web separa:
- **En tiempo real**: `registro_predicciones.csv`, que vive en el repositorio. Cada actualización
  reescribe la predicción de los partidos pendientes y la congela cuando empieza el partido.
  No hay forma de "retocarla" después: el historial de Git lo demuestra.
- **Reconstruido**: el backtest con origen móvil (lo que habría dicho el modelo con lo que se sabía
  cada semana). Mucha más muestra, pero hecho a posteriori.

Métricas (todas "cuanto menor, mejor", salvo el acierto): RPS (Epstein, 1969; respeta el orden
victoria-empate-derrota), Brier multiclase y log-loss. La comparación con el mercado o con el modelo
ingenuo es un contraste de Diebold-Mariano: media de las diferencias de pérdida partido a partido.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

COLS_PRED = ["game_id", "fecha", "rival", "condicion", "p_victoria", "p_empate", "p_derrota",
             "goles_esperados_rm", "goles_esperados_rival", "guardada"]
MARGEN_CIERRE = pd.Timedelta(minutes=30)   # la última predicción válida, media hora antes del partido


# ---------------------------------------------------------------- métricas
def rps(p: np.ndarray, y: np.ndarray) -> np.ndarray:
    """p: (n, 3) en orden victoria, empate, derrota (o local, empate, visitante); y: índice 0-2."""
    p = np.asarray(p, float)
    o = np.eye(3)[np.asarray(y, int)]
    return 0.5 * ((np.cumsum(p, 1)[:, :2] - np.cumsum(o, 1)[:, :2]) ** 2).sum(1)


def brier(p: np.ndarray, y: np.ndarray) -> np.ndarray:
    return ((np.asarray(p, float) - np.eye(3)[np.asarray(y, int)]) ** 2).sum(1)


def logloss(p: np.ndarray, y: np.ndarray) -> np.ndarray:
    p = np.asarray(p, float)
    return -np.log(np.clip(p[np.arange(len(p)), np.asarray(y, int)], 1e-12, None))


def diebold_mariano(perdida_a: np.ndarray, perdida_b: np.ndarray) -> dict:
    """Diferencia media de pérdidas (a − b) con su IC del 95 % y p-valor bilateral.
    Los partidos son de fechas distintas y las predicciones se hacen a un paso: sin autocorrelación
    relevante, así que basta el error típico de una media (t con n − 1 g.l.)."""
    d = np.asarray(perdida_a, float) - np.asarray(perdida_b, float)
    d = d[np.isfinite(d)]
    n = len(d)
    if n < 3:
        return {"n": n, "dif": float(d.mean()) if n else None, "inf": None, "sup": None, "p": None}
    se = d.std(ddof=1) / np.sqrt(n)
    tc = stats.t.ppf(0.975, n - 1)
    t = d.mean() / se if se > 0 else 0.0
    return {"n": n, "dif": float(d.mean()), "inf": float(d.mean() - tc * se), "sup": float(d.mean() + tc * se),
            "p": float(2 * stats.t.sf(abs(t), n - 1))}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (float(c - h), float(c + h))


def calibracion(P: np.ndarray, y: np.ndarray, n_tramos: int = 10) -> list[dict]:
    """Las tres probabilidades de cada partido juntas: ¿cuando se dice 60 %, pasa el 60 % de las veces?"""
    cortes = np.linspace(0, 1, n_tramos + 1)
    p = np.asarray(P, float).ravel()
    o = np.eye(3)[np.asarray(y, int)].ravel()
    tramo = np.clip(np.digitize(p, cortes[1:-1]), 0, len(cortes) - 2)
    filas = []
    for k in range(len(cortes) - 1):
        m = tramo == k
        if m.sum() == 0:
            continue
        inf, sup = wilson(int(o[m].sum()), int(m.sum()))
        filas.append({"desde": float(cortes[k]), "hasta": float(cortes[k + 1]), "predicho": float(p[m].mean()),
                      "observado": float(o[m].mean()), "inf": inf, "sup": sup, "n": int(m.sum())})
    return filas


# ---------------------------------------------------------------- registro en tiempo real
def actualizar(registro: pd.DataFrame | None, predicciones: list[dict], ahora: pd.Timestamp) -> pd.DataFrame:
    """Inserta o reescribe las predicciones de partidos que aún no han empezado; las demás no se tocan."""
    reg = registro.copy() if registro is not None and len(registro) else pd.DataFrame(columns=COLS_PRED)
    reg["fecha"] = pd.to_datetime(reg["fecha"], utc=True)
    ahora = pd.Timestamp(ahora)
    ahora = ahora.tz_localize("UTC") if ahora.tzinfo is None else ahora
    for p in predicciones:
        fecha = pd.Timestamp(p["fecha"])
        fecha = fecha.tz_localize("UTC") if fecha.tzinfo is None else fecha
        if ahora >= fecha - MARGEN_CIERRE:
            continue   # ya empezado (o a punto): la predicción que valga es la última guardada
        fila = {k: p.get(k) for k in COLS_PRED if k not in ("fecha", "guardada")}
        fila |= {"fecha": fecha, "guardada": ahora.strftime("%Y-%m-%dT%H:%MZ")}
        reg = reg[reg.game_id.astype(str) != str(p["game_id"])]
        reg = pd.concat([reg, pd.DataFrame([fila])], ignore_index=True)
    return reg.sort_values("fecha").reset_index(drop=True)[COLS_PRED]


def evaluar(registro: pd.DataFrame, rm: pd.DataFrame, base: np.ndarray | None = None,
            mercado: pd.DataFrame | None = None) -> pd.DataFrame:
    """Añade resultado y métricas a las predicciones cuyo partido ya se jugó (rm: rm_partidos).
    base: frecuencias (local, empate, visitante) del modelo ingenuo. mercado: m_victoria... por game_id."""
    if registro is None or registro.empty:
        return pd.DataFrame()
    ev = registro.copy()
    ev["game_id"] = ev.game_id.astype(int)
    jug = rm[rm.jugado][["game_id", "gf", "gc", "xgf", "xgc"]]
    ev = ev.merge(jug, on="game_id", how="left")
    ev["jugado"] = ev.gf.notna()
    ev["resultado"] = np.where(ev.gf > ev.gc, "V", np.where(ev.gf == ev.gc, "E", "D"))
    ev.loc[~ev.jugado, "resultado"] = None
    j = ev.jugado.to_numpy()
    y = np.select([ev.gf > ev.gc, ev.gf == ev.gc], [0, 1], 2)
    P = ev[["p_victoria", "p_empate", "p_derrota"]].to_numpy(float)
    for nombre, f in (("rps", rps), ("brier", brier), ("logloss", logloss)):
        ev[nombre] = np.where(j, f(P, y), np.nan)
    ev["acierto"] = np.where(j, P.argmax(1) == y, np.nan)
    if base is not None:
        B = np.array([_perspectiva(base, c) for c in ev.condicion])
        ev[["b_victoria", "b_empate", "b_derrota"]] = B
        ev["rps_base"] = np.where(j, rps(B, y), np.nan)
    if mercado is not None and len(mercado):
        ev = ev.drop(columns=[c for c in ("m_victoria", "m_empate", "m_derrota") if c in ev]).merge(
            mercado[["game_id", "m_victoria", "m_empate", "m_derrota"]], on="game_id", how="left")
        M = ev[["m_victoria", "m_empate", "m_derrota"]].to_numpy(float)
        ev["rps_mercado"] = np.where(j & np.isfinite(M).all(1), rps(np.nan_to_num(M), y), np.nan)
    return ev


def _perspectiva(p_lev: np.ndarray, condicion: str) -> np.ndarray:
    """(local, empate, visitante) -> (victoria, empate, derrota) del Madrid."""
    p_lev = np.asarray(p_lev, float)
    return p_lev if condicion == "Local" else p_lev[::-1]


def a_perspectiva_madrid(df: pd.DataFrame, pref: str, equipo: str = "Real Madrid") -> np.ndarray:
    """Columnas pref_local/pref_empate/pref_visitante -> matriz (victoria, empate, derrota) del Madrid."""
    P = df[[f"{pref}_local", f"{pref}_empate", f"{pref}_visitante"]].to_numpy(float).copy()
    visit = (df.visitante == equipo).to_numpy()
    P[visit] = P[visit][:, ::-1]
    return P


# ---------------------------------------------------------------- resumen para la web
def resumen(bt: pd.DataFrame, en_vivo: pd.DataFrame, equipo: str = "Real Madrid") -> dict:
    """bt: backtest de toda LaLiga (con m_* si hay cuotas). en_vivo: salida de `evaluar`."""
    out: dict = {}
    hay_m = {"m_local", "m_empate", "m_visitante"} <= set(bt.columns)
    P = bt[["p_local", "p_empate", "p_visitante"]].to_numpy(float)
    B = bt[["b_local", "b_empate", "b_visitante"]].to_numpy(float)
    y = bt.resultado.to_numpy(int)
    bt = bt.assign(rps_modelo=rps(P, y), rps_base=rps(B, y), brier_modelo=brier(P, y), logloss_modelo=logloss(P, y),
                   acierto=(P.argmax(1) == y))
    con_m = np.zeros(len(bt), bool)
    if hay_m:
        M = bt[["m_local", "m_empate", "m_visitante"]].to_numpy(float)
        con_m = np.isfinite(M).all(1)
        bt["rps_mercado"] = np.where(con_m, rps(np.nan_to_num(M), y), np.nan)
        bt["acierto_mercado"] = np.where(con_m, np.nan_to_num(M).argmax(1) == y, np.nan)

    def bloque(d: pd.DataFrame, m_ok: np.ndarray) -> dict:
        r = {"n": len(d), "rps_modelo": float(d.rps_modelo.mean()), "rps_base": float(d.rps_base.mean()),
             "brier_modelo": float(d.brier_modelo.mean()), "logloss_modelo": float(d.logloss_modelo.mean()),
             "acierto": float(d.acierto.mean()), "vs_base": diebold_mariano(d.rps_modelo, d.rps_base)}
        if m_ok.sum() >= 10:
            dm = d[m_ok]
            r |= {"n_mercado": int(m_ok.sum()), "rps_mercado": float(dm.rps_mercado.mean()),
                  "rps_modelo_con_mercado": float(dm.rps_modelo.mean()), "acierto_mercado": float(dm.acierto_mercado.mean()),
                  "vs_mercado": diebold_mariano(dm.rps_modelo, dm.rps_mercado)}
        return r

    out["liga"] = bloque(bt, con_m)
    es_rm = ((bt.local == equipo) | (bt.visitante == equipo)).to_numpy()
    out["madrid"] = bloque(bt[es_rm], con_m[es_rm])
    out["por_temporada"] = [{"temporada": t, **{k: v for k, v in bloque(d, con_m[bt.temporada.to_numpy() == t]).items()
                                                if not isinstance(v, dict)}}
                            for t, d in bt.groupby("temporada")]
    out["calibracion"] = calibracion(P, y)
    if hay_m and con_m.sum() >= 30:
        out["calibracion_mercado"] = calibracion(np.nan_to_num(M[con_m]), y[con_m])

    # partidos del Madrid reconstruidos, en su perspectiva
    rmb = bt[es_rm].copy()
    PV = a_perspectiva_madrid(rmb, "p")
    loc = (rmb.local == equipo).to_numpy()
    yv = np.where(loc, rmb.resultado, 2 - rmb.resultado)
    out["madrid_partidos"] = [
        {"fecha": f.strftime("%Y-%m-%dT%H:%MZ"), "rival": (v if casa else lo), "condicion": "Local" if casa else "Visitante",
         "p_victoria": float(p[0]), "p_empate": float(p[1]), "p_derrota": float(p[2]), "resultado": "VED"[int(r)],
         "rps": float(x)}
        for f, lo, v, casa, p, r, x in zip(pd.to_datetime(rmb.fecha), rmb.local, rmb.visitante, loc, PV, yv,
                                           rmb.rps_modelo, strict=True)]

    # en tiempo real
    if en_vivo is not None and len(en_vivo):
        ev = en_vivo[en_vivo.jugado]
        vivo = {"n": len(ev), "pendientes": int((~en_vivo.jugado).sum())}
        if len(ev):
            vivo |= {"rps_modelo": float(ev.rps.mean()), "acierto": float(ev.acierto.mean())}
            if "rps_base" in ev:
                vivo |= {"rps_base": float(ev.rps_base.mean()), "vs_base": diebold_mariano(ev.rps, ev.rps_base)}
            if "rps_mercado" in ev and ev.rps_mercado.notna().sum() >= 3:
                em = ev[ev.rps_mercado.notna()]
                vivo |= {"n_mercado": len(em), "rps_mercado": float(em.rps_mercado.mean()),
                         "vs_mercado": diebold_mariano(em.rps, em.rps_mercado)}
        out["en_vivo"] = vivo
    else:
        out["en_vivo"] = {"n": 0, "pendientes": 0}
    return out
