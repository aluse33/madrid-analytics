"""Fotos de los jugadores del Madrid, de Wikipedia (Wikimedia Commons, licencias libres).

ESPN da una dirección de foto para cada jugador, pero casi nunca existe la imagen. Wikipedia
tiene foto de casi todos los del primer equipo. Para cada nombre se busca su artículo y solo
se acepta si la descripción corta dice que es futbolista: mejor sin foto que con la de otro.

Se guarda en data/raw/fotos/wikipedia.json y cada jugador se vuelve a mirar como mucho una vez al
mes (los que no tienen foto, una vez a la semana).
"""

from __future__ import annotations

import json
import logging
import time
import unicodedata
from datetime import UTC, datetime

import pandas as pd
import requests

from rma.config import Config

log = logging.getLogger(__name__)

API = "https://en.wikipedia.org/w/api.php"
CABECERAS = {"User-Agent": "minuto-90/1.0 (proyecto personal; https://github.com/aluse33/madrid-analytics)"}
DIAS_CON_FOTO, DIAS_SIN_FOTO = 30, 7


def _ruta(cfg: Config):
    d = cfg.raw / "fotos"
    d.mkdir(parents=True, exist_ok=True)
    return d / "wikipedia.json"


def _es_futbolista(pagina: dict) -> bool:
    desc = (pagina.get("description") or "").lower()
    return any(p in desc for p in ("footballer", "football player", "soccer player", "goalkeeper"))


def _llano(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def _coincide(nombre: str, titulo: str | None) -> bool:
    """El título del artículo tiene que llevar el apellido (o el nombre único: 'Rodrygo')."""
    if not titulo:
        return False
    apellido = _llano(nombre).split()[-1]
    return apellido in _llano(titulo).replace("(", " ").split()


def buscar(nombre: str) -> dict:
    """Mejor artículo de Wikipedia para un futbolista. Devuelve {} si no hay uno fiable."""
    r = requests.get(API, headers=CABECERAS, timeout=30, params={
        "action": "query", "format": "json", "formatversion": 2,
        "generator": "search", "gsrsearch": f"{nombre} footballer", "gsrlimit": 3,
        "prop": "pageimages|description", "piprop": "thumbnail|name", "pithumbsize": 400,
    })
    r.raise_for_status()
    paginas = sorted(r.json().get("query", {}).get("pages", []), key=lambda p: p.get("index", 99))
    for p in paginas:
        if _es_futbolista(p) and p.get("thumbnail") and _coincide(nombre, p["title"]):
            return {"titulo": p["title"], "foto": p["thumbnail"]["source"], "archivo": p.get("pageimage"),
                    "descripcion": p.get("description")}
    return {}


def descargar(cfg: Config, nombres: list[str]) -> None:
    ruta = _ruta(cfg)
    cache = json.loads(ruta.read_text()) if ruta.exists() else {}
    ahora = datetime.now(UTC)
    nuevos = 0
    for n in sorted(set(nombres)):
        c = cache.get(n)
        if c and (not c.get("foto") or _coincide(n, c.get("titulo"))):
            edad = (ahora - datetime.fromisoformat(c["mirado"])).days
            if edad < (DIAS_CON_FOTO if c.get("foto") else DIAS_SIN_FOTO):
                continue
        try:
            cache[n] = buscar(n) | {"mirado": ahora.isoformat(timespec="seconds")}
            nuevos += 1
            time.sleep(0.3)
        except requests.RequestException:
            log.warning("Wikipedia: sin respuesta para %s", n, exc_info=True)
    ruta.write_text(json.dumps(cache, ensure_ascii=False, indent=1))
    con = sum(1 for v in cache.values() if v.get("foto"))
    log.info("Fotos: %d consultadas, %d de %d jugadores con foto", nuevos, con, len(cache))


def nombres_madrid(cfg: Config) -> list[str]:
    """Jugadores de esta temporada: los de Understat (si ya están procesados) y la plantilla de ESPN."""
    out = []
    jp = cfg.processed / "jugadores_partido.parquet"
    if jp.exists():
        from rma.config import codigo_temporada, etiqueta_temporada

        d = pd.read_parquet(jp, columns=["equipo", "jugador", "temporada"])
        temp = etiqueta_temporada(codigo_temporada(cfg.temporada_actual))
        out += d[(d.equipo == cfg.equipo) & (d.temporada == temp)].jugador.unique().tolist()
    pl = cfg.raw / "espn" / "plantilla.json"
    if pl.exists():
        for a in json.loads(pl.read_text()).get("athletes", []):
            for x in a.get("items", [a]):
                if x.get("displayName"):
                    out.append(x["displayName"])
    return out


def tabla(cfg: Config) -> pd.DataFrame:
    ruta = _ruta(cfg)
    if not ruta.exists():
        return pd.DataFrame()
    filas = [{"nombre": n, "foto": v["foto"], "pagina": v.get("titulo"), "archivo": v.get("archivo"), "fuente": "wikipedia"}
             for n, v in json.loads(ruta.read_text()).items() if v.get("foto") and _coincide(n, v.get("titulo"))]
    return pd.DataFrame(filas)
