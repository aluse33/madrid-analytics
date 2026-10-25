---
title: Metodología
---

# Metodología

## Datos

Todo sale de **Understat** a través de la librería de Python [soccerdata](https://github.com/probberechts/soccerdata): resultado y xG de cada partido de LaLiga, todos los tiros (posición, xG, situación, parte del cuerpo) y estadísticas por jugador y partido. Understat solo cubre las ligas, así que la Champions y la Copa no aparecen. Las coordenadas se pasan a metros en un campo de 105 × 68 m.

## Dixon-Coles con objetivo en xG

Para cada partido con local $i$ y visitante $j$:

```tex
\log \lambda_{ij} = \mu + h + a_i + d_j, \qquad \log \nu_{ij} = \mu + a_j + d_i
```

donde $a$ es la capacidad ofensiva, $d$ la fragilidad defensiva y $h$ la ventaja de campo. Los parámetros se estiman por **cuasi-verosimilitud de Poisson ponderada y penalizada**:

```tex
\max_{\mu, h, a, d} \; \sum_k w_k \left[ y_k \log \lambda_k - \lambda_k \right] - \frac{\kappa}{2}\left(\lVert a \rVert^2 + \lVert d \rVert^2\right),
\qquad w_k = 2^{-\text{edad}_k / \text{semivida}}
```

- El objetivo $y$ es una mezcla de xG y goles. La cuasi-verosimilitud de Poisson solo necesita que la media esté bien especificada, así que admite un $y$ continuo; usar xG reduce mucho la varianza, porque el marcador es una realización muy ruidosa de la calidad de las ocasiones.
- La penalización L2 identifica el modelo (sin ella se puede pasar una constante de $a$ a $d$) y encoge hacia la media de la liga a los equipos con pocos partidos.
- En un segundo paso se estima $\rho$, la corrección de Dixon y Coles (1997) para 0-0, 1-0, 0-1 y 1-1, por máxima verosimilitud sobre los goles reales.

La evaluación es **fuera de muestra con origen móvil**: cada semana se reajusta con el pasado y se predice la siguiente. La métrica principal es el *Ranked Probability Score*, que respeta el orden victoria > empate > derrota.

## Shrinkage empírico-bayesiano

Para la tasa por 90 minutos $\theta_i$ de cada jugador, con $e_i$ = minutos / 90:

```tex
\theta_i \sim \text{Gamma}(\alpha, \beta), \qquad \mathbb{E}[X_i \mid \theta_i] = \theta_i e_i, \quad \operatorname{Var}[X_i \mid \theta_i] = \phi\, \theta_i e_i
```

La posterior es conjugada y su media pondera la tasa observada y la del puesto:

```tex
\mathbb{E}[\theta_i \mid X_i] = B_i \frac{\alpha}{\beta} + (1 - B_i) \frac{X_i}{e_i}, \qquad B_i = \frac{\beta}{\beta + e_i / \phi}
```

- $(\alpha, \beta)$ se estiman por máxima verosimilitud marginal (binomial negativa) con **todos los jugadores de LaLiga del mismo puesto**.
- $\phi$ es la dispersión de Pearson dentro de cada jugador, partido a partido. Hace falta porque el xG es una suma de probabilidades pequeñas: su varianza ($\sum p_k^2$) es muy inferior a su media ($\sum p_k$), y suponer una Poisson ($\phi = 1$) haría creer al modelo que casi todo es ruido y encogería de más. En LaLiga sale $\phi \approx 0{,}3$.

## Goles frente a xG: Poisson-binomial

Si el tiro $k$ es gol con probabilidad $p_k$ (su xG), de forma independiente, el número de goles sigue una distribución Poisson-binomial, que se calcula exactamente por convolución. Con ella:

- **¿Acierto o suerte?** $P(G \ge g)$: cuán raro es marcar al menos $g$ goles con esos tiros.
- **Resultado merecido**: convolucionando las distribuciones de los dos equipos se obtiene la probabilidad de victoria, empate y derrota con esas mismas ocasiones, y los puntos esperados.

## Modelo xG propio

Regresión logística (distancia, log-distancia, ángulo de portería, cabeza, situación) y *gradient boosting* (`HistGradientBoostingClassifier`, que además usa las coordenadas). Validación cruzada agrupada por partido (`GroupKFold`). Los penaltis se excluyen y reciben su tasa de conversión empírica.

## Simulación de la temporada

Monte Carlo de los partidos pendientes: para cada uno se muestrea un marcador de la matriz de Dixon-Coles, se suman puntos y diferencia de goles y se ordena la tabla. Las fuerzas se fijan en la estimación de hoy y el desempate es por diferencia de goles (no por el golaveraje particular de LaLiga).

## Limitaciones

- Understat no da contexto de los tiros (posición de defensas y portero, tipo de pase previo), así que ningún xG basado en sus datos puede ir mucho más allá del suyo.
- Las tasas por 90 dependen del rol: un extremo y un delantero centro no deberían compartir prior. Agrupar por puesto es una aproximación.
- Con pocas jornadas, todo es provisional. Por eso cada cifra lleva su intervalo.
