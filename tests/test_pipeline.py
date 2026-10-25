"""De datos sintéticos a ficheros de la web, en un directorio temporal."""

import json
from datetime import date

import pandas as pd
import pytest

from rma import config, salidas, sample
from rma.process import build
from rma.process.normalize import canonico


@pytest.fixture(scope="module")
def entorno(tmp_path_factory):
    raiz = tmp_path_factory.mktemp("rma")
    cfg = config.Config(
        equipo="Real Madrid", liga="ESP-La Liga", temporada_actual="2026-2027",
        temporadas_historicas=("2024-2025", "2025-2026"),
        modelos=config.cargar().modelos | {"modelo_xg": {"reentrenar": True, "folds": 3}},
        raw=raiz / "raw", processed=raiz / "processed",
    )
    cfg.raw.mkdir()
    cfg.processed.mkdir()
    sample.generar(cfg, hoy=date(2026, 10, 25))
    tablas = build.construir(cfg)
    return cfg, tablas, raiz


def test_tablas_procesadas(entorno):
    _, t, _ = entorno
    lp, rm, ti = t["liga_partidos"], t["rm_partidos"], t["tiros"]
    assert lp.game_id.is_unique
    assert set(rm.resultado.dropna()) <= {"V", "E", "D"}
    assert (rm.groupby("temporada").size() == 38).all()
    # coordenadas en metros dentro del campo y penaltis reconocidos
    assert ti.x.between(0, 105).all() and ti.y.between(0, 68).all()
    assert (ti.situacion == "Penalty").any() and ti.situacion.notna().all()
    # los goles de los tiros cuadran con el marcador (en los sintéticos no hay autogoles)
    goles = ti.groupby("game_id").es_gol.sum()
    marcador = lp.set_index("game_id").pipe(lambda d: d.goles_local + d.goles_visitante)
    assert (goles == marcador.loc[goles.index]).all()
    # npxG nunca supera al xG (salvo redondeo: Understat redondea cada tiro y cada total a 4 decimales)
    jp = t["jugadores_partido"]
    assert (jp.npxg <= jp.xg + 1e-3).all()


def test_salidas_web(entorno, monkeypatch):
    cfg, _, raiz = entorno
    web = raiz / "web"
    monkeypatch.setattr(salidas, "WEB", web)
    monkeypatch.setattr(salidas, "RUTA_MODELO_XG", raiz / "xg.joblib")
    salidas.generar(cfg)
    esperados = {"estado.json", "rm_partidos.csv", "temporadas.json", "ratings.csv",
                 "prediccion.json", "backtest.json", "simulacion.json", "xg_modelo.json",
                 "tiros_rm.csv", "jugadores_rm.csv", "jugadores_eb.csv", "finalizacion.csv"}
    assert esperados <= {p.name for p in web.iterdir()}

    estado = json.loads((web / "estado.json").read_text())
    assert estado["muestra"] is True  # el aviso de datos sintéticos no se puede perder

    pred = json.loads((web / "prediccion.json").read_text())
    for p in pred["partidos"]:
        assert p["p_victoria"] + p["p_empate"] + p["p_derrota"] == pytest.approx(1, abs=1e-6)

    sim = json.loads((web / "simulacion.json").read_text())
    assert sum(r["p_campeon"] for r in sim["tabla"]) == pytest.approx(1, abs=1e-6)

    xg = json.loads((web / "xg_modelo.json").read_text())
    # cualquier modelo xG razonable tiene que batir a predecir la tasa media
    assert xg["metricas_cv"]["boosting"]["log_loss"] < xg["metricas_cv"]["tasa_base"]["log_loss"]

    # booleanos en minúsculas para que d3.autoType los entienda
    assert set(pd.read_csv(web / "rm_partidos.csv", dtype=str).jugado) <= {"true", "false"}


def test_nombres_canonicos():
    assert canonico("Atlético de Madrid") == "Atletico Madrid"
    assert canonico("Athletic Bilbao") == "Athletic Club"
    assert canonico("Real Madrid CF") == "Real Madrid"
    assert canonico("Club Desconocido") == "Club Desconocido"
