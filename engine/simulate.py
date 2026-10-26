"""E3: Monte Carlo cash simulator (build plan v0.4 section 5.3).

Liquidity = net cash (bank - OD drawn) + drawing power. Shortfall = obligation that liquidity can't cover.
"""
from datetime import date, timedelta
import time

import numpy as np
import pandas as pd

from engine import arrival, ledger
from engine.ledger import P_QTR_SLIP, RHO   # the engine defaults; a tenant's profile params override them
from engine.tenants import DEFAULT

ORDER_LEAD_DAYS = 30   # new order is invoiced on dispatch, TODAY+30
_CACHE = {}            # tenant -> its ledger and fitted curves; answer.reload drops it


def _state(tenant=DEFAULT):
    """Load the tenant's ledger and fit the KM once."""
    if tenant not in _CACHE:
        prof = ledger.profile(tenant)
        inv, obl, pos = ledger.load(tenant)
        inv = inv.copy()
        inv["invoice_date"] = pd.to_datetime(inv["invoice_date"]).dt.date
        inv["paid_date"] = pd.to_datetime(inv["paid_date"]).dt.date.where(inv["paid_date"].notna(), None)
        obl = obl.copy()
        obl["date"] = pd.to_datetime(obl["date"]).dt.date
        # profile buyers in order, then any buyer that only appears in the invoices
        buyers = prof["buyers"] + [b for b in dict.fromkeys(inv["buyer"]) if b not in prof["buyers"]]
        km = arrival.fit(inv, prof["today"], buyers)
        # a new customer is assumed to pay like the tenant's middle buyer by speed (lower middle if even);
        # a business with no buyers yet (signed up without data) gives a new order no extra slip
        ref = sorted(buyers, key=lambda b: arrival.median_delay(km, b))[(len(buyers) - 1) // 2] if buyers else None
        live = inv[inv["paid_date"].isna()]            # open on today or planned future
        _CACHE[tenant] = dict(inv=inv, obl=obl, pos=pos, km=km, prof=prof, buyers=buyers, ref=ref,
                              how=arrival.source(inv, prof["today"], buyers), live=live.reset_index(drop=True))
    return _CACHE[tenant]


def _phi(x):
    """Standard normal CDF (Abramowitz-Stegun 7.1.26 erf, |err| < 1.5e-7)."""
    z = np.abs(x) / np.sqrt(2.0)
    t = 1.0 / (1.0 + 0.3275911 * z)
    poly = t * (0.254829592 + t * (-0.284496736 + t * (1.421413741 + t * (-1.453152027 + t * 1.061405429))))
    erf = 1.0 - poly * np.exp(-z * z)
    return 0.5 * (1.0 + np.sign(x) * erf)


def _next_20th(d):
    y, m = (d.year, d.month + 1) if d.month < 12 else (d.year + 1, 1)
    return date(y, m, 20)


def _qtr_map(horizon, today):
    """map[k] = day index a payment due on day k slips to (last 10 days of quarter -> first week of next)."""
    m = np.arange(horizon + 1)
    for k in range(1, horizon + 1):
        d = today + timedelta(days=k)
        q_end_month = 3 * ((d.month - 1) // 3 + 1)
        nxt = date(d.year + (q_end_month == 12), q_end_month % 12 + 1, 1)
        if (nxt - d).days <= 10:
            m[k] = (nxt - today).days + d.toordinal() % 7
    return np.minimum(m, horizon + 1)


def simulate(extra_delay=None, order=None, extra_obligations=None, n_paths=1000, horizon=90,
             seed=0, shared=True, noise=True, received=None, tenant=DEFAULT):
    """received = {buyer: (cash_inr, date)}: that buyer pays this much on that day, settling its invoices
    (dated on or before the day, not disputed) oldest first; the rest of its invoices keep their random delays."""
    S = _state(tenant)
    live, pos, km, prm = S["live"], S["pos"], S["km"], S["prof"]["params"]
    extra_delay = extra_delay or {}
    P, H, today = n_paths, horizon, S["prof"]["today"]
    buyers = S["buyers"]
    NEVER = arrival.NEVER

    # ---- invoice table: (inv_k, age, gross, receipt, buyer) incl. open, planned future, and the order ----
    inv_k = np.array([(d - today).days for d in live["invoice_date"]], dtype=int)
    age = np.maximum(-inv_k, 0)
    gross = live["gross_inr"].to_numpy(float, copy=True)   # a promised payment edits it; keep the cache clean
    receipt = gross - live["tds_inr"].to_numpy(float)
    buyer = live["buyer"].to_numpy()
    disputed = live["disputed"].to_numpy().astype(bool)
    n_live = len(live)

    # ---- promised payments: split the settled part of each invoice off into a fixed-day column ----
    fix = []                                                # (pay_k, inv_k, gross, receipt, payer)
    for b, (cash, d) in (received or {}).items():
        k, left = (d - today).days, float(cash)
        for i in sorted(np.flatnonzero((buyer == b) & ~disputed & (inv_k <= k)), key=lambda i: inv_k[i]):
            if left <= 0:
                break
            take = min(left, receipt[i])
            share = take / receipt[i]
            fix.append((k, inv_k[i], gross[i] * share, take, b))
            gross[i] -= gross[i] * share
            receipt[i] -= take
            left -= take
        if left > 0.5:
            raise ValueError(f"{b} owes only ₹{(cash - left) / 1e5:.2f} L (after TDS) on invoices dated by {d:%d %b}")

    # ---- randomness: draw everything up-front in fixed order so scenarios share random numbers ----
    rng = np.random.default_rng(seed)
    zb = rng.standard_normal((P, len(buyers)))
    zi = rng.standard_normal((P, n_live + 1))              # last column: the order
    qtr = rng.random(P) < prm["p_qtr_slip"]
    rho = prm["rho"] if shared else 0.0

    def uniforms(b_idx, cols):
        z = rho * zb[:, [b_idx]] + np.sqrt(1 - rho ** 2) * zi[:, cols]
        return np.clip(_phi(z), 1e-6, 1 - 1e-6)

    delay = np.empty((P, n_live), dtype=np.int64)
    for j, b in enumerate(buyers):
        cols = np.flatnonzero(buyer == b)
        if len(cols) == 0:
            continue
        u = uniforms(j, cols) if noise else np.full((P, len(cols)), 0.5)
        delay[:, cols] = arrival.sample_delay(km, b, age[cols], u) + extra_delay.get(b, 0)
    pay_k = inv_k + delay
    pay_k[:, disputed] = NEVER                              # disputed: never paid in the horizon

    inflow = np.zeros((P, H + 2))                           # col 0 unused, col H+1 = outside horizon
    out_day = np.zeros(H + 1)
    obl = [dict(date=r.date, label=r.label, amount_inr=float(r.amount_inr))
           for r in S["obl"].itertuples() if today < r.date <= today + timedelta(days=H)]
    extra_rows = list(extra_obligations or [])
    extra_pay_k = np.empty((P, 0), dtype=np.int64)
    extra_gross = extra_age = extra_inv_k = np.empty(0)

    if order:
        amt, adv = float(order["amount_inr"]), float(order.get("advance_pct", 0)) / 100
        d0 = today + timedelta(days=7)
        d_inv = today + timedelta(days=ORDER_LEAD_DAYS)
        g = amt * (1 + prm["gst_rate"])
        tds = amt * prm["tds_rate"]
        bar = ledger.MATERIAL_SHARE * amt
        extra_rows += [
            dict(date=d0, label="Bar stock for new order", kind="supplier", amount_inr=bar),
            dict(date=_next_20th(d_inv), label="GST on new order", kind="gst",
                 amount_inr=prm["gst_rate"] * (amt - bar)),
        ]
        slip = np.zeros(P, dtype=np.int64)
        if noise and S["ref"]:
            b = S["ref"]
            u = uniforms(buyers.index(b), [n_live])[:, 0]
            sd = arrival.sample_delay(km, b, np.zeros(1, dtype=np.int64), u)
            slip = np.maximum(0, sd - int(round(arrival.median_delay(km, b)))).astype(np.int64)
        party_extra = extra_delay.get(order.get("party"), 0)
        extra_pay_k = (ORDER_LEAD_DAYS + int(order.get("terms_days", 0)) + party_extra + slip)[:, None]
        extra_inv_k, extra_age = np.array([ORDER_LEAD_DAYS]), np.array([0])
        extra_gross = np.array([g * (1 - adv)])
        inflow[:, 7] += g * adv                              # advance, certain
        extra_receipt = np.array([g * (1 - adv) - tds])
    else:
        extra_receipt = np.empty(0)

    for r in extra_rows:
        d = pd.Timestamp(r["date"]).date()
        if today < d <= today + timedelta(days=H):
            obl.append(dict(date=d, label=r["label"], amount_inr=float(r["amount_inr"])))
    obl.sort(key=lambda r: r["date"])
    for r in obl:
        out_day[(r["date"] - today).days] += r["amount_inr"]
    is_obl = out_day > 0

    # ---- quarter-end shock: payments in last 10 days of quarter slip together ----
    all_pay = np.concatenate([pay_k, extra_pay_k], axis=1)
    if noise:
        in_h = (all_pay >= 1) & (all_pay <= H)
        shifted = _qtr_map(H, today)[np.clip(all_pay, 0, H)]
        all_pay = np.where(qtr[:, None] & in_h, shifted, all_pay)
    fk, fi, fg, fr, fp = (np.array(c) for c in zip(*fix)) if fix else (np.empty(0, int),) * 4 + (np.empty(0, object),)
    all_pay = np.concatenate([all_pay, np.broadcast_to(fk, (P, len(fk)))], axis=1)   # promised: no slip

    # ---- receipts ----
    all_receipt = np.concatenate([receipt, extra_receipt, fr])
    all_gross = np.concatenate([gross, extra_gross, fg])
    all_inv_k = np.concatenate([inv_k, extra_inv_k, fi]).astype(int)
    col = np.where((all_pay >= 1) & (all_pay <= H), all_pay, H + 1)
    flat = (np.arange(P)[:, None] * (H + 2) + col).ravel()
    inflow += np.bincount(flat, weights=np.broadcast_to(all_receipt, col.shape).ravel(),
                          minlength=P * (H + 2)).reshape(P, H + 2)
    inflow = inflow[:, 1:H + 1]
    # mean receipts per day by payer (for the expected-vs-due view and the bridge)
    payer = np.concatenate([buyer, np.array([order["party"]] if order else [], dtype=object), fp])
    by_payer = {}
    for name in dict.fromkeys(payer):
        m = payer == name
        w = np.broadcast_to(all_receipt[m], (P, m.sum())).ravel()
        by_payer[name] = np.bincount(col[:, m].ravel(), weights=w, minlength=H + 2)[1:H + 1] / P
    if order:
        by_payer[order["party"]][6] += g * adv                # the advance lands on day 7

    # ---- weekly drawing power: gross unpaid receivables younger than 90 days ----
    dp = np.zeros((P, H))
    recompute = [k for k in range(1, H + 1) if k == 1 or (today + timedelta(days=k)).weekday() == 0]
    for i, k in enumerate(recompute):
        nxt = recompute[i + 1] if i + 1 < len(recompute) else H + 1
        base = np.where((all_inv_k <= k) & (k - all_inv_k < prm["dp_max_age"]), all_gross, 0.0)
        recv = ((all_pay > k) * base).sum(axis=1)
        dp[:, k - 1:nxt - 1] = ledger.drawing_power(pos["stock_inr"], recv, tenant)[:, None]

    net0 = pos["bank_inr"] - pos["od_drawn_inr"]
    liquidity = net0 + np.cumsum(inflow - out_day[1:], axis=1) + dp
    shortfall = np.where(is_obl[1:], np.maximum(0.0, -liquidity), 0.0)

    open_ = live[live["invoice_date"] <= today]
    ages = np.array([(today - d).days for d in open_["invoice_date"]])
    g_open = open_["gross_inr"].to_numpy(float)
    dp0 = float(ledger.drawing_power(pos["stock_inr"], g_open[ages < prm["dp_max_age"]].sum(), tenant))
    return dict(
        dates=[today + timedelta(days=k) for k in range(1, H + 1)],
        liquidity=liquidity, shortfall=shortfall, inflow=inflow, dp=dp, inflow_by_payer=by_payer,
        obligations=[dict(date=r["date"], label=r["label"], amount_inr=int(round(r["amount_inr"]))) for r in obl],
        today=dict(bank_inr=int(pos["bank_inr"]), od_limit_inr=int(pos["od_limit_inr"]),
                   od_drawn_inr=int(pos["od_drawn_inr"]), drawing_power_inr=int(round(dp0)),
                   headroom_inr=int(round(dp0 - pos["od_drawn_inr"])),
                   receivable_inr=int(round(g_open.sum())),
                   overdue_45_inr=int(round(g_open[ages > 45].sum()))),
    )


def weekly(sim):
    sf, rows = sim["shortfall"], []
    for w in range(13):
        sl = sf[:, 7 * w:7 * w + 7]
        rows.append(dict(week_start=sim["dates"][0] + timedelta(days=7 * w),
                         p_shortfall=float((sl.sum(axis=1) > 0).mean()),
                         expected_shortfall_inr=float(sl.sum(axis=1).mean())))
    return rows


def p_shortfall(sim):
    return float((sim["shortfall"].sum(axis=1) > 0).mean())


def _reference(tenant=DEFAULT):
    """Plain-Python day loop at median delays (u=0.5), no randomness, for the self-check."""
    S = _state(tenant)
    live, pos, km = S["live"], S["pos"], S["km"]
    today, prm = S["prof"]["today"], S["prof"]["params"]
    rows = []                                              # (inv_date, gross, receipt, pay_date)
    for r in live.itertuples():
        a = max((today - r.invoice_date).days, 0)
        d = int(arrival.sample_delay(km, r.buyer, np.array([a]), np.array([0.5]))[0])
        pay = None if r.disputed else r.invoice_date + timedelta(days=d)
        rows.append((r.invoice_date, r.gross_inr, r.gross_inr - r.tds_inr, pay))
    oblig = {}
    for r in S["obl"].itertuples():
        oblig[r.date] = oblig.get(r.date, 0) + r.amount_inr
    cash, dp, out = pos["bank_inr"] - pos["od_drawn_inr"], 0.0, []
    for k in range(1, 91):
        d = today + timedelta(days=k)
        cash += sum(rc for _, _, rc, pay in rows if pay == d)
        if k == 1 or d.weekday() == 0:
            recv = sum(g for idt, g, _, pay in rows
                       if idt <= d and (d - idt).days < prm["dp_max_age"] and (pay is None or pay > d))
            dp = min(pos["od_limit_inr"], float(ledger.drawing_power(pos["stock_inr"], recv, tenant)))
        cash -= oblig.get(d, 0)
        out.append(cash + dp)
    return np.array(out)


if __name__ == "__main__":
    # 1. zero variance == plain day loop
    s0 = simulate(n_paths=3, noise=False)
    assert (s0["liquidity"] == s0["liquidity"][0]).all() and (s0["shortfall"] == s0["shortfall"][0]).all()
    ref = _reference()
    err = np.abs(s0["liquidity"][0] - ref).max()
    assert err < 1, f"deterministic path differs from reference by {err}"

    # 2. shared shock widens the inflow band (weekly flows are lumpy, so the effect shows mostly cumulatively)
    def band(sh):
        s = simulate(n_paths=2000, seed=1, shared=sh)
        wk = np.stack([s["inflow"][:, 7 * w:7 * w + 7].sum(1) for w in range(13)], axis=1)
        cum = np.cumsum(wk, axis=1)
        w = lambda a: float(np.mean(np.percentile(a, 90, axis=0) - np.percentile(a, 10, axis=0)))
        return w(wk), w(cum)
    (w_sh, c_sh), (w_ind, c_ind) = band(True), band(False)
    print(f"P10-P90 band, weekly inflow:     shared Rs {w_sh:,.0f}  independent Rs {w_ind:,.0f}")
    print(f"P10-P90 band, cumulative inflow: shared Rs {c_sh:,.0f}  independent Rs {c_ind:,.0f}")
    assert w_sh >= w_ind and c_sh > 1.15 * c_ind

    # 3. sanity
    t0 = time.time()
    base = simulate()
    dt = time.time() - t0
    assert base["liquidity"].shape == (1000, 90) == base["shortfall"].shape and (base["shortfall"] >= 0).all()
    assert abs(base["today"]["receivable_inr"] - 4_600_000) < 300_000, base["today"]
    ds = [o["date"] for o in base["obligations"]]
    assert ds == sorted(ds)
    p0 = p_shortfall(base)
    p_ord = p_shortfall(simulate(order=dict(party="Buyer B", amount_inr=1_200_000, terms_days=90, advance_pct=0)))
    p_del = p_shortfall(simulate(extra_delay={"Buyer A": 30}))
    assert p_ord > p0, (p_ord, p0)
    assert p_del >= p0, (p_del, p0)
    print(f"today {base['today']}")
    print(f"base p_shortfall {p0:.3f}  with Rs12L/90d order {p_ord:.3f}  Buyer A +30d {p_del:.3f}  ({dt:.2f}s/call)")
    wk = weekly(base)
    for r in wk:
        print(f"  {r['week_start']}  p={r['p_shortfall']:.2f}  E[short]=Rs {r['expected_shortfall_inr']:,.0f}")
    worst = max(wk, key=lambda r: r["p_shortfall"])
    print("worst week:", worst["week_start"], f"p={worst['p_shortfall']:.2f}")
    print("ok")
