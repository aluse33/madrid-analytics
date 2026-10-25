"""Escudos de los equipos para la web.

Fuente: https://github.com/luukhopman/football-logos (PNG 139x181 por temporada).
Los escudos son marcas de cada club; aquí se usan solo para identificar a los equipos
en una web personal sin ánimo de lucro.

- Los PNG viven en `assets/escudos/<slug>.png` (versionados en el repo).
- `descargar_faltan` baja los que falten (p. ej. un recién ascendido).
- `generar_modulo` los copia a la web y escribe `web/src/equipos/equipos.js`, que la web
  importa para pintar escudo, nombre y abreviatura de cada equipo.
"""

from __future__ import annotations

import json
import logging
import shutil
import urllib.parse
import urllib.request
from collections.abc import Iterable

from rma.config import RAIZ
from rma.process.normalize import EQUIPOS, slug

log = logging.getLogger(__name__)

ASSETS = RAIZ / "assets" / "escudos"
WEB = RAIZ / "web" / "src" / "equipos"
BASE = "https://raw.githubusercontent.com/luukhopman/football-logos/master"
CARPETAS = [
    "logos/Spain - LaLiga",
    *[f"history/{t}/Spain - LaLiga" for t in ("2025-26", "2024-25", "2023-24", "2022-23", "2021-22")],
]


def descargar_faltan(equipos: Iterable[str] | None = None) -> list[str]:
    """Descarga los escudos que no estén en assets/. Devuelve los que no se encontraron."""
    ASSETS.mkdir(parents=True, exist_ok=True)
    faltan = []
    for canon in equipos or EQUIPOS:
        e = EQUIPOS.get(canon)
        destino = ASSETS / f"{slug(canon)}.png"
        if destino.exists():
            continue
        if not e or not e.logo:
            faltan.append(canon)
            continue
        for carpeta in CARPETAS:
            url = f"{BASE}/{urllib.parse.quote(carpeta)}/{urllib.parse.quote(e.logo)}.png"
            try:
                with urllib.request.urlopen(url, timeout=20) as r:
                    destino.write_bytes(r.read())
                log.info("Escudo descargado: %s", canon)
                break
            except Exception:
                continue
        else:
            faltan.append(canon)
    return faltan


def generar_modulo(equipos: Iterable[str]) -> None:
    """Copia los escudos de `equipos` a la web y escribe el módulo JS con sus datos."""
    if WEB.exists():
        shutil.rmtree(WEB)
    WEB.mkdir(parents=True)
    datos, adjuntos = {}, []
    for canon in sorted(set(equipos)):
        e = EQUIPOS.get(canon)
        info = {"nombre": e.nombre if e else canon, "corto": e.corto if e else canon[:3].upper()}
        png = ASSETS / f"{slug(canon)}.png"
        if png.exists():
            shutil.copy(png, WEB / png.name)
            # FileAttachment necesita rutas literales para que Framework copie el fichero
            adjuntos.append(f'  {json.dumps(canon, ensure_ascii=False)}: FileAttachment("./{png.name}"),')
        datos[canon] = info

    js = f"""// GENERADO por rma.escudos: no editar a mano (se sobrescribe en cada `rma salidas`).
import {{FileAttachment}} from "observablehq:stdlib";
import {{html}} from "npm:htl";

export const EQUIPOS = {json.dumps(datos, ensure_ascii=False, indent=1)};

const ADJUNTOS = {{
{chr(10).join(adjuntos)}
}};

const iniciales = (n) => n.split(/\\s+/).filter((p) => /^[A-ZÁÉÍÓÚ]/.test(p)).map((p) => p[0]).join("").slice(0, 2) || n[0];

// URL del escudo; si no hay, un círculo con las iniciales (como hace la web de referencia)
export function escudoUrl(equipo) {{
  const a = ADJUNTOS[equipo];
  if (a) return a.href;
  const t = iniciales(nombre(equipo));
  return "data:image/svg+xml," + encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40"><circle cx="20" cy="20" r="18" fill="#8a8f98"/>` +
    `<text x="20" y="25" text-anchor="middle" font-family="sans-serif" font-size="14" font-weight="700" fill="white">${{t}}</text></svg>`
  );
}}

export const nombre = (equipo) => EQUIPOS[equipo]?.nombre ?? equipo;
export const corto = (equipo) => EQUIPOS[equipo]?.corto ?? String(equipo).slice(0, 3).toUpperCase();

// <img> del escudo
export const escudo = (equipo, size = 22) =>
  html`<img class="escudo" src=${{escudoUrl(equipo)}} alt="" width=${{size}} height=${{size}} style="height:${{size}}px;width:auto">`;

// escudo + nombre en línea (tablas, listas)
export const conEscudo = (equipo, size = 18) =>
  html`<span class="con-escudo">${{escudo(equipo, size)}}<span>${{nombre(equipo)}}</span></span>`;
"""
    (WEB / "equipos.js").write_text(js, encoding="utf-8")

    # El CSS no puede cargar PNG en Framework: el escudo del Madrid (barra lateral) va incrustado
    import base64
    rm = ASSETS / "real-madrid.png"
    url = f"url(data:image/png;base64,{base64.b64encode(rm.read_bytes()).decode()})" if rm.exists() else "none"
    (WEB / "marca.css").write_text(f":root {{ --escudo-rm: {url}; }}\n", encoding="utf-8")
