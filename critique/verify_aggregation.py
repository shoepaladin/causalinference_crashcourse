"""Verification simulations for the critique of "Data Aggregation and Bias.ipynb".

Replicates the notebook's DGP with plain numpy and disentangles the sources of
the reported "aggregation bias":
  (1) aggregation itself (mean of y, max of W) is unbiased for the per-period
      effect when the model has no lagged dependent variable;
  (2) the bias appears only when a lagged dependent variable is included --
      that is Nickell (1981) bias, which grows as aggregation shrinks the
      time dimension (T=100 micro periods -> T=10 aggregated periods);
  (3) MAPE-of-the-difference is a pathological error metric;
  (4) aggregation is only precision-improving when there are true
      aggregated-period shocks; the notebook sets aggt_effect = 0.
"""
import numpy as np
import pandas as pd

rng = np.random.default_rng(20240601)


def dgp(N=60, preT=5, pstT=5, micro=10, X_var=0.25, ar=0.5, atet=2.0,
        error_std=1.0, aggt_std=0.0, err_rho=0.0):
    totalT = (preT + pstT) * micro
    unit_effect = rng.uniform(-1, 1, N)
    treated = np.zeros(N); treated[0] = 1.0  # notebook: exactly one treated unit
    agg_fe = rng.normal(0, aggt_std, preT + pstT)
    t_eff = rng.uniform(-1, 1, (totalT, N))
    inno = rng.normal(0, error_std, (totalT, N))
    if err_rho > 0:  # AR(1) idiosyncratic errors
        eps = np.zeros((totalT, N))
        eps[0] = inno[0]
        for t in range(1, totalT):
            eps[t] = err_rho * eps[t - 1] + inno[t]
    else:
        eps = inno
    X = rng.normal(0, X_var, (totalT, N)) * rng.binomial(1, 0.05, (totalT, N))
    W = ((np.arange(totalT) >= preT * micro)[:, None] * treated[None, :]).astype(float)

    y = np.zeros((totalT, N))
    for t in range(totalT):
        prey = y[t - 1] if t > 0 else np.zeros(N)
        a = agg_fe[t // micro]
        y[t] = ar * prey + X[t] + atet * W[t] + t_eff[t] + unit_effect + a + eps[t]

    idx = pd.MultiIndex.from_product([np.arange(totalT), np.arange(N)], names=['t', 'unitid'])
    df = pd.DataFrame({'y': y.ravel(), 'X': X.ravel(), 'W': W.ravel()}, index=idx).reset_index()
    df['aggT'] = df['t'] // micro
    return df


def twfe(df, ycol, use_lag, tcol='t'):
    d = df.copy()
    if use_lag:
        d['lag'] = d.groupby('unitid')[ycol].shift()
        d = d.dropna(subset=['lag'])
    # within-transform by entity and time dummies (balanced panel)
    d['y_dm'] = d[ycol] - d.groupby('unitid')[ycol].transform('mean') \
                      - d.groupby(tcol)[ycol].transform('mean') + d[ycol].mean()
    cols = ['W'] + (['lag'] if use_lag else [])
    Xd = d[cols].copy()
    for c in cols:
        Xd[c] = d[c] - d.groupby('unitid')[c].transform('mean') \
                     - d.groupby(tcol)[c].transform('mean') + d[c].mean()
    Xd.insert(0, 'const', 1.0)
    beta, res, rank, _ = np.linalg.lstsq(Xd.values, d['y_dm'].values, rcond=None)
    yhat = Xd.values @ beta
    resid = d['y_dm'].values - yhat
    dof = len(d) - rank
    sigma2 = resid @ resid / dof
    cov = sigma2 * np.linalg.pinv(Xd.values.T @ Xd.values)
    return beta[1], np.sqrt(cov[1, 1])  # W coefficient


def run(configs, sims=200):
    rows = []
    for cfg in configs:
        for s in range(sims):
            df = dgp(**cfg)
            dg = df.groupby(['unitid', 'aggT'], as_index=False).agg(y=('y', 'mean'),
                                                                   W=('W', 'max'),
                                                                   X=('X', 'mean'))
            for lag in (False, True):
                b_i, se_i = twfe(df, 'y', lag)
                b_a, se_a = twfe(dg, 'y', lag, tcol='aggT')
                rows.append({**{k: cfg.get(k) for k in
                               ('ar', 'error_std', 'aggt_std', 'err_rho', 'preT', 'pstT')},
                             'lag': lag, 'b_indiv': b_i, 'se_indiv': se_i,
                             'b_agg': b_a, 'se_agg': se_a, 'sim': s})
    return pd.DataFrame(rows)


if __name__ == '__main__':
    atet = 2.0
    # Experiment 1: bias decomposition over ar, notebook's aggt_std = 0
    cfg1 = [dict(ar=a) for a in (0.0, 0.1, 0.5, 0.75)]
    r1 = run(cfg1)
    print('\n=== Exp 1: mean bias (estimate - 2.0) by AR, lag, granularity ===')
    print(r1.assign(bias_i=r1.b_indiv - atet, bias_a=r1.b_agg - atet)
            .groupby(['ar', 'lag'])[['bias_i', 'bias_a', 'se_indiv', 'se_agg']]
            .mean().round(3).to_string())

    # Experiment 2: with true aggregated-period shocks, does aggregation help?
    cfg2 = [dict(ar=0.0, aggt_std=g) for g in (0.0, 1.0, 3.0)]
    r2 = run(cfg2)
    print('\n=== Exp 2: no-lag models, bias & SE as aggregated shock variance grows ===')
    print(r2[~r2.lag].assign(bias_i=r2.b_indiv - atet, bias_a=r2.b_agg - atet)
            .groupby('aggt_std')[['bias_i', 'bias_a', 'se_indiv', 'se_agg']]
            .mean().round(3).to_string())

    # Experiment 3: serially correlated errors -> does aggregation help precision?
    cfg3 = [dict(ar=0.0, err_rho=r) for r in (0.0, 0.5, 0.9)]
    r3 = run(cfg3)
    print('\n=== Exp 3b: no-lag models, sampling std of the W estimate (200 sims), AR(1) errors ===')
    print(r3[~r3.lag].groupby('err_rho')[['b_indiv', 'b_agg']]
            .agg(['mean', 'std']).round(3).to_string())

    # Experiment 4: MAPE-of-difference pathology on an unbiased estimator
    r = r1[(r1.ar == 0) & (~r1.lag)]
    mape = ((r.b_indiv - atet) / atet).abs().mean()
    rmse = np.sqrt(((r.b_indiv - atet) ** 2).mean())
    mcse = r.b_indiv.std() / np.sqrt(len(r))
    print('\n=== Exp 3: unbiased estimator (ar=0, no lag, daily) ===')
    print(f'mean estimate      = {r.b_indiv.mean():.3f}')
    print(f'MAPE(diff)         = {mape:.3f}  (notebook reports ~0.03 as "bias")')
    print(f'RMSE               = {rmse:.3f}')
    print(f'Monte Carlo SE     = {mcse:.4f}  -> sampling noise, not bias')
