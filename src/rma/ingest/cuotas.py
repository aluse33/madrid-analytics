"""Cuotas de las casas de apuestas para LaLiga (football-data.co.uk), como referencia del mercado.

Se usan solo para evaluar el modelo: la probabilidad implícita de las cuotas de cierre es el
listón más exigente que hay (el mercado agrega mucha información). No se publican las cuotas:
solo métricas agregadas de comparación.

    descargar(cfg)          -> data/raw/cuotas/SP1_<temporada>.csv (las cerradas, una sola vez)
    probabilidades(cfg)     -> DataFrame(fecha, local, visitante, m_local, m_empate, m_visitante, fuente)
"""

from __future__ import annotations

import io
import logging
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from rma.config import Config, codigo_temporada

log = logging.getLogger(__name__)

URL = "https://www.football-data.co.uk/mmz4281/{codigo}/SP1.csv"
# nombres de football-data -> nombres de Understat (los canónicos de la web)
ALIAS = {
    "Ath Bilbao": "Athletic Club", "Ath Madrid": "Atletico Madrid", "Betis": "Real Betis", "Celta": "Celta Vigo",
    "Espanol": "Espanyol", "La Coruna": "Deportivo La Coruna", "Sociedad": "Real Sociedad",
    "Vallecano": "Rayo Vallecano", "Valladolid": "Real Valladolid", "Huesca": "SD Huesca", "Oviedo": "Real Oviedo",
    "Santander": "Racing Santander", "Racing": "Racing Santander", "Sp Gijon": "Sporting Gijon",
}
# de mejor a peor: Pinnacle al cierre, media del mercado al cierre, Pinnacle, media, Bet365
FUENTES = [("PSCH", "PSCD", "PSCA"), ("AvgCH", "AvgCD", "AvgCA"), ("PSH", "PSD", "PSA"),
           ("AvgH", "AvgD", "AvgA"), ("B365H", "B365D", "B365A")]


def _dir(cfg: Config) -> Path:
    d = cfg.raw / "cuotas"
    d.mkdir(parents=True, exist_ok=True)
    return d


def descargar(cfg: Config) -> None:
    d = _dir(cfg)
    for t in cfg.todas_las_temporadas:
        cod = codigo_temporada(t)
        ruta = d / f"SP1_{cod}.csv"
        if ruta.exists() and t != cfg.temporada_actual:
            continue
        r = requests.get(URL.format(codigo=cod), timeout=30, headers={"User-Agent": "Mozilla/5.0 (minuto-90)"})
        if r.status_code == 404:
            log.info("Cuotas %s: aún no publicadas", t)
            continue
        r.raise_for_status()
        ruta.write_bytes(r.content)
        time.sleep(0.5)


def leer_csv(texto: str | bytes) -> pd.DataFrame:
    """Un SP1.csv -> probabilidades implícitas sin margen (normalización proporcional)."""
    if isinstance(texto, bytes):
        texto = texto.decode("latin-1")
    df = pd.read_csv(io.StringIO(texto), on_bad_lines="skip")
    df = df.dropna(subset=["HomeTeam", "AwayTeam", "Date"])
    filas = []
    for _, r in df.iterrows():
        for cols in FUENTES:
            if all(c in df.columns for c in cols):
                o = pd.to_numeric(pd.Series([r[c] for c in cols]), errors="coerce").to_numpy(float)
                if np.all(np.isfinite(o)) and np.all(o > 1):
                    inv = 1 / o
                    p = inv / inv.sum()
                    filas.append({"fecha": pd.to_datetime(r["Date"], dayfirst=True, errors="coerce"),
                                  "local": ALIAS.get(r["HomeTeam"].strip(), r["HomeTeam"].strip()),
                                  "visitante": ALIAS.get(r["AwayTeam"].strip(), r["AwayTeam"].strip()),
                                  "m_local": p[0], "m_empate": p[1], "m_visitante": p[2], "fuente": cols[0]})
                    break
    return pd.DataFrame(filas, columns=["fecha", "local", "visitante", "m_local", "m_empate", "m_visitante", "fuente"])


def probabilidades(cfg: Config) -> pd.DataFrame:
    partes = [leer_csv(f.read_bytes()) for f in sorted(_dir(cfg).glob("SP1_*.csv"))]
    partes = [p for p in partes if len(p)]
    return pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()


def cruzar(partidos: pd.DataFrame, mercado: pd.DataFrame) -> pd.DataFrame:
    """Añade m_local/m_empate/m_visitante a `partidos` (local, visitante, fecha) por equipos y fecha (±2 días)."""
    out = partidos.copy()
    for c in ("m_local", "m_empate", "m_visitante"):
        out[c] = np.nan
    if mercado is None or mercado.empty:
        return out
    m = mercado.dropna(subset=["fecha"])
    claves = m.groupby(["local", "visitante"])
    grupos = {k: g for k, g in claves}
    for i, r in out.iterrows():
        g = grupos.get((r.local, r.visitante))
        if g is None:
            continue
        f = pd.Timestamp(r.fecha).tz_localize(None).normalize() if pd.Timestamp(r.fecha).tzinfo else pd.Timestamp(r.fecha).normalize()
        dif = (g.fecha - f).abs()
        j = dif.idxmin()
        if dif[j] <= pd.Timedelta(days=2):
            out.loc[i, ["m_local", "m_empate", "m_visitante"]] = g.loc[j, ["m_local", "m_empate", "m_visitante"]].to_numpy(float)
    return out
