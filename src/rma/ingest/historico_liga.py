"""Todas las Ligas del Madrid partido a partido, desde 1929, para la curva de puntos acumulados.

- 1928/29 a 2024/25: el conjunto abierto `engsoccerdata` (James Curley), con todos los partidos
  de Primera. Es histórico, así que se baja una vez y se renueva como mucho cada 30 días.
- Desde 2025/26: Understat (lo que ya usa el resto de la web).

Para comparar épocas, todas las temporadas se cuentan con 3 puntos por victoria.
"""

from __future__ import annotations

import logging
import time

import pandas as pd
import requests

from rma.config import Config

log = logging.getLogger(__name__)

URL = "https://raw.githubusercontent.com/jalapic/engsoccerdata/master/data-raw/spain.csv"
CADUCIDAD_DIAS = 30


def _ruta(cfg: Config):
    d = cfg.raw / "historico"
    d.mkdir(parents=True, exist_ok=True)
    return d / "laliga_engsoccerdata.csv"


def descargar(cfg: Config) -> None:
    f = _ruta(cfg)
    if f.exists() and time.time() - f.stat().st_mtime < CADUCIDAD_DIAS * 86400:
        return
    r = requests.get(URL, timeout=60)
    r.raise_for_status()
    f.write_bytes(r.content)
    log.info("Histórico de LaLiga descargado (%d KB)", len(r.content) // 1024)


def _etiqueta(anio: int) -> str:
    """1968 -> '1968/69' (el mismo formato que el resto de la web)."""
    return f"{anio}/{str(anio + 1)[-2:]}"


def curvas(cfg: Config, rm_partidos: pd.DataFrame, campeonas: set[str] | None = None) -> pd.DataFrame:
    """Una fila por partido de Liga del Madrid: temporada, número de partido y puntos acumulados."""
    f = _ruta(cfg)
    filas = []
    if f.exists():
        d = pd.read_csv(f)
        d = d[(d.tier == 1) & ((d.home == cfg.equipo) | (d.visitor == cfg.equipo))].copy()
        casa = d.home == cfg.equipo
        d["temporada"] = d.Season.map(_etiqueta)
        d["fecha"] = pd.to_datetime(d.Date)
        d["rival"] = d.visitor.where(casa, d.home)
        d["gf"] = d.hgoal.where(casa, d.vgoal)
        d["gc"] = d.vgoal.where(casa, d.hgoal)
        filas.append(d[["temporada", "fecha", "rival", "gf", "gc"]])
    # lo que no está en el histórico (las temporadas más recientes) sale de Understat
    hechas = set(filas[0].temporada) if filas else set()
    u = rm_partidos[rm_partidos.jugado & ~rm_partidos.temporada.isin(hechas)]
    if len(u):
        filas.append(u[["temporada", "fecha", "rival", "gf", "gc"]])
    if not filas:
        return pd.DataFrame()
    t = pd.concat(filas, ignore_index=True)
    t["fecha"] = pd.to_datetime(t.fecha, utc=True).dt.tz_localize(None)  # mismas fechas, sin zona
    t = t.sort_values(["temporada", "fecha"])
    t["gf"] = t.gf.astype(int)
    t["gc"] = t.gc.astype(int)
    t["puntos"] = 3 * (t.gf > t.gc) + (t.gf == t.gc)
    t["n"] = t.groupby("temporada").cumcount() + 1
    t["acumulado"] = t.groupby("temporada").puntos.cumsum()
    t["campeon"] = t.temporada.isin(campeonas or set())
    return t[["temporada", "n", "fecha", "rival", "gf", "gc", "acumulado", "campeon"]]


def temporadas_campeonas(historia: dict | None) -> set[str]:
    """Ligas ganadas según el palmarés de Wikipedia ('1931–32' -> '1931/32')."""
    if not historia or not historia.get("palmares"):
        return set()
    liga = next((p for p in historia["palmares"] if p["competicion"] == "LaLiga"), None)
    if not liga:
        return set()
    out = set()
    for s in liga["temporadas"]:
        a = s.replace("–", "-").split("-")
        out.add(f"{a[0]}/{a[1][-2:]}" if len(a) == 2 else s)
    return out
