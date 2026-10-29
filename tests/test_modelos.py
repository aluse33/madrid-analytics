"""Tests de los modelos: simular con parámetros conocidos y comprobar que se recuperan."""

import numpy as np
import pandas as pd
import pytest
from scipy.stats import binom

from rma.models import causal, inferencia, shrinkage
from rma.models import dixon_coles as dc

# ---------------------------------------------------------------- Dixon-Coles

@pytest.fixture(scope="module")
def liga_simulada():
    rng = np.random.default_rng(0)
    equipos = [f"E{i:02d}" for i in range(20)]
    ataque = rng.normal(0, 0.3, 20)
    ataque -= ataque.mean()
    defensa = rng.normal(0, 0.25, 20)
    defensa -= defensa.mean()
    mu, campo = 0.25, 0.25
    filas = []
    fecha = pd.Timestamp("2023-08-15")
    for _ in range(3):  # tres temporadas de doble vuelta
        for i in range(20):
            for j in range(20):
                if i == j:
                    continue
                lam = np.exp(mu + campo + ataque[i] + defensa[j])
                nu = np.exp(mu + ataque[j] + defensa[i])
                filas.append({"game_id": len(filas), "temporada": "x", "fecha": fecha,
                              "local": equipos[i], "visitante": equipos[j],
                              "goles_local": rng.poisson(lam), "goles_visitante": rng.poisson(nu),
                              "xg_local": lam, "xg_visitante": nu, "jugado": True})
                fecha += pd.Timedelta(hours=8)
    return pd.DataFrame(filas), ataque, defensa, campo


def test_dixon_coles_recupera_parametros(liga_simulada):
    df, ataque, defensa, campo = liga_simulada
    m = dc.ajustar(df, tipo="xg", l2=0.01, semivida_dias=1e6, anios=None)
    assert m.info["convergio"]
    assert m.campo == pytest.approx(campo, abs=0.02)        # con xG la señal es casi exacta
    assert np.corrcoef(m.ataque, ataque)[0, 1] > 0.99
    assert np.corrcoef(m.defensa, defensa)[0, 1] > 0.99


def test_dixon_coles_con_goles_es_mas_ruidoso_pero_insesgado(liga_simulada):
    df, ataque, _, campo = liga_simulada
    m = dc.ajustar(df, tipo="goals", l2=0.01, semivida_dias=1e6, anios=None)
    assert m.campo == pytest.approx(campo, abs=0.08)
    assert np.corrcoef(m.ataque, ataque)[0, 1] > 0.85
    assert abs(m.rho) < 0.15  # los datos son Poisson puros: rho ~ 0


def test_probabilidades_suman_uno(liga_simulada):
    df, *_ = liga_simulada
    m = dc.ajustar(df, anios=None)
    p = m.prob_1x2("E00", "E01")
    assert sum(p.values()) == pytest.approx(1, abs=1e-9)
    assert m.matriz("E00", "E01").sum() == pytest.approx(1)
    # un equipo desconocido (recién ascendido) cae en la media de la liga, sin romper nada
    assert sum(m.prob_1x2("Nuevo FC", "E01").values()) == pytest.approx(1, abs=1e-9)


def test_no_mira_el_futuro(liga_simulada):
    df, *_ = liga_simulada
    corte = df.fecha.iloc[500]
    m = dc.ajustar(df, fecha_ref=corte, anios=None)
    assert m.info["partidos"] == (df.fecha < corte).sum()


def test_rps_casos_conocidos():
    acierto = dc.rps(np.array([[1.0, 0, 0]]), np.array([0]))
    fallo = dc.rps(np.array([[1.0, 0, 0]]), np.array([2]))
    assert acierto[0] == 0
    assert fallo[0] == 1.0
    # predecir empate seguro cuando gana el local está a medio camino
    assert dc.rps(np.array([[0, 1.0, 0]]), np.array([0]))[0] == pytest.approx(0.5)


# ---------------------------------------------------------------- shrinkage

@pytest.fixture(scope="module")
def jugadores_simulados():
    """Tasas θ_i ~ Gamma; datos con dispersión φ < 1 (como el xG): X = φ · Poisson(θ e / φ)."""
    rng = np.random.default_rng(1)
    phi, a, b = 0.3, 6.0, 20.0  # media del prior 0,30 por 90'
    filas = []
    for i in range(300):
        theta = rng.gamma(a, 1 / b)
        for g in range(rng.integers(3, 30)):
            minutos = int(rng.choice([90, 90, 90, 70, 30, 15]))
            x = phi * rng.poisson(theta * (minutos / 90) / phi)
            filas.append({"jugador_id": i, "jugador": f"J{i}", "equipo": "X", "puesto": "DEL",
                          "game_id": g, "minutos": minutos, "xg": x, "theta": theta})
    return pd.DataFrame(filas), phi, a / b


