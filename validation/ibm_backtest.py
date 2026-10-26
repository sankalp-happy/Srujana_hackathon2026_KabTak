"""External check of the payment-arrival model and the shared buyer shock on an IBM public AR sample.

Protocol copied from cashcast (cashcast/demo.py + forecast.py): 10 forecast origins (1st of each month,
2013-02-01 .. 2013-11-01); at each, the open invoices are those issued before the origin and not paid before
it; the horizon is 8 weeks from the origin; weekly cash = amount of those open invoices actually paid in
each week (new invoices ignored); band = P10..P90 of the simulated weekly sums; coverage over 10x8 = 80 weeks.
Reuses engine.arrival (Kaplan-Meier per buyer, sample_delay) and engine.simulate (RHO, _phi shared shock).

Run: python3 -m validation.ibm_backtest   (fixed seed; writes results/ibm_validation.json and refreshes the
table in docs/planning/validation-ibm.md). Nothing here is tuned on the test period: RHO, MIN_EVENTS, PATHS
were fixed before the first run.
"""
import json
import math
import re
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from engine import arrival
from engine.simulate import RHO, _phi

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "data" / "raw" / "ibm_ar.csv"
URL = "https://raw.githubusercontent.com/pthiagu2/DataMining/master/WA_Fn-UseC_-Accounts-Receivable.csv"
OUT = ROOT / "results" / "ibm_validation.json"
DOC = ROOT / "docs" / "planning" / "validation-ibm.md"

ORIGINS = pd.date_range("2013-02-01", "2013-11-01", freq="MS")   # cashcast DATES
WEEKS = 8
PATHS = 2000          # cashcast DRAWS (the engine's own default is 1,000)
MIN_EVENTS = 5        # customer needs this many paid invoices for its own KM, else pooled KM
SEED = 20261025
POOL = "__pool__"
CASHCAST = {"weekly_cash_coverage_80": 0.675, "weeks": 80, "per_invoice_coverage_80": 0.771,
            "open_rows": 905, "not_yet_due_rows": 784, "mean_weekly_actual_cash": 693.5}


def load() -> pd.DataFrame:
    if not CSV.exists():
        CSV.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["curl", "-sL", "-o", str(CSV), URL], check=True)
    d = pd.read_csv(CSV, dtype=str)
    p = lambda c: pd.to_datetime(d[c], format="%m/%d/%Y")
    return pd.DataFrame({"buyer": d["customerID"], "invoice_date": p("InvoiceDate"), "due": p("DueDate"),
                         "paid": p("SettledDate"), "amount": d["InvoiceAmount"].astype(float)})


def wilson(k, n, z=1.96):
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(c - h, 3), round(c + h, 3)]


def crps(samples, y):
    """Mean CRPS of an ensemble (P x W) against y (W,): E|X-y| - 0.5 E|X-X'|."""
    x = np.sort(samples, axis=0)
    n = len(x)
    e_xy = np.abs(x - y).mean(axis=0)
    e_xx = (2 * (2 * np.arange(1, n + 1) - n - 1)[:, None] * x).sum(axis=0) / n ** 2
    return float((e_xy - 0.5 * e_xx).mean())


def loo_points(buyer, dtp):
    """Leave-one-out per-customer mean delay for each paid invoice (pooled mean if < MIN_EVENTS)."""
    s = pd.Series(dtp.astype(float))
    g = s.groupby(buyer)
    n, tot = g.transform("size").to_numpy(), g.transform("sum").to_numpy()
    own = np.where(n > 1, (tot - s.to_numpy()) / np.maximum(n - 1, 1), s.mean())
    return np.where(n - 1 >= MIN_EVENTS, own, (s.sum() - s.to_numpy()) / (len(s) - 1))


class Baseline:
    """Point forecast + independent empirical-residual spread, truncated to > age (same protocol as the KM rows)."""

    def __init__(self, name, point_fn, resid):
        self.name, self.point_fn, self.R = name, point_fn, np.sort(resid)

    def delay(self, point, age, u):
        lo = np.searchsorted(self.R, age + 1 - point, side="left")      # residuals that keep the delay > age
        idx = np.minimum(lo + (u * (len(self.R) - lo)).astype(int), len(self.R) - 1)
        return np.where(lo < len(self.R), np.rint(point + self.R[idx]), age + 1).astype(int)


