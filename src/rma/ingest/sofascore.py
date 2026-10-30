"""Sofascore: mapas de calor, posiciones medias, tiros con xGOT, dominio y estadísticas por jugador.

Cubre todas las competiciones (también la Champions, donde Understat no llega). Sofascore
bloquea a los clientes normales, así que se usa `curl_cffi`, que imita la huella de un Chrome.
Desde los servidores de GitHub puede que lo bloquee igualmente: por eso nada de esto tumba la
actualización y, si falla, la web conserva el último `sofascore.json` que se subió.

    descargar(cfg)                  -> data/raw/sofascore/  (un partido cerrado no se vuelve a bajar)
    salidas(cfg, web, nombres_rm)   -> web/src/data/sofascore.json

Solo se publican datos elaborados: los mapas de calor van ya suavizados en una rejilla de 5 m,
no los puntos originales.
"""

from __future__ import annotations

import json
import logging
import time
import unicodedata
from pathlib import Path

import numpy as np

from rma.config import Config

log = logging.getLogger(__name__)

API = "https://www.sofascore.com/api/v1"
ID_MADRID = 2829
# competiciones oficiales (se descartan amistosos)
OFICIALES = ("LaLiga", "UEFA Champions League", "Copa del Rey", "Supercopa", "UEFA Super Cup",
             "FIFA Club World Cup", "FIFA Intercontinental Cup")
L, A = 105.0, 68.0          # campo en metros
NX, NY = 21, 14             # rejilla del mapa de calor (5 m x 4,9 m)
SIGMA = 5.0                 # suavizado gaussiano, en metros
HORAS_CIERRE = 36           # pasado este tiempo, un partido ya no cambia y no se vuelve a bajar

# estadísticas por jugador que se publican: clave de Sofascore -> nombre corto
STATS_JUGADOR = {
    "minutesPlayed": "min", "rating": "nota", "touches": "toques",
    "totalPass": "pases", "accuratePass": "pases_ok", "keyPass": "pases_clave",
    "accurateOppositionHalfPasses": "pases_campo_rival", "totalLongBalls": "balones_largos",
    "accurateLongBalls": "balones_largos_ok", "totalCross": "centros", "accurateCross": "centros_ok",
    "expectedAssists": "xa", "bigChanceCreated": "ocasiones_creadas",
    "totalShots": "tiros", "onTargetScoringAttempt": "tiros_puerta", "goals": "goles", "goalAssist": "asistencias",
    "ballRecovery": "recuperaciones", "interceptionWon": "intercepciones", "totalTackle": "entradas",
    "wonTackle": "entradas_ganadas", "totalClearance": "despejes",
    "duelWon": "duelos_ganados", "duelLost": "duelos_perdidos", "aerialWon": "aereos_ganados",
    "aerialLost": "aereos_perdidos", "totalContest": "regates", "wonContest": "regates_ok",
    "dispossessed": "perdidas_robadas", "possessionLostCtrl": "perdidas",
    "progressiveBallCarriesCount": "conducciones_prog", "totalProgression": "progresion_m",
    "kilometersCovered": "km", "numberOfSprints": "sprints", "topSpeed": "vel_max",
    "saves": "paradas", "fouls": "faltas", "wasFouled": "faltas_recibidas",
}
SIN_CERO = {"nota", "km", "vel_max", "sprints", "paradas"}
STATS_EQUIPO = {
    "ballPossession": "posesion", "expectedGoals": "xg", "expectedGoalsOnTarget": "xgot",
    "bigChanceCreated": "ocasiones_claras", "totalShotsOnGoal": "tiros", "shotsOnGoal": "tiros_puerta",
    "touchesInOppBox": "toques_area", "finalThirdEntries": "entradas_ultimo_tercio",
    "accuratePasses": "pases_ok", "passes": "pases", "ballRecovery": "recuperaciones",
    "interceptionWon": "intercepciones", "totalTackle": "entradas", "duelWonPercent": "duelos_ganados_pct",
    "kilometersCovered": "km", "numberOfSprints": "sprints", "cornerKicks": "corners", "fouls": "faltas",
    "goalsPrevented": "goles_evitados",
}


# ---------------------------------------------------------------- descarga
def _get(ruta: str) -> dict | None:
    """GET a la API. Devuelve None si Sofascore dice 404 (dato que no existe para ese partido)."""
    from curl_cffi import requests as cr

    for intento in range(3):
        r = cr.get(f"{API}{ruta}", impersonate="chrome", timeout=25,
                   headers={"Referer": "https://www.sofascore.com/"})
        if r.status_code == 200:
            time.sleep(0.5)
            return r.json()
        if r.status_code == 404:
            return None
        if r.status_code == 403 and intento == 0:
            log.info("Sofascore: 403 en %s; reintento", ruta)
        time.sleep(2 * (intento + 1))
    raise RuntimeError(f"Sofascore {r.status_code} en {ruta}")


