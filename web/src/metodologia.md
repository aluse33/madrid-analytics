---
title: Metodología
---

# Metodología

## Datos

Todo sale de **Understat** a través de la librería de Python [soccerdata](https://github.com/probberechts/soccerdata): resultado y xG de cada partido de LaLiga, todos los tiros (posición, xG, situación, parte del cuerpo) y estadísticas por jugador y partido. Understat solo cubre las ligas, así que la Champions y la Copa no aparecen. Las coordenadas se pasan a metros en un campo de 105 × 68 m.

## Dixon-Coles con objetivo en xG

Para cada partido con local ${tex`i`} y visitante ${tex`j`}:

```tex
\log \lambda_{ij} = \mu + h + a_i + d_j, \qquad \log \nu_{ij} = \mu + a_j + d_i
```

donde ${tex`a`} es la capacidad ofensiva, ${tex`d`} la fragilidad defensiva y ${tex`h`} la ventaja de campo. Los parámetros se estiman por **cuasi-verosimilitud de Poisson ponderada y penalizada**:

```tex
\max_{\mu, h, a, d} \; \sum_k w_k \left[ y_k \log \lambda_k - \lambda_k \right] - \frac{\kappa}{2}\left(\lVert a \rVert^2 + \lVert d \rVert^2\right),
\qquad w_k = 2^{-\text{edad}_k / \text{semivida}}
```

- El objetivo ${tex`y`} es una mezcla de xG y goles. La cuasi-verosimilitud de Poisson solo necesita que la media esté bien especificada, así que admite un ${tex`y`} continuo; usar xG reduce mucho la varianza, porque el marcador es una realización muy ruidosa de la calidad de las ocasiones.
- La penalización L2 identifica el modelo (sin ella se puede pasar una constante de ${tex`a`} a ${tex`d`}) y encoge hacia la media de la liga a los equipos con pocos partidos.
- En un segundo paso se estima ${tex`\rho`}, la corrección de Dixon y Coles (1997) para 0-0, 1-0, 0-1 y 1-1, por máxima verosimilitud sobre los goles reales.

La evaluación es **fuera de muestra con origen móvil**: cada semana se reajusta con el pasado y se predice la siguiente. La métrica principal es el *Ranked Probability Score*, que respeta el orden victoria > empate > derrota.

## Shrinkage empírico-bayesiano

Para la tasa por 90 minutos ${tex`\theta_i`} de cada jugador, con ${tex`e_i`} = minutos / 90:

```tex
\theta_i \sim \text{Gamma}(\alpha, \beta), \qquad \mathbb{E}[X_i \mid \theta_i] = \theta_i e_i, \quad \operatorname{Var}[X_i \mid \theta_i] = \phi\, \theta_i e_i
```

La posterior es conjugada y su media pondera la tasa observada y la del puesto:

```tex
\mathbb{E}[\theta_i \mid X_i] = B_i \frac{\alpha}{\beta} + (1 - B_i) \frac{X_i}{e_i}, \qquad B_i = \frac{\beta}{\beta + e_i / \phi}
```

- ${tex`(\alpha, \beta)`} se estiman por máxima verosimilitud marginal (binomial negativa) con **todos los jugadores de LaLiga del mismo puesto**.
- ${tex`\phi`} es la dispersión de Pearson dentro de cada jugador, partido a partido. Hace falta porque el xG es una suma de probabilidades pequeñas: su varianza (${tex`\sum p_k^2`}) es muy inferior a su media (${tex`\sum p_k`}), y suponer una Poisson (${tex`\phi = 1`}) haría creer al modelo que casi todo es ruido y encogería de más. En LaLiga sale ${tex`\phi \approx 0{,}3`}.

## Goles frente a xG: Poisson-binomial

Si el tiro ${tex`k`} es gol con probabilidad ${tex`p_k`} (su xG), de forma independiente, el número de goles sigue una distribución Poisson-binomial, que se calcula exactamente por convolución. Con ella:

- **¿Acierto o suerte?** ${tex`P(G \ge g)`}: cuán raro es marcar al menos ${tex`g`} goles con esos tiros.
- **Resultado merecido**: convolucionando las distribuciones de los dos equipos se obtiene la probabilidad de victoria, empate y derrota con esas mismas ocasiones, y los puntos esperados.

## Modelo xG propio

Regresión logística (distancia, log-distancia, ángulo de portería, cabeza, situación) y *gradient boosting* (`HistGradientBoostingClassifier`, que además usa las coordenadas). Validación cruzada agrupada por partido (`GroupKFold`). Los penaltis se excluyen y reciben su tasa de conversión empírica.

## Simulación de la temporada

Monte Carlo de los partidos pendientes: en cada una de las 10.000 temporadas simuladas, cada partido se resuelve con un marcador sacado de la matriz de Dixon-Coles, se suman puntos y diferencia de goles y se ordena la tabla. Desempate por diferencia de goles (no por el golaveraje particular de LaLiga).

Fijar las fuerzas en su estimación puntual haría la simulación demasiado segura. Cada temporada simulada usa unas fuerzas distintas, con tres fuentes de incertidumbre:

**1. Error de estimación.** Se muestrea ${tex`\theta \sim \mathcal{N}(\hat\theta, \hat\Sigma)`} con la covarianza **sándwich** de la cuasi-verosimilitud ponderada y penalizada:

```tex
\hat\Sigma = H^{-1} B\, H^{-1}, \qquad H = \sum_k w_k \lambda_k x_k x_k^\top + \kappa I, \qquad B = \sum_{\text{partidos}} s_m s_m^\top
```

donde ${tex`s_m`} es la contribución de cada partido a la ecuación de estimación. No supone que el objetivo sea Poisson, así que vale para el xG (infradisperso) y para la mezcla con goles.

**2. Deriva de las fuerzas.** La fuerza de un equipo cambia con el tiempo. Se modela como un paseo aleatorio,

```tex
a_{i,t} = a_{i,t-1} + \eta_{i,t}, \qquad \eta_{i,t} \sim \mathcal{N}(0, \tau^2 \Delta t),
```

y ${tex`\tau^2`} se estima con los datos: se ajusta el modelo (con xG, sin ponderación temporal) en cada media temporada por separado y se compara la fuerza de cada equipo entre ventanas consecutivas,

```tex
\mathbb{E}\big[(\hat a_{i,2} - \hat a_{i,1})^2\big] = \operatorname{se}_{i,1}^2 + \operatorname{se}_{i,2}^2 + \tau^2 \Delta t .
```

Igual para la defensa. Sale una desviación de unas 0,10 unidades de ataque (en logaritmos) cada 200 días.

**3. Desfase y deriva futura.** Con deriva, la estimación ponderada de tres años describe al equipo "medio" de ese periodo, no al de hoy. Con pesos normalizados ${tex`\omega_s`} y antigüedades ${tex`s`} (en días), el error añadido es

```tex
\operatorname{Var}\Big(\sum_s \omega_s a_{t-s} - a_t\Big) = \tau^2 \sum_s \sum_r \omega_s \omega_r \min(s, r),
```

y de aquí a mayo las fuerzas siguen moviéndose con el mismo ${tex`\tau^2`}.

Es una versión simplificada de un modelo de espacio de estados con filtro de Kalman, que sería el siguiente paso natural. Las probabilidades de los próximos partidos son también **predictivas posteriores**: la matriz de marcadores se promedia sobre esta misma incertidumbre, en lugar de evaluarse solo en ${tex`\hat\theta`}.

## Limitaciones

- Understat no da contexto de los tiros (posición de defensas y portero, tipo de pase previo), así que ningún xG basado en sus datos puede ir mucho más allá del suyo.
- Las tasas por 90 dependen del rol: un extremo y un delantero centro no deberían compartir prior. Agrupar por puesto es una aproximación.
- La deriva se estima con todos los equipos a la vez: un mismo ${tex`\tau^2`} para todos, y sin distinguir verano (fichajes) de temporada.
- Con pocas jornadas, todo es provisional. Por eso cada cifra lleva su intervalo.
