# Preference for Experimentation: Theory, Critique, and Roadmap

Julian Hsu — 2025

---

## 1. What This Is

This document accompanies `Preference_for_Experimentation.ipynb`. It records the full theoretical development of the loss function used there, the academic critiques the notebook received, and a concrete implementation plan for the next version — which incorporates the dynamic value of information rather than the current static η bonus.

---

## 2. The Problem

We run a sequential experiment over T rounds. Each round the agent chooses a proportion p of n users to assign to treatment. Treatment has a true effect μ_T = −3; control has μ_C = 0. Both arms have equal noise σ = 9. The agent observes realized outcomes but does not know the true arm means.

The optimal policy is all-control (p = 0), but the agent must learn this through experience. The question is: how does the agent's *tolerance for variance* and *preference for experimentation* govern the allocation path and the cumulative outcome?

---

## 3. The Current Loss Function

### 3.1 Derivation

The agent minimizes a loss each round over a grid of candidate allocations p ∈ [0.05, 0.95]:

$$L(p) = -\underbrace{\bigl[p\tilde{\mu}_T + (1-p)\tilde{\mu}_C\bigr]}_{\text{expected reward}} + \lambda\underbrace{\bigl[\sigma^2 + p(1-p)(\tilde{\mu}_T - \tilde{\mu}_C)^2\bigr]}_{\text{outcome variance}} - \eta\underbrace{\frac{n \cdot p(1-p)}{\sigma^2}}_{\text{allocation balance}}$$

**Parameters:**
- **λ** (variance aversion): penalizes outcome variance. Higher λ → agent prefers corners to eliminate the between-arm term.
- **η** (experimentation incentive): rewards balanced allocation. Higher η → agent stays near p = 0.5.

**Arm mean beliefs** use Thompson Sampling: the agent draws $\tilde{\mu}_{arm} \sim \mathcal{N}(\bar{x}_{arm},\, \sigma^2/n_{arm})$ each round from the posterior under a flat prior and known σ². This introduces genuine uncertainty early on (wide posteriors) and confident exploitation late (tight posteriors).

### 3.2 Pooled Outcome Variance

With equal σ_T = σ_C = σ, the pooled outcome variance by the law of total variance is:

$$\text{Var}(Y) = p\sigma^2 + (1-p)\sigma^2 + p(1-p)(\mu_T - \mu_C)^2 = \sigma^2 + p(1-p)(\mu_T - \mu_C)^2$$

The within-arm term σ² is constant in p; only the between-arm term varies. It peaks at p = 0.5 and vanishes at the corners.

### 3.3 Interior vs. Corner Optimum

The curvature of L in p:

$$\frac{d^2 L}{dp^2} = -2\lambda(\tilde{\mu}_T - \tilde{\mu}_C)^2 + \frac{2\eta n}{\sigma^2}$$

| Condition | Curvature | Optimal p |
|---|---|---|
| λ > λ* = ηn / (σ²·gap²) | Negative (concave) | Corner (p ≈ 0 or 1) |
| λ < λ* | Positive (convex) | Interior (p ≈ 0.5) |

With n = 50, σ = 9, true gap = 3: **λ\* = η / 14.58**.

### 3.4 Why a Pure Variance Penalty Fails

Without the η term, the between-arm component p(1−p) evaluates to exactly 0.0475 at both extreme grid points (p = 0.05 and p = 0.95). Therefore:

$$L(0.95) - L(0.05) = 0.9(\tilde{\mu}_C - \tilde{\mu}_T)$$

Every λ term cancels. The agent picks whichever corner its Thompson Sample favors — λ has zero effect on the allocation decision.

---

## 4. Issues from Academic Review

Three independent reviews were conducted (ML/RL, statistics, economics perspectives). Key findings:

### 4.1 Critical: Variance Term Conflates Aleatoric and Epistemic Uncertainty

**The problem.** The loss uses a single Thompson Sample $(\tilde{\mu}_T, \tilde{\mu}_C)$ in the variance penalty:

$$\text{variance} = \sigma^2 + p(1-p)(\tilde{\mu}_T - \tilde{\mu}_C)^2$$

This conflates two distinct sources of variance:

1. **Aleatoric**: σ² — irreducible outcome noise.
2. **Epistemic**: uncertainty about the gap (μ_T − μ_C)², which shrinks as data accumulates.

