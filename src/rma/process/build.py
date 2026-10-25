"""Construcción de las tablas limpias.

Convenciones:
- coordenadas en metros en un campo de 105 x 68, atacando siempre hacia x = 105;
- temporada como etiqueta "2026/27";
- `jugado` distingue partidos disputados de calendario futuro.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from rma.config import Config, etiqueta_temporada
from rma.ingest import understat
from rma.process.normalize import canonico

LARGO, ANCHO, PORTERIA = 105.0, 68.0, 7.32

RESULTADO_TIRO = {
    "Goal": "gol", "Saved Shot": "parado", "Missed Shot": "fuera",
    "Shot On Post": "poste", "Blocked Shot": "bloqueado",
}


def geometria(x_m: np.ndarray, y_m: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Distancia al centro de la portería y ángulo (radianes) que abren los dos postes."""
    dx = LARGO - x_m
    dy = y_m - ANCHO / 2
    dist = np.hypot(dx, dy)
    ang = np.arctan2(PORTERIA * dx, dx**2 + dy**2 - (PORTERIA / 2) ** 2)
    ang = np.where(ang < 0, ang + np.pi, ang)
    return dist, ang


def liga_partidos(schedule: pd.DataFrame) -> pd.DataFrame:
    df = pd.DataFrame({
        "game_id": schedule["game_id"].astype(int),
        "temporada": schedule["season"].astype(str).map(etiqueta_temporada),
        "fecha": pd.to_datetime(schedule["date"]),
        "local": schedule["home_team"].map(canonico),
        "visitante": schedule["away_team"].map(canonico),
        "goles_local": pd.to_numeric(schedule["home_goals"], errors="coerce"),
        "goles_visitante": pd.to_numeric(schedule["away_goals"], errors="coerce"),
        "xg_local": pd.to_numeric(schedule["home_xg"], errors="coerce"),
        "xg_visitante": pd.to_numeric(schedule["away_xg"], errors="coerce"),
        "jugado": schedule["is_result"].astype(bool),
    })
    return df.sort_values("fecha").drop_duplicates("game_id").reset_index(drop=True)


def partidos_equipo(partidos: pd.DataFrame, equipo: str) -> pd.DataFrame:
    """Una fila por partido del equipo, desde su punto de vista."""
    p = partidos[(partidos.local == equipo) | (partidos.visitante == equipo)].copy()
    casa = p.local == equipo
    p["condicion"] = np.where(casa, "Local", "Visitante")
    p["rival"] = np.where(casa, p.visitante, p.local)
    p["gf"] = np.where(casa, p.goles_local, p.goles_visitante)
    p["gc"] = np.where(casa, p.goles_visitante, p.goles_local)
    p["xgf"] = np.where(casa, p.xg_local, p.xg_visitante)
    p["xgc"] = np.where(casa, p.xg_visitante, p.xg_local)
    p["resultado"] = np.select(
        [p.gf > p.gc, p.gf == p.gc, p.gf < p.gc], ["V", "E", "D"], default=None
    )
    p.loc[~p.jugado, "resultado"] = None
    p["puntos"] = p.resultado.map({"V": 3, "E": 1, "D": 0})
    p["jornada"] = p.groupby("temporada").cumcount() + 1
    cols = ["game_id", "temporada", "jornada", "fecha", "condicion", "rival", "gf", "gc",
            "xgf", "xgc", "resultado", "puntos", "jugado"]
    return p[cols].reset_index(drop=True)


def tiros(shots: pd.DataFrame) -> pd.DataFrame:
    s = shots.copy()
    s = s[s["result"] != "Own Goal"]  # los autogoles no son tiros del equipo que los "marca"
    x = pd.to_numeric(s["location_x"]).to_numpy() * LARGO
    y = pd.to_numeric(s["location_y"]).to_numpy() * ANCHO
    dist, ang = geometria(x, y)
    # soccerdata deja en NA la única situación que no mapea: el penalti
    situacion = s["situation"].astype(object).where(s["situation"].notna(), "Penalty")
    out = pd.DataFrame({
        "shot_id": s["shot_id"].astype(int),
        "game_id": s["game_id"].astype(int),
        "temporada": s["season"].astype(str).map(etiqueta_temporada),
        "equipo": s["team"].map(canonico),
        "jugador": s["player"].astype(str),
        "jugador_id": s["player_id"].astype(int),
        "asistente": s["assist_player"].astype(object),
        "minuto": s["minute"].astype(int),
        "x": x.round(2), "y": y.round(2),
        "distancia": dist.round(2), "angulo": ang.round(4),
        "cabeza": (s["body_part"] == "Other").to_numpy(),
        "parte_cuerpo": s["body_part"].astype(object),
        "situacion": situacion.to_numpy(),
        "xg_understat": pd.to_numeric(s["xg"]).to_numpy(),
        "resultado": s["result"].map(RESULTADO_TIRO).fillna("fuera").to_numpy(),
    })
    out["es_gol"] = out.resultado.eq("gol")
    return out.reset_index(drop=True)