def snapshot(df, as_of, rng):
    today = as_of - pd.Timedelta(days=1)                  # engine "today" = last day of knowledge
    hist = df[df["invoice_date"] <= today].copy()
    hist["paid_date"] = hist["paid"].where(hist["paid"] <= today)   # NaT = open (censored) at the origin
    km = arrival.fit(hist, today)
    km[POOL] = arrival.fit(hist.assign(buyer=POOL), today)[POOL]
    events = hist.groupby("buyer")["paid_date"].count()
    own = {b for b in km if b != POOL and events.get(b, 0) >= MIN_EVENTS}

    op = hist[hist["paid_date"].isna()].reset_index(drop=True)
    age = (today - op["invoice_date"]).dt.days.to_numpy()
    terms = (op["due"] - op["invoice_date"]).dt.days.to_numpy()
    actual = (op["paid"] - op["invoice_date"]).dt.days.to_numpy()       # true delay (all invoices end up paid)
    amt = op["amount"].to_numpy()
    key = np.array([b if b in own else POOL for b in op["buyer"]])
    cust = {b: i for i, b in enumerate(sorted(set(op["buyer"])))}
    cidx = np.array([cust[b] for b in op["buyer"]])
    n = len(op)

    known = hist[hist["paid_date"].notna()]
    dtp = (known["paid_date"] - known["invoice_date"]).dt.days.to_numpy()
    kb = known["buyer"].to_numpy()
    cmean = {b: dtp[kb == b].mean() for b in own}
    pool_mean = dtp.mean()
    bases = [
        Baseline("paid on the due date", lambda b, t: t.astype(float),
                 dtp - (known["due"] - known["invoice_date"]).dt.days.to_numpy()),
        Baseline("customer average delay", lambda b, t: np.array([cmean.get(x, pool_mean) for x in b]),
                 dtp - loo_points(kb, dtp)),
    ]

    def km_delay(u, pooled=False):                        # u: (P, n) uniforms or (n,)
        out = np.empty(np.broadcast(u, age).shape, dtype=np.int64)
        for k in ([POOL] if pooled else np.unique(key)):
            c = np.ones(n, bool) if pooled else key == k
            out[..., c] = arrival.sample_delay(km, k, age[c], u[..., c] if u.ndim == 2 else u[c])
        return out

    zb = rng.standard_normal((PATHS, len(cust)))
    zi = rng.standard_normal((PATHS, n))
    z_ind = zi
    models = {"ours, invoices independent": lambda: km_delay(np.clip(_phi(z_ind), 1e-6, 1 - 1e-6))}

    def shared(rho):
        z = rho * zb[:, cidx] + np.sqrt(1 - rho ** 2) * zi
        return lambda: km_delay(np.clip(_phi(z), 1e-6, 1 - 1e-6))
    models["ours, shared buyer shock"] = shared(RHO)
    for rho in (0.3, 0.9):                                # sensitivity only, never used for the headline
        models[f"sens: shared shock rho={rho}"] = shared(rho)
    # post-hoc diagnostic (added after seeing the headline, so NOT a result): one pooled KM for every customer
    models["diag: pooled KM, independent"] = lambda: km_delay(np.clip(_phi(z_ind), 1e-6, 1 - 1e-6), pooled=True)
    for b in bases:
        pts = b.point_fn(op["buyer"].to_numpy(), terms)
        models[b.name + " + residual spread"] = (lambda b=b, pts=pts:
                                                 b.delay(pts, age, np.clip(_phi(z_ind), 1e-6, 1 - 1e-6)))

    wk_actual = np.array([amt[(actual - age - 1 >= 7 * w) & (actual - age - 1 < 7 * w + 7)].sum()
                          for w in range(WEEKS)])
    res = {"as_of": str(as_of.date()), "open": n, "not_yet_due": int(((age + 1) <= terms).sum()),
           "pooled_km_rows": int((key == POOL).sum()), "actual_week": wk_actual, "models": {}}
    u10, u90 = np.full(n, 0.1), np.full(n, 0.9)
    for name, draw in models.items():
        d = draw()                                        # (P, n) delay in days from invoice
        day = d - (age + 1)                               # days after the origin
        sims = np.stack([(amt * ((day >= 7 * w) & (day < 7 * w + 7))).sum(axis=1) for w in range(WEEKS)], axis=1)
        if name.startswith(("ours", "sens", "diag")):
            pl = name.startswith("diag")
            lo, hi, mid = (km_delay(u, pl) for u in (u10, u90, np.full(n, 0.5)))
        else:                                             # baselines: same truncated residual quantiles
            b = next(x for x in bases if name.startswith(x.name))
            pts = b.point_fn(op["buyer"].to_numpy(), terms)
            lo, hi, mid = (b.delay(pts, age, np.full(n, q)) for q in (0.1, 0.9, 0.5))
        res["models"][name] = {
            "inv_in": ((actual >= lo) & (actual <= hi)), "inv_err": np.abs(actual - mid),
            "inv_width": (hi - lo), "week_lo": np.percentile(sims, 10, axis=0),
            "week_hi": np.percentile(sims, 90, axis=0), "week_mean": sims.mean(axis=0),
            "crps": crps(sims, wk_actual)}
    return res