def test_dispersion_se_estima(jugadores_simulados):
    df, phi, _ = jugadores_simulados
    assert shrinkage.dispersion(df, "xg") == pytest.approx(phi, rel=0.15)


def test_shrinkage_mejora_al_bruto(jugadores_simulados):
    df, _, media_prior = jugadores_simulados
    r = shrinkage.shrink(df, "xg")
    verdad = df.groupby("jugador_id").theta.first()
    r = r.set_index("jugador_id").join(verdad)
    ecm_bruto = ((r.bruto_p90 - r.theta) ** 2).mean()
    ecm_eb = ((r.eb_p90 - r.theta) ** 2).mean()
    assert ecm_eb < ecm_bruto  # el objetivo del shrinkage: menos error cuadrático
    assert r.prior_media_p90.iloc[0] == pytest.approx(media_prior, rel=0.1)
    # la estimación queda entre la bruta y la media del prior
    lo = np.minimum(r.bruto_p90, r.prior_media_p90) - 1e-9
    hi = np.maximum(r.bruto_p90, r.prior_media_p90) + 1e-9
    assert ((r.eb_p90 >= lo) & (r.eb_p90 <= hi)).all()
    # cobertura de los intervalos del 90 %, con margen
    cobertura = ((r.theta >= r.eb_inf) & (r.theta <= r.eb_sup)).mean()
    assert 0.8 < cobertura < 0.98


# ---------------------------------------------------------------- inferencia

def test_poisson_binomial_coincide_con_binomial():
    pmf = inferencia.poisson_binomial_pmf([0.2] * 15)
    assert np.allclose(pmf, binom.pmf(np.arange(16), 15, 0.2))
    assert pmf.sum() == pytest.approx(1)


def test_goles_vs_xg():
    r = inferencia.goles_vs_xg([0.1] * 10, 0)
    assert r["p_al_menos"] == pytest.approx(1)
    assert r["p_como_mucho"] == pytest.approx(0.9**10)
    assert inferencia.goles_vs_xg([0.1] * 10, 11)["p_al_menos"] == 0


def test_bootstrap_cubre_la_media():
    x = np.random.default_rng(3).normal(1, 1, 200)
    est, inf, sup = inferencia.bootstrap_ci(x, B=2000)
    assert inf < 1 < sup and inf < est < sup
    d = inferencia.bootstrap_diferencia(x + 5, x, B=1000)
    assert d["p_mayor_que_cero"] == 1.0


# ---------------------------------------------------------------- incertidumbre y simulación

def test_errores_sandwich_tienen_buena_cobertura(liga_simulada):
    """Con goles (Poisson) como objetivo, θ̂ ± 1,96·se debe cubrir el valor real ~95 % de las veces."""
    df, ataque, defensa, _ = liga_simulada
    m = dc.ajustar(df, tipo="goals", l2=0.01, semivida_dias=1e6, anios=None)
    n = len(m.equipos)
    se = np.sqrt(np.diag(m.cov))
    # la identificación es relativa a la media: se comparan desviaciones respecto a ella
    z_a = (m.ataque - m.ataque.mean() - (ataque - ataque.mean())) / se[2:2 + n]
    z_d = (m.defensa - m.defensa.mean() - (defensa - defensa.mean())) / se[2 + n:]
    cobertura = np.mean(np.abs(np.r_[z_a, z_d]) < 1.96)
    assert 0.8 <= cobertura <= 1.0
    assert np.all(np.linalg.eigvalsh(m.cov) > -1e-10)  # semidefinida positiva


