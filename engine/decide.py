"""E4: decisions on top of the simulator: 'kab tak?' (how late can a buyer pay) and safest order terms.

All runs use the same seed (common random numbers), so risk is monotone in delay / terms / advance.
"""
from engine import simulate as sm
from engine.tenants import DEFAULT


def threshold(p_base, risk_target=0.05):
    """Risk we tolerate: the target, or 'risk target points above where we already are'."""
    return risk_target if p_base <= risk_target else p_base + risk_target


_P = {}   # (tenant, delay, order, n_paths, seed) -> p_shortfall; answer.reload drops a tenant's keys


def _p(tenant, delay, order, n_paths, seed):
    """p_shortfall of one scenario. delay = ((buyer, days),...), order = ((key, value),...) or None."""
    k = (tenant, delay, order, n_paths, seed)
    if k not in _P:
        sim = sm.simulate(extra_delay=dict(delay) or None, order=dict(order) if order else None,
                          n_paths=n_paths, seed=seed, tenant=tenant)
        _P[k] = float(sm.p_shortfall(sim))
    return _P[k]


def _run(delay=None, order=None, n_paths=1000, seed=0, tenant=DEFAULT):
    return _p(tenant, tuple(sorted((delay or {}).items())), tuple(sorted(order.items())) if order else None,
              n_paths, seed)


def _largest(ok, lo, hi):
    """Largest i in [lo, hi] with ok(i), assuming ok is monotone (True then False) and ok(lo) holds."""
    if ok(hi):
        return hi
    while hi - lo > 1:
        mid = (lo + hi) // 2
        lo, hi = (mid, hi) if ok(mid) else (lo, mid)
    return lo


def kab_tak(risk_target=0.05, n_paths=1000, seed=0, buyers=("Buyer A", "Buyer B", "CPSE"), base_order=None,
            tenant=DEFAULT):
    thr = threshold(_run(None, base_order, n_paths, seed, tenant), risk_target)
    return [{"buyer": b,
             "max_delay_days": _largest(lambda d: _run({b: d}, base_order, n_paths, seed, tenant) <= thr, 0, 120)}
            for b in buyers]


def order_terms(order, risk_target=0.05, n_paths=1000, seed=0, tenant=DEFAULT):
    thr = threshold(_run(None, None, n_paths, seed, tenant), risk_target)
    req = min(int(order["terms_days"]), 180)

    def p(terms=req, adv=0):
        return _run(None, {**order, "terms_days": terms, "advance_pct": adv}, n_paths, seed, tenant)

    # terms 0 can still be unsafe (the cash gap is before the invoice); the advance search runs regardless
    terms = _largest(lambda t: p(t) <= thr, 0, req) if p(0) <= thr else 0
    adv = next((a for a in range(0, 101, 5) if p(adv=a) <= thr), 100)
    return {"max_safe_terms_days": terms, "min_advance_pct": adv}


if __name__ == "__main__":
    N = 500
    A = {"Buyer A": 0}
    delays = [0, 10, 20, 40, 60, 90]
    ps = [_run({"Buyer A": d}, None, N, 0) for d in delays]
    print("Buyer A p_shortfall by delay", dict(zip(delays, [round(x, 3) for x in ps])))
    assert all(a <= b for a, b in zip(ps, ps[1:])), "not monotone in delay"

    kt = kab_tak(n_paths=N)
    print("kab_tak", kt)
    thr = threshold(_run(None, None, N, 0))
    d = kt[0]["max_delay_days"]
    assert _run({"Buyer A": d}, None, N, 0) <= thr
    assert d == 120 or _run({"Buyer A": d + 1}, None, N, 0) > thr, "bisection boundary wrong"

    o = {"party": "New buyer", "amount_inr": 1_200_000, "terms_days": 90, "advance_pct": 0}
    ot = order_terms(o, n_paths=N)
    print("order_terms", ot, "threshold", round(thr, 3))
    def po(t, a): return _run(None, {**o, "terms_days": t, "advance_pct": a}, N, 0)
    assert all(po(t, 0) <= po(t + 15, 0) for t in range(0, 90, 15)), "shorter terms riskier"
    assert all(po(90, a + 20) <= po(90, a) for a in range(0, 80, 20)), "more advance riskier"
    assert po(ot["max_safe_terms_days"], 0) <= thr or ot["max_safe_terms_days"] == 0
    a = ot["min_advance_pct"]
    assert po(90, a) <= thr and (a == 0 or po(90, a - 5) > thr), "min advance not minimal"
    print("ok")
