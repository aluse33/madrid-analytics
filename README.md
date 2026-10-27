# Minuto 90

Web de análisis del Real Madrid en LaLiga con modelos estadísticos y de *machine learning*, que se actualiza sola tras cada jornada.

- **Python** para todo lo que es datos y modelos (`src/rma`).
- **Observable Framework** para la web (`web/`): páginas en Markdown con gráficos de Observable Plot. La web solo lee JSON y CSV ya calculados, así que se publica como sitio estático en cualquier sitio.
- **GitHub Actions** descarga, recalcula y publica cada mañana.

## Qué hay dentro

| Página | Qué enseña | Modelo |
|---|---|---|
| Resumen | Puntos, xG partido a partido, temporada actual frente a las anteriores, probabilidad de ganar la Liga | Bootstrap; Monte Carlo |
| Partido | Alineaciones sobre el campo, cronología, estadísticas, mapa de tiros, xG acumulado, dominio cada 5 minutos, quién generó más peligro, resultado "merecido" | Poisson-binomial exacta |
| Champions League | Resultados, próximo partido, ficha de cada partido y tabla de la fase liga (solo descriptivo) | — |
| Histórico | Vitrina, títulos en el tiempo, puesto en Liga desde 1929, esta temporada frente a las campeonas, camino a cada Copa de Europa, mapa de las finales, Clásico y derbi, entrenadores y récords | — |
| Jugadores | npxG/90 y xA/90 con intervalos creíbles; goles frente a npxG | Shrinkage empírico-bayesiano Gamma-Poisson con sobredispersión |
| Ficha de jugador | Percentiles frente a su puesto en LaLiga, mapa de tiros, partido a partido y temporada a temporada | Percentiles; shrinkage EB |
| Predicción | 1X2 y marcadores de los próximos partidos, fuerza de cada equipo | Dixon-Coles ponderado, penalizado y con objetivo en xG; predictiva posterior |
| Simulación Monte Carlo | Probabilidad de título, trayectorias de puntos, quién acaba dónde, lo que vale el próximo partido | 10.000 temporadas con incertidumbre de parámetros (sándwich) y deriva de las fuerzas (paseo aleatorio estimado) |
| Laboratorio | xG propio frente al de Understat; backtest de Dixon-Coles frente a una referencia | Logística y gradient boosting con CV agrupada por partido |
| Metodología | Las fórmulas y las limitaciones | — |

## Estructura

```
config.yaml                 club, temporadas e hiperparámetros: lo único que cambia cada año
src/rma/
  ingest/understat.py       descarga con soccerdata (idempotente: solo baja lo nuevo)
  ingest/espn.py            todas las competiciones, alineaciones, cronologías y tabla de Champions (API de ESPN)
  ingest/wikipedia.py       histórico del club (palmarés, temporadas, Europa, finales, entrenadores, récords)
  sample.py                 datos sintéticos con el mismo esquema, para trabajar sin conexión
  process/build.py          tablas limpias: metros, temporadas, npxG, puestos
  process/normalize.py      nombres canónicos de equipos entre fuentes
  models/dixon_coles.py     ajuste, predicción y backtest con origen móvil
  models/shrinkage.py       empírico-bayes con dispersión de cuasi-verosimilitud
  models/inferencia.py      Poisson-binomial y bootstrap
  models/xg_modelo.py       modelo xG propio y su evaluación
  models/simulacion.py      Monte Carlo del resto de la temporada
  escudos.py                escudos de los equipos (assets/escudos) y módulo web/src/equipos
  traduccion.py             genera las páginas en inglés (web/src/en) con una tabla de traducciones
  salidas.py                ejecuta los modelos y escribe web/src/data/
  pipeline.py               línea de comandos `rma`
data/processed/             tablas limpias en Parquet (versionadas)
web/src/                    páginas .md, componentes JS y data/ (salidas del pipeline)
tests/                      tests con parámetros conocidos y del pipeline completo
.github/workflows/          actualización diaria + publicación, y tests
```

## Puesta en marcha

Requisitos: Python 3.11 o superior y Node 20 o superior.

