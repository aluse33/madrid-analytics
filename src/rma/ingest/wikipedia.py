"""Wikipedia: el histórico del club (palmarés, temporadas, Europa, finales, entrenadores, récords).

Se baja con la API de MediaWiki (una petición por página, como mucho una vez por semana) y se
convierte en un único `historia.json` para la página Histórico. Los textos de Wikipedia son
CC BY-SA: la página lo cita.
"""

from __future__ import annotations

import io
import json
import logging
import re
import time
import warnings
from pathlib import Path

import pandas as pd
import requests

from rma.config import Config

log = logging.getLogger(__name__)

API = "https://{}.wikipedia.org/w/api.php"
CABECERAS = {"User-Agent": "madridismo-analitico/1.0 (proyecto personal; https://github.com/aluse33/madrid-analytics)"}
PAGINAS = {
    "club": ("en", "Real Madrid CF"),
    "temporadas": ("en", "List of Real Madrid CF seasons"),
    "entrenadores": ("en", "List of Real Madrid CF managers"),
    "europa": ("en", "Real Madrid CF in international football"),
    "records": ("en", "List of Real Madrid CF records and statistics"),
    "clasico": ("en", "El Clásico"),
    "derbi": ("en", "Madrid derby"),
    "finales": ("en", "List of European Cup and UEFA Champions League finals"),
}
CADUCIDAD_DIAS = 7


def _dir(cfg: Config) -> Path:
    d = cfg.raw / "wikipedia"
    d.mkdir(parents=True, exist_ok=True)
    return d


def descargar(cfg: Config, forzar: bool = False) -> None:
    d = _dir(cfg)
    for clave, (idioma, titulo) in PAGINAS.items():
        f = d / f"{clave}.json"
        if not forzar and f.exists() and time.time() - f.stat().st_mtime < CADUCIDAD_DIAS * 86400:
            continue
        r = requests.get(API.format(idioma), headers=CABECERAS, timeout=30, params={
            "action": "parse", "page": titulo, "prop": "text", "format": "json", "formatversion": 2, "redirects": 1})
        r.raise_for_status()
        f.write_text(r.text)
        time.sleep(1)
    log.info("Wikipedia al día")


# ------------------------------------------------------------------ limpieza
def _tablas(ruta: Path) -> list[pd.DataFrame]:
    html = json.loads(ruta.read_text())["parse"]["text"]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return pd.read_html(io.StringIO(html))


def _limpio(x) -> str | None:
    """Quita notas [n 3], [12], marcas †*‡ y espacios raros."""
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    s = re.sub(r"\[[^\]]*\]", "", str(x))
    s = s.replace("​", "").replace("\xa0", " ")
    s = re.sub(r"[†*‡§]", "", s).strip()
    return s or None


def _entero(x) -> int | None:
    s = _limpio(x)
    if s is None:
        return None
    m = re.match(r"^-?\d+", s.replace(",", "").replace("−", "-"))
    return int(m.group()) if m else None


def _plano(df: pd.DataFrame) -> pd.DataFrame:
    """Columnas MultiIndex -> 'nivel1|nivel2' limpias."""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ["|".join(dict.fromkeys(_limpio(c) or "" for c in col)) for col in df.columns]
    else:
        df.columns = [_limpio(c) or "" for c in df.columns]
    return df


def _buscar(tablas, *columnas) -> pd.DataFrame:
    """La primera tabla que tenga todas esas columnas (los índices cambian cuando editan la página)."""
    for t in tablas:
        t = _plano(t.copy())
        cols = " ".join(t.columns)
        if all(c in cols for c in columnas):
            return t
    raise LookupError(f"Wikipedia: no encuentro una tabla con {columnas}")


def _col(df: pd.DataFrame, *trozos: str) -> str:
    """Columna cuyo primer nivel es exactamente trozos[0] (y que contiene el resto), o si no la que contenga todos."""
    for c in df.columns:
        if c.split("|")[0] == trozos[0] and all(t in c for t in trozos[1:]):
            return c
    for c in df.columns:
        if all(t in c for t in trozos):
            return c
    raise LookupError(trozos)


