"""Nombres canónicos de equipos y jugadores entre fuentes.

Cada web escribe los clubes a su manera ("Atletico Madrid", "Atlético de Madrid",
"Atl. Madrid"...). El nombre CANÓNICO es el de Understat (sin tildes, estable) y es el
que se usa en todos los datos. Para la web hay además un nombre bonito, una abreviatura
de tres letras y el fichero de su escudo.

Para añadir un equipo (p. ej. un recién ascendido): una entrada en EQUIPOS. Para una
fuente nueva: sus variantes en `alias`.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Equipo:
    nombre: str                 # para mostrar en la web
    corto: str                  # abreviatura de 3 letras
    logo: str | None = None     # nombre del PNG en github.com/luukhopman/football-logos
    alias: tuple[str, ...] = field(default_factory=tuple)


# clave = nombre canónico (Understat)
EQUIPOS: dict[str, Equipo] = {
    "Real Madrid": Equipo("Real Madrid", "RMA", "Real Madrid", ("Real Madrid CF", "Real Madrid C.F.", "R. Madrid")),
    "Barcelona": Equipo("Barcelona", "BAR", "FC Barcelona", ("FC Barcelona", "Barça", "Barca")),
    "Atletico Madrid": Equipo("Atlético de Madrid", "ATM", "Atlético de Madrid",
                              ("Atlético Madrid", "Atlético de Madrid", "Atletico", "Atl. Madrid", "Atlético")),
    "Athletic Club": Equipo("Athletic Club", "ATH", "Athletic Bilbao", ("Athletic Bilbao", "Athletic", "Ath Bilbao")),
    "Real Sociedad": Equipo("Real Sociedad", "RSO", "Real Sociedad", ("Sociedad", "Real Sociedad de Fútbol")),
    "Real Betis": Equipo("Real Betis", "BET", "Real Betis Balompié", ("Betis", "Real Betis Balompié")),
    "Villarreal": Equipo("Villarreal", "VIL", "Villarreal CF", ("Villarreal CF",)),
    "Sevilla": Equipo("Sevilla", "SEV", "Sevilla FC", ("Sevilla FC",)),
    "Valencia": Equipo("Valencia", "VAL", "Valencia CF", ("Valencia CF",)),
    "Celta Vigo": Equipo("Celta de Vigo", "CEL", "Celta de Vigo", ("Celta", "RC Celta", "Celta de Vigo")),
    "Osasuna": Equipo("Osasuna", "OSA", "CA Osasuna", ("CA Osasuna",)),
    "Getafe": Equipo("Getafe", "GET", "Getafe CF", ("Getafe CF",)),
    "Rayo Vallecano": Equipo("Rayo Vallecano", "RAY", "Rayo Vallecano", ("Rayo",)),
    "Mallorca": Equipo("Mallorca", "MLL", "RCD Mallorca", ("RCD Mallorca",)),
    "Girona": Equipo("Girona", "GIR", "Girona FC", ("Girona FC",)),
    "Alaves": Equipo("Alavés", "ALA", "Deportivo Alavés", ("Alavés", "Deportivo Alavés", "Deportivo Alaves", "CD Alaves")),
    "Espanyol": Equipo("Espanyol", "ESP", "RCD Espanyol Barcelona", ("RCD Espanyol", "Espanyol Barcelona")),
    "Levante": Equipo("Levante", "LEV", "Levante UD", ("Levante UD",)),
    "Elche": Equipo("Elche", "ELC", "Elche CF", ("Elche CF",)),
    "Real Oviedo": Equipo("Real Oviedo", "OVI", "Real Oviedo", ("Oviedo",)),
    "Racing Santander": Equipo("Racing de Santander", "RAC", "Racing Santander", ("Racing", "Racing de Santander")),
    "Malaga": Equipo("Málaga", "MAL", "Málaga CF", ("Málaga", "Málaga CF")),
    "Deportivo La Coruna": Equipo("Deportivo de La Coruña", "DEP", "Deportivo A Coruña",
                                  ("Deportivo", "Deportivo de La Coruña", "Deportivo A Coruña", "Deportivo de A Coruna")),
    "Cadiz": Equipo("Cádiz", "CAD", "Cádiz CF", ("Cádiz", "Cádiz CF")),
    "Almeria": Equipo("Almería", "ALM", "UD Almería", ("Almería", "UD Almería")),
    "Granada": Equipo("Granada", "GRA", "Granada CF", ("Granada CF",)),
    "Leganes": Equipo("Leganés", "LEG", "CD Leganés", ("Leganés", "CD Leganés")),
    "Las Palmas": Equipo("Las Palmas", "LPA", "UD Las Palmas", ("UD Las Palmas",)),
    "Real Valladolid": Equipo("Real Valladolid", "VLL", "Real Valladolid CF", ("Valladolid", "Real Valladolid CF")),
    # sin escudo en la fuente (temporadas anteriores a 2021-22): la web pone sus iniciales
    "Eibar": Equipo("Eibar", "EIB", None, ("SD Eibar",)),
    "SD Huesca": Equipo("Huesca", "HUE", None, ("Huesca",)),
}

# Jugadores: Understat a veces usa el nombre completo o quita tildes
JUGADORES: dict[str, str] = {
    "Kylian Mbappe-Lottin": "Kylian Mbappé",
    "Brahim Diaz": "Brahim Díaz",
    "Aurelien Tchouameni": "Aurélien Tchouaméni",
    "Eder Militão": "Éder Militão",
    "Vinicius Junior": "Vinícius Júnior",
    "Álvaro Fernández": "Álvaro Carreras",  # Understat usa su primer apellido (Álvaro Fernández Carreras)
}


def _clave(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return " ".join(s.lower().replace(".", " ").split())


_INDICE = {_clave(c): c for c in EQUIPOS} | {
    _clave(v): c for c, e in EQUIPOS.items() for v in (e.nombre, *e.alias)
}


def canonico(nombre: str) -> str:
    """Nombre canónico si se conoce; si no, el original (y conviene añadirlo a EQUIPOS)."""
    if nombre is None:
        return nombre
    return _INDICE.get(_clave(str(nombre)), str(nombre))


def jugador(nombre: str) -> str:
    if nombre is None:
        return nombre
    return JUGADORES.get(str(nombre), str(nombre))


def slug(texto: str) -> str:
    """'Atletico Madrid' -> 'atletico-madrid' (nombre de fichero del escudo)."""
    return "-".join(_clave(texto).replace("'", "").split())