Using a single TS draw means the variance penalty is noisy — it can be inflated by a lucky TS draw even when the true gap is known, causing the agent to flee to corners for the wrong reason.

**The fix.** Apply the law of total variance over the posterior:

$$\mathbb{E}_\pi\bigl[(\tilde{\mu}_T - \tilde{\mu}_C)^2\bigr] = (\bar{T} - \bar{C})^2 + \frac{\sigma^2}{n_T} + \frac{\sigma^2}{n_C}$$

The corrected variance term is:

$$\text{variance} = \sigma^2 + p(1-p)\left[(\bar{T} - \bar{C})^2 + \frac{\sigma^2}{n_T} + \frac{\sigma^2}{n_C}\right]$$

This is deterministic given current data, and the estimation noise terms σ²/n_T + σ²/n_C shrink naturally as data accumulates. The effective threshold becomes time-varying:

$$\lambda^*_t = \frac{\eta n}{\sigma^2 \cdot \left[(\bar{T} - \bar{C})^2 + \sigma^2/n_T + \sigma^2/n_C\right]}$$

Early in the experiment, the estimation noise inflates the denominator, lowering λ*_t — making interior allocation easier to achieve when the agent is most uncertain. As data accumulates, λ*_t converges to the asymptotic η/14.58.

### 4.2 Critical: η Term is a Static Proxy for a Dynamic Quantity

**The problem.** The current η·p(1−p)·n/σ² bonus is fixed — it does not:
- Decrease as the gap becomes well-established (exploration should phase out)
- Increase with remaining rounds (early information is worth more)

It is a reasonable functional approximation (peaks at p = 0.5, zero at corners) but has no derivation from first principles.

**The fix.** See Section 5 — this is the main roadmap item.

### 4.3 Major: "Fisher Information" is Mislabeled

The term p(1−p)·n/σ² is called "Fisher information for ATE" in the notebook, but the actual Fisher information for estimating the ATE is:

$$I(\text{ATE}) = \frac{n}{p(1-p)\sigma^2}$$

which is *highest at the corners* — the opposite of what the notebook claims. What the notebook implements is the **sample-size product** or **allocation balance index**, not Fisher information. The terminology should be corrected.

### 4.4 Other Issues (noted, lower priority)

- **±1 SD bands** on plots should be ±1 SEM for confidence intervals on the mean, or relabeled as "individual run variability."
- **Cumulative reward** as a welfare metric is misleading: a high-λ agent sacrificing reward to control variance may be optimizing correctly under its own preferences. Cumulative loss Σ L(p_t) is the right comparison.
- **No regret analysis**: the literature benchmarks via cumulative regret (forgone reward vs. optimal policy), not raw reward.
- **Random initialization** (round 1 picks p uniformly at random) is a minor inconsistency with the loss-function narrative; the agent could instead evaluate L(p) with flat priors.
- **SUTVA not stated**: outcomes are assumed independent across users.

---

## 5. Implementation Roadmap: Dynamic Value of Information

### 5.1 The Core Idea

A rational agent choosing p at round t should account for the fact that this round's allocation determines how much is learned, and that learning has value over the remaining T − t rounds. The current η term is a free parameter meant to proxy this value. The goal is to *derive* the correct information bonus from the structure of the problem.

### 5.2 Theoretical Foundation

#### Expected optimal future reward

At round t, if the agent were to commit to the better arm from round t+1 onward, its expected per-round reward (using current posteriors) is:

$$\mathbb{E}_\pi[\max(\mu_T, \mu_C)] = \bar{C} + (\bar{T} - \bar{C})\Phi(d_t) + \sigma_{\text{gap},t}\,\phi(d_t)$$

where:
- $d_t = (\bar{T} - \bar{C})\,/\,\sigma_{\text{gap},t}$ is the standardized posterior gap
- $\sigma_{\text{gap},t} = \sqrt{\sigma^2/n_T + \sigma^2/n_C}$ is the current posterior SD on the gap
- Φ and φ are the standard normal CDF and PDF

This is the standard formula for the expected maximum of two correlated normals (equivalent to a call-option formula). It increases as σ_gap,t decreases — tighter posteriors mean the agent can more reliably identify and exploit the better arm.

#### Key derivative

$$\frac{\partial\,\mathbb{E}_\pi[\max(\mu_T, \mu_C)]}{\partial\,\sigma_{\text{gap}}} = \phi(d_t)$$

