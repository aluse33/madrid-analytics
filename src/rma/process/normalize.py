"""Nombres canónicos de equipos entre fuentes.

Cada web escribe los clubes a su manera ("Atletico Madrid", "Atlético de Madrid",
"Atl. Madrid"...). Tener un nombre canónico desde el día uno evita el problema que
arrastra la web de referencia (emparejar escudos y partidos con heurísticas).

Para añadir una fuente nueva basta con meter sus variantes en ALIAS.
"""

from __future__ import annotations

import unicodedata

# canónico -> variantes conocidas (Understat, FBref, WhoScored, ESPN, ClubElo, Transfermarkt)
ALIAS: dict[str, list[str]] = {
    "Real Madrid": ["Real Madrid CF", "Real Madrid C.F.", "RealMadrid", "R. Madrid"],
    "Barcelona": ["FC Barcelona", "Barça", "Barca"],
    "Atletico Madrid": ["Atlético Madrid", "Atlético de Madrid", "Atletico", "Atl. Madrid", "Atlético"],
    "Athletic Club": ["Athletic Bilbao", "Athletic", "Ath Bilbao"],
    "Real Sociedad": ["Sociedad", "Real Sociedad de Fútbol"],
    "Real Betis": ["Betis", "Real Betis Balompié"],
    "Celta Vigo": ["Celta", "RC Celta", "Celta de Vigo"],
    "Alaves": ["Alavés", "Deportivo Alavés", "Deportivo Alaves", "CD Alaves"],
    "Rayo Vallecano": ["Rayo"],
    "Espanyol": ["RCD Espanyol", "Espanyol Barcelona"],
    "Real Oviedo": ["Oviedo"],
    "Girona": ["Girona FC"],
    "Mallorca": ["RCD Mallorca"],
    "Valencia": ["Valencia CF"],
    "Sevilla": ["Sevilla FC"],
    "Villarreal": ["Villarreal CF"],
    "Osasuna": ["CA Osasuna"],
    "Getafe": ["Getafe CF"],
    "Levante": ["Levante UD"],
    "Elche": ["Elche CF"],
}


def _clave(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return " ".join(s.lower().replace(".", " ").split())


_INDICE = {_clave(c): c for c in ALIAS} | {_clave(v): c for c, vs in ALIAS.items() for v in vs}


def canonico(nombre: str) -> str:
    """Nombre canónico si se conoce; si no, el original (y conviene añadirlo a ALIAS)."""
    if nombre is None:
        return nombre
    return _INDICE.get(_clave(str(nombre)), str(nombre))