# ------------------------------------------------------------------ partes
COMPETICIONES = {
    "La Liga": "LaLiga", "Copa del Rey": "Copa del Rey", "Copa de la Liga": "Copa de la Liga",
    "Supercopa de España": "Supercopa de España", "Copa Eva Duarte": "Copa Eva Duarte",
    "European Cup/UEFA Champions League": "Copa de Europa / Champions League",
    "UEFA Cup/UEFA Europa League": "Copa de la UEFA", "UEFA Super Cup": "Supercopa de Europa",
    "Latin Cup": "Copa Latina", "Ibero-American Cup": "Copa Iberoamericana",
    "FIFA Club World Cup": "Mundial de Clubes", "Intercontinental Cup": "Copa Intercontinental",
    "FIFA Intercontinental Cup": "Copa Intercontinental de la FIFA",
    "Campeonato de Madrid/Campeonato Regional Centro": "Campeonato Regional", "Copa Federación Centro": "Copa Federación Centro",
}
TIPOS = {"Domestic": "Nacional", "Continental": "Europeo", "Intercontinental": "Intercontinental",
         "Worldwide": "Mundial", "Regional": "Regional"}


def palmares(tablas) -> list[dict]:
    t = _buscar(tablas, "Competition", "Titles", "Seasons")
    out = []
    for r in t.itertuples(index=False):
        comp = _limpio(r[1])
        out.append({"tipo": TIPOS.get(_limpio(r[0]), _limpio(r[0])), "competicion_en": comp,
                    "competicion": COMPETICIONES.get(comp, comp), "titulos": _entero(r[2]),
                    "compartido": str(r[2]).strip().endswith("s"),
                    "temporadas": [s.strip() for s in (_limpio(r[3]) or "").split(",") if s.strip()]})
    return out


def temporadas(tablas) -> list[dict]:
    t = _buscar(tablas, "Season", "Pld", "Pts", "Pos")
    c = lambda *x: _col(t, *x)  # noqa: E731
    out = []
    for _, r in t.iterrows():
        temp = _limpio(r[c("Season")])
        if not temp or not re.match(r"^\d{4}", temp):
            continue
        pos_txt = _limpio(r[c("Pos")])
        division = _limpio(r[c("Division")]) or ""
        # temporadas con dos torneos en la misma celda (Liga + Regional): los números vienen pegados
        mezcla = "La Liga" in division and division != "La Liga"
        out.append({
            "temporada": temp, "division": "La Liga" if mezcla else division,
            "pj": _entero(r[c("Pld")]), "v": _entero(r[c("W")]), "e": _entero(r[c("D")]),
            "d": _entero(r[c("L")]), "gf": _entero(r[c("GF")]), "gc": _entero(r[c("GA")]),
            "puntos": _entero(r[c("Pts")]), "puesto": _entero(pos_txt),
            "mezcla": mezcla,
            "copa": _limpio(r[c("CdR")]),
            "europa": _limpio(r[c("Competition", "Europe")]), "europa_ronda": _limpio(r[c("Result", "Europe")]),
            "goleador": _limpio(r[c("Player")]), "goles_goleador": _entero(r[c("Goals")]),
        })
    for x in out:  # en las mezcladas solo vale el puesto
        if x.pop("mezcla"):
            x.update(pj=None, v=None, e=None, d=None, gf=None, gc=None, puntos=None)
    return out


def europa(tablas) -> list[dict]:
    t = _buscar(tablas, "Season", "Round", "Opposition", "Score")
    return [{"temporada": _limpio(r[0]), "ronda": _limpio(r[1]), "rival": _limpio(r[2]), "marcador": _limpio(r[3])}
            for r in t.itertuples(index=False) if _limpio(r[3])]


def europa_resumen(tablas) -> list[dict]:
    t = _buscar(tablas, "Competition", "Played", "Won", "Drew", "Lost")
    return [{"competicion": _limpio(r[0]), "pj": _entero(r[1]), "v": _entero(r[2]), "e": _entero(r[3]),
             "d": _entero(r[4]), "gf": _entero(r[5]), "gc": _entero(r[6])} for r in t.itertuples(index=False)]


def finales(tablas) -> list[dict]:
    t = _buscar(tablas, "Season", "Winners", "Score", "Runners-up", "Venue")
    out = []
    for _, r in t.iterrows():
        g, p = _limpio(r["Winners"]), _limpio(r["Runners-up"])
        if "Real Madrid" not in (g or "") + (p or ""):
            continue
        partes = [x.strip() for x in (_limpio(r["Venue"]) or "").split(",")]
        out.append({"temporada": _limpio(r["Season"]), "gano": g == "Real Madrid",
                    "rival": p if g == "Real Madrid" else g, "marcador": _limpio(r["Score"]),
                    "estadio": partes[0] if partes else None, "ciudad": partes[1] if len(partes) > 1 else None,
                    "pais": partes[-1] if len(partes) > 2 else None,
                    "publico": _entero(r[_col(t, "Attendance")])})
    return out


