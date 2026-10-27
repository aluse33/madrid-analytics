---
title: Methodology
toc:
  label: "On this page"
---
<!-- GENERADO por `rma traducir` a partir de ../metodologia.md: no editar a mano -->

# Methodology

## Data

LaLiga data come from **Understat** through the Python library [soccerdata](https://github.com/probberechts/soccerdata): result and xG of every match, every shot (location, xG, situation, body part) and per-player match stats. Coordinates are converted to metres on a 105 × 68 m pitch. Since Understat only covers leagues, the Champions League and other competitions, line-ups, match timelines and player photos come from **ESPN**, and the club's history from **Wikipedia**.

**Updates.** The site updates itself every morning: the process starts at 7:23 (Madrid time) in winter and 8:23 in summer, and takes between ten minutes and half an hour. GitHub, which runs it, sometimes starts it a little late.

## What xG is

**xG** (*expected goals*) measures the quality of a chance: it is the **probability that a shot ends up as a goal**, given where and how it is taken. A 0.30 xG shot goes in three times out of ten when a chance like that comes up. A penalty is worth about 0.76 xG, because roughly three in four are scored; a long-range shot from outside the box, usually under 0.05.

**How it is calculated.** A statistical model is trained on hundreds of thousands of past shots whose outcome is known. For each shot, the model takes into account things like:

- the distance and angle to goal;
- the body part (foot or head);
- the type of play: open play, counter-attack, corner, direct free kick or penalty;
- in some models, the type of assist or the defensive pressure.

From that it estimates ${tex`\text{xG}_k = P(\text{goal}_k \mid \text{distance}, \text{angle}, \dots)`}, and the xG of a team or a player in a match is the sum of the xG of their shots. Understat uses a neural network trained on more than 100,000 shots; this site also has its own model, explained below and compared in the [Model lab](./modelos).

**How to read it.** xG says how many goals the chances *deserved*, not how many were scored. If a team creates 2.1 xG and concedes 0.8, it created far more danger even if it lost 0-1. Over many matches, goals tend to converge to xG, which is why it measures a team's true level better than the scoreline. It ignores who shoots and who is in goal: a 0.30 xG shot is the scoring probability for an *average* player in that situation. Consistently scoring above one's xG is precisely what sets a great finisher apart.

**Variants used on this site:** **npxG**, xG without penalties (fairer for comparing players); **xA**, the xG of the shots a player sets up for a team-mate with his pass; **xGChain**, the xG of every possession he is involved in, and **xGBuildup**, the same leaving out the shot and the final pass.

## Dixon-Coles with an xG target

For each match with home team ${tex`i`} and away team ${tex`j`}:

```tex
\log \lambda_{ij} = \mu + h + a_i + d_j, \qquad \log \nu_{ij} = \mu + a_j + d_i
```

where ${tex`a`} is attacking strength, ${tex`d`} defensive weakness and ${tex`h`} home advantage. Parameters are estimated by **weighted, penalised Poisson quasi-likelihood**:

```tex
\max_{\mu, h, a, d} \; \sum_k w_k \left[ y_k \log \lambda_k - \lambda_k \right] - \frac{\kappa}{2}\left(\lVert a \rVert^2 + \lVert d \rVert^2\right),
\qquad w_k = 2^{-\text{age}_k / \text{half-life}}
```

- The target ${tex`y`} is a mix of xG and goals. Poisson quasi-likelihood only needs the mean to be correctly specified, so it accepts a continuous ${tex`y`}; using xG cuts the variance a lot, because the scoreline is a very noisy realisation of chance quality.
- The L2 penalty identifies the model (without it a constant can be shifted from ${tex`a`} to ${tex`d`}) and shrinks teams with few matches towards the league average.
- In a second step ${tex`\rho`}, the Dixon and Coles (1997) correction for 0-0, 1-0, 0-1 and 1-1, is estimated by maximum likelihood on actual goals.

Evaluation is **out of sample with a rolling origin**: each week the model is refitted on the past and predicts the next one. The main metric is the *Ranked Probability Score*, which respects the ordering win > draw > loss.

## Empirical Bayes shrinkage

For each player's per-90 rate ${tex`\theta_i`}, with ${tex`e_i`} = minutes / 90:

```tex
\theta_i \sim \text{Gamma}(\alpha, \beta), \qquad \mathbb{E}[X_i \mid \theta_i] = \theta_i e_i, \quad \operatorname{Var}[X_i \mid \theta_i] = \phi\, \theta_i e_i
```

The posterior is conjugate and its mean weights the observed rate against the position average:

```tex
\mathbb{E}[\theta_i \mid X_i] = B_i \frac{\alpha}{\beta} + (1 - B_i) \frac{X_i}{e_i}, \qquad B_i = \frac{\beta}{\beta + e_i / \phi}
```

- ${tex`(\alpha, \beta)`} are estimated by marginal maximum likelihood (negative binomial) using **all LaLiga players in the same position**.
- ${tex`\phi`} is the within-player Pearson dispersion, match by match. It is needed because xG is a sum of small probabilities: its variance (${tex`\sum p_k^2`}) is far below its mean (${tex`\sum p_k`}), and assuming a Poisson (${tex`\phi = 1`}) would make the model think almost everything is noise and over-shrink. In LaLiga it comes out at ${tex`\phi \approx 0.3`}.

## Goals against xG: Poisson-binomial

If shot ${tex`k`} is a goal with probability ${tex`p_k`} (its xG), independently, the number of goals follows a Poisson-binomial distribution, computed exactly by convolution. With it:

- **Skill or luck?** ${tex`P(G \ge g)`}: how rare it is to score at least ${tex`g`} goals from those shots.
- **Deserved result**: convolving both teams' distributions gives the probability of a win, draw and loss from those same chances, and the expected points.

## Our own xG model

Logistic regression (distance, log-distance, goal angle, header, situation) and *gradient boosting* (`HistGradientBoostingClassifier`, which also uses the coordinates). Cross-validation grouped by match (`GroupKFold`). Penalties are excluded and get their empirical conversion rate.

## Season simulation

Monte Carlo over the remaining matches: in each of the 10,000 simulated seasons every match is decided by a scoreline drawn from the Dixon-Coles matrix, points and goal difference are added up and the table is sorted. Ties are broken on goal difference (not LaLiga's head-to-head rule).

Fixing strengths at their point estimates would make the simulation overconfident. Each simulated season uses different strengths, with three sources of uncertainty:

**1. Estimation error.** We draw ${tex`\theta \sim \mathcal{N}(\hat\theta, \hat\Sigma)`} with the **sandwich** covariance of the weighted, penalised quasi-likelihood:

```tex
\hat\Sigma = H^{-1} B\, H^{-1}, \qquad H = \sum_k w_k \lambda_k x_k x_k^\top + \kappa I, \qquad B = \sum_{\text{matches}} s_m s_m^\top
```

where ${tex`s_m`} is each match's contribution to the estimating equation. It does not assume the target is Poisson, so it is valid for xG (underdispersed) and for the mix with goals.

**2. Strength drift.** A team's strength changes over time. It is modelled as a random walk,

```tex
a_{i,t} = a_{i,t-1} + \eta_{i,t}, \qquad \eta_{i,t} \sim \mathcal{N}(0, \tau^2 \Delta t),
```

and ${tex`\tau^2`} is estimated from the data: the model is fitted (on xG, without time weighting) on each half-season separately and each team's strength is compared across consecutive windows,

```tex
\mathbb{E}\big[(\hat a_{i,2} - \hat a_{i,1})^2\big] = \operatorname{se}_{i,1}^2 + \operatorname{se}_{i,2}^2 + \tau^2 \Delta t .
```

Likewise for defence. It comes out at a standard deviation of about 0.10 attack units (log scale) every 200 days.

**3. Lag and future drift.** With drift, the weighted three-year estimate describes the team's "average" over that period, not today's team. With normalised weights ${tex`\omega_s`} and ages ${tex`s`} (in days), the added error is

```tex
\operatorname{Var}\Big(\sum_s \omega_s a_{t-s} - a_t\Big) = \tau^2 \sum_s \sum_r \omega_s \omega_r \min(s, r),
```

and from now until May strengths keep moving with the same ${tex`\tau^2`}.

It is a simplified version of a state-space model with a Kalman filter, which would be the natural next step. Upcoming-match probabilities are also **posterior predictive**: the scoreline matrix is averaged over this same uncertainty instead of being evaluated only at ${tex`\hat\theta`}.

## Limitations

- Understat gives no shot context (defender and goalkeeper positions, type of assist), so no xG built on its data can go much beyond its own.
- Per-90 rates depend on role: a winger and a centre-forward should not share a prior. Grouping by position is an approximation.
- Drift is estimated across all teams at once: a single ${tex`\tau^2`} for everyone, without separating the summer (transfers) from the season.
- Early in the season everything is provisional. That is why every figure comes with an interval.