def test_incertidumbre_ensancha_la_simulacion(liga_simulada):
    from rma.models import simulacion as sm

    df, *_ = liga_simulada
    df = df.copy()
    corte = df.fecha.iloc[len(df) // 3 * 2]
    df["jugado"] = df.fecha < corte
    df.loc[~df.jugado, ["goles_local", "goles_visitante"]] = np.nan
    temporada = df[df.fecha >= df.fecha.iloc[len(df) // 3]]
    m = dc.ajustar(df, fecha_ref=corte, anios=None)
    deriva = {"tau2_ataque": 5e-5, "tau2_defensa": 3e-5}
    fija = sm.simular(m, temporada, n=2000, incertidumbre=False)
    incierta = sm.simular(m, temporada, n=2000, deriva=deriva, var_desfase_dias=150)
    for s in (fija, incierta):
        assert s["tabla"].p_campeon.sum() == pytest.approx(1)
    ancho = lambda s: (s["tabla"].puntos_p95 - s["tabla"].puntos_p05).mean()  # noqa: E731
    assert ancho(incierta) > ancho(fija)
    # y el favorito pierde algo de seguridad
    assert incierta["tabla"].p_campeon.max() <= fija["tabla"].p_campeon.max() + 0.02


# ---------------------------------------------------------------- Inferencia causal

def test_ols_cluster_recupera_parametros():
    rng = np.random.default_rng(42)
    N, G = 300, 10
    clusters = np.repeat(np.arange(G), N // G)
    x1 = rng.normal(0, 1, N)
    x2 = rng.binomial(1, 0.5, N).astype(float)
    X = np.column_stack([x1, x2])
    beta_true = np.array([0.75, -1.20])
    
    # Error con heterocedasticidad y shock por cluster
    cluster_shocks = rng.normal(0, 0.5, G)
    e = rng.normal(0, 1.0, N) + cluster_shocks[clusters]
    y = X @ beta_true + e
    
    res = causal.ols_cluster(y, X, clusters, nombres=["x1", "x2"])
    params = {p["param"]: p for p in res["parametros"]}
    
    assert params["x1"]["coef"] == pytest.approx(0.75, abs=0.25)
    assert params["x2"]["coef"] == pytest.approx(-1.20, abs=0.35)
    # Los intervalos de confianza del 95 % deben cubrir el valor verdadero
    assert params["x1"]["ci95"][0] <= 0.75 <= params["x1"]["ci95"][1]
    assert params["x2"]["ci95"][0] <= -1.20 <= params["x2"]["ci95"][1]


def test_efectos_fijos_en_panel_desequilibrado():
    """Con rivales que aparecen un número distinto de veces y un tratamiento correlacionado con el
    rival, restar medias de rival y de temporada sesga el coeficiente; las ficticias, no."""
    rng = np.random.default_rng(7)
    filas = []
    for temporada in range(8):
        for rival in range(30):
            if rng.random() < 0.35:  # panel desequilibrado: no todos los rivales en todas las temporadas
                continue
            for _ in range(rng.integers(1, 3)):
                fe_r = rival / 10
                # el "tratamiento" se da más contra rivales flojos y en unas temporadas que en otras
                d = float(rng.random() < 0.2 + 0.5 * (rival / 30) + 0.05 * temporada)
                y = 1.0 * fe_r + 0.3 * temporada - 0.5 * d + rng.normal(0, 0.5)
                filas.append({"rival": f"R{rival}", "temporada": f"T{temporada}", "d": d, "y": y})
    df = pd.DataFrame(filas)
    res = causal.regresion_fe(df, "y", ["d"])
    (b,) = res["parametros"]
    assert b["param"] == "d"
    assert b["coef"] == pytest.approx(-0.5, abs=0.12)
    assert b["ci95"][0] <= -0.5 <= b["ci95"][1]
    assert res["cluster"] == "rival" and res["clusters"] == 30


def test_descanso_cuenta_todas_las_competiciones():
    rm = pd.DataFrame({
        "game_id": [1, 2], "temporada": ["2025/26"] * 2, "jugado": [True, True],
        "fecha": pd.to_datetime(["2025-09-13 19:00", "2025-09-20 19:00"]),
        "condicion": ["Local", "Visitante"], "rival": ["A", "B"],
        "xgf": [2.0, 1.5], "xgc": [1.0, 1.0], "gf": [2, 1], "gc": [1, 1],
    })
    # Champions el miércoles entre los dos partidos de Liga
    oficiales = pd.DataFrame({"fecha": pd.to_datetime(["2025-09-17 19:00"]), "liga": ["uefa.champions"]})
    d = causal.descansos(rm, oficiales)
    assert np.isnan(d.descanso.iloc[0])                      # primer partido: sin anterior
    assert d.descanso.iloc[1] == pytest.approx(3.0)           # no 7 días: hubo Champions
    assert d.tras_champions.iloc[1] == 1.0
    assert d.corto.iloc[1] == 1.0


def test_analisis_causal_estructura(liga_simulada):
    df, *_ = liga_simulada
    rm_df = df[df["local"] == "E00"].copy()
    rm_df["condicion"] = "Local"
    rm_df["rival"] = rm_df["visitante"]
    rm_df["gf"] = rm_df["goles_local"]
    rm_df["gc"] = rm_df["goles_visitante"]
    rm_df["xgf"] = rm_df["xg_local"]
    rm_df["xgc"] = rm_df["xg_visitante"]
    jp_sim = pd.DataFrame([
        {"game_id": gid, "equipo": "Real Madrid", "jugador": "Karim Benzema", "minutos": 90}
        for gid in rm_df["game_id"]
    ])
    res = causal.analisis_completo(df, rm_df, jp_sim)
    assert {"metodo", "localia", "descanso", "ausencias"} <= set(res)
    assert res["metodo"]["cluster"] == "rival"
