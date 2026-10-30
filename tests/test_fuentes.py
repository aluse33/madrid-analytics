"""ESPN y Wikipedia: lo que se puede comprobar sin conexión."""

import pandas as pd

from rma.ingest import espn, wikipedia


def test_minuto_y_tipos_espn():
    assert espn._minuto({"displayValue": "90'+4'"}) == (90.04, "90'+4'")
    assert espn._minuto({"displayValue": "14'"})[0] == 14
    assert espn._tipo("goal---header") == "gol"
    assert espn._tipo("penalty---scored") == "gol"
    assert espn._tipo("own-goal") == "autogol"
    assert espn._tipo("yellow-card") == "amarilla"
    assert espn._tipo("substitution") == "cambio"
    assert espn._tipo("kickoff") is None


def test_detalle_espn():
    js = {
        "keyEvents": [
            {"type": {"type": "goal"}, "clock": {"displayValue": "9'"}, "period": {"number": 1},
             "team": {"displayName": "Real Madrid"},
             "participants": [{"athlete": {"displayName": "Jude Bellingham"}}, {"athlete": {"displayName": "Arda Güler"}}]},
            {"type": {"type": "substitution"}, "clock": {"displayValue": "64'"}, "period": {"number": 2},
             "team": {"displayName": "Atlético Madrid"},
             "participants": [{"athlete": {"displayName": "A"}}, {"athlete": {"displayName": "B"}}]},
        ],
        "rosters": [{"homeAway": "home", "team": {"displayName": "Real Madrid"}, "formation": "4-3-3",
                     "roster": [{"athlete": {"displayName": "Thibaut Courtois", "shortName": "T. Courtois"},
                                 "jersey": "1", "position": {"abbreviation": "G"}, "starter": True,
                                 "stats": [{"name": "yellowCards", "value": 1.0}]}]}],
        "boxscore": {"teams": [{"team": {"displayName": "Real Madrid"}, "statistics": [{"name": "possessionPct", "displayValue": "60"}]}]},
        "gameInfo": {"venue": {"fullName": "Santiago Bernabéu"}, "attendance": 78000,
                     "officials": [{"displayName": "Árbitro", "position": {"name": "Referee"}}]},
    }
    d = espn.detalle(js)
    gol, cambio = d["eventos"]
    assert gol == {"tipo": "gol", "subtipo": "goal", "minuto": 9.0, "reloj": "9'", "parte": 1,
                   "equipo": "Real Madrid", "jugador": "Jude Bellingham", "otro": "Arda Güler"}
    assert cambio["equipo"] == "Atletico Madrid"  # nombre canónico
    assert d["alineaciones"][0]["jugadores"][0]["amarillas"] == 1
    assert d["estadisticas"]["Real Madrid"]["possessionPct"] == "60"
    assert d["arbitro"] == "Árbitro"


def test_limpieza_wikipedia():
    assert wikipedia._limpio("La Liga[340]") == "La Liga"
    assert wikipedia._limpio("2nd†") == "2nd"
    assert wikipedia._entero("31‡[n 32]") == 31
    assert wikipedia._entero("—") is None
    assert wikipedia._entero("1,147") == 1147


def test_tabla_por_columnas_wikipedia():
    t = pd.DataFrame({"Type": ["Domestic"], "Competition": ["La Liga[1]"], "Titles": ["36"], "Seasons": ["1931–32, 2023–24"]})
    p = wikipedia.palmares([pd.DataFrame({"x": [1]}), t])
    assert p == [{"tipo": "Nacional", "competicion_en": "La Liga", "competicion": "LaLiga", "titulos": 36,
                  "compartido": False, "temporadas": ["1931–32", "2023–24"]}]


def test_fotos_solo_futbolistas():
    from rma.ingest import fotos

    assert fotos._es_futbolista({"description": "French footballer (born 1998)"})
    assert fotos._es_futbolista({"description": "Belgian association football goalkeeper"})
    assert not fotos._es_futbolista({"description": "Spanish politician"})
    assert not fotos._es_futbolista({})


def test_fotos_coincide_apellido():
    from rma.ingest.fotos import _coincide

    assert _coincide("Raúl Asencio", "Raúl Asencio (footballer, born 2003)")
    assert _coincide("Rodrygo", "Rodrygo")
    assert not _coincide("Jorge Cestero", "Manuel Ángel")
    assert not _coincide("Dean Huijsen", None)


def test_sofascore_rejilla_y_nombres():
    from rma.ingest import sofascore as so

    # todos los puntos en el área rival, por la banda derecha (y baja) -> el máximo cae ahí
    g = so.rejilla([[95, 10]] * 20 + [[90, 15]] * 10)
    assert len(g) == so.NX * so.NY and max(g) == 100
    fila, col = divmod(g.index(100), so.NX)
    assert col >= so.NX - 3          # cerca de la portería rival (derecha)
    assert fila >= so.NY - 3         # filas de abajo = banda derecha del Madrid
    assert so.rejilla([]) == []
    web = ["Vinícius Júnior", "Kylian Mbappé", "Trent Alexander-Arnold", "Éder Militão", "Arda Güler"]
    assert so.emparejar("Vinícius Jr.", web) == "Vinícius Júnior"
    assert so.emparejar("Eder Militao", web) == "Éder Militão"
    assert so.emparejar("T. Alexander-Arnold", web) == "Trent Alexander-Arnold"
    assert so.emparejar("Antonio Rüdiger", web) is None