def entrenadores(tablas) -> list[dict]:
    t = _buscar(tablas, "Manager", "From", "To", "W", "Honours")
    out = []
    for _, r in t.iterrows():
        nombre = _limpio(r["Manager"])
        if not nombre or nombre == "Manager":
            continue
        out.append({"nombre": nombre, "desde": _limpio(r["From"]), "hasta": _limpio(r["To"]),
                    "pj": _entero(r[_col(t, "G")]), "v": _entero(r["W"]), "e": _entero(r["D"]), "d": _entero(r["L"]),
                    "gf": _entero(r["GF"]), "gc": _entero(r["GA"]), "titulos": _limpio(r["Honours"])})
    return out


def entrenadores_titulos(tablas) -> list[dict]:
    t = _buscar(tablas, "Rank", "Manager", "LL", "UCL", "Total")
    return [{"nombre": _limpio(r["Manager"]), "liga": _entero(r["LL"]) or 0, "copa": _entero(r["CdR"]) or 0,
             "champions": _entero(r["UCL"]) or 0, "total": _entero(r["Total"])} for _, r in t.iterrows()]


def records(tablas) -> dict:
    out = {}
    ap = _buscar(tablas, "Rank", "Player", "Years", "League", "Total")
    out["partidos"] = [{"jugador": _limpio(r["Player"]), "anios": _limpio(r["Years"]), "total": _entero(r["Total"])}
                       for _, r in ap.iterrows()]
    gol = _buscar(tablas, "Rank", "Player", "Years", "Total", "Ratio")
    out["goles"] = [{"jugador": _limpio(r["Player"]), "anios": _limpio(r["Years"]), "goles": _entero(r["Total"]),
                     "partidos": _entero(re.sub(r"^.*\(", "", str(r["Total"]))), "ratio": float(_limpio(r["Ratio"]) or 0)}
                    for _, r in gol.iterrows()]
    return out


def cara_a_cara(tablas, rival: str) -> list[dict]:
    """Resumen por competición del Clásico o del derbi (las tablas tienen formatos distintos)."""
    t = _buscar(tablas, "Competition", "Matches")
    cols = list(t.columns)
    vic = [c for c in cols if "Wins" in c or "wins" in c]
    gol = [c for c in cols if "Goals" in c or "goals" in c]
    rm_v = next(c for c in vic if "RMA" in c or "Real Madrid" in c)
    ri_v = next(c for c in vic if c != rm_v)
    rm_g = next(c for c in gol if "RMA" in c or "Real Madrid" in c)
    ri_g = next(c for c in gol if c != rm_g)
    emp = next(c for c in cols if "Draws" in c)
    out = []
    for _, r in t.iterrows():
        comp = _limpio(r[cols[0]])
        if comp is None or "Exhibition" in comp or comp == "All matches":
            continue
        out.append({"rival": rival, "competicion": comp, "pj": _entero(r[_col(t, "Matches")]),
                    "v": _entero(r[rm_v]), "e": _entero(r[emp]), "d": _entero(r[ri_v]),
                    "gf": _entero(r[rm_g]), "gc": _entero(r[ri_g])})
    return out


def historia(cfg: Config) -> dict | None:
    d = cfg.raw / "wikipedia"
    if not (d / "club.json").exists():
        return None
    T = {k: _tablas(d / f"{k}.json") for k in PAGINAS if (d / f"{k}.json").exists()}
    out: dict = {"actualizado": pd.Timestamp((d / "club.json").stat().st_mtime, unit="s").strftime("%Y-%m-%d")}
    partes = {
        "palmares": lambda: palmares(T["club"]),
        "temporadas": lambda: temporadas(T["temporadas"]),
        "europa": lambda: europa(T["europa"]),
        "europa_resumen": lambda: europa_resumen(T["europa"]),
        "finales": lambda: finales(T["finales"]),
        "entrenadores": lambda: entrenadores(T["entrenadores"]),
        "entrenadores_titulos": lambda: entrenadores_titulos(T["entrenadores"]),
        "records": lambda: records(T["records"]),
        "cara_a_cara": lambda: cara_a_cara(T["clasico"], "Barcelona") + cara_a_cara(T["derbi"], "Atletico Madrid"),
    }
    for clave, f in partes.items():
        try:
            out[clave] = f()
        except (LookupError, KeyError, ValueError, StopIteration):
            # si editan una tabla de Wikipedia, esa sección falta pero el resto sigue
            log.warning("Wikipedia: no se pudo leer '%s'", clave, exc_info=True)
            out[clave] = None
    return out
