"""Informe de cada equipo de LaLiga para la página del próximo rival (rivales.json).

Lo que no se puede sacar en la web de los CSV que ya se publican: de dónde tira y desde dónde le
tiran (densidad suavizada en medio campo), su perfil de tiro y en qué tramos marca y encaja.
Solo datos agregados: ningún tiro suelto de Understat.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

L, A = 105.0, 68.0
NU, NV = 14, 11          # rejilla en medio campo: 14 columnas a lo ancho (4,9 m), 11 filas a lo largo (4,8 m)
SIGMA = 4.0
TRAMOS = [0, 15, 30, 45, 60, 75, 200]


def rejilla_medio(x: np.ndarray, y: np.ndarray) -> list[int]:
    """Tiros en metros (x hacia la portería atacada en 105) -> densidad en medio campo vertical.
    Columnas: u = 68 − y (izquierda del atacante a la izquierda); filas desde la portería (arriba)."""
    if len(x) == 0:
        return []
    u = A - np.asarray(y, float)
    v = np.asarray(x, float)
    cu = (np.arange(NU) + 0.5) * A / NU
    cv = L - (np.arange(NV) + 0.5) * (L / 2) / NV        # fila 0 = junto a la portería
    ku = np.exp(-0.5 * ((cu[None, :] - u[:, None]) / SIGMA) ** 2)
    kv = np.exp(-0.5 * ((cv[None, :] - v[:, None]) / SIGMA) ** 2)
    dens = kv.T @ ku
    return np.rint(100 * dens / dens.max()).astype(int).ravel().tolist()


def _perfil(t: pd.DataFrame, partidos: int) -> dict:
    sin_pen = t[t.situacion != "Penalty"]
    dentro = (t.x >= L - 16.5) & (t.y.between((A - 40.32) / 2, (A + 40.32) / 2))
    bp = t.situacion.isin(["From Corner", "Set Piece", "Direct Freekick"])
    goles = t[t.es_gol == 1]
    n = max(len(t), 1)
    return {
        "tiros_pp": len(t) / partidos, "npxg_pp": float(sin_pen.xg_understat.sum()) / partidos,
        "xg_por_tiro": float(sin_pen.xg_understat.mean()) if len(sin_pen) else None,
        "pct_fuera_area": float((~dentro).sum() / n), "pct_cabeza": float((t.parte_cuerpo == "Head").sum() / n),
        "pct_balon_parado": float(bp.sum() / n), "goles": int(len(goles)),
        "goles_balon_parado": int((goles.situacion.isin(["From Corner", "Set Piece", "Direct Freekick"])).sum()),
        "goles_penalti": int((goles.situacion == "Penalty").sum()),
        "dist_media": float(sin_pen.distancia.mean()) if len(sin_pen) and "distancia" in t else None,
    }


def _por_tramo(t: pd.DataFrame) -> dict:
    tr = pd.cut(t.minuto, TRAMOS, right=False, labels=False)
    goles = t.es_gol.groupby(tr).sum().reindex(range(len(TRAMOS) - 1), fill_value=0)
    xg = t.xg_understat.groupby(tr).sum().reindex(range(len(TRAMOS) - 1), fill_value=0)
    return {"goles": [int(g) for g in goles], "xg": [round(float(v), 2) for v in xg]}


def informe(lp_temp: pd.DataFrame, tiros_temp: pd.DataFrame) -> dict:
    """lp_temp: partidos de LaLiga de la temporada; tiros_temp: sus tiros (todos los equipos)."""
    jug = lp_temp[lp_temp.jugado]
    t = tiros_temp[tiros_temp.game_id.isin(jug.game_id)]
    equipos = sorted(set(lp_temp.local) | set(lp_temp.visitante))
    out = {}
    for e in equipos:
        ids = jug[(jug.local == e) | (jug.visitante == e)].game_id
        pj = len(ids)
        if pj == 0:
            continue
        favor = t[(t.equipo == e) & t.game_id.isin(ids)]
        contra = t[(t.equipo != e) & t.game_id.isin(ids)]
        fp, cp = favor[favor.situacion != "Penalty"], contra[contra.situacion != "Penalty"]
        out[e] = {
            "pj": pj,
            "favor": _perfil(favor, pj) | {"rejilla": rejilla_medio(fp.x.to_numpy(), fp.y.to_numpy()), "n": len(fp)},
            "contra": _perfil(contra, pj) | {"rejilla": rejilla_medio(cp.x.to_numpy(), cp.y.to_numpy()), "n": len(cp)},
            "tramos_favor": _por_tramo(favor), "tramos_contra": _por_tramo(contra),
        }
    return {"rejilla": [NU, NV], "tramos": TRAMOS[:-1], "equipos": out}