Every unit reduction in posterior SD on the gap improves expected future reward per round by φ(d_t). When d_t ≈ 0 (gap is unknown), φ(0) ≈ 0.40 — learning is most valuable. When |d_t| is large (gap is clear), φ(d_t) → 0 — further learning has near-zero marginal value.

#### Reduction in posterior uncertainty from this round

Allocating fraction p this round adds n·p treatment observations and n·(1−p) control observations. The posterior SD after this round is:

$$\sigma_{\text{gap},t+1}(p) = \sqrt{\frac{\sigma^2}{n_T + n_{\text{round}}\cdot p} + \frac{\sigma^2}{n_C + n_{\text{round}}\cdot(1-p)}}$$

The reduction is:

$$\Delta\sigma_{\text{gap}}(p) = \sigma_{\text{gap},t} - \sigma_{\text{gap},t+1}(p)$$

This is maximized at p = 0.5 (balanced allocation reduces gap uncertainty fastest) and zero at the corners (all observations go to one arm, giving no information about the other).

#### The VOI term

Projecting the improvement over the T − t remaining rounds:

$$\text{VOI}_t(p) = (T - t)\cdot n_{\text{round}}\cdot\phi(d_t)\cdot\Delta\sigma_{\text{gap}}(p)$$

**Interpretation:**
- (T − t): information gathered now is useful for all remaining rounds
- φ(d_t): scales down to zero as the gap becomes well-established — exploration phases out endogenously
- Δσ_gap(p): the actual reduction in uncertainty this allocation achieves

### 5.3 The Full Updated Loss Function

$$\boxed{L_t(p) = -\bigl[p\tilde{\mu}_T + (1-p)\tilde{\mu}_C\bigr] + \lambda\!\left[\sigma^2 + p(1-p)\!\left((\bar{T}-\bar{C})^2 + \frac{\sigma^2}{n_T} + \frac{\sigma^2}{n_C}\right)\right] - \gamma\cdot(T-t)\cdot n\cdot\phi(d_t)\cdot\Delta\sigma_{\text{gap}}(p)}$$

**Parameters:**
- **λ**: variance aversion (same as before)
- **γ**: value per unit reduction in posterior SD on the gap, in reward units. One natural calibration: γ ≈ |T̄ − C̄| (the cost of one round in the wrong corner per user), or fit to observed decision-making data.

**What each change buys:**

| Current | Updated | Why it matters |
|---|---|---|
| TS draw in variance | Posterior mean + estimation noise | Separates aleatoric and epistemic variance |
| η·p(1−p)·n/σ² | γ·(T−t)·n·φ(d_t)·Δσ_gap(p) | Exploration phases out as gap is learned; early rounds valued more |
| λ* = η/14.58 (fixed) | λ*_t = γ(T−t)·φ(d_t)·∂Δσ/∂[·] / [gap² + σ²/n_T + σ²/n_C] (time-varying) | Threshold evolves with evidence |

### 5.4 Connection to Existing Literature

This formulation connects to several threads:

- **Bayesian bandit / Gittins index** (Gittins 1979): The full dynamic solution to the sequential allocation problem. The VOI term is a one-step lookahead approximation to the Gittins index for a Gaussian bandit. The full Gittins solution would require backward induction but produces the same φ(d_t) structure.
- **Value of information** (Raiffa & Schlaifer 1961; Howard 1966): EVSI (expected value of sample information) for a two-action decision (treat all vs. control all) after T rounds of experimentation. The VOI formula above is a rolling EVSI approximation.
- **Thompson Sampling theory** (Russo & Van Roy 2016): TS is Bayes-optimal for reward maximization in bandit problems. The current notebook extends TS to a mean-variance loss. Adding the VOI term makes the extended problem closer to Bayes-optimal for the full inference-and-decision problem.
- **Adaptive clinical trials** (Berry 2004; Thall & Wathen 2007): The same structure — allocate patients between arms to balance learning and outcome — with the additional complication that the gap may be heterogeneous.

### 5.5 Step-by-Step Implementation Plan

**Step 1: Fix the variance term (Section 4.1)**

In `choose_best_allocation`, replace:
```python
var_T = np.var(treatment_outcomes, ddof=1) if n_t > 1 else noise_treat**2
var_C = np.var(control_outcomes,   ddof=1) if n_c > 1 else noise_control**2
variance = var_known + p * (1-p) * (mu_t - mu_c)**2
```
with:
```python
gap_sq_posterior = (T_bar - C_bar)**2 + var_known/n_t + var_known/n_c
variance = var_known + p * (1-p) * gap_sq_posterior
```
Keep TS draws only in the reward term.

