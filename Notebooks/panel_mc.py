"""Monte-Carlo bias/coverage study behind the Panel Models deck.

Fits DiD, SC-ADH, SC-DI, and SDID on `dgp.simulate_panel` data under two
scenarios — parallel trends (`sigma_lambda=0`) and a violation
(`sigma_lambda=1`) — all sharing the same conformal (time-block permutation)
inference. Writes one row per (scenario, seed, model) to `panel_mc_results.csv`,
which the deck's fig9 skip-cell and the companion notebook read.

panelib is the canonical panel library in the statanomics repo; this script
imports it from a sibling clone (shallow-cloning it if absent) so nothing is
duplicated. The full run (200 seeds x 2 scenarios x 4 models, each with
conformal inference) takes a few hours; drop N_SEEDS for a quick pass.
"""
import os, sys, io, subprocess, warnings, time
from contextlib import redirect_stdout
warnings.filterwarnings("ignore")


def _ensure_panelib():
    here = os.getcwd()
    for base in [here, os.path.dirname(here), os.path.dirname(os.path.dirname(here)),
                 os.path.expanduser("~")]:
        p = os.path.join(base, "statanomics", "workingcode", "panelmodels")
        if os.path.exists(os.path.join(p, "panelib.py")):
            return p
    dest = os.path.join(os.path.dirname(here), "statanomics")
    if not os.path.exists(dest):
        subprocess.run(["git", "clone", "--depth", "1",
                        "https://github.com/shoepaladin/statanomics.git", dest],
                       check=True)
    return os.path.join(dest, "workingcode", "panelmodels")

sys.path.insert(0, _ensure_panelib())
import numpy as np
import pandas as pd
from panelib import did, sc, sdid, dgp

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "panel_mc_results.csv")
DD = {"treatment": "treated", "date": "time", "post": "post",
      "unitid": "unit_id", "outcome": "y"}
PARAMS = dict(T_pre=20, T_post=2, N_control=100, noise_sd=0.1, att_pct=0.05, rho=0.8)
CONF_GRID = np.arange(-9, 9, 0.025)
INFERENCE = {"alpha": 0.05, "theta_grid": CONF_GRID}
SCENARIOS = {"parallel": 0.0, "violated": 1.0}
N_SEEDS = 200


def one_seed(scenario, sigma_lambda, seed):
    df, true_att = dgp.simulate_panel(seed=seed, sigma_lambda=sigma_lambda, **PARAMS)
    rows = []

    def add(model, att, lo, hi):
        rows.append(dict(scenario=scenario, seed=seed, model=model,
                         true_att=true_att, att=att, ci_lower=lo, ci_upper=hi,
                         bias=att - true_att, covered=int(lo <= true_att <= hi)))

    with redirect_stdout(io.StringIO()):
        inf = did.conformal_inference(data=df, data_dict=DD, theta_grid=CONF_GRID)
        att, se = inf["real_att"], inf["se"]
        add("DiD", att, att - 1.96 * se, att + 1.96 * se)

        for name, label in [("adh", "SC-ADH"), ("di", "SC-DI")]:
            r = sc.sc_model(model_name=name, data=df, data_dict=DD, inference=INFERENCE)
            res = r["results_df"]
            add(label, float(res["atet"].values[0]),
                float(res["ci_lower"].values[0]), float(res["ci_upper"].values[0]))

        inf = sdid.conformal_inference(data=df, data_dict=DD, theta_grid=CONF_GRID)
        att, se = inf["real_att"], inf["se"]
        add("SDID", att, att - 1.96 * se, att + 1.96 * se)
    return rows


def main(n_seeds=N_SEEDS):
    all_rows, t0 = [], time.time()
    for scenario, sig in SCENARIOS.items():
        for seed in range(n_seeds):
            all_rows.extend(one_seed(scenario, sig, seed))
            if (seed + 1) % 5 == 0 or seed == n_seeds - 1:
                pd.DataFrame(all_rows).to_csv(OUT, index=False)
                print(f"{scenario} seed {seed+1}/{n_seeds}  "
                      f"elapsed {(time.time()-t0)/60:.1f} min", flush=True)
    pd.DataFrame(all_rows).to_csv(OUT, index=False)
    print("DONE", OUT, flush=True)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else N_SEEDS)
