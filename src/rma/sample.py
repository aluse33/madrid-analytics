"""Datos sintéticos con el MISMO esquema que la descarga de Understat.

Sirven para desarrollar la web, probar el pipeline y correr los tests sin conexión.
Los resultados, tiros y jugadores son inventados: la web muestra un aviso cuando
`estado.json` dice `"muestra": true`, y el workflow de producción nunca los usa.

El proceso generador tiene estructura real (que es lo que necesitan los modelos):
- cada equipo tiene ataque y defensa latentes que derivan entre temporadas;
- el número de tiros depende de esas fuerzas y del factor campo;
- la probabilidad de gol de cada tiro es logística en distancia, ángulo, cabeza y situación,
  y el xG "de Understat" es esa probabilidad con ruido, así que un modelo xG propio
  puede aprender algo;
- los jugadores tienen calidad latente, para que el shrinkage tenga señal que recuperar.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from rma.config import RAIZ, Config, codigo_temporada
from rma.ingest.understat import ruta

EQUIPOS = [
    "Real Madrid", "Barcelona", "Atletico Madrid", "Athletic Club", "Real Sociedad",
    "Villarreal", "Real Betis", "Sevilla", "Valencia", "Celta Vigo", "Osasuna", "Getafe",
    "Rayo Vallecano", "Mallorca", "Girona", "Alaves", "Espanyol", "Levante", "Elche",
    "Real Oviedo",
]
# Fuerza base (log-escala): ataque alto es bueno, defensa alta es mala (concede más).
FUERZA = {
    "Real Madrid": (0.50, -0.40), "Barcelona": (0.52, -0.25), "Atletico Madrid": (0.25, -0.30),
    "Athletic Club": (0.12, -0.15), "Villarreal": (0.15, -0.05), "Real Sociedad": (0.05, -0.08),
    "Real Betis": (0.08, 0.0),
}
POSICIONES = ["GK"] + ["D"] * 4 + ["M"] * 3 + ["FW"] * 3  # once inicial
PESO_TIRO = {"GK": 0.0, "D": 0.35, "M": 0.9, "FW": 2.4}
PESO_ASIST = {"GK": 0.02, "D": 0.5, "M": 1.4, "FW": 1.0}
NOMBRES_RM = [
    "Portero Uno", "Portero Dos",                                              # GK
    "Lateral Diestro", "Central Alto", "Central Rápido", "Lateral Zurdo",       # D
    "Central Joven", "Lateral Suplente",                                       # D
    "Mediocentro Ancla", "Interior Llegador", "Interior Creativo",             # M
    "Pivote Suplente", "Mediapunta Joven", "Interior Canterano",               # M
    "Delantero Centro", "Extremo Izquierdo", "Extremo Derecho",                # FW
    "Delantero Suplente", "Extremo Canterano",                                 # FW
    "Pivote Canterano", "Central Canterano", "Delantero Canterano",            # M, D, FW
]
POS_PLANTILLA = ["GK", "GK"] + ["D"] * 6 + ["M"] * 6 + ["FW"] * 5 + ["M", "D", "FW"]


def _sigmoid(z):
    return 1.0 / (1.0 + np.exp(-z))


def _calendario(equipos: list[str], rng: np.random.Generator) -> list[list[tuple[str, str]]]:
    """Doble vuelta por el método del círculo (38 jornadas de 10 partidos), alternando
    casa y fuera como en un calendario real."""
    eq = list(equipos)
    rng.shuffle(eq)
    n = len(eq)
    fijo, rota = eq[0], eq[1:]
    ida = []
    for r in range(n - 1):
        jornada = [(fijo, rota[-1]) if r % 2 == 0 else (rota[-1], fijo)]
        for i in range(n // 2 - 1):
            a, b = rota[i], rota[-2 - i]
            jornada.append((a, b) if i % 2 == 0 else (b, a))
        ida.append(jornada)
        rota = [rota[-1], *rota[:-1]]
    vuelta = [[(b, a) for a, b in j] for j in ida]
    return ida + vuelta


def _plantillas(rng: np.random.Generator) -> dict[str, pd.DataFrame]:
    out = {}
    pid = 1000
    for eq in EQUIPOS:
        filas = []
        for j, pos in enumerate(POS_PLANTILLA):
            nombre = NOMBRES_RM[j] if eq == "Real Madrid" else f"{eq.split()[0][:3].upper()} {j + 1:02d}"
            calidad = rng.lognormal(0, 0.35)  # multiplica su cuota de tiros/asistencias
            # los primeros de cada puesto son titulares habituales
            filas.append({"player": nombre, "player_id": pid, "pos": pos, "calidad": calidad,
                          "titularidad": 1.0 if j in {0, 2, 3, 4, 5, 8, 9, 10, 14, 15, 16} else 0.25})
            pid += 1
        out[eq] = pd.DataFrame(filas)
    return out


def _tiro(rng, situacion_p):
    """Un tiro: posición, rasgos y probabilidad real de gol."""
    sit = rng.choice(["Open Play", "From Corner", "Set Piece", "Direct Freekick", "Penalty"],
                     p=situacion_p)
    if sit == "Penalty":
        dx, dy, cabeza = 11.0, 0.0, False
    elif sit == "Direct Freekick":
        dx, dy, cabeza = rng.uniform(17, 30), rng.normal(0, 8), False
    else:
        dx = 4 + rng.gamma(2.2, 5.5)
        dy = rng.normal(0, 7 + 0.25 * dx)
        cabeza = rng.random() < (0.45 if sit == "From Corner" else 0.15)
    dx, dy = min(dx, 40.0), float(np.clip(dy, -30, 30))
    dist = np.hypot(dx, dy)
    ang = np.arctan2(7.32 * dx, dx**2 + dy**2 - (7.32 / 2) ** 2)
    ang = ang if ang > 0 else ang + np.pi
    if sit == "Penalty":
        p = 0.76
    else:
        z = -1.2 - 0.105 * dist + 1.6 * ang - 0.85 * cabeza + (-0.35 if sit == "Direct Freekick" else 0)
        p = float(_sigmoid(z))
    return sit, dx, dy, cabeza, p


def generar(cfg: Config, hoy: date | None = None, semilla: int = 7) -> None:
    rng = np.random.default_rng(semilla)
    hoy = hoy or date.today()
    (cfg.raw / "MUESTRA").write_text("Datos sintéticos: no publicar.\n", encoding="utf-8")
    (RAIZ / "models" / "xg.joblib").unlink(missing_ok=True)  # nunca mezclar un modelo de otros datos
    plantillas = _plantillas(rng)
    fuerza = {e: np.array(FUERZA.get(e, (rng.normal(-0.1, 0.12), rng.normal(0.1, 0.12))))
              for e in EQUIPOS}
    sit_p = [0.74, 0.11, 0.09, 0.035, 0.025]
    shot_id = 1
    game_id = 10_000

    for t in cfg.todas_las_temporadas:
        cod = codigo_temporada(t)
        anio = int(t[:4])
        inicio = date(anio, 8, 16)
        # deriva entre temporadas (AR(1) hacia la base)
        fuerza = {e: 0.7 * f + 0.3 * np.array(FUERZA.get(e, f)) + rng.normal(0, 0.06, 2)
                  for e, f in fuerza.items()}
        sched, shots, pm = [], [], []
        for r, jornada in enumerate(_calendario(EQUIPOS, rng)):
            dia = inicio + timedelta(days=7 * r + (21 if r >= 19 else 0))  # parón invernal
            for local, visit in jornada:
                game_id += 1
                jugado = dia < hoy
                fila = {
                    "league": cfg.liga, "season": cod, "game": f"{dia.isoformat()} {local}-{visit}",
                    "league_id": 2, "season_id": anio, "game_id": game_id,
                    "date": pd.Timestamp(dia) + pd.Timedelta(hours=21),
                    "home_team_id": EQUIPOS.index(local) + 1, "away_team_id": EQUIPOS.index(visit) + 1,
                    "home_team": local, "away_team": visit,
                    "home_team_code": local[:3].upper(), "away_team_code": visit[:3].upper(),
                    "home_goals": None, "away_goals": None, "home_xg": None, "away_xg": None,
                    "is_result": jugado, "has_data": jugado,
                    "url": f"https://understat.com/match/{game_id}",
                }
                if not jugado:
                    sched.append(fila)
                    continue
                goles = {local: 0, visit: 0}
                xgs = {local: 0.0, visit: 0.0}
                # alineaciones: 11 titulares + 3 suplentes por equipo
                alineados = {}
                for eq in (local, visit):
                    pl = plantillas[eq]
                    tit = []
                    for pos, k in [("GK", 1), ("D", 4), ("M", 3), ("FW", 3)]:
                        cand = pl[pl.pos == pos]
                        w = cand.titularidad.to_numpy() / cand.titularidad.sum()
                        tit += list(rng.choice(cand.index, size=k, replace=False, p=w))
                    resto = [i for i in pl.index if i not in tit and pl.loc[i, "pos"] != "GK"]
                    sup = list(rng.choice(resto, size=3, replace=False))
                    mins = {i: 90 for i in tit}
                    for s, sale in zip(sup, rng.choice([i for i in tit if pl.loc[i, "pos"] != "GK"], 3, replace=False), strict=True):
                        m = int(rng.integers(55, 85))
                        mins[sale] = m
                        mins[s] = 90 - m
                    alineados[eq] = (pl, mins)
                for eq, rival, campo in ((local, visit, 1), (visit, local, 0)):
                    lam = 11.5 * np.exp(0.08 * campo + 0.5 * (fuerza[eq][0] + fuerza[rival][1]))
                    pl, mins = alineados[eq]
                    ids = list(mins)
                    w_t = np.array([PESO_TIRO[pl.loc[i, "pos"]] * pl.loc[i, "calidad"] * mins[i] for i in ids])
                    w_a = np.array([PESO_ASIST[pl.loc[i, "pos"]] * pl.loc[i, "calidad"] * mins[i] for i in ids])
                    stats = {i: dict(goals=0, shots=0, xg=0.0, xa=0.0, key_passes=0, assists=0) for i in ids}
                    for _ in range(rng.poisson(lam)):
                        sit, dx, dy, cabeza, p = _tiro(rng, sit_p)
                        xg = float(np.clip(_sigmoid(np.log(p / (1 - p)) + rng.normal(0, 0.25)), 0.005, 0.97))
                        tirador = ids[int(rng.choice(len(ids), p=w_t / w_t.sum()))]
                        gol = rng.random() < p
                        if gol:
                            res = "Goal"
                        else:
                            res = rng.choice(["Saved Shot", "Missed Shot", "Blocked Shot", "Shot On Post"],
                                             p=[0.33, 0.38, 0.26, 0.03])
                        asist = None
                        if sit not in {"Penalty", "Direct Freekick"} and rng.random() < 0.72:
                            w = w_a.copy()
                            w[ids.index(tirador)] = 0
                            asist = ids[int(rng.choice(len(ids), p=w / w.sum()))]
                            stats[asist]["xa"] += xg
                            stats[asist]["key_passes"] += 1
                            stats[asist]["assists"] += int(gol)
                        stats[tirador]["shots"] += 1
                        stats[tirador]["xg"] += xg
                        stats[tirador]["goals"] += int(gol)
                        goles[eq] += int(gol)
                        xgs[eq] += xg
                        minuto = int(np.clip(rng.integers(1, 96), 1, 95))
                        shots.append({
                            "league": cfg.liga, "season": cod, "game": fila["game"], "team": eq,
                            "player": pl.loc[tirador, "player"], "league_id": 2, "season_id": anio,
                            "game_id": game_id, "date": fila["date"] + pd.Timedelta(minutes=minuto),
                            "shot_id": shot_id, "team_id": EQUIPOS.index(eq) + 1,
                            "player_id": int(pl.loc[tirador, "player_id"]),
                            "assist_player_id": None if asist is None else int(pl.loc[asist, "player_id"]),
                            "assist_player": None if asist is None else pl.loc[asist, "player"],
                            "xg": round(xg, 4), "location_x": round(1 - dx / 105, 4),
                            "location_y": round(0.5 + dy / 68, 4), "minute": minuto,
                            "body_part": "Other" if cabeza else rng.choice(["Right Foot", "Left Foot"], p=[0.68, 0.32]),
                            "situation": None if sit == "Penalty" else sit,  # Understat: penalti -> NA en soccerdata
                            "result": res,
                        })
                        shot_id += 1
                    for i in ids:
                        s = stats[i]
                        pm.append({
                            "league": cfg.liga, "season": cod, "game": fila["game"], "team": eq,
                            "player": pl.loc[i, "player"], "league_id": 2, "season_id": anio,
                            "game_id": game_id, "team_id": EQUIPOS.index(eq) + 1,
                            "player_id": int(pl.loc[i, "player_id"]), "position": pl.loc[i, "pos"],
                            "position_id": POSICIONES.index(pl.loc[i, "pos"]) + 1, "minutes": mins[i],
                            "goals": s["goals"], "own_goals": 0, "shots": s["shots"], "xg": round(s["xg"], 4),
                            "xg_chain": round((s["xg"] + s["xa"]) * 1.4, 4),
                            "xg_buildup": round(s["xa"] * 0.5, 4), "assists": s["assists"],
                            "xa": round(s["xa"], 4), "key_passes": s["key_passes"],
                            "yellow_cards": int(rng.random() < 0.08), "red_cards": int(rng.random() < 0.004),
                        })
                fila.update(home_goals=goles[local], away_goals=goles[visit],
                            home_xg=round(xgs[local], 4), away_xg=round(xgs[visit], 4))
                sched.append(fila)
        pd.DataFrame(sched).to_parquet(ruta(cfg, "schedule", t), index=False)
        pd.DataFrame(shots).to_parquet(ruta(cfg, "shots", t), index=False)
        pd.DataFrame(pm).to_parquet(ruta(cfg, "player_match", t), index=False)
