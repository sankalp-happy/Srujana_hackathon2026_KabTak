"""Payment-delay model: Kaplan-Meier survival curve per buyer.

Open invoices are right-censored (not paid *yet*), so a plain average of paid
delays would be biased towards fast payers. KM uses them correctly.
"""
import numpy as np
import pandas as pd

from engine.ledger import TODAY

NEVER = 10_000  # "not paid within any horizon"


def _km(dur: np.ndarray, event: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    t = np.unique(dur[event])                                  # sorted event days
    at_risk = (dur[None, :] >= t[:, None]).sum(axis=1)         # censored on an event day still at risk
    deaths = ((dur[None, :] == t[:, None]) & event).sum(axis=1)
    return t, np.cumprod(1 - deaths / at_risk)


def fit(invoices: pd.DataFrame, today=TODAY) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Per buyer: (t, S) with S[i] = P(delay > t[i]). Future invoices are ignored."""
    inv = invoices[pd.to_datetime(invoices["invoice_date"]) <= pd.Timestamp(today)]
    start = pd.to_datetime(inv["invoice_date"])
    paid = pd.to_datetime(inv["paid_date"])
    event = paid.notna().to_numpy()
    dur = np.where(event, (paid - start).dt.days, (pd.Timestamp(today) - start).dt.days)
    buyers = inv["buyer"].to_numpy()
    return {b: _km(dur[buyers == b].astype(int), event[buyers == b]) for b in np.unique(buyers)}


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
    km = fit(inv)
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
    print("ok")