def jugadores_partido(pm: pd.DataFrame) -> pd.DataFrame:
    cols = {"game_id": "game_id", "team": "equipo", "player": "jugador", "player_id": "jugador_id",
            "position": "posicion", "minutes": "minutos", "goals": "goles", "shots": "tiros",
            "xg": "xg", "xa": "xa", "assists": "asistencias", "key_passes": "pases_clave",
            "xg_chain": "xg_chain", "xg_buildup": "xg_buildup"}
    out = pm[list(cols)].rename(columns=cols).copy()
    out["temporada"] = pm["season"].astype(str).map(etiqueta_temporada)
    out["equipo"] = out.equipo.map(canonico)
    for c in ["minutos", "goles", "tiros", "asistencias", "pases_clave", "game_id", "jugador_id"]:
        out[c] = pd.to_numeric(out[c]).fillna(0).astype(int)
    for c in ["xg", "xa", "xg_chain", "xg_buildup"]:
        out[c] = pd.to_numeric(out[c]).astype(float)
    # Understat usa códigos como "FW", "AML", "DC", "Sub"; agrupamos en 4 puestos
    out["puesto"] = out.posicion.astype(str).map(_puesto)
    return out


def _puesto(p: str) -> str:
    p = (p or "").upper()
    if p.startswith("GK"):
        return "POR"
    if p.startswith("DM"):  # DMC/DML/DMR: mediocentro defensivo, no defensa
        return "MED"
    if p.startswith("D"):
        return "DEF"
    if p.startswith("FW") or p in {"AML", "AMR", "AMC", "FWL", "FWR"}:
        return "DEL"
    return "MED"  # incluye "Sub": se reasigna con su puesto más frecuente en `puesto_habitual`


def puesto_habitual(jp: pd.DataFrame) -> pd.DataFrame:
    """Cada jugador con el puesto en el que más minutos jugó como no-suplente."""
    base = jp[jp.posicion.astype(str).str.upper() != "SUB"]
    moda = (base.groupby(["jugador_id", "puesto"]).minutos.sum().reset_index()
            .sort_values("minutos").drop_duplicates("jugador_id", keep="last")
            .set_index("jugador_id").puesto)
    jp = jp.copy()
    jp["puesto"] = jp.jugador_id.map(moda).fillna(jp.puesto)
    return jp


def temporadas_equipo(pe: pd.DataFrame) -> pd.DataFrame:
    j = pe[pe.jugado]
    t = j.groupby("temporada").agg(
        pj=("game_id", "size"), puntos=("puntos", "sum"), gf=("gf", "sum"), gc=("gc", "sum"),
        xgf=("xgf", "sum"), xgc=("xgc", "sum"),
    ).reset_index()
    for c in ["puntos", "gf", "gc", "xgf", "xgc"]:
        t[f"{c}_pp"] = t[c] / t.pj
    return t


def construir(cfg: Config) -> dict[str, pd.DataFrame]:
    schedule = understat.leer(cfg, "schedule")
    shots = understat.leer(cfg, "shots")
    pm = understat.leer(cfg, "player_match")

    lp = liga_partidos(schedule)
    pe = partidos_equipo(lp, cfg.equipo)
    ti = tiros(shots)
    jp = puesto_habitual(jugadores_partido(pm))
    # npxG por jugador y partido desde los tiros (Understat no lo da a nivel partido)
    npxg = (ti[ti.situacion != "Penalty"].groupby(["game_id", "jugador_id"]).xg_understat.sum()
            .rename("npxg"))
    jp = jp.merge(npxg, left_on=["game_id", "jugador_id"], right_index=True, how="left")
    jp["npxg"] = jp.npxg.fillna(0.0)
    te = temporadas_equipo(pe)

    ids_rm = set(pe.game_id)
    tablas = {
        "liga_partidos": lp,
        "rm_partidos": pe,
        "tiros": ti,                                         # toda la liga: entrena el modelo xG
        "rm_tiros": ti[ti.game_id.isin(ids_rm)],             # lo que pinta la web
        "jugadores_partido": jp,                             # toda la liga: prior del shrinkage
        "rm_temporadas": te,
    }
    for nombre, df in tablas.items():
        df.to_parquet(cfg.processed / f"{nombre}.parquet", index=False)
    return tablas
