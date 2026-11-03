import numpy as np
import pandas as pd

from rma import rivales
from rma.ingest import cuotas
from rma.models import registro


def test_rps_valores_conocidos():
    p = np.array([[1, 0, 0], [0.5, 0.3, 0.2], [1 / 3, 1 / 3, 1 / 3]])
    r = registro.rps(p, np.array([0, 2, 1]))
    assert r[0] == 0
    assert np.isclose(r[1], 0.5 * (0.5**2 + 0.8**2))
    assert np.isclose(r[2], 0.5 * ((1 / 3) ** 2 + (1 / 3) ** 2))


def test_registro_se_congela_al_empezar():
    base = {"game_id": 1, "rival": "Valencia", "condicion": "Visitante", "p_victoria": 0.5, "p_empate": 0.3,
            "p_derrota": 0.2, "goles_esperados_rm": 1.8, "goles_esperados_rival": 1.0}
    f = pd.Timestamp("2026-11-07 20:00", tz="UTC")
    r1 = registro.actualizar(None, [{**base, "fecha": f}], f - pd.Timedelta(days=2))
    r2 = registro.actualizar(r1, [{**base, "fecha": f, "p_victoria": 0.6}], f - pd.Timedelta(hours=5))
    assert len(r2) == 1 and r2.p_victoria.iloc[0] == 0.6           # antes del partido: se reescribe
    r3 = registro.actualizar(r2, [{**base, "fecha": f, "p_victoria": 0.9}], f + pd.Timedelta(hours=3))
    assert r3.p_victoria.iloc[0] == 0.6                              # después: congelada
    rm = pd.DataFrame({"game_id": [1], "gf": [2], "gc": [1], "xgf": [1.9], "xgc": [0.8], "jugado": [True]})
    ev = registro.evaluar(r3, rm, base=np.array([0.45, 0.27, 0.28]))
    assert ev.resultado.iloc[0] == "V" and ev.acierto.iloc[0] == 1
    # visitante: el ingenuo en perspectiva del Madrid es (visitante, empate, local)
    assert np.allclose(ev[["b_victoria", "b_empate", "b_derrota"]].iloc[0], [0.28, 0.27, 0.45])


def test_calibracion_y_diebold_mariano():
    rng = np.random.default_rng(0)
    P = rng.dirichlet([2, 1, 1.5], 3000)
    y = np.array([rng.choice(3, p=p) for p in P])
    cal = registro.calibracion(P, y)
    assert all(abs(c["predicho"] - c["observado"]) < 0.06 for c in cal if c["n"] > 200)
    dm = registro.diebold_mariano(registro.rps(P, y), registro.rps(np.full_like(P, 1 / 3), y))
    assert dm["dif"] < 0 and dm["p"] < 0.01


def test_cuotas_csv_y_cruce():
    csv = ("Div,Date,HomeTeam,AwayTeam,PSCH,PSCD,PSCA,B365H,B365D,B365A\n"
           "SP1,07/11/2026,Valencia,Real Madrid,4.50,4.00,1.80,4.4,4.0,1.8\n"
           "SP1,08/11/2026,Ath Madrid,Betis,1.70,3.80,5.50,,,\n")
    m = cuotas.leer_csv(csv.encode())
    assert list(m.local) == ["Valencia", "Atletico Madrid"] and m.visitante.iloc[1] == "Real Betis"
    assert np.allclose(m[["m_local", "m_empate", "m_visitante"]].sum(1), 1)
    assert m.m_visitante.iloc[0] > 0.5
    p = pd.DataFrame({"local": ["Valencia"], "visitante": ["Real Madrid"], "fecha": [pd.Timestamp("2026-11-07 20:00", tz="UTC")]})
    assert cuotas.cruzar(p, m).m_visitante.notna().all()


def test_rejilla_rival_orientacion():
    # tiros cerca de la portería y por la izquierda del atacante (y alta) -> arriba a la izquierda
    g = rivales.rejilla_medio(np.array([100.0, 99.0]), np.array([60.0, 58.0]))
    fila, col = divmod(g.index(100), rivales.NU)
    assert fila <= 1 and col <= 2
