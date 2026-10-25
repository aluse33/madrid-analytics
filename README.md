# Real Madrid Analytics

Web de análisis del Real Madrid en LaLiga con modelos estadísticos y de *machine learning*, que se actualiza sola tras cada jornada.

- **Python** para todo lo que es datos y modelos (`src/rma`).
- **Observable Framework** para la web (`web/`): páginas en Markdown con gráficos de Observable Plot. La web solo lee JSON y CSV ya calculados, así que se publica como sitio estático en cualquier sitio.
- **GitHub Actions** descarga, recalcula y publica cada mañana.

## Qué hay dentro

| Página | Qué enseña | Modelo |
|---|---|---|
| Resumen | Puntos, xG partido a partido, temporada actual frente a las anteriores, probabilidad de ganar la Liga | Bootstrap; Monte Carlo |
| Partido | Mapa de tiros, xG acumulado, resultado "merecido" y "¿acierto o suerte?" | Poisson-binomial exacta |
| Jugadores | npxG/90 y xA/90 con intervalos creíbles; goles frente a npxG | Shrinkage empírico-bayesiano Gamma-Poisson con sobredispersión |
| Predicción | 1X2 y marcadores de los próximos partidos, simulación de la Liga, fuerza de cada equipo | Dixon-Coles ponderado, penalizado y con objetivo en xG |
| Laboratorio | xG propio frente al de Understat; backtest de Dixon-Coles frente a una referencia | Logística y gradient boosting con CV agrupada por partido |
| Metodología | Las fórmulas y las limitaciones | — |

## Estructura

```
config.yaml                 club, temporadas e hiperparámetros: lo único que cambia cada año
src/rma/
  ingest/understat.py       descarga con soccerdata (idempotente: solo baja lo nuevo)
  sample.py                 datos sintéticos con el mismo esquema, para trabajar sin conexión
  process/build.py          tablas limpias: metros, temporadas, npxG, puestos
  process/normalize.py      nombres canónicos de equipos entre fuentes
  models/dixon_coles.py     ajuste, predicción y backtest con origen móvil
  models/shrinkage.py       empírico-bayes con dispersión de cuasi-verosimilitud
  models/inferencia.py      Poisson-binomial y bootstrap
  models/xg_modelo.py       modelo xG propio y su evaluación
  models/simulacion.py      Monte Carlo del resto de la temporada
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

Comandos sueltos: `rma ingesta`, `rma procesar`, `rma salidas [--reentrenar-xg]`, `rma muestra`. Tests: `pytest`.

## Publicar en GitHub Pages

1. Crea un repositorio en GitHub y sube el proyecto.
2. En **Settings → Pages**, elige **Source: GitHub Actions**.
3. En **Actions**, lanza "Actualizar y publicar" a mano la primera vez. Después corre solo cada día a las 06:23 UTC.

El modelo xG se reentrena el día 1 de cada mes, o a mano desde Actions. ¿Prefieres Vercel? Importa el repo, pon `web` como directorio raíz, `npm run build` como comando y `dist` como salida. Los datos los seguirá generando GitHub Actions.

## Decisiones de modelización

- **Dixon-Coles sobre xG.** El marcador es una realización muy ruidosa de la calidad de las ocasiones. La cuasi-verosimilitud de Poisson admite un objetivo continuo, así que se ajusta sobre una mezcla `0,6·xG + 0,4·goles`. ρ se estima aparte, sobre los goles reales.
- **Penalización L2** en ataque y defensa: identifica el modelo y encoge a los recién ascendidos hacia la media.
- **Sobredispersión en el shrinkage.** El xG tiene varianza muy inferior a una Poisson (φ ≈ 0,3). Sin corregirlo, el modelo encoge muchísimo de más: en los datos sintéticos, un titular con unos 2.800 minutos pesaba un 92 % hacia la media de su puesto; con la corrección, un 27 %.
- **Evaluación siempre fuera de muestra** y frente a una referencia tonta. Si un modelo no la bate, la web lo enseña.

## Siguientes pasos

- **Más fuentes**, ya preparadas en `normalize.py`: ClubElo (`soccerdata.ClubElo`) como predictor y referencia; ESPN para Champions y Copa, que Understat no cubre; WhoScored para eventos de pase (exige Selenium y suele fallar desde servidores, mejor en local).
- **Modelos**: Dixon-Coles dinámico (fuerzas que evolucionan en el tiempo, p. ej. filtro de Kalman), priors por rol más finos que el puesto y xG con contexto si se añaden datos de eventos.
- **Web**: ficha por jugador, comparador de temporadas y escudos.

## Aviso

Proyecto personal, sin relación con el Real Madrid C.F. Los datos se obtienen de webs públicas mediante *scraping*: revisa sus condiciones de uso antes de publicar nada, cita la fuente y no redistribuyas los datos crudos.
