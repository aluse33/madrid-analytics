"""ESPN: todas las competiciones del Madrid, la tabla de la Champions y el detalle de cada partido.

Understat solo cubre LaLiga y no trae alineaciones ni tarjetas. La API pública de ESPN
(la que usa su propia web) da, por partido, la cronología (goles, tarjetas, cambios), las
alineaciones con su dibujo táctico y las estadísticas de equipo.

    descargar(cfg)   -> data/raw/espn/   (un partido terminado no se vuelve a bajar)
    salidas(cfg, web) -> partidos_todas.csv, eventos.json, champions_tabla.csv
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import pandas as pd
import requests

from rma.config import Config
from rma.process.normalize import canonico

log = logging.getLogger(__name__)

API = "https://site.api.espn.com/apis/site/v2/sports/soccer"
API_TABLAS = "https://site.api.espn.com/apis/v2/sports/soccer"
ID_MADRID = 86
CABECERAS = {"User-Agent": "Mozilla/5.0 (madridismo-analitico; proyecto personal)"}
# competiciones oficiales que seguimos (los amistosos se descartan)
COMPETICIONES = {
    "esp.1": "LaLiga",
    "uefa.champions": "Champions League",
    "esp.copa_del_rey": "Copa del Rey",
    "esp.super_cup": "Supercopa de España",
    "uefa.super_cup": "Supercopa de Europa",
    "fifa.cwc": "Mundial de Clubes",
    "fifa.intercontinental_cup": "Copa Intercontinental",
}


def _dir(cfg: Config) -> Path:
    d = cfg.raw / "espn"
    (d / "partidos").mkdir(parents=True, exist_ok=True)
    return d


def _get(url: str, params: dict | None = None) -> dict:
    for intento in range(3):
        try:
            r = requests.get(url, params=params, headers=CABECERAS, timeout=30)
            r.raise_for_status()
            time.sleep(0.5)
            return r.json()
        except requests.RequestException:
            if intento == 2:
                raise
            time.sleep(3 * (intento + 1))
    raise RuntimeError("inalcanzable")


def descargar(cfg: Config) -> None:
    d = _dir(cfg)
    base = f"{API}/all/teams/{ID_MADRID}/schedule"
    (d / "calendario.json").write_text(json.dumps(_get(base)))
    (d / "proximos.json").write_text(json.dumps(_get(base, {"fixture": "true"})))
    try:
        (d / "champions_tabla.json").write_text(json.dumps(_get(f"{API_TABLAS}/uefa.champions/standings")))
    except requests.RequestException:
        log.warning("ESPN: sin tabla de la Champions", exc_info=True)
    try:  # plantilla: trae la foto de cada jugador
        (d / "plantilla.json").write_text(json.dumps(_get(f"{API}/esp.1/teams/{ID_MADRID}/roster")))
    except requests.RequestException:
        log.warning("ESPN: sin plantilla", exc_info=True)

    nuevos = 0
    for e in _eventos(d / "calendario.json"):
        if e["estado"] != "post":
            continue
        f = d / "partidos" / f"{e['id']}.json"
        if f.exists():
            continue
        try:
            f.write_text(json.dumps(_get(f"{API}/{e['liga']}/summary", {"event": e["id"]})))
            nuevos += 1
        except requests.RequestException:
            log.warning("ESPN: no se pudo bajar el partido %s", e["id"], exc_info=True)
    log.info("ESPN: %d partidos nuevos", nuevos)


# ------------------------------------------------------------------ lectura
def _eventos(ruta: Path) -> list[dict]:
    if not ruta.exists():
        return []
    out = []
    for e in json.loads(ruta.read_text()).get("events", []):
        liga = e.get("league", {}).get("slug", "")
        if liga not in COMPETICIONES:
            continue
        c = e["competitions"][0]
        eq = {x["homeAway"]: x for x in c["competitors"]}
        if set(eq) != {"home", "away"}:
            continue

        def goles(x):
            s = x.get("score")
            v = s.get("value") if isinstance(s, dict) else s
            try:
                return int(float(v))
            except (TypeError, ValueError):
                return None

        def penaltis(x):
            s = x.get("shootoutScore")
            return int(s) if s not in (None, "") else None

        logo = lambda x: (x["team"].get("logos") or [{}])[0].get("href")  # noqa: E731
        out.append({
            "id": int(e["id"]), "fecha": pd.Timestamp(e["date"]).tz_convert(None),
            "liga": liga, "competicion": COMPETICIONES[liga],
            "fase": e.get("seasonType", {}).get("name", ""),
            "local": canonico(eq["home"]["team"]["displayName"]),
            "visitante": canonico(eq["away"]["team"]["displayName"]),
            "escudo_local": logo(eq["home"]), "escudo_visitante": logo(eq["away"]),
            "goles_local": goles(eq["home"]), "goles_visitante": goles(eq["away"]),
            "penaltis_local": penaltis(eq["home"]), "penaltis_visitante": penaltis(eq["away"]),
            "estado": c["status"]["type"]["state"],  # pre / in / post
            "estadio": (c.get("venue") or {}).get("fullName"),
        })
    return out


def _minuto(clock: dict) -> tuple[float | None, str]:
    texto = (clock or {}).get("displayValue", "") or ""
    try:
        base, _, extra = texto.replace("'", "").partition("+")
        return float(base) + (float(extra) / 100 if extra else 0), texto
    except ValueError:
        return None, texto


def _tipo(t: str) -> str | None:
    if t.startswith("own-goal"):
        return "autogol"
    if t.startswith("penalty---saved") or t.startswith("penalty---missed"):
        return "penalti_fallado"
    if t.startswith("goal") or t.startswith("penalty---scored"):
        return "gol"
    if t == "yellow-card":
        return "amarilla"
    if t in ("red-card", "yellow-red-card", "second-yellow-card"):
        return "roja"
    if t == "substitution":
        return "cambio"
    return None


def detalle(js: dict) -> dict:
    """Lo que la web necesita de la ficha de un partido de ESPN."""
    eventos = []
    for e in js.get("keyEvents", []):
        tipo = _tipo(e.get("type", {}).get("type", ""))
        if tipo is None:
            continue
        minuto, texto = _minuto(e.get("clock"))
        nombres = [p["athlete"]["displayName"] for p in e.get("participants", []) if "athlete" in p]
        eventos.append({
            "tipo": tipo, "subtipo": e["type"]["type"], "minuto": minuto, "reloj": texto,
            "parte": e.get("period", {}).get("number"),
            "equipo": canonico(e["team"]["displayName"]) if e.get("team") else None,
            "jugador": nombres[0] if nombres else None,
            # gol: asistente · cambio: el que sale
            "otro": nombres[1] if len(nombres) > 1 else None,
        })
    alineaciones = []
    for r in js.get("rosters", []):
        jug = []
        for p in r.get("roster", []):
            st = {s["name"]: s.get("value") for s in p.get("stats", [])}
            jug.append({
                "id": p["athlete"].get("id"),
                "nombre": p["athlete"]["displayName"], "corto": p["athlete"].get("shortName"),
                "dorsal": p.get("jersey"), "pos": p.get("position", {}).get("abbreviation"),
                "titular": bool(p.get("starter")), "entra": bool(p.get("subbedIn")),
                "sale": bool(p.get("subbedOut")),
                "goles": int(st.get("totalGoals") or 0), "asistencias": int(st.get("goalAssists") or 0),
                "amarillas": int(st.get("yellowCards") or 0), "rojas": int(st.get("redCards") or 0),
            })
        alineaciones.append({"lado": "local" if r.get("homeAway") == "home" else "visitante",
                             "equipo": canonico(r["team"]["displayName"]), "formacion": r.get("formation"),
                             "jugadores": jug})
    stats = {}
    for t in js.get("boxscore", {}).get("teams", []):
        stats[canonico(t["team"]["displayName"])] = {s["name"]: s.get("displayValue") for s in t.get("statistics", [])}
    info = js.get("gameInfo", {})
    arbitro = next((o.get("displayName") for o in info.get("officials", [])
                    if o.get("position", {}).get("name") == "Referee"), None)
    return {"eventos": eventos, "alineaciones": alineaciones, "estadisticas": stats,
            "estadio": (info.get("venue") or {}).get("fullName"), "asistencia": info.get("attendance"),
            "arbitro": arbitro}


def tabla_champions(js: dict) -> pd.DataFrame:
    filas = []
    for grupo in js.get("children", []):
        for i, en in enumerate(grupo.get("standings", {}).get("entries", []), 1):
            s = {x["name"]: x.get("value") for x in en.get("stats", [])}
            filas.append({
                "puesto": int(s.get("rank") or (en.get("note") or {}).get("rank") or i),
                "equipo": canonico(en["team"]["displayName"]),
                "escudo": (en["team"].get("logos") or [{}])[0].get("href"),
                "pj": int(s.get("gamesPlayed") or 0), "v": int(s.get("wins") or 0),
                "e": int(s.get("ties") or 0), "d": int(s.get("losses") or 0),
                "gf": int(s.get("pointsFor") or 0), "gc": int(s.get("pointsAgainst") or 0),
                "dg": int(s.get("pointDifferential") or 0), "puntos": int(s.get("points") or 0),
            })
    return pd.DataFrame(filas).sort_values("puesto") if filas else pd.DataFrame()


FOTO = "https://a.espncdn.com/i/headshots/soccer/players/full/{}.png"


def fotos_madrid(cfg: Config, detalles: dict) -> pd.DataFrame:
    """Jugadores del Madrid con su foto de ESPN: de la plantilla si la trae, si no por su identificador."""
    filas = {}
    for det in detalles.values():
        for al in det["alineaciones"]:
            if al["equipo"] != cfg.equipo:
                continue
            for j in al["jugadores"]:
                if j.get("id"):
                    filas[j["id"]] = {"espn_id": j["id"], "nombre": j["nombre"], "dorsal": j.get("dorsal"),
                                      "foto": FOTO.format(j["id"])}
    ruta = cfg.raw / "espn" / "plantilla.json"
    if ruta.exists():
        js = json.loads(ruta.read_text())
        for a in js.get("athletes", []):
            # según la versión de la API, lista plana o agrupada por posición
            for x in a.get("items", [a]):
                if not x.get("id"):
                    continue
                f = filas.setdefault(x["id"], {"espn_id": x["id"], "nombre": x.get("displayName"),
                                               "dorsal": x.get("jersey"), "foto": FOTO.format(x["id"])})
                if (x.get("headshot") or {}).get("href"):
                    f["foto"] = x["headshot"]["href"]
    return pd.DataFrame(filas.values())


def salidas(cfg: Config, web: Path, escribir_csv, escribir_json) -> None:
    """Escribe los ficheros de la web. Si no hay datos de ESPN, no hace nada (la web lo tolera)."""
    d = cfg.raw / "espn"
    evs = {e["id"]: e for e in _eventos(d / "calendario.json") + _eventos(d / "proximos.json")}
    if not evs:
        log.warning("ESPN: no hay datos descargados; se omite")
        return
    df = pd.DataFrame(sorted(evs.values(), key=lambda e: e["fecha"]))
    for c in ("goles_local", "goles_visitante", "penaltis_local", "penaltis_visitante"):
        df[c] = df[c].astype("Int64")
    rm_local = df.local == cfg.equipo
    gf = df.goles_local.where(rm_local, df.goles_visitante)
    gc = df.goles_visitante.where(rm_local, df.goles_local)
    pf = df.penaltis_local.where(rm_local, df.penaltis_visitante)
    pc = df.penaltis_visitante.where(rm_local, df.penaltis_local)
    jugado = df.estado == "post"
    res = pd.Series("E", index=df.index).mask(gf > gc, "V").mask(gf < gc, "D")
    res = res.mask((gf == gc) & pf.notna() & (pf > pc), "V").mask((gf == gc) & pf.notna() & (pf < pc), "D")
    df["rm_local"] = rm_local
    df["rival"] = df.visitante.where(rm_local, df.local)
    df["resultado"] = res.where(jugado)
    df["jugado"] = jugado
    escribir_csv(df, web / "partidos_todas.csv")

    detalles = {}
    for f in sorted((d / "partidos").glob("*.json")):
        if int(f.stem) in evs:
            try:
                detalles[f.stem] = detalle(json.loads(f.read_text()))
            except (KeyError, ValueError):
                log.warning("ESPN: ficha ilegible %s", f.name, exc_info=True)
    escribir_json(detalles, web / "eventos.json")

    fotos = fotos_madrid(cfg, detalles)
    if not fotos.empty:
        escribir_csv(fotos, web / "jugadores_fotos.csv")

    ruta = d / "champions_tabla.json"
    tabla = tabla_champions(json.loads(ruta.read_text())) if ruta.exists() else pd.DataFrame()
    if not tabla.empty:
        escribir_csv(tabla, web / "champions_tabla.csv")
