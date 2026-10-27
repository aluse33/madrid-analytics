"""Línea de comandos.

    rma ingesta            descarga Understat (todas las temporadas de config.yaml) y ESPN
    rma ingesta --actual   solo la temporada en curso (lo que corre tras cada jornada)
    rma muestra            genera datos sintéticos (sin conexión)
    rma procesar           data/raw -> data/processed
    rma salidas            modelos -> web/src/data
    rma traducir           genera las páginas en inglés (web/src/en) desde las españolas
    rma todo [--muestra]   todo seguido
"""

from __future__ import annotations

import argparse
import logging
from datetime import date

from rma import config, salidas, sample
from rma.ingest import espn, historico_liga, understat, wikipedia
from rma.process import build


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="rma", description="Minuto 90")
    ap.add_argument("orden", choices=["ingesta", "muestra", "procesar", "salidas", "traducir", "todo"])
    ap.add_argument("--actual", action="store_true", help="ingesta: solo la temporada en curso")
    ap.add_argument("--muestra", action="store_true", help="todo: con datos sintéticos")
    ap.add_argument("--reentrenar-xg", action="store_true", help="fuerza a reentrenar el modelo xG")
    ap.add_argument("--hoy", type=date.fromisoformat, help="muestra: fecha de corte (AAAA-MM-DD)")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = config.cargar()
    reentrenar = True if a.reentrenar_xg else None

    if a.orden == "ingesta":
        understat.descargar(cfg, solo_actual=a.actual)
        _espn(cfg)
    elif a.orden == "muestra":
        sample.generar(cfg, hoy=a.hoy)
    elif a.orden == "procesar":
        build.construir(cfg)
    elif a.orden == "salidas":
        salidas.generar(cfg, reentrenar_xg=reentrenar)
        _traducir()
    elif a.orden == "traducir":
        _traducir()
    elif a.orden == "todo":
        if a.muestra:
            sample.generar(cfg, hoy=a.hoy)
        else:
            understat.descargar(cfg, solo_actual=False)
            _espn(cfg)
        build.construir(cfg)
        salidas.generar(cfg, reentrenar_xg=reentrenar)
        _traducir()


def _espn(cfg) -> None:
    """ESPN y Wikipedia son extras: si fallan, se avisa y se sigue con lo de Understat."""
    for nombre, f in (("ESPN", espn.descargar), ("Wikipedia", wikipedia.descargar),
                      ("Histórico de LaLiga", historico_liga.descargar)):
        try:
            f(cfg)
        except Exception:  # noqa: BLE001
            logging.getLogger("rma").warning("%s no disponible; la web usará lo último descargado", nombre, exc_info=True)


def _traducir() -> None:
    from rma.traduccion import traducir

    faltan = traducir()
    if faltan:
        raise SystemExit(
            "Faltan traducciones (actualiza src/rma/traduccion.py):\n  " + "\n  ".join(faltan))


if __name__ == "__main__":
    main()