```bash
python -m venv .venv && source .venv/bin/activate      # en Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# Opción A: datos sintéticos, sin conexión (la web muestra un aviso)
rma todo --muestra

# Opción B: datos reales de Understat (la primera vez tarda: baja varias temporadas)
rma todo

cd web
npm install
npm run dev        # abre http://127.0.0.1:3000 y recarga al editar
```

Comandos sueltos: `rma ingesta`, `rma procesar`, `rma salidas [--reentrenar-xg]`, `rma traducir`, `rma muestra`. Tests: `pytest`.

## Español e inglés

Las páginas antiguas se escriben **solo en español** (`web/src/*.md`); las nuevas (ficha de jugador, Champions, Histórico) llevan los dos idiomas dentro con `t("texto", "text")` de `formato.js`. Las inglesas (`web/src/en/`) se generan con `rma traducir` (también lo hace `rma salidas`) a partir de la tabla de `src/rma/traduccion.py`. Si cambias un texto en español, añade o corrige su par en esa tabla: si no, `rma traducir` falla diciéndote qué texto falta. Números, fechas, V/E/D → W/D/L y puestos se adaptan solos (`web/src/components/formato.js`).

## Publicar en GitHub Pages

1. Sube el proyecto a un repositorio **público** de GitHub (GitHub Pages es gratis con repositorios públicos).
2. En el repositorio: **Settings → Pages → Source: GitHub Actions**.
3. En **Actions → Actualizar y publicar → Run workflow**, lánzalo la primera vez. Descarga los datos, calcula los modelos y publica la web en `https://<tu-usuario>.github.io/<repositorio>/`.

A partir de ahí corre solo cada día a las 06:23 UTC. Cada vez que subas cambios a `main`, la web se vuelve a publicar en un par de minutos (sin descargar datos). El modelo xG se reentrena el día 1 de cada mes.

Los datos de Understat, ESPN y Wikipedia (`data/raw`, `data/processed`) **no se suben**: sus condiciones no permiten redistribuirlos. Se publican solo los resultados de los modelos que enseña la web.

## Decisiones de modelización

- **Dixon-Coles sobre xG.** El marcador es una realización muy ruidosa de la calidad de las ocasiones. La cuasi-verosimilitud de Poisson admite un objetivo continuo, así que se ajusta sobre una mezcla `0,6·xG + 0,4·goles`. ρ se estima aparte, sobre los goles reales.
- **Penalización L2** en ataque y defensa: identifica el modelo y encoge a los recién ascendidos hacia la media.
- **Sobredispersión en el shrinkage.** El xG tiene varianza muy inferior a una Poisson (φ ≈ 0,3). Sin corregirlo, el modelo encoge muchísimo de más: en los datos sintéticos, un titular con unos 2.800 minutos pesaba un 92 % hacia la media de su puesto; con la corrección, un 27 %.
- **Evaluación siempre fuera de muestra** y frente a una referencia tonta. Si un modelo no la bate, la web lo enseña.

## Siguientes pasos

- **Más fuentes**, ya preparadas en `normalize.py`: ClubElo (`soccerdata.ClubElo`) como predictor y referencia; ESPN para Champions y Copa, que Understat no cubre; WhoScored para eventos de pase (exige Selenium y suele fallar desde servidores, mejor en local).
- **Modelos**: Dixon-Coles dinámico (fuerzas que evolucionan en el tiempo, p. ej. filtro de Kalman), priors por rol más finos que el puesto y xG con contexto si se añaden datos de eventos.
- **Web**: ficha por jugador, comparador de temporadas y escudos.

## Escudos

De [luukhopman/football-logos](https://github.com/luukhopman/football-logos), guardados en `assets/escudos/` con el nombre canónico de cada equipo. Si asciende un equipo nuevo, añádelo a `EQUIPOS` en `src/rma/process/normalize.py` y `rma salidas` intentará descargar su escudo. Son marcas de cada club.

## Aviso

Proyecto personal, sin relación con el Real Madrid C.F. Los datos se obtienen de webs públicas mediante *scraping*: revisa sus condiciones de uso antes de publicar nada, cita la fuente y no redistribuyas los datos crudos.