**Step 2: Compute σ_gap and d_t each round**

```python
sigma_gap_current = np.sqrt(var_known/n_t + var_known/n_c)
d_t = (T_bar - C_bar) / sigma_gap_current   # standardized posterior gap
```

**Step 3: Replace the η term with the VOI term**

```python
def sigma_gap_after(n_t, n_c, p, var_known, n_round):
    return np.sqrt(var_known / (n_t + n_round*p) + var_known / (n_c + n_round*(1-p)))

from scipy.stats import norm

for p in p_grid:
    reward   = p * mu_t + (1-p) * mu_c
    variance = var_known + p*(1-p)*gap_sq_posterior
    
    delta_sigma = sigma_gap_current - sigma_gap_after(n_t, n_c, p, var_known, n_per_round)
    phi_d       = norm.pdf(d_t)
    voi         = rounds_remaining * n_per_round * phi_d * delta_sigma
    
    cur = -reward + lambda_weight * variance - gamma * voi
```

**Step 4: Update `outputs()` signature**

Replace `eta` with `gamma`. Add `t` (current round) and `T` (total rounds) to `choose_best_allocation` so it can compute `rounds_remaining = T - t`.

**Step 5: Parameter sweep**

The interesting dimensions are now:
- **λ sweep** (fix γ, e.g. γ = 5): shows how variance aversion drives corner allocation
- **γ sweep** (fix λ, e.g. λ = 0.5): shows how information value drives experimentation
- **Horizon sweep** (fix λ, γ, vary T): shows that more rounds → more early experimentation

**Step 6: New diagnostic plots**

In addition to the allocation plot, add:
- **σ_gap over time** for each (λ, γ) condition — shows how quickly agents learn the gap
- **φ(d_t) over time** — shows when exploration value collapses
- **Cumulative loss** Σ L_t(p_t) — the welfare metric each agent is actually optimizing
- **Effective λ*_t over time** — shows the time-varying threshold

**Step 7: Regret analysis**

Compute and plot cumulative regret:

$$\text{Regret}(T) = \sum_{t=1}^T n_{\text{round}} \cdot \max(\mu_T, \mu_C) - \sum_{t=1}^T \text{realized reward}_t$$

= number of rounds × n × optimal_per_user − realized total reward

This enables comparison with pure Thompson Sampling and UCB baselines.

---

## 6. Summary of the Narrative

The notebook builds toward one main economic claim:

> **An agent with high variance aversion (λ large) will not experiment, even when experimentation is cheap, because the between-arm variance of doing a balanced experiment is penalized by the loss function. This leads to premature commitment to a corner allocation, which may be the wrong corner — and the agent is slow to self-correct because it accumulates little data on the arm it has neglected.**

The current notebook captures this qualitatively but the machinery has gaps. The roadmap above produces a version where:

1. The variance penalty correctly reflects the agent's posterior beliefs (not a noisy TS sample of them)
2. The information bonus is derived from first principles (EVSI / VOI) rather than a free parameter
3. The bonus phases out endogenously as the agent learns — matching the intuition that you experiment when uncertain and exploit when confident
4. The threshold λ*_t is time-varying and directly connected to the posterior uncertainty, providing a clean empirical prediction that can be validated against the simulation

The resulting model is a tractable, pedagogically clear version of the Bayesian bandit problem with mean-variance preferences — a natural bridge between the bandit literature and the experimentation-in-firms economics literature.

---

## 7. References

- Berry, D.A. (2004). *Bayesian clinical trials*. Nature Reviews Drug Discovery.
- Gittins, J.C. (1979). Bandit processes and dynamic allocation indices. *Journal of the Royal Statistical Society B*.
- Howard, R.A. (1966). Information value theory. *IEEE Transactions on Systems Science and Cybernetics*.
- Raiffa, H. & Schlaifer, R. (1961). *Applied Statistical Decision Theory*. Harvard Business School.
- Russo, D. & Van Roy, B. (2016). An information-theoretic analysis of Thompson Sampling. *Journal of Machine Learning Research*.
- Thall, P.F. & Wathen, J.K. (2007). Practical Bayesian adaptive randomisation in clinical trials. *European Journal of Cancer*.