def _dir(cfg: Config) -> Path:
    d = cfg.raw / "sofascore" / "partidos"
    d.mkdir(parents=True, exist_ok=True)
    return d.parent


def _es_oficial(e: dict) -> bool:
    nombre = e.get("tournament", {}).get("uniqueTournament", {}).get("name") or e.get("tournament", {}).get("name", "")
    return any(o.lower() in nombre.lower() for o in OFICIALES) and "friendly" not in nombre.lower()


def _inicio_temporada(cfg: Config) -> int:
    """1 de julio del primer año de la temporada actual, en segundos Unix."""
    import datetime as dt

    anio = int(cfg.temporada_actual.split("-")[0])
    return int(dt.datetime(anio, 7, 1, tzinfo=dt.UTC).timestamp())


def descargar(cfg: Config) -> None:
    d = _dir(cfg)
    desde = _inicio_temporada(cfg)
    partidos: dict[int, dict] = {}
    for pagina in range(3):  # 30 partidos por página; con 2-3 hay de sobra para una temporada
        js = _get(f"/team/{ID_MADRID}/events/last/{pagina}") or {}
        evs = js.get("events", [])
        for e in evs:
            if e.get("startTimestamp", 0) >= desde and e.get("status", {}).get("type") == "finished" and _es_oficial(e):
                partidos[e["id"]] = e
        if not js.get("hasNextPage") or not evs or min(e.get("startTimestamp", 0) for e in evs) < desde:
            break
    (d / "calendario.json").write_text(json.dumps(sorted(partidos.values(), key=lambda e: e["startTimestamp"]),
                                                  ensure_ascii=False))
    ahora = time.time()
    nuevos = 0
    for ev, e in partidos.items():
        carpeta = d / "partidos" / str(ev)
        if (carpeta / "cerrado").exists():
            continue
        carpeta.mkdir(exist_ok=True)
        for nombre, ruta in (("alineaciones", "lineups"), ("posiciones", "average-positions"),
                             ("tiros", "shotmap"), ("dominio", "graph"), ("estadisticas", "statistics")):
            js = _get(f"/event/{ev}/{ruta}")
            if js is not None:
                (carpeta / f"{nombre}.json").write_text(json.dumps(js, ensure_ascii=False))
        lado = "home" if e["homeTeam"]["id"] == ID_MADRID else "away"
        ali = carpeta / "alineaciones.json"
        jugaron = []
        if ali.exists():
            jugaron = [p["player"]["id"] for p in json.loads(ali.read_text()).get(lado, {}).get("players", [])
                       if (p.get("statistics") or {}).get("minutesPlayed")]
        calor = {}
        for pid in jugaron:
            js = _get(f"/event/{ev}/player/{pid}/heatmap")
            if js and js.get("heatmap"):
                calor[str(pid)] = [[p["x"], p["y"]] for p in js["heatmap"]]
        (carpeta / "calor.json").write_text(json.dumps(calor))
        if ahora - e["startTimestamp"] > HORAS_CIERRE * 3600:
            (carpeta / "cerrado").touch()
        nuevos += 1
    log.info("Sofascore: %d partidos de la temporada, %d descargados ahora", len(partidos), nuevos)


# ---------------------------------------------------------------- elaboración
def rejilla(puntos, nx: int = NX, ny: int = NY, sigma: float = SIGMA) -> list[int]:
    """Puntos de Sofascore (0-100 en ambos ejes, el equipo atacando hacia x = 100) -> densidad
    suavizada con un núcleo gaussiano en una rejilla de nx x ny celdas, escalada a 0-100 (máximo = 100).
    Se devuelve fila a fila empezando por arriba (y alta), como espera Plot.raster."""
    p = np.asarray(puntos, dtype=float).reshape(-1, 2)
    if len(p) == 0:
        return []
    px, py = p[:, 0] * L / 100, p[:, 1] * A / 100
    cx = (np.arange(nx) + 0.5) * L / nx
    cy = (np.arange(ny) + 0.5) * A / ny
    kx = np.exp(-0.5 * ((cx[None, :] - px[:, None]) / sigma) ** 2)     # (n, nx)
    ky = np.exp(-0.5 * ((cy[None, :] - py[:, None]) / sigma) ** 2)     # (n, ny)
    dens = ky.T @ kx                                                    # (ny, nx)
    dens = dens[::-1]  # primera fila = la de arriba
    return np.rint(100 * dens / dens.max()).astype(int).ravel().tolist()