def run():
    df = load()
    rng = np.random.default_rng(SEED)
    snaps = [snapshot(df, o, rng) for o in ORIGINS]
    names = list(snaps[0]["models"])
    wk_actual = np.concatenate([s["actual_week"] for s in snaps])
    rows = {}
    for name in names:
        M = [s["models"][name] for s in snaps]
        lo, hi = np.concatenate([m["week_lo"] for m in M]), np.concatenate([m["week_hi"] for m in M])
        inside = (wk_actual >= lo) & (wk_actual <= hi)
        inv = np.concatenate([m["inv_in"] for m in M])
        rows[name] = {
            "per_invoice_coverage_80": round(float(inv.mean()), 3),
            "per_invoice_median_abs_err_days": round(float(np.median(np.concatenate([m["inv_err"] for m in M]))), 2),
            "per_invoice_mean_band_width_days": round(float(np.concatenate([m["inv_width"] for m in M]).mean()), 1),
            "weekly_cash_coverage_80": round(float(inside.mean()), 3),
            "weekly_cash_coverage_95ci_naive": wilson(int(inside.sum()), len(inside)),
            "weekly_cash_coverage_by_origin": [round(float(((s["actual_week"] >= m["week_lo"]) &
                                                            (s["actual_week"] <= m["week_hi"])).mean()), 3)
                                               for s, m in zip(snaps, M)],
            "weekly_band_width_mean": round(float((hi - lo).mean()), 1),
            "weekly_band_width_pct_of_mean_actual": round(float((hi - lo).mean() / wk_actual.mean()), 3),
            "weekly_cash_mae": round(float(np.abs(np.concatenate([m["week_mean"] for m in M]) - wk_actual).mean()), 1),
            "weekly_crps": round(float(np.mean([m["crps"] for m in M])), 1),
            "weeks_below_band": int((wk_actual < lo).sum()), "weeks_above_band": int((wk_actual > hi).sum()),
        }
    out = {
        "dataset": "IBM Watson sample Accounts Receivable (external public dataset we didn't generate)",
        "protocol": {"origins": [str(o.date()) for o in ORIGINS], "horizon_weeks": WEEKS, "paths": PATHS,
                     "band": "P10-P90 of simulated weekly cash", "rho_engine": RHO, "min_events_own_km": MIN_EVENTS,
                     "seed": SEED},
        "n_open_rows": int(sum(s["open"] for s in snaps)),
        "n_not_yet_due_rows": int(sum(s["not_yet_due"] for s in snaps)),
        "n_rows_using_pooled_km": int(sum(s["pooled_km_rows"] for s in snaps)),
        "weeks": len(wk_actual), "mean_weekly_actual_cash": round(float(wk_actual.mean()), 1),
        "cashcast_published": CASHCAST,
        "rows": rows,
        "shock_diagnostic": shock_diagnostic(df),
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    return out


def shock_diagnostic(df):
    """Descriptive: do same-customer invoices issued in the same month pay alike beyond the customer's own norm?"""
    d = df.assign(delay=(df["paid"] - df["invoice_date"]).dt.days, m=df["invoice_date"].dt.to_period("M"))
    d["z"] = d.groupby("buyer")["delay"].transform(lambda s: (s - s.mean()) / s.std())
    def mean_pair(groups):
        num = den = 0.0
        for _, g in groups:
            z = g["z"].to_numpy()
            k = len(z)
            if k > 1:
                num += (z.sum() ** 2 - (z ** 2).sum()) / 2
                den += k * (k - 1) / 2
        return round(float(num / den), 3), int(den)
    same, n_same = mean_pair(d.groupby(["buyer", "m"]))
    d["q"] = d["invoice_date"].dt.to_period("Q")
    qtr, n_q = mean_pair(d.groupby(["buyer", "q"]))
    return {"same_customer_same_month_corr": same, "pairs_month": n_same,
            "same_customer_same_quarter_corr": qtr, "pairs_quarter": n_q,
            "note": "pairwise correlation of within-customer standardised delay; ~0 means no shared shock to find"}


def table(out):
    r = out["rows"]
    order = [("ours, invoices independent", "Ours, invoices independent"),
             ("ours, shared buyer shock", "Ours, shared buyer shock (RHO=0.6)"),
             ("paid on the due date + residual spread", "Baseline: paid on the due date"),
             ("customer average delay + residual spread", "Baseline: per-customer average delay"),
             ("sens: shared shock rho=0.3", "Sensitivity only: shared shock, rho=0.3"),
             ("sens: shared shock rho=0.9", "Sensitivity only: shared shock, rho=0.9"),
             ("diag: pooled KM, independent", "Post-hoc diagnostic: one pooled KM for all customers")]
    lines = ["| Model | Per-invoice 80% interval hit | Weekly cash 80% band hit | Weekly band width | Weekly CRPS |",
             "|---|---|---|---|---|"]
    for k, label in order:
        x = r[k]
        lo, hi = x["weekly_cash_coverage_95ci_naive"]
        lines.append(f"| {label} | {x['per_invoice_coverage_80']:.1%} | {x['weekly_cash_coverage_80']:.1%} "
                     f"(95% CI {lo:.0%} to {hi:.0%}) | {x['weekly_band_width_mean']:,.0f} "
                     f"({x['weekly_band_width_pct_of_mean_actual']:.0%} of mean week) | {x['weekly_crps']:,.1f} |")
    c = out["cashcast_published"]
    lines.append(f"| cashcast (TabPFN), as published | {c['per_invoice_coverage_80']:.1%} | "
                 f"{c['weekly_cash_coverage_80']:.1%} | not published | not published |")
    return "\n".join(lines)


def refresh_doc(out):
    if DOC.exists():
        txt = DOC.read_text()
        new = re.sub(r"(<!-- TABLE -->\n).*?(\n<!-- /TABLE -->)", lambda m: m.group(1) + table(out) + m.group(2),
                     txt, flags=re.S)
        DOC.write_text(new)


def self_check(out):
    # protocol match: same open-invoice counts as cashcast's replay (905 open rows, 784 not yet due)
    assert out["n_open_rows"] == CASHCAST["open_rows"], out["n_open_rows"]
    assert out["n_not_yet_due_rows"] == CASHCAST["not_yet_due_rows"], out["n_not_yet_due_rows"]
    assert out["weeks"] == CASHCAST["weeks"]
    assert abs(out["mean_weekly_actual_cash"] - CASHCAST["mean_weekly_actual_cash"]) < 0.1   # same weekly actuals
    # KM sampling sanity: u=0.5 gives the median of a known sample, later u gives later delays, always > age
    t = np.arange(1, 101)
    km = {"b": arrival._km(t, np.ones(100, bool))}
    assert int(arrival.sample_delay(km, "b", 0, 0.5)) == 50
    d = arrival.sample_delay(km, "b", np.full(5, 60), np.linspace(0.05, 0.95, 5))
    assert (d > 60).all() and (np.diff(d) >= 0).all()
    # the shared shock must widen the weekly band (else it is not doing what the pitch says)
    r = out["rows"]
    assert r["ours, shared buyer shock"]["weekly_band_width_mean"] > r["ours, invoices independent"]["weekly_band_width_mean"]
    # CRPS of a perfect point forecast is 0; of a wide ensemble it is positive
    assert crps(np.full((10, 1), 3.0), np.array([3.0])) == 0 and crps(np.arange(10.0)[:, None], np.array([5.0])) > 0
    print("self-check ok")


if __name__ == "__main__":
    out = run()
    self_check(out)
    refresh_doc(out)
    print(table(out))
    print(json.dumps(out["shock_diagnostic"], indent=1))
    for k, v in out["rows"].items():
        print(f"{k:<46} inv {v['per_invoice_coverage_80']:.3f}  wk {v['weekly_cash_coverage_80']:.3f}  "
              f"width {v['weekly_band_width_mean']:>8,.0f}  below/above {v['weeks_below_band']}/{v['weeks_above_band']}")
