"""Modelo xG propio, entrenado con todos los tiros de LaLiga.

Dos modelos y una referencia:
- logístico: distancia, log-distancia, ángulo, cabeza y situación; interpretable;
- gradient boosting (HistGradientBoosting): captura interacciones (p. ej. ángulo × cabeza);
- Understat: su xG publicado, como referencia externa.

La validación cruzada agrupa por PARTIDO (GroupKFold): los tiros de un mismo partido no
son independientes y mezclarlos entre entrenamiento y test inflaría las métricas.
Los penaltis se quedan fuera del modelo y reciben su tasa de conversión empírica.

Métricas: log-loss y Brier (calibración + discriminación), AUC (solo discriminación)
y ECE (error de calibración esperado, 10 tramos).
"""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

NUM = ["distancia", "log_distancia", "angulo", "cabeza"]
SITUACIONES = ["Open Play", "From Corner", "Set Piece", "Direct Freekick"]
CAT = ["situacion"]


def rasgos(t: pd.DataFrame) -> pd.DataFrame:
    X = t[["distancia", "angulo", "cabeza", "situacion", "x", "y"]].copy()
    X["log_distancia"] = np.log1p(X.distancia)
    X["cabeza"] = X.cabeza.astype(float)
    X["situacion"] = X.situacion.astype(str)
    return X


def modelos() -> dict[str, Pipeline]:
    pre_lin = ColumnTransformer([
        ("num", StandardScaler(), NUM),
        # "Open Play" como referencia: los coeficientes de situación se leen frente a juego abierto
        ("cat", OneHotEncoder(categories=[SITUACIONES], drop="first", handle_unknown="ignore"), CAT),
    ])
    pre_gb = ColumnTransformer([
        ("num", "passthrough", NUM + ["x", "y"]),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CAT),
    ])
    return {
        "logistico": Pipeline([("pre", pre_lin), ("m", LogisticRegression(max_iter=2000))]),
        "boosting": Pipeline([("pre", pre_gb), ("m", HistGradientBoostingClassifier(
            learning_rate=0.05, max_iter=400, max_leaf_nodes=15, min_samples_leaf=80,
            l2_regularization=1.0, early_stopping=True, validation_fraction=0.1, random_state=0,
        ))]),
    }


def ece(y, p, tramos: int = 10) -> float:
    q = np.quantile(p, np.linspace(0, 1, tramos + 1))
    b = np.clip(np.searchsorted(q, p, side="right") - 1, 0, tramos - 1)
    err = 0.0
    for k in range(tramos):
        m = b == k
        if m.any():
            err += m.mean() * abs(y[m].mean() - p[m].mean())
    return float(err)


def fiabilidad(y, p, tramos: int = 10) -> pd.DataFrame:
    """Tabla para el diagrama de fiabilidad: xG medio predicho vs tasa de gol observada."""
    q = np.unique(np.quantile(p, np.linspace(0, 1, tramos + 1)))
    b = np.clip(np.searchsorted(q, p, side="right") - 1, 0, len(q) - 2)
    d = pd.DataFrame({"y": y, "p": p, "b": b})
    return d.groupby("b").agg(predicho=("p", "mean"), observado=("y", "mean"), n=("y", "size")).reset_index(drop=True)


def metricas(y, p) -> dict[str, float]:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return {"log_loss": float(log_loss(y, p)), "brier": float(brier_score_loss(y, p)),
            "auc": float(roc_auc_score(y, p)), "ece": ece(y, p)}


def entrenar(tiros: pd.DataFrame, folds: int = 5, ruta_modelo: Path | None = None) -> dict:
    sin_pen = tiros[tiros.situacion != "Penalty"].reset_index(drop=True)
    pen = tiros[tiros.situacion == "Penalty"]
    tasa_penalti = float(pen.es_gol.mean()) if len(pen) else 0.76

    X, y, g = rasgos(sin_pen), sin_pen.es_gol.to_numpy(int), sin_pen.game_id.to_numpy()
    oof = {k: np.zeros(len(y)) for k in modelos()}
    for tr, te in GroupKFold(n_splits=folds).split(X, y, g):
        for nombre, m in modelos().items():
            m.fit(X.iloc[tr], y[tr])
            oof[nombre][te] = m.predict_proba(X.iloc[te])[:, 1]

    resultados = {nombre: metricas(y, p) for nombre, p in oof.items()}
    resultados["understat"] = metricas(y, sin_pen.xg_understat.to_numpy())
    resultados["tasa_base"] = metricas(y, np.full(len(y), y.mean()))

    tablas_fiab = {n: fiabilidad(y, p) for n, p in oof.items()}
    tablas_fiab["understat"] = fiabilidad(y, sin_pen.xg_understat.to_numpy())

    finales = {}
    for nombre, m in modelos().items():
        finales[nombre] = m.fit(X, y)
    if ruta_modelo:
        ruta_modelo.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"modelos": finales, "tasa_penalti": tasa_penalti}, ruta_modelo)

    # coeficientes del logístico (escala estandarizada): lo interpretable
    lr = finales["logistico"]
    nombres = list(lr.named_steps["pre"].get_feature_names_out())
    coefs = dict(zip(nombres, lr.named_steps["m"].coef_[0].round(4).tolist(), strict=True))

    return {
        "n_tiros": len(y), "n_penaltis": len(pen), "tasa_penalti": tasa_penalti,
        "metricas_cv": resultados,
        "fiabilidad": {k: v.to_dict(orient="records") for k, v in tablas_fiab.items()},
        "coeficientes_logistico": coefs,
        "modelos": finales,
    }


def predecir(modelos_finales: dict, tiros: pd.DataFrame, tasa_penalti: float, cual: str = "boosting") -> np.ndarray:
    p = modelos_finales[cual].predict_proba(rasgos(tiros))[:, 1]
    return np.where(tiros.situacion.to_numpy() == "Penalty", tasa_penalti, p)
