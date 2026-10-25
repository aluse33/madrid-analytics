"""Ejecuta los modelos y escribe los ficheros que lee la web (`web/src/data/`).

La web no necesita Python para construirse: lee JSON y CSV ya calculados. Así se puede
desplegar en cualquier sitio (GitHub Pages, Vercel, Netlify) sin instalar nada científico.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from rma import escudos
from rma.config import RAIZ, Config, codigo_temporada, etiqueta_temporada
from rma.models import dixon_coles as dc
from rma.models import inferencia, shrinkage, simulacion, xg_modelo

log = logging.getLogger(__name__)
WEB = RAIZ / "web" / "src" / "data"
RUTA_MODELO_XG = RAIZ / "models" / "xg.joblib"


def _json(obj, ruta: Path) -> None:
    def conv(o):
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return None if np.isnan(o) else round(float(o), 5)
        if isinstance(o, (pd.Timestamp, datetime)):
            # Understat da las horas en UTC: se marcan con Z para que el navegador las pase a hora local
            return o.isoformat() if o.tzinfo else o.strftime("%Y-%m-%dT%H:%M") + "Z"
        if isinstance(o, np.ndarray):
            return o.tolist()
        raise TypeError(type(o))
    ruta.write_text(json.dumps(obj, ensure_ascii=False, default=conv, indent=1), encoding="utf-8")


def _csv(df: pd.DataFrame, ruta: Path) -> None:
    df = df.copy()
    for c in df.columns:  # d3.autoType solo reconoce true/false en minúsculas
        if df[c].dtype == bool:
            df[c] = df[c].map({True: "true", False: "false"})
    df.to_csv(ruta, index=False, float_format="%.4f", date_format="%Y-%m-%dT%H:%MZ")  # UTC


def generar(cfg: Config, reentrenar_xg: bool | None = None) -> None:
    WEB.mkdir(parents=True, exist_ok=True)
    muestra = (cfg.raw / "MUESTRA").exists()
    P = cfg.processed
    lp = pd.read_parquet(P / "liga_partidos.parquet")
    rm = pd.read_parquet(P / "rm_partidos.parquet")
    ti = pd.read_parquet(P / "tiros.parquet")
    jp = pd.read_parquet(P / "jugadores_partido.parquet")
    temp = etiqueta_temporada(codigo_temporada(cfg.temporada_actual))
    temp_ant = sorted(t for t in rm.temporada.unique() if t < temp)
    hoy = lp.loc[lp.jugado, "fecha"].max() + pd.Timedelta(hours=12)
    mdc = cfg.modelos["dixon_coles"]
    kw = dict(semivida_dias=mdc["semivida_dias"], l2=mdc["l2"], tipo=mdc["objetivo"],
              peso_xg=mdc["peso_xg"], anios=mdc["anios_entrenamiento"])

    # ---------------- partidos y temporadas
    _csv(rm, WEB / "rm_partidos.csv")
    # partidos de toda la Liga esta temporada: forma y clasificación de cada rival
    _csv(lp[lp.temporada == etiqueta_temporada(codigo_temporada(cfg.temporada_actual))]
         .drop(columns=["temporada"]), WEB / "liga_temporada.csv")

    # escudos de todos los equipos que aparecen (bajando los que falten, si hay red)
    equipos = set(lp.local) | set(lp.visitante)
    try:
        sin_escudo = escudos.descargar_faltan(equipos)
        if sin_escudo:
            log.info("Sin escudo (se mostrarán sus iniciales): %s", ", ".join(sorted(sin_escudo)))
    except Exception:  # sin conexión: se usan los que haya
        log.warning("No se pudieron comprobar los escudos", exc_info=True)
    escudos.generar_modulo(equipos)
    j = rm[rm.jugado].copy()
    j["dif_xg"] = j.xgf - j.xgc
    actual = j[j.temporada == temp]
    filas = []
    for t, d in j.groupby("temporada"):
        est, inf, sup = inferencia.bootstrap_ci(d.dif_xg.to_numpy())
        ppp, pinf, psup = inferencia.bootstrap_ci(d.puntos.to_numpy(float))
        filas.append({"temporada": t, "pj": len(d), "puntos_pp": ppp, "puntos_pp_inf": pinf,
                      "puntos_pp_sup": psup, "dif_xg_pp": est, "dif_xg_inf": inf, "dif_xg_sup": sup,
                      "xgf_pp": d.xgf.mean(), "xgc_pp": d.xgc.mean(), "gf_pp": d.gf.mean(),
                      "gc_pp": d.gc.mean()})
    comparativa = None
    if len(actual) >= 3 and temp_ant:
        previas = j[j.temporada.isin(temp_ant)]
        comparativa = {
            "dif_xg": inferencia.bootstrap_diferencia(actual.dif_xg, previas.dif_xg),
            "xgf": inferencia.bootstrap_diferencia(actual.xgf, previas.xgf),
            "xgc": inferencia.bootstrap_diferencia(actual.xgc, previas.xgc),
            "referencia": f"{temp_ant[0]} a {temp_ant[-1]}",
        }
    _json({"temporadas": filas, "comparativa": comparativa}, WEB / "temporadas.json")

    # ---------------- Dixon-Coles: ratings, próximos partidos, backtest, simulación
    modelo = dc.ajustar(lp, fecha_ref=hoy, **kw)
    _csv(modelo.ratings(), WEB / "ratings.csv")

    # incertidumbre de las fuerzas: deriva temporal estimada con los datos y desfase de la estimación
    deriva = simulacion.estimar_deriva(lp)
    var_desfase = simulacion.varianza_desfase(lp, hoy, mdc["semivida_dias"], mdc["anios_entrenamiento"])
    log.info("Deriva: τ² ataque %.2e/día, defensa %.2e/día; desfase %.0f días",
             deriva["tau2_ataque"], deriva["tau2_defensa"], var_desfase)

    proximos = rm[~rm.jugado].sort_values("fecha").head(5)
    preds = []
    for r in proximos.itertuples():
        local, visit = ("Real Madrid", r.rival) if r.condicion == "Local" else (r.rival, "Real Madrid")
        dias = max((r.fecha - hoy).total_seconds() / 86400, 0)
        # predictiva posterior: promedio sobre la incertidumbre de las fuerzas
        m = simulacion.matriz_predictiva(modelo, local, visit, dias, deriva, var_desfase)
        g = np.arange(m.shape[0])
        p_local, p_empate, p_visit = float(np.tril(m, -1).sum()), float(np.trace(m)), float(np.triu(m, 1).sum())
        lam, nu = float(m.sum(1) @ g), float(m.sum(0) @ g)
        rm_es_local = r.condicion == "Local"
        preds.append({
            "game_id": r.game_id, "fecha": r.fecha, "local": local, "visitante": visit,
            "condicion": r.condicion, "rival": r.rival,
            "p_victoria": p_local if rm_es_local else p_visit,
            "p_empate": p_empate,
            "p_derrota": p_visit if rm_es_local else p_local,
            "goles_esperados_rm": lam if rm_es_local else nu,
            "goles_esperados_rival": nu if rm_es_local else lam,
            "matriz": m[:7, :7],  # filas: goles del local; columnas: goles del visitante
        })
    _json({"modelo": modelo.info | {"campo": modelo.campo, "rho": modelo.rho},
           "partidos": preds}, WEB / "prediccion.json")

    # backtest: temporada anterior completa + lo que va de esta
    if temp_ant:
        desde = lp[lp.temporada == temp_ant[-1]].fecha.min()
        bt = dc.backtest(lp, desde=desde, **kw)
        resumen = (bt.groupby("temporada")[["rps_modelo", "rps_base", "logloss_modelo", "logloss_base"]]
                   .mean().reset_index().to_dict(orient="records"))
        # calibración: probabilidad predicha de victoria local vs frecuencia observada
        bt["tramo"] = pd.cut(bt.p_local, np.linspace(0, 1, 11), include_lowest=True)
        cal = (bt.groupby("tramo", observed=True)
               .agg(predicho=("p_local", "mean"), observado=("resultado", lambda s: (s == 0).mean()),
                    n=("resultado", "size")).reset_index(drop=True))
        _json({"por_temporada": resumen, "n": len(bt),
               "calibracion_local": cal.to_dict(orient="records")}, WEB / "backtest.json")

    temporada_lp = lp[lp.temporada == temp]
    if (~temporada_lp.jugado).any():
        _json(salida_simulacion(modelo, temporada_lp, proximos, deriva, var_desfase), WEB / "simulacion.json")

    # ---------------- modelo xG propio
    reentrenar = cfg.modelos["modelo_xg"]["reentrenar"] if reentrenar_xg is None else reentrenar_xg
    if reentrenar or not RUTA_MODELO_XG.exists():
        log.info("Entrenando modelo xG (%d tiros)", len(ti))
        info = xg_modelo.entrenar(ti, folds=cfg.modelos["modelo_xg"]["folds"], ruta_modelo=RUTA_MODELO_XG)
        _json({k: v for k, v in info.items() if k != "modelos"}, WEB / "xg_modelo.json")
    guardado = joblib.load(RUTA_MODELO_XG)

    ids_rm = set(rm.game_id)
    tr = ti[ti.game_id.isin(ids_rm) & ti.temporada.isin([temp, *temp_ant[-1:]])].copy()
    tr["xg_propio"] = xg_modelo.predecir(guardado["modelos"], tr, guardado["tasa_penalti"])
    cols = ["shot_id", "game_id", "temporada", "equipo", "jugador", "asistente", "minuto", "x", "y",
            "distancia", "situacion", "parte_cuerpo", "xg_understat", "xg_propio", "resultado"]
    _csv(tr[cols], WEB / "tiros_rm.csv")

    # ---------------- jugadores: partido a partido, shrinkage y finalización
    jt = jp[jp.temporada == temp]
    _csv(jt[jt.equipo == "Real Madrid"].drop(columns=["posicion"]), WEB / "jugadores_rm.csv")

    minimos = cfg.modelos["shrinkage"]["minutos_minimos_web"]
    eb = []
    campo = jt[jt.puesto != "POR"]
    for met in ("npxg", "xa"):
        r = shrinkage.shrink(campo, met).rename(columns={f"{met}_total": "total"})
        eb.append(r[r.equipo == "Real Madrid"])
    eb = pd.concat(eb, ignore_index=True)
    eb["minimo_web"] = eb.minutos >= minimos
    _csv(eb, WEB / "jugadores_eb.csv")

    fin = []
    tiros_rm_temp = ti[(ti.equipo == "Real Madrid") & (ti.temporada == temp)]
    for jugador, d in tiros_rm_temp.groupby("jugador"):
        np_ = d[d.situacion != "Penalty"]
        if len(np_) < 3:
            continue
        g = inferencia.goles_vs_xg(np_.xg_understat.to_numpy(), int(np_.es_gol.sum()))
        fin.append({"jugador": jugador, "tiros": len(np_), **g})
    _csv(pd.DataFrame(fin).sort_values("xg", ascending=False), WEB / "finalizacion.csv")

    # ---------------- estado
    _json({
        "actualizado": datetime.now(UTC).isoformat(timespec="minutes"),
        "temporada": temp, "partidos_jugados": len(actual),
        "ultimo_partido": actual.fecha.max() if len(actual) else None,
        "muestra": muestra,
        "fallos": (cfg.raw / "fallos.txt").read_text().splitlines() if (cfg.raw / "fallos.txt").exists() else [],
    }, WEB / "estado.json")


def salida_simulacion(modelo, temporada, proximos, deriva, var_desfase, n: int = 10_000) -> dict:
    """Simulación con incertidumbre, la ingenua para comparar y todo lo que pinta la página Monte Carlo."""
    clas = simulacion.clasificacion(temporada[temporada.jugado])
    # equipos seguidos jornada a jornada: el Madrid y los tres primeros de hoy
    seguidos = tuple(dict.fromkeys(["Real Madrid", *clas.equipo.head(3)]))
    clave = int(proximos.game_id.iloc[0]) if len(proximos) else None
    sim = simulacion.simular(modelo, temporada, n=n, deriva=deriva, var_desfase_dias=var_desfase,
                             seguimiento=seguidos, partido_clave=clave)
    ingenua = simulacion.simular(modelo, temporada, n=n, incertidumbre=False)

    eq = sim["equipos"]
    k = eq.index("Real Madrid")
    E = len(eq)
    campeon = sim["puestos"] == 1

    # matriz equipo × puesto final
    puestos = [{"equipo": e, "puesto": p + 1, "prob": float((sim["puestos"][:, i] == p + 1).mean())}
               for i, e in enumerate(eq) for p in range(E)]
    # distribución de puntos finales de los equipos seguidos
    dist = []
    for e in seguidos:
        v = sim["puntos"][:, eq.index(e)]
        c = np.bincount(v.astype(int))
        dist += [{"equipo": e, "puntos": int(p), "prob": float(c[p] / n)} for p in np.nonzero(c)[0]]
    # trayectorias: cuantiles por fecha y una muestra de simulaciones
    tray = {}
    if "seguimiento" in sim:
        S = sim["seguimiento"]
        q = np.quantile(S["serie"], [0.05, 0.25, 0.5, 0.75, 0.95], axis=0)  # (5, fechas, equipos)
        tray = {
            "fechas": S["fechas"],
            "equipos": S["equipos"],
            "cuantiles": [{"equipo": e, "fecha": f, "p05": q[0, t, i], "p25": q[1, t, i], "p50": q[2, t, i],
                           "p75": q[3, t, i], "p95": q[4, t, i]}
                          for i, e in enumerate(S["equipos"]) for t, f in enumerate(S["fechas"])],
            # compacto: una lista de puntos por simulación y equipo (las fechas son las de arriba)
            "muestra": [{"sim": s, "equipo": e, "puntos": S["muestra"][s, :, i].astype(int).tolist()}
                        for s in range(min(50, S["muestra"].shape[0])) for i, e in enumerate(S["equipos"])],
        }
    # convergencia del Monte Carlo: P(campeón) acumulada y su error estándar
    pasos = np.unique(np.geomspace(20, n, 60).astype(int))
    conv = []
    for e in seguidos[:3]:
        x = campeon[:, eq.index(e)].astype(float)
        acum = np.cumsum(x)
        for m in pasos:
            p = acum[m - 1] / m
            conv.append({"equipo": e, "n": int(m), "p": p, "se": float(np.sqrt(max(p * (1 - p), 1e-12) / m))})
    # lo que se juega en el próximo partido: P(título del Madrid) según su resultado
    clave_out = None
    if "clave" in sim:
        c = sim["clave"]
        rm_local = c["local"] == "Real Madrid"
        gf = c["goles_local"] if rm_local else c["goles_visitante"]
        gc = c["goles_visitante"] if rm_local else c["goles_local"]
        res = np.where(gf > gc, "V", np.where(gf == gc, "E", "D"))
        clave_out = {"local": c["local"], "visitante": c["visitante"], "condicionado": [
            {"resultado": r, "p_resultado": float((res == r).mean()),
             "p_campeon_rm": float(campeon[res == r, k].mean()) if (res == r).any() else None,
             "p_campeon_lider": float(campeon[res == r, eq.index(seguidos[1])].mean()) if (res == r).any() and len(seguidos) > 1 else None}
            for r in ("V", "E", "D")], "lider": seguidos[1] if len(seguidos) > 1 else None}
    comp = ingenua["tabla"][["equipo", "p_campeon"]].rename(columns={"p_campeon": "p_ingenua"}).merge(
        sim["tabla"][["equipo", "p_campeon"]], on="equipo")
    return {
        "tabla": sim["tabla"].to_dict(orient="records"),
        "pendientes": sim["pendientes"], "n": n,
        "rm_dist_puesto": np.bincount(sim["puestos"][:, k], minlength=E + 1)[1:] / n,
        "deriva": deriva | {"var_desfase_dias": var_desfase,
                            "sd_desfase_ataque": float(np.sqrt(deriva["tau2_ataque"] * var_desfase)),
                            "sd_200_dias_ataque": float(np.sqrt(deriva["tau2_ataque"] * 200))},
        "comparacion": comp.sort_values("p_campeon", ascending=False).head(6).to_dict(orient="records"),
        "puestos": puestos, "distribucion_puntos": dist, "trayectorias": tray,
        "convergencia": conv, "clave": clave_out,
    }
