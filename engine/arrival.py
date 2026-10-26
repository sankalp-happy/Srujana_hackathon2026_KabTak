"""Payment-delay model: Kaplan-Meier survival curve per buyer.

Open invoices are right-censored (not paid *yet*), so a plain average of paid
delays would be biased towards fast payers. KM uses them correctly.
"""
import math

import numpy as np
import pandas as pd

from engine.ledger import TODAY

NEVER = 10_000  # "not paid within any horizon"
MIN_OWN = 5      # a buyer needs this many paid invoices for its own curve; fewer: the pooled curve
MIN_POOLED = 10  # a tenant needs this many paid invoices in total for a pooled curve; fewer: the default curve
DEFAULT_MEDIAN, DEFAULT_SIGMA = 45, 0.4   # default curve: lognormal, days from invoice to payment


def _km(dur: np.ndarray, event: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    t = np.unique(dur[event])                                  # sorted event days
    at_risk = (dur[None, :] >= t[:, None]).sum(axis=1)         # censored on an event day still at risk
    deaths = ((dur[None, :] == t[:, None]) & event).sum(axis=1)
    return t, np.cumprod(1 - deaths / at_risk)


def _default() -> tuple[np.ndarray, np.ndarray]:
    t = np.arange(1, 401)
    return t, np.array([0.5 * math.erfc(math.log(x / DEFAULT_MEDIAN) / DEFAULT_SIGMA / math.sqrt(2)) for x in t])


def _counts(invoices: pd.DataFrame, today):
    """(dur, event, buyer per invoice) of invoices dated on or before today; duration is censored at today if open."""
    inv = invoices[pd.to_datetime(invoices["invoice_date"]) <= pd.Timestamp(today)]
    start = pd.to_datetime(inv["invoice_date"])
    paid = pd.to_datetime(inv["paid_date"])
    event = paid.notna().to_numpy()
    dur = np.where(event, (paid - start).dt.days, (pd.Timestamp(today) - start).dt.days)
    return dur.astype(int), event, inv["buyer"].to_numpy()


def source(invoices: pd.DataFrame, today=TODAY, buyers=()) -> dict[str, str]:
    """Which curve each buyer gets: "own", "pooled" (fewer than MIN_OWN paid) or "default" (tenant under MIN_POOLED paid)."""
    dur, event, who = _counts(invoices, today)
    names = list(dict.fromkeys([*buyers, *np.unique(who)]))
    if event.sum() < MIN_POOLED:
        return {b: "default" for b in names}
    return {b: "own" if event[who == b].sum() >= MIN_OWN else "pooled" for b in names}


def fit(invoices: pd.DataFrame, today=TODAY, buyers=()) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Per buyer (those listed plus any in the invoices): (t, S) with S[i] = P(delay > t[i]). Future invoices are
    ignored. Buyers with thin history use the pooled or the default curve, see `source`."""
    dur, event, who = _counts(invoices, today)
    how = source(invoices, today, buyers)
    curves = {"pooled": _km(dur, event) if event.sum() >= MIN_POOLED else None, "default": _default()}
    return {b: _km(dur[who == b], event[who == b]) if h == "own" else curves[h] for b, h in how.items()}


def sample_delay(km, buyer: str, age_days, u) -> np.ndarray:
    """Total delay (days from invoice) by inverse CDF of S(t)/S(age); always > age.

    Smallest t with S(t) <= (1-u)*S(age). NEVER if the KM tail never gets that low.
    """
    t, S = km[buyer]
    age, u = np.broadcast_arrays(np.asarray(age_days), np.asarray(u, dtype=float))
    k = np.searchsorted(t, age, side="right")                  # events at or before age
    s_age = np.where(k > 0, S[np.maximum(k - 1, 0)], 1.0)
    i = np.searchsorted(-S, -(1 - u) * s_age, side="left")     # first S[i] <= target (S is non-increasing)
    out = np.where(i < len(t), t[np.minimum(i, len(t) - 1)], NEVER)
    return np.maximum(out, age + 1).astype(int)                # S(age)=0 edge: just past age


def median_delay(km, buyer: str) -> float:
    t, S = km[buyer]
    i = np.searchsorted(-S, -0.5, side="left")
    return float(t[i]) if i < len(t) else float(NEVER)


if __name__ == "__main__":
    from engine.ledger import BUYERS, PLANTED_MEDIAN_DELAY, load

    inv, _, _ = load()
    km = fit(inv, buyers=BUYERS)
    rng = np.random.default_rng(0)
    u = rng.uniform(1e-6, 1 - 1e-6, 20_000)
    print(f"{'buyer':<16}{'planted':>8}{'fitted':>8}{'sampled':>8}")
    for b in BUYERS:
        planted = PLANTED_MEDIAN_DELAY[b]
        samp = float(np.median(sample_delay(km, b, np.zeros(u.size, int), u)))
        fitted = median_delay(km, b)
        print(f"{b:<16}{planted:>8}{fitted:>8.1f}{samp:>8.1f}")
        tol = max(0.15 * planted, 6)
        assert abs(samp - planted) <= tol, (b, planted, samp)
        assert abs(fitted - planted) <= tol, (b, planted, fitted)
        for a in (30, 60):
            d = sample_delay(km, b, np.full(u.size, a), u)
            assert (d > a).all(), (b, a)
        assert (np.diff(sample_delay(km, b, np.full(u.size, 10), np.sort(u))) >= 0).all(), b
    cond = np.median(sample_delay(km, "Buyer A", np.full(u.size, 60), u))
    print(f"Buyer A median | age 60: {cond:.1f}")
    assert cond >= np.median(sample_delay(km, "Buyer A", np.zeros(u.size, int), u))

    # cold start: thin history falls back to the pooled curve, then to the default (median 45 days, sigma 0.4)
    th = inv[(inv.buyer != "CPSE") | inv.paid_date.isna()].copy()
    cp = inv[(inv.buyer == "CPSE") & inv.paid_date.notna()].head(3)
    th = pd.concat([th, cp])
    assert source(th, buyers=BUYERS) == {"Buyer A": "own", "Buyer B": "own", "CPSE": "pooled", "Small customers": "own"}
    kt = fit(th, buyers=BUYERS)
    assert kt["CPSE"] is not kt["Buyer A"] and median_delay(kt, "CPSE") < 79   # pooled curve is faster than CPSE's own
    pooled = fit(th, buyers=BUYERS + ["Newcomer"])
    assert source(th, buyers=BUYERS + ["Newcomer"])["Newcomer"] == "pooled" and pooled["Newcomer"] is pooled["CPSE"]
    tiny = inv[inv.paid_date.notna()].head(9)
    kd = fit(tiny, buyers=BUYERS)
    assert set(source(tiny, buyers=BUYERS).values()) == {"default"}
    assert abs(median_delay(kd, "CPSE") - DEFAULT_MEDIAN) <= 1
    d = sample_delay(kd, "CPSE", np.zeros(u.size, int), u)
    assert abs(np.median(d) - DEFAULT_MEDIAN) <= 2 and abs(np.std(np.log(d)) - DEFAULT_SIGMA) <= 0.03
    assert (sample_delay(kd, "Buyer A", np.full(u.size, 100), u) > 100).all()
    print("ok")
