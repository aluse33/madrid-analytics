r"""Monte Carlo del resto de la temporada con Dixon-Coles, propagando la incertidumbre.

Una simulación ingenua fija las fuerzas en la estimación de hoy y las da por conocidas y
constantes: sale demasiado segura de sí misma (con 6 puntos de ventaja tras 9 jornadas
llegaba a dar un 94 % de título). Aquí cada temporada simulada usa unas fuerzas distintas,
con tres fuentes de incertidumbre:

1. **Estimación.** θ̂ tiene error: se muestrea θ ~ N(θ̂, Σ) con Σ el sándwich del ajuste.
2. **Desfase.** El ajuste promedia partidos de hasta 3 años (ponderados), pero la fuerza de
   un equipo se mueve como un paseo aleatorio, a_t = a_{t-1} + η_t, Var(η_t) = τ²·Δt. La
   estimación describe al equipo "medio" de ese periodo, no al de hoy. Con pesos ω_s y
   antigüedades s, el error añadido es Var = τ² Σ_s Σ_t ω_s ω_t min(s, t).
3. **Deriva futura.** De aquí a mayo las fuerzas siguen moviéndose con el mismo τ².

τ² se estima con los datos (`estimar_deriva`): se ajusta el modelo en cada media temporada
por separado y se compara la fuerza de cada equipo entre ventanas consecutivas:
E[(Δa)²] = se²_1 + se²_2 + τ²·Δt.

Cada partido pendiente se resuelve muestreando un marcador de la matriz de Dixon-Coles de
esa simulación. Desempate por diferencia de goles (no el golaveraje particular de LaLiga).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import poisson

from rma.models import dixon_coles as dc

# ---------------------------------------------------------------- deriva temporal

def estimar_deriva(partidos: pd.DataFrame, l2: float = 0.05) -> dict:
    """τ² por día de ataque y defensa, comparando ajustes de medias temporadas consecutivas."""
    j = partidos[partidos.jugado].dropna(subset=["xg_local", "xg_visitante"]).sort_values("fecha")
    ventanas = []
    for _, d in j.groupby("temporada"):
        if len(d) < 300:  # temporada incompleta: no da media temporada fiable
            continue
        h = len(d) // 2
        ventanas += [d.iloc[:h], d.iloc[h:]]
    ajustes = []
    for v in ventanas:
        m = dc.ajustar(v, fecha_ref=v.fecha.max() + pd.Timedelta(days=1), semivida_dias=1e9,
                       l2=l2, tipo="xg", anios=None)
        se2 = np.diag(m.cov)
        n = len(m.equipos)
        ajustes.append((v.fecha.mean(), {
            e: (m.ataque[k] - m.ataque.mean(), m.defensa[k] - m.defensa.mean(), se2[2 + k], se2[2 + n + k])
            for k, e in enumerate(m.equipos)
        }))
    out = {"ventanas": len(ventanas)}
    for nombre, ic in (("ataque", 0), ("defensa", 1)):
        num, den = [], []
        for (t0, f0), (t1, f1) in zip(ajustes[:-1], ajustes[1:], strict=True):
            dt = (t1 - t0).days
            for e in set(f0) & set(f1):
                num.append((f1[e][ic] - f0[e][ic]) ** 2 - f0[e][2 + ic] - f1[e][2 + ic])
                den.append(dt)
        out[f"tau2_{nombre}"] = max(float(np.sum(num) / np.sum(den)), 0.0) if den else 0.0
        out[f"pares_{nombre}"] = len(num)
    return out


def varianza_desfase(partidos: pd.DataFrame, fecha_ref: pd.Timestamp, semivida_dias: float,
                     anios: float = 3) -> float:
    """Σ_s Σ_t ω_s ω_t min(s, t) en días: multiplicado por τ² da la varianza que añade
    estimar la fuerza de HOY con partidos antiguos (aproximación con los pesos de la liga)."""
    j = partidos[partidos.jugado & (partidos.fecha < fecha_ref)
                 & (partidos.fecha >= fecha_ref - pd.Timedelta(days=365 * anios))]
    edad = (fecha_ref - j.fecha).dt.total_seconds().to_numpy() / 86400
    w = 0.5 ** (edad / semivida_dias)
    w = w / w.sum()
    return float(w @ np.minimum.outer(edad, edad) @ w)


# ---------------------------------------------------------------- un partido

def matriz_predictiva(modelo: dc.DixonColes, local: str, visitante: str, dias: float = 0.0,
                      deriva: dict | None = None, var_desfase_dias: float = 0.0,
                      n: int = 4000, semilla: int = 2, G: int = 11) -> np.ndarray:
    """P(marcador) promediada sobre la incertidumbre de las fuerzas (predictiva posterior),
    en lugar de evaluarla solo en la estimación puntual."""
    rng = np.random.default_rng(semilla)
    th = modelo.muestrear(n, rng)
    nm = len(modelo.equipos)

    def fuerza(eq, bloque, tau2):
        i = modelo.equipos.index(eq) if eq in modelo.equipos else -1
        x = th[:, bloque + i] if i >= 0 else np.zeros(n)
        if deriva:
            x = x + rng.normal(0, np.sqrt(tau2 * (var_desfase_dias + dias)), n)
        return x

    t2a = deriva["tau2_ataque"] if deriva else 0.0
    t2d = deriva["tau2_defensa"] if deriva else 0.0
    al, dl = fuerza(local, 2, t2a), fuerza(local, 2 + nm, t2d)
    av, dv = fuerza(visitante, 2, t2a), fuerza(visitante, 2 + nm, t2d)
    lam = np.exp(th[:, 0] + th[:, 1] + al + dv)
    nu = np.exp(th[:, 0] + av + dl)
    k = np.arange(G)
    m = poisson.pmf(k[None, :], lam[:, None])[:, :, None] * poisson.pmf(k[None, :], nu[:, None])[:, None, :]
    r = modelo.rho
    m[:, 0, 0] *= np.clip(1 - lam * nu * r, 0, None)
    m[:, 0, 1] *= 1 + lam * r
    m[:, 1, 0] *= 1 + nu * r
    m[:, 1, 1] *= 1 - r
    m = m / m.sum(axis=(1, 2), keepdims=True)
    return m.mean(axis=0)


# ---------------------------------------------------------------- clasificación

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


# ---------------------------------------------------------------- simulación

def _marcadores(lam, nu, rho, rng, G=9):
    """Un marcador por simulación de Dixon-Coles con λ, ν vectores (una tasa por simulación)."""
    k = np.arange(G)
    pl = poisson.pmf(k[None, :], lam[:, None])
    pv = poisson.pmf(k[None, :], nu[:, None])
    m = pl[:, :, None] * pv[:, None, :]
    m[:, 0, 0] *= np.clip(1 - lam * nu * rho, 0, None)
    m[:, 0, 1] *= 1 + lam * rho
    m[:, 1, 0] *= 1 + nu * rho
    m[:, 1, 1] *= 1 - rho
    m = m.reshape(len(lam), -1)
    c = np.cumsum(m, axis=1)
    u = rng.random(len(lam)) * c[:, -1]
    idx = (c < u[:, None]).sum(axis=1)
    return idx // G, idx % G


def simular(
    modelo: dc.DixonColes,
    temporada: pd.DataFrame,
    n: int = 10_000,
    semilla: int = 1,
    deriva: dict | None = None,
    var_desfase_dias: float = 0.0,
    incertidumbre: bool = True,
    seguimiento: tuple[str, ...] = (),
    trayectorias: int = 150,
    partido_clave: int | None = None,
) -> dict:
    """Simula los partidos pendientes `n` veces.

    Con `incertidumbre=False` reproduce la simulación ingenua (fuerzas fijas y conocidas).
    `seguimiento`: equipos cuyos puntos se guardan jornada a jornada (para los gráficos).
    `partido_clave`: game_id cuyo marcador se guarda en cada simulación (para condicionar).
    """
    rng = np.random.default_rng(semilla)
    jug = temporada[temporada.jugado]
    pend = temporada[~temporada.jugado].sort_values("fecha")
    equipos = sorted(set(temporada.local) | set(temporada.visitante))
    k = {e: i for i, e in enumerate(equipos)}
    E = len(equipos)

    # parámetros por simulación: (n, ...) en el orden de `equipos`
    idx_modelo = np.array([modelo.equipos.index(e) if e in modelo.equipos else -1 for e in equipos])
    nm = len(modelo.equipos)
    if incertidumbre:
        th = modelo.muestrear(n, rng)
    else:
        th = np.tile(np.r_[modelo.mu, modelo.campo, modelo.ataque, modelo.defensa], (n, 1))
    mu, h = th[:, 0], th[:, 1]
    a_m, d_m = th[:, 2:2 + nm], th[:, 2 + nm:]
    a = np.where(idx_modelo >= 0, a_m[:, np.maximum(idx_modelo, 0)], 0.0)
    d = np.where(idx_modelo >= 0, d_m[:, np.maximum(idx_modelo, 0)], 0.0)

    t2a = t2d = 0.0
    if incertidumbre and deriva:
        t2a, t2d = deriva["tau2_ataque"], deriva["tau2_defensa"]
        # desfase: la fuerza de hoy frente a la "media" que estima el modelo
        a = a + rng.normal(0, np.sqrt(t2a * var_desfase_dias), (n, E))
        d = d + rng.normal(0, np.sqrt(t2d * var_desfase_dias), (n, E))

    base = clasificacion(jug).set_index("equipo") if len(jug) else pd.DataFrame()
    pts = np.zeros((n, E))
    dg = np.zeros((n, E))
    for e in equipos:
        if e in base.index:
            pts[:, k[e]] = base.loc[e, "puntos"]
            dg[:, k[e]] = base.loc[e, "dg"]

    hoy = modelo.fecha_ref
    t_prev = hoy
    # puntos jornada a jornada de los equipos seguidos (en cada fecha de partido)
    seg_idx = [k[e] for e in seguimiento if e in k]
    hitos, serie = [], []
    clave_res = None
    for fecha, bloque in pend.groupby(pend.fecha.dt.normalize(), sort=True):
        # deriva futura hasta esta fecha
        dt = max((fecha - t_prev).days, 0)
        if dt and (t2a or t2d):
            a = a + rng.normal(0, np.sqrt(t2a * dt), (n, E))
            d = d + rng.normal(0, np.sqrt(t2d * dt), (n, E))
        t_prev = max(t_prev, fecha)
        for r in bloque.itertuples():
            i, j = k[r.local], k[r.visitante]
            lam = np.exp(mu + h + a[:, i] + d[:, j])
            nu = np.exp(mu + a[:, j] + d[:, i])
            gl, gv = _marcadores(lam, nu, modelo.rho, rng)
            if partido_clave is not None and r.game_id == partido_clave:
                clave_res = (r.local, r.visitante, gl.copy(), gv.copy())
            pts[:, i] += np.where(gl > gv, 3, np.where(gl == gv, 1, 0))
            pts[:, j] += np.where(gv > gl, 3, np.where(gl == gv, 1, 0))
            dg[:, i] += gl - gv
            dg[:, j] += gv - gl
        if seg_idx:
            hitos.append(fecha)
            serie.append(pts[:, seg_idx].copy())

    # puesto final: puntos y, a igualdad, diferencia de goles (+ ruido para empates exactos)
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

    out = {"tabla": res, "puestos": puesto, "puntos": pts, "equipos": equipos,
           "pendientes": int(len(pend)), "n": n}
    if clave_res is not None:
        out["clave"] = {"local": clave_res[0], "visitante": clave_res[1],
                        "goles_local": clave_res[2], "goles_visitante": clave_res[3]}
    if seg_idx:
        S = np.stack(serie, axis=1)  # (n, fechas, equipos seguidos)
        out["seguimiento"] = {
            "equipos": [equipos[i] for i in seg_idx],
            "fechas": hitos,
            "serie": S,
            "muestra": S[:trayectorias],
        }
    return out
