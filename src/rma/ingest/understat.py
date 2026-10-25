"""Descarga de Understat con soccerdata.

Understat da, para cada partido de liga: resultado y xG de cada equipo, todos los tiros
(posición, xG, situación, parte del cuerpo, resultado) y estadísticas por jugador
(minutos, xG, xA, pases clave, xGChain, xGBuildup).

Se guarda una tabla por temporada en `data/raw/understat/<tabla>_<codigo>.parquet`.
Las temporadas cerradas se leen de la caché de soccerdata; la actual se fuerza a
descargar de nuevo para recoger los partidos recién jugados.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from rma.config import RAIZ, Config, codigo_temporada

log = logging.getLogger(__name__)

TABLAS = ("schedule", "shots", "player_match")


def ruta(cfg: Config, tabla: str, temporada: str) -> Path:
    d = cfg.raw / "understat"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{tabla}_{codigo_temporada(temporada)}.parquet"


def _limpiar(df: pd.DataFrame) -> pd.DataFrame:
    """Índice de soccerdata a columnas y tipos 'nullable' a tipos normales (parquet-friendly)."""
    df = df.reset_index()
    for c in df.columns:
        if str(df[c].dtype) in {"string", "string[python]"}:
            df[c] = df[c].astype(object)
    return df


def descargar_temporada(cfg: Config, temporada: str, forzar: bool = False) -> dict[str, pd.DataFrame]:
    import soccerdata as sd  # import diferido: no hace falta para trabajar con datos de muestra

    es_actual = temporada == cfg.temporada_actual
    us = sd.Understat(leagues=cfg.liga, seasons=temporada, no_cache=forzar or es_actual)

    log.info("Understat %s: calendario", temporada)
    schedule = _limpiar(us.read_schedule())

    # Solo partidos jugados y con datos; así no se piden páginas vacías.
    jugados = schedule.loc[schedule["is_result"].astype(bool) & schedule["has_data"].astype(bool), "game_id"]
    ids = [int(i) for i in jugados]

    if ids:
        log.info("Understat %s: tiros de %d partidos", temporada, len(ids))
        shots = _limpiar(us.read_shot_events(match_id=ids))
        log.info("Understat %s: estadísticas de jugadores", temporada)
        player_match = _limpiar(us.read_player_match_stats(match_id=ids))
    else:
        shots = pd.DataFrame()
        player_match = pd.DataFrame()

    out = {"schedule": schedule, "shots": shots, "player_match": player_match}
    for nombre, df in out.items():
        df.to_parquet(ruta(cfg, nombre, temporada), index=False)
    return out


def descargar(cfg: Config, solo_actual: bool = False, forzar: bool = False) -> None:
    """Descarga idempotente: las temporadas cerradas solo se piden si faltan en disco
    (o con `forzar`); la temporada en curso se refresca siempre."""
    marcador = cfg.raw / "MUESTRA"
    if marcador.exists():
        # había datos sintéticos: fuera todos, para no mezclarlos con los reales
        for p in (cfg.raw / "understat").glob("*.parquet"):
            p.unlink()
        marcador.unlink()
        # y el modelo xG entrenado con ellos: se reentrena con los datos reales
        (RAIZ / "models" / "xg.joblib").unlink(missing_ok=True)
    temporadas = [cfg.temporada_actual] if solo_actual else cfg.todas_las_temporadas
    fallos: list[str] = []
    (cfg.raw / "fallos.txt").unlink(missing_ok=True)
    for t in temporadas:
        cerrada = t != cfg.temporada_actual
        if cerrada and not forzar and all(ruta(cfg, tb, t).exists() for tb in TABLAS):
            log.info("Understat %s: ya en disco", t)
            continue
        try:
            descargar_temporada(cfg, t, forzar=forzar)
        except Exception as e:  # una fuente caída no debe tumbar todo el pipeline
            log.exception("Fallo descargando %s", t)
            fallos.append(f"understat {t}: {e}")
    if fallos:
        (cfg.raw / "fallos.txt").write_text("\n".join(fallos), encoding="utf-8")


def leer(cfg: Config, tabla: str) -> pd.DataFrame:
    """Concatena una tabla cruda de todas las temporadas disponibles en disco."""
    partes = []
    for t in cfg.todas_las_temporadas:
        p = ruta(cfg, tabla, t)
        if p.exists():
            df = pd.read_parquet(p)
            if len(df):
                partes.append(df)
    if not partes:
        raise FileNotFoundError(
            f"No hay datos crudos de '{tabla}'. Ejecuta `rma ingesta` o `rma muestra`."
        )
    return pd.concat(partes, ignore_index=True)
