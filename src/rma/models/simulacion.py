"""Monte Carlo del resto de la temporada con Dixon-Coles.

Cada partido pendiente se simula muestreando un marcador de su matriz de probabilidades
(no solo 1X2, para poder desempatar por diferencia de goles). Se suman los puntos ya
conseguidos y se cuenta en cuántas simulaciones acaba cada equipo en cada puesto.

Simplificaciones: las fuerzas se fijan en la estimación de hoy (no se actualizan dentro
de la simulación) y el desempate es por diferencia de goles, no por el golaveraje
particular que usa LaLiga.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from rma.models.dixon_coles import DixonColes


def clasificacion(jugados: pd.DataFrame) -> pd.DataFrame:
    filas = []
    for r in jugados.itertuples():
        gl, gv = int(r.goles_local), int(r.goles_visitante)
        pl = 3 if gl > gv else 1 if gl == gv else 0
        pv = 3 if gv > gl else 1 if gl == gv else 0
        filas += [(r.local, pl, gl - gv, gl), (r.visitante, pv, gv - gl, gv)]
    t = pd.DataFrame(filas, columns=["equipo", "puntos", "dg", "gf"])
    return (t.groupby("equipo").agg(pj=("puntos", "size"), puntos=("puntos", "sum"),
                                    dg=("dg", "sum"), gf=("gf", "sum"))
            .sort_values(["puntos", "dg", "gf"], ascending=False).reset_index())


def simular(modelo: DixonColes, temporada: pd.DataFrame, n: int = 10_000, semilla: int = 1,
            max_goles: int = 8) -> dict:
    rng = np.random.default_rng(semilla)
    jug = temporada[temporada.jugado]
    pend = temporada[~temporada.jugado]
    equipos = sorted(set(temporada.local) | set(temporada.visitante))
    k = {e: i for i, e in enumerate(equipos)}
    E = len(equipos)

    base = clasificacion(jug).set_index("equipo") if len(jug) else pd.DataFrame()
    pts = np.zeros((n, E))
    dg = np.zeros((n, E))
    for e in equipos:
        if e in base.index:
            pts[:, k[e]] = base.loc[e, "puntos"]
            dg[:, k[e]] = base.loc[e, "dg"]

    G = max_goles + 1
    for r in pend.itertuples():
        m = modelo.matriz(r.local, r.visitante, max_goles).ravel()
        idx = np.searchsorted(np.cumsum(m), rng.random(n) * m.sum())
        gl, gv = np.minimum(idx // G, max_goles), np.minimum(idx % G, max_goles)
        i, j = k[r.local], k[r.visitante]
        pts[:, i] += np.where(gl > gv, 3, np.where(gl == gv, 1, 0))
        pts[:, j] += np.where(gv > gl, 3, np.where(gl == gv, 1, 0))
        dg[:, i] += gl - gv
        dg[:, j] += gv - gl

    # puesto final: ordenar por puntos y, a igualdad, por diferencia de goles (+ ruido para empates exactos)
    clave = pts * 1000 + dg + rng.random((n, E)) * 1e-3
    orden = np.argsort(-clave, axis=1)
    puesto = np.empty_like(orden)
    puesto[np.arange(n)[:, None], orden] = np.arange(1, E + 1)

    res = pd.DataFrame({
        "equipo": equipos,
        "puntos_actuales": [float(base.loc[e, "puntos"]) if e in base.index else 0.0 for e in equipos],
        "puntos_media": pts.mean(0),
        "puntos_p05": np.quantile(pts, 0.05, axis=0),
        "puntos_p95": np.quantile(pts, 0.95, axis=0),
        "p_campeon": (puesto == 1).mean(0),
        "p_top4": (puesto <= 4).mean(0),
        "p_descenso": (puesto > E - 3).mean(0),
    }).sort_values("puntos_media", ascending=False, ignore_index=True)
    return {"tabla": res, "puestos": puesto, "puntos": pts, "equipos": equipos,
            "pendientes": len(pend), "n": n}
