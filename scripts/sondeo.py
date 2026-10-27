"""Sondeo de fuentes nuevas: ESPN, Wikipedia y WhoScored.

Se ejecuta UNA vez en tu ordenador (desde la carpeta del proyecto, con el .venv activo):

    python scripts/sondeo.py

Guarda muestras en data/sondeo/ (no se sube a GitHub) para ver exactamente qué
devuelve cada fuente antes de meterla en el pipeline. WhoScored abre una ventana de
Chrome: no la cierres, se cierra sola al terminar.
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

import requests

SALIDA = Path("data/sondeo")
SALIDA.mkdir(parents=True, exist_ok=True)
CABECERAS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"}
RESUMEN: list[str] = []


def anotar(msg: str) -> None:
    print(msg, flush=True)
    RESUMEN.append(msg)


def bajar(nombre: str, url: str, params: dict | None = None) -> requests.Response | None:
    try:
        r = requests.get(url, params=params, headers=CABECERAS, timeout=30)
        ext = "json" if "json" in r.headers.get("content-type", "") else "html"
        (SALIDA / f"{nombre}.{ext}").write_bytes(r.content)
        anotar(f"[{r.status_code}] {nombre:<28} {len(r.content):>9,} bytes  {r.url}")
        time.sleep(1)
        return r
    except Exception as e:  # noqa: BLE001
        anotar(f"[ERROR] {nombre}: {e}")
        return None


# ---------------------------------------------------------------- ESPN
def espn() -> None:
    anotar("\n== ESPN ==")
    base = "https://site.api.espn.com/apis/site/v2/sports/soccer"
    comps = ["esp.1", "uefa.champions", "esp.copa_del_rey", "esp.super_cup", "fifa.cwc", "all"]
    ultimo = None
    for c in comps:
        r = bajar(f"espn_calendario_{c}", f"{base}/{c}/teams/86/schedule")
        bajar(f"espn_proximos_{c}", f"{base}/{c}/teams/86/schedule", {"fixture": "true"})
        if c == "uefa.champions" and r is not None and r.ok:
            jugados = [e for e in r.json().get("events", [])
                       if e["competitions"][0]["status"]["type"].get("completed")]
            if jugados:
                ultimo = jugados[-1]["id"]
    bajar("espn_clasificacion_champions", "https://site.api.espn.com/apis/v2/sports/soccer/uefa.champions/standings")
    bajar("espn_equipo", f"{base}/esp.1/teams/86")
    # ficha completa del último partido de Champions y del último de Liga
    if ultimo:
        bajar("espn_partido_champions", f"{base}/uefa.champions/summary", {"event": ultimo})
    r = requests.get(f"{base}/esp.1/teams/86/schedule", headers=CABECERAS, timeout=30)
    if r.ok:
        jugados = [e for e in r.json().get("events", [])
                   if e["competitions"][0]["status"]["type"].get("completed")]
        if jugados:
            bajar("espn_partido_liga", f"{base}/esp.1/summary", {"event": jugados[-1]["id"]})
    # temporadas anteriores (¿hasta dónde llega el histórico?)
    for anio in (2024, 2015, 2005):
        bajar(f"espn_champions_{anio}", f"{base}/uefa.champions/teams/86/schedule", {"season": anio})


# ---------------------------------------------------------------- Wikipedia
def wikipedia() -> None:
    anotar("\n== Wikipedia ==")
    api = "https://en.wikipedia.org/w/api.php"
    paginas = {
        "wiki_club": "Real Madrid CF",
        "wiki_temporadas": "List of Real Madrid CF seasons",
        "wiki_entrenadores": "List of Real Madrid CF managers",
        "wiki_europa": "Real Madrid CF in international football",
        "wiki_records": "List of Real Madrid CF records and statistics",
        "wiki_clasico": "El Clásico",
        "wiki_derbi": "Madrid derby",
        "wiki_finales_copa_europa": "List of European Cup and UEFA Champions League finals",
    }
    for nombre, titulo in paginas.items():
        bajar(nombre, api, {"action": "parse", "page": titulo, "prop": "text",
                            "format": "json", "formatversion": 2, "redirects": 1})
    es = "https://es.wikipedia.org/w/api.php"
    bajar("wikies_palmares", es, {"action": "parse", "page": "Palmarés del Real Madrid Club de Fútbol",
                                  "prop": "text", "format": "json", "formatversion": 2, "redirects": 1})


# ---------------------------------------------------------------- WhoScored
def whoscored() -> None:
    anotar("\n== WhoScored (abre Chrome, paciencia) ==")
    import soccerdata as sd

    ws = sd.WhoScored(leagues="ESP-La Liga", seasons="2627", headless=False)
    cal = ws.read_schedule()
    cal.reset_index().to_csv(SALIDA / "whoscored_calendario.csv", index=False)
    anotar(f"calendario: {len(cal)} partidos; columnas: {list(cal.columns)}")
    rm = cal.reset_index()
    rm = rm[(rm.home_team.str.contains("Real Madrid") | rm.away_team.str.contains("Real Madrid"))]
    import pandas as pd

    # jugado = empezó hace más de 3 horas
    fin = rm[pd.to_datetime(rm.date, utc=True) < pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=3)]
    if fin.empty:
        anotar("no encuentro partidos jugados del Madrid en el calendario")
        return
    partido = int(fin.sort_values("date").iloc[-1].game_id)
    anotar(f"partido de prueba: {partido}")
    ev = ws.read_events(match_id=partido, output_fmt="events")
    ev.reset_index().to_parquet(SALIDA / "whoscored_eventos.parquet")
    ev.reset_index().head(400).to_csv(SALIDA / "whoscored_eventos_muestra.csv", index=False)
    anotar(f"eventos: {len(ev)} filas; columnas: {list(ev.columns)}")
    anotar("tipos: " + ", ".join(f"{k}={v}" for k, v in ev["type"].value_counts().head(25).items()))
    crudo = ws.read_events(match_id=partido, output_fmt="raw")
    with open(SALIDA / "whoscored_crudo.json", "w") as f:
        json.dump(crudo, f, default=str)
    anotar("WhoScored OK")


if __name__ == "__main__":
    for paso in (espn, wikipedia, whoscored):
        if len(sys.argv) > 1 and paso.__name__ not in sys.argv[1:]:
            continue
        try:
            paso()
        except Exception:  # noqa: BLE001
            anotar(f"[FALLO en {paso.__name__}]\n{traceback.format_exc()}")
    (SALIDA / "resumen.txt").write_text("\n".join(RESUMEN))
    print(f"\nListo. Todo guardado en {SALIDA.resolve()}")
