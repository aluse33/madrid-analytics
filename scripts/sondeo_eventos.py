"""Sondeo de fuentes de eventos (mapas de calor, pases, posiciones medias).

Se ejecuta en tu ordenador, desde la carpeta del proyecto y con el .venv activo:

    python scripts/sondeo_eventos.py            # Sofascore y WhoScored
    python scripts/sondeo_eventos.py sofascore  # solo Sofascore (rápido)

Guarda muestras en data/sondeo/eventos/ (no se sube a GitHub) para ver qué devuelve cada
fuente antes de montar nada.
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

SALIDA = Path("data/sondeo/eventos")
SALIDA.mkdir(parents=True, exist_ok=True)
RESUMEN: list[str] = []
API = "https://api.sofascore.com/api/v1"
ID_MADRID = 2829  # Real Madrid en Sofascore
CABECERAS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/130.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.sofascore.com/",
    "Origin": "https://www.sofascore.com",
}


def anotar(msg: str) -> None:
    print(msg, flush=True)
    RESUMEN.append(msg)


# ---------------------------------------------------------------- Sofascore
HOSTS = ["https://www.sofascore.com/api/v1", "https://api.sofascore.com/api/v1"]
UA_133 = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
          "Chrome/133.0.0.0 Safari/537.36")


def _m_requests(url):
    import requests

    r = requests.get(url, headers=CABECERAS, timeout=20)
    return r.status_code, (r.json() if r.status_code == 200 else None)


def _m_tls(url):
    import tls_requests

    r = tls_requests.get(url, headers={**CABECERAS, "User-Agent": UA_133}, timeout=20,
                         client_identifier="chrome_133")
    return r.status_code, (r.json() if r.status_code == 200 else None)


def _m_curl_cffi(url):
    from curl_cffi import requests as cr  # pip install curl_cffi

    r = cr.get(url, impersonate="chrome", headers={"Referer": "https://www.sofascore.com/"}, timeout=20)
    return r.status_code, (r.json() if r.status_code == 200 else None)


_NAVEGADOR = {}


def _m_navegador(url):
    """Último recurso: un Chrome de verdad (seleniumbase, modo 'undetected') abre la URL y leemos el JSON."""
    if "sb" not in _NAVEGADOR:
        from seleniumbase import SB

        _NAVEGADOR["ctx"] = SB(uc=True, headless=False)
        _NAVEGADOR["sb"] = _NAVEGADOR["ctx"].__enter__()
        _NAVEGADOR["sb"].uc_open_with_reconnect("https://www.sofascore.com/", 4)
    sb = _NAVEGADOR["sb"]
    sb.open(url)
    texto = sb.get_text("body")
    try:
        datos = json.loads(texto)
    except ValueError:
        return 0, None
    if isinstance(datos, dict) and "error" in datos:
        return datos["error"].get("code", 0), None
    return 200, datos


METODOS = {"requests": _m_requests, "tls_requests": _m_tls, "curl_cffi": _m_curl_cffi, "navegador": _m_navegador}
_GANADOR: list = []  # (host, método) que funcionó la primera vez; luego se reutiliza


def _get_sofa(ruta: str):
    if _GANADOR:
        host, nombre = _GANADOR[0]
        try:
            estado, datos = METODOS[nombre](f"{host}{ruta}")
        except Exception as e:  # noqa: BLE001
            estado, datos = repr(e)[:60], None
        return (datos, nombre) if datos is not None else (None, f"{nombre}={estado}")
    intentos = []
    for nombre, metodo in METODOS.items():
        for host in HOSTS:
            try:
                estado, datos = metodo(f"{host}{ruta}")
            except ModuleNotFoundError:
                intentos.append(f"{nombre}=no instalado")
                break
            except Exception as e:  # noqa: BLE001
                estado, datos = repr(e)[:50], None
            if datos is not None:
                _GANADOR.append((host, nombre))
                anotar(f"   -> funciona: {nombre} con {host}")
                return datos, nombre
            intentos.append(f"{nombre}@{host.split('//')[1].split('/')[0]}={estado}")
    return None, ", ".join(intentos)


def guardar(nombre: str, ruta: str):
    datos, como = _get_sofa(ruta)
    if datos is None:
        anotar(f"[FALLO] {nombre:<26} {ruta}  ({como})")
        return None
    (SALIDA / f"{nombre}.json").write_text(json.dumps(datos, ensure_ascii=False))
    anotar(f"[OK]    {nombre:<26} {ruta}  ({como}, {len(json.dumps(datos)) // 1024} KB)")
    time.sleep(0.6)
    return datos


def sofascore() -> None:
    anotar("\n== Sofascore ==")
    ultimos = guardar("sofa_ultimos", f"/team/{ID_MADRID}/events/last/0")
    if not ultimos:
        return
    jugados = [e for e in ultimos.get("events", []) if e.get("status", {}).get("type") == "finished"]
    if not jugados:
        anotar("no hay partidos terminados en la respuesta")
        return
    # el último de Liga, y si hay, el último de Champions
    def es(e, palabra):
        return palabra in (e.get("tournament", {}).get("name", "") + e.get("tournament", {}).get("uniqueTournament", {}).get("name", ""))
    elegidos = {"liga": next((e for e in reversed(jugados) if es(e, "LaLiga")), jugados[-1])}
    ucl = next((e for e in reversed(jugados) if es(e, "Champions")), None)
    if ucl:
        elegidos["champions"] = ucl
    for clave, e in elegidos.items():
        ev = e["id"]
        anotar(f"partido {clave}: {e['homeTeam']['name']} {e.get('homeScore', {}).get('current')}–"
               f"{e.get('awayScore', {}).get('current')} {e['awayTeam']['name']} (id {ev})")
        lineups = guardar(f"sofa_{clave}_alineaciones", f"/event/{ev}/lineups")
        guardar(f"sofa_{clave}_posiciones_medias", f"/event/{ev}/average-positions")
        guardar(f"sofa_{clave}_tiros", f"/event/{ev}/shotmap")
        guardar(f"sofa_{clave}_dominio", f"/event/{ev}/graph")
        guardar(f"sofa_{clave}_estadisticas", f"/event/{ev}/statistics")
        if lineups:
            lado = "home" if e["homeTeam"]["id"] == ID_MADRID else "away"
            titulares = [p for p in lineups.get(lado, {}).get("players", []) if not p.get("substitute")][:3]
            for p in titulares:
                pid = p["player"]["id"]
                guardar(f"sofa_{clave}_calor_{pid}", f"/event/{ev}/player/{pid}/heatmap")
            if titulares:
                pid = titulares[0]["player"]["id"]
                # por si existe: mapa de calor de la temporada entera del jugador
                guardar("sofa_temporadas_jugador", f"/player/{pid}/statistics/seasons")


# ---------------------------------------------------------------- WhoScored
def whoscored() -> None:
    anotar("\n== WhoScored (abre Chrome) ==")
    import soccerdata as sd

    ws = sd.WhoScored(leagues="ESP-La Liga", seasons="2627", headless=False)
    cal = ws.read_schedule().reset_index()
    rm = cal[(cal.home_team.str.contains("Real Madrid")) | (cal.away_team.str.contains("Real Madrid"))]
    import pandas as pd

    fin = rm[pd.to_datetime(rm.date, utc=True) < pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=3)]
    partido = int(fin.sort_values("date").iloc[-1].game_id)
    ev = ws.read_events(match_id=partido, output_fmt="events").reset_index()
    ev.to_parquet(SALIDA / "whoscored_eventos.parquet")
    anotar(f"WhoScored OK: {len(ev)} eventos del partido {partido}; tipos: {ev['type'].value_counts().head(8).to_dict()}")


if __name__ == "__main__":
    pasos = [sofascore, whoscored]
    for paso in pasos:
        if len(sys.argv) > 1 and paso.__name__ not in sys.argv[1:]:
            continue
        try:
            paso()
        except Exception:  # noqa: BLE001
            anotar(f"[FALLO en {paso.__name__}]\n{traceback.format_exc()[-1500:]}")
    if "ctx" in _NAVEGADOR:
        _NAVEGADOR["ctx"].__exit__(None, None, None)
    (SALIDA / "resumen.txt").write_text("\n".join(RESUMEN))
    print(f"\nListo. Todo guardado en {SALIDA.resolve()}")
