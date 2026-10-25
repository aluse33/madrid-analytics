"""Carga de `config.yaml` y rutas del proyecto."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

RAIZ = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Config:
    equipo: str
    liga: str
    temporada_actual: str
    temporadas_historicas: tuple[str, ...]
    modelos: dict[str, Any]
    raw: Path
    processed: Path

    @property
    def todas_las_temporadas(self) -> list[str]:
        return [*self.temporadas_historicas, self.temporada_actual]


@lru_cache
def cargar(ruta: str | Path | None = None) -> Config:
    ruta = Path(ruta) if ruta else RAIZ / "config.yaml"
    with open(ruta, encoding="utf-8") as f:
        c = yaml.safe_load(f)
    raw = RAIZ / c["rutas"]["raw"]
    processed = RAIZ / c["rutas"]["processed"]
    raw.mkdir(parents=True, exist_ok=True)
    processed.mkdir(parents=True, exist_ok=True)
    return Config(
        equipo=c["equipo"],
        liga=c["liga"],
        temporada_actual=str(c["temporada_actual"]),
        temporadas_historicas=tuple(str(t) for t in c["temporadas_historicas"]),
        modelos=c["modelos"],
        raw=raw,
        processed=processed,
    )


def codigo_temporada(t: str) -> str:
    """'2026-2027' -> '2627', el código que devuelve soccerdata en la columna `season`."""
    a, b = t.split("-")
    return a[-2:] + b[-2:]


def etiqueta_temporada(codigo: str) -> str:
    """'2627' -> '2026/27'."""
    codigo = str(codigo)
    return f"20{codigo[:2]}/{codigo[2:]}"