def _llano(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", str(s)) if unicodedata.category(c) != "Mn").lower().strip()


def emparejar(nombre: str, candidatos) -> str | None:
    """Nombre de Sofascore -> nombre de la web (Understat). Mismo nombre sin tildes; si no, mismo
    apellido; si no, una palabra larga en común. Solo si la coincidencia es única."""
    n = _llano(nombre).replace(".", "")
    cand = list(dict.fromkeys(candidatos))
    llanos = {c: _llano(c) for c in cand}
    for c, lc in llanos.items():
        if lc == n:
            return c
    ap = n.split()[-1]
    m = [c for c, lc in llanos.items() if lc.split()[-1] == ap and len(ap) > 2]
    if len(m) == 1:
        return m[0]
    pal = {w for w in n.replace("-", " ").split() if len(w) > 3 and w not in {"junior"}}
    m = [c for c, lc in llanos.items() if pal & set(lc.replace("-", " ").split())]
    return m[0] if len(m) == 1 else None


def _num(v):
    if v is None:
        return None
    return round(float(v), 3) if isinstance(v, float) else v


def partido(carpeta: Path, e: dict) -> dict:
    """Todo lo publicable de un partido, en la orientación del Madrid (ataca hacia la derecha)."""
    rm_local = e["homeTeam"]["id"] == ID_MADRID
    lado, lado_riv = ("home", "away") if rm_local else ("away", "home")
    leer = lambda n: json.loads((carpeta / f"{n}.json").read_text()) if (carpeta / f"{n}.json").exists() else {}  # noqa: E731
    ali, pos, tir, dom, est, calor = (leer(n) for n in ("alineaciones", "posiciones", "tiros", "dominio",
                                                         "estadisticas", "calor"))
    out: dict = {"sofascore_id": e["id"], "fecha": e["startTimestamp"], "rm_local": rm_local,
                 "rival": (e["awayTeam"] if rm_local else e["homeTeam"])["name"],
                 "competicion": e.get("tournament", {}).get("uniqueTournament", {}).get("name")}

    # jugadores del Madrid: estadísticas
    jugadores = []
    for p in ali.get(lado, {}).get("players", []):
        s = p.get("statistics") or {}
        if not s.get("minutesPlayed"):
            continue
        fila = {"id": p["player"]["id"], "nombre": p["player"]["name"], "corto": p["player"].get("shortName"),
                "dorsal": p.get("shirtNumber") or p["player"].get("jerseyNumber"), "pos": p.get("position"),
                "titular": not p.get("substitute")}
        # Sofascore omite los ceros; las medidas físicas y la nota, en cambio, pueden faltar de verdad
        fila.update({k2: _num(s.get(k1, None if k2 in SIN_CERO else 0)) for k1, k2 in STATS_JUGADOR.items()})
        jugadores.append(fila)
    out["jugadores"] = jugadores
    out["formacion"] = {"rm": ali.get(lado, {}).get("formation"), "rival": ali.get(lado_riv, {}).get("formation")}

    # mapas de calor del Madrid (por jugador y del equipo)
    out["calor"] = {k: rejilla(v) for k, v in calor.items() if v}
    todos = [pt for v in calor.values() for pt in v]
    out["calor_equipo"] = rejilla(todos) if todos else []

    # posiciones medias: el rival se refleja para atacar hacia la izquierda
    def medias(filas, propio):
        r = []
        for f in filas:
            x, y = f["averageX"] * L / 100, f["averageY"] * A / 100
            r.append({"id": f["player"]["id"], "nombre": f["player"].get("shortName") or f["player"]["name"],
                      "dorsal": f["player"].get("jerseyNumber"), "x": round(x if propio else L - x, 1),
                      "y": round(y if propio else A - y, 1), "toques": f.get("pointsCount")})
        return r
    titulares = {p["player"]["id"] for t in ("home", "away") for p in ali.get(t, {}).get("players", []) if not p.get("substitute")}
    out["posiciones"] = [{**f, "equipo": "rm", "titular": f["id"] in titulares} for f in medias(pos.get(lado, []), True)] + \
                        [{**f, "equipo": "rival", "titular": f["id"] in titulares} for f in medias(pos.get(lado_riv, []), False)]

    # tiros: Sofascore mide x como distancia a la portería atacada e y al revés que las posiciones
    tiros = []
    for s in tir.get("shotmap", []):
        propio = s.get("isHome") == rm_local
        c = s.get("playerCoordinates", {})
        x, y = (100 - c.get("x", 0)) * L / 100, (100 - c.get("y", 0)) * A / 100
        g = s.get("goalMouthCoordinates") or {}
        tiros.append({"equipo": "rm" if propio else "rival", "jugador": s.get("player", {}).get("name"),
                      "minuto": s.get("time"), "x": round(x if propio else L - x, 1), "y": round(y if propio else A - y, 1),
                      "xg": _num(s.get("xg")), "xgot": _num(s.get("xgot")), "resultado": s.get("shotType"),
                      "situacion": s.get("situation"), "cuerpo": s.get("bodyPart"),
                      # portería vista de frente: y de 0 a 100 de palo a palo aprox. (45-55), z altura
                      "py": _num(g.get("y")), "pz": _num(g.get("z"))})
    out["tiros"] = sorted(tiros, key=lambda t: t["minuto"] or 0)

    # dominio (presión ofensiva minuto a minuto): positivo = local; lo pasamos a positivo = Madrid
    signo = 1 if rm_local else -1
    out["dominio"] = [[g["minute"], signo * g["value"]] for g in dom.get("graphPoints", [])]

    # estadísticas de equipo (partido completo)
    eq = {}
    for per in est.get("statistics", []):
        if per.get("period") != "ALL":
            continue
        for grupo in per.get("groups", []):
            for it in grupo.get("statisticsItems", []):
                k = STATS_EQUIPO.get(it.get("key"))
                if k and k not in eq:
                    rm_v, riv_v = (it.get("homeValue"), it.get("awayValue")) if rm_local else (it.get("awayValue"), it.get("homeValue"))
                    eq[k] = [_num(rm_v), _num(riv_v)]
    out["equipo"] = eq
    return out


def salidas(cfg: Config, web: Path, escribir_json, nombres_rm=(), partidos_espn=None) -> None:
    """Escribe sofascore.json. Si no hay nada descargado, no toca el fichero que ya hubiera."""
    d = cfg.raw / "sofascore"
    cal_f = d / "calendario.json"
    if not cal_f.exists():
        log.info("Sofascore: sin datos descargados; se conserva el sofascore.json anterior")
        return
    cal = json.loads(cal_f.read_text())
    por_partido = {}
    puntos_jugador: dict[int, list] = {}
    nombre_jugador: dict[int, str] = {}
    sumas: dict[int, dict] = {}
    for e in cal:
        carpeta = d / "partidos" / str(e["id"])
        if not (carpeta / "alineaciones.json").exists():
            continue
        try:
            p = partido(carpeta, e)
        except (KeyError, ValueError, TypeError):
            log.warning("Sofascore: partido %s ilegible", e["id"], exc_info=True)
            continue
        clave = _clave_espn(e, partidos_espn)
        por_partido[clave] = p
        calor = json.loads((carpeta / "calor.json").read_text()) if (carpeta / "calor.json").exists() else {}
        for j in p["jugadores"]:
            nombre_jugador[j["id"]] = j["nombre"]
            puntos_jugador.setdefault(j["id"], []).extend(calor.get(str(j["id"]), []))
            acc = sumas.setdefault(j["id"], {"partidos": 0})
            acc["partidos"] += 1
            for k, v in j.items():
                if k in STATS_JUGADOR.values() and k not in ("nota", "vel_max") and isinstance(v, (int, float)):
                    acc[k] = acc.get(k, 0) + v
            if j.get("nota"):
                acc.setdefault("_notas", []).append(j["nota"])
            if j.get("vel_max"):
                acc["vel_max"] = max(acc.get("vel_max", 0), j["vel_max"])

    jugadores = {}
    for pid, acc in sumas.items():
        notas = acc.pop("_notas", [])
        nombre_web = emparejar(nombre_jugador[pid], nombres_rm) if nombres_rm else None
        jugadores[str(pid)] = {"nombre": nombre_jugador[pid], "nombre_web": nombre_web,
                               "nota_media": round(float(np.mean(notas)), 2) if notas else None,
                               **{k: _num(v) for k, v in acc.items()},
                               "calor": rejilla(puntos_jugador[pid]) if puntos_jugador.get(pid) else []}
    escribir_json({"rejilla": [NX, NY], "partidos": por_partido, "jugadores": jugadores}, web / "sofascore.json")
    log.info("Sofascore: %d partidos y %d jugadores en sofascore.json", len(por_partido), len(jugadores))


def _clave_espn(e: dict, partidos_espn) -> str:
    """Id de ESPN del mismo partido (mismo día, ±1), para que la web los cruce; si no, 's<id>'."""
    if partidos_espn is not None and len(partidos_espn):
        import pandas as pd

        f = pd.to_datetime(partidos_espn["fecha"], utc=True)
        t = pd.Timestamp(e["startTimestamp"], unit="s", tz="UTC")
        dif = (f - t).abs()
        i = dif.idxmin()
        if dif[i] <= pd.Timedelta(hours=30):
            return str(partidos_espn.loc[i, "id"])
    return f"s{e['id']}"
