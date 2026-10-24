"""E5: answer(scenario) -> EngineResult dict (shape of fixtures/engine_result.json)."""
from datetime import date, datetime, timedelta

import numpy as np

from engine import decide, ledger, simulate as sm

RISK_TARGET = 0.05
KEYS = ["type", "party", "amount_inr", "days", "pct", "date", "obligation", "transcript",
        "needs_clarification", "question"]
SUPPORTED = {"status": [], "new_order": ["party", "amount_inr", "days"],
             "delay_payment": ["party", "days"], "expense_shock": ["amount_inr", "date"]}
KNOWN = {"status", "new_order", "delay_payment", "expense_shock", "sales_drop", "supplier_terms",
         "schedule_change", "payment_received"}


def _check(s):
    if not isinstance(s, dict):
        raise ValueError("Scenario must be a dict")
    t = s.get("type")
    if t not in KNOWN:
        raise ValueError(f"Unknown scenario type: {t!r}")
    if s.get("needs_clarification"):
        raise ValueError(s.get("question") or "Scenario needs clarification")
    if t not in SUPPORTED:
        raise ValueError(f"{t} not supported yet")
    for f in SUPPORTED[t]:
        if s.get(f) is None:
            raise ValueError(f"{t} needs '{f}'")
    a, d = s.get("amount_inr"), s.get("days")
    if "amount_inr" in SUPPORTED[t] and (isinstance(a, bool) or not isinstance(a, int) or a <= 0):
        raise ValueError("amount_inr must be a positive whole number of rupees")
    if "days" in SUPPORTED[t] and (isinstance(d, bool) or not isinstance(d, int) or not 0 <= d <= 365):
        raise ValueError("days must be a whole number from 0 to 365")
    if t == "delay_payment" and s["party"] not in ledger.BUYERS:
        raise ValueError(f"Unknown party {s['party']!r}; expected one of {', '.join(ledger.BUYERS)}")
    if t == "new_order" and not (isinstance(s["party"], str) and s["party"].strip()):
        raise ValueError("party must be a name")


def _shock_date(s):
    try:
        d = datetime.strptime(s["date"], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        raise ValueError("date must be YYYY-MM-DD")
    if not ledger.TODAY < d <= ledger.TODAY + timedelta(days=90):
        raise ValueError("date must fall within the next 90 days")
    return d


def _pct(x, step=1000.0):
    return [float(v) for v in np.round(x / step) * step]


def _worst(weeks, obligations):
    w = max(weeks, key=lambda r: r["p_shortfall"])
    start = date.fromisoformat(w["week_start"])
    due = [f"{o['label']} {date.fromisoformat(o['date']).day} {date.fromisoformat(o['date']):%b}"
           for o in obligations if start <= date.fromisoformat(o["date"]) < start + timedelta(days=7)]
    return {"week_start": w["week_start"], "p_shortfall": w["p_shortfall"], "obligation": ", ".join(due)}


# Contract due dates for the expected-vs-due view: MSMED s.15 caps agreed terms at 45 days
TERMS_DAYS = {"Buyer A": 45, "Buyer B": 45, "CPSE": 45, "Small customers": 30}
N_SAMPLE = 30
CURVE_DELAYS = list(range(0, 61, 5))


def _sample_paths(sim):
    """~30 paths picked evenly by rank of their lowest liquidity, so safe and short paths both show."""
    liq, short = sim["liquidity"], sim["shortfall"].sum(axis=1) > 0
    order = np.argsort(liq.min(axis=1))
    pick = order[np.linspace(0, len(order) - 1, N_SAMPLE).round().astype(int)]
    return [{"values": _pct(liq[i]), "short": bool(short[i])} for i in pick]


def _arrivals(sim):
    """Per payer: receipts due on contract dates vs mean simulated receipts, by week (net of TDS)."""
    live, today, start = sm._state()["live"], ledger.TODAY, sim["dates"][0]
    out = []
    rank = lambda kv: ledger.BUYERS.index(kv[0]) if kv[0] in ledger.BUYERS else len(ledger.BUYERS)
    for b, exp in sorted(sim["inflow_by_payer"].items(), key=rank):
        rows = live[live.buyer == b]
        due = np.zeros(13)
        for r in rows.itertuples():
            k = max(0, (r.invoice_date + timedelta(days=TERMS_DAYS[b]) - start).days) // 7   # overdue -> week 1
            if k < 13:
                due[k] += r.gross_inr - r.tds_inr
        opened = rows[rows.invoice_date <= today].gross_inr.sum()
        out.append({"buyer": b, "open_inr": int(opened),
                    "due_by_week_inr": [int(round(x)) for x in due],
                    "expected_by_week_inr": [int(round(exp[7 * w:7 * w + 7].sum())) for w in range(13)]})
    return out


def _bridge(sim, worst):
    """Mean path from today to the last day of the worst week: start + receipts - obligations + change in DP = end."""
    start_day = sim["dates"][0]
    end_k = (date.fromisoformat(worst["week_start"]) - start_day).days + 6          # index of last day
    end_date = start_day + timedelta(days=end_k)
    pos = sm._state()["pos"]
    dp0 = sim["dp"][:, 0].mean()
    start = pos["bank_inr"] - pos["od_drawn_inr"] + dp0     # liquidity before day 1's flows
    items = [{"label": f"Receipts: {b}", "amount_inr": int(round(v[:end_k + 1].sum()))}
             for b, v in sim["inflow_by_payer"].items() if v[:end_k + 1].sum() >= 500]
    paid = {}
    for o in sim["obligations"]:
        if o["date"] <= end_date:
            paid[o["label"]] = paid.get(o["label"], 0) + o["amount_inr"]
    items += [{"label": k, "amount_inr": -int(v)} for k, v in paid.items()]
    items.append({"label": "Change in drawing power", "amount_inr": int(round(sim["dp"][:, end_k].mean() - dp0))})
    end = float(sim["liquidity"][:, end_k].mean())
    assert abs(start + sum(i["amount_inr"] for i in items) - end) <= 500 * len(items), "bridge does not reconcile"
    return {"week_start": worst["week_start"], "start_inr": int(round(start)), "items": items,
            "end_inr": int(round(end))}


def _summary(sim, weeks, obligations, p10, p50, p90):
    return {"p_shortfall": round(sm.p_shortfall(sim), 3), "worst_week": _worst(weeks, obligations),
            "fan": {"p10": _pct(p10), "p50": _pct(p50), "p90": _pct(p90)}}


_BASE = []


def _baseline():
    """Status-run summary, cached: what things look like with no scenario."""
    if not _BASE:
        answer({"type": "status"})
    return _BASE[0]


def answer(scenario):
    _check(scenario)
    t = scenario["type"]
    order = delay = extra = None
    if t == "new_order":
        order = {"party": scenario["party"], "amount_inr": scenario["amount_inr"],
                 "terms_days": scenario["days"], "advance_pct": 0}
    elif t == "delay_payment":
        delay = {scenario["party"]: scenario["days"]}
    elif t == "expense_shock":
        extra = [{"date": _shock_date(scenario), "label": "Unplanned expense", "kind": "expense",
                  "amount_inr": scenario["amount_inr"]}]

    sim = sm.simulate(extra_delay=delay, order=order, extra_obligations=extra)
    liq = sim["liquidity"]
    p10, p50, p90 = np.percentile(liq, [10, 50, 90], axis=0)
    obligations = [{"date": o["date"].isoformat(), "label": o["label"], "amount_inr": int(o["amount_inr"])}
                   for o in sim["obligations"]]
    weeks = [{"week_start": w["week_start"].isoformat() if hasattr(w["week_start"], "isoformat") else str(w["week_start"]),
              "p_shortfall": round(float(w["p_shortfall"]), 2),
              "expected_shortfall_inr": int(round(w["expected_shortfall_inr"]))} for w in sm.weekly(sim)]

    out_order = None
    if order:
        ot = decide.order_terms(order, RISK_TARGET)
        out_order = {"party": order["party"], "amount_inr": order["amount_inr"], "terms_days": order["terms_days"],
                     **ot, "margin_inr": int(round(order["amount_inr"] * ledger.ORDER_MARGIN_PCT))}

    summary = _summary(sim, weeks, obligations, p10, p50, p90)
    worst = _worst(weeks, obligations)
    result = {
        "as_of": ledger.TODAY.isoformat(), "synthetic": True, "placeholder": False, "risk_target": RISK_TARGET,
        "scenario": {k: scenario.get(k) for k in KEYS},
        "today": {k: int(v) for k, v in sim["today"].items()},
        "fan": {"dates": [d.isoformat() for d in sim["dates"]], "p10": _pct(p10), "p50": _pct(p50), "p90": _pct(p90)},
        "obligations": obligations,
        "weeks": weeks,
        "worst_week": worst,
        "kab_tak": decide.kab_tak(RISK_TARGET, base_order=order),
        "order": out_order,
        "fixes": [],
        "plan": None,
        "assumptions": [
            {"name": "Risk target", "value": f"{RISK_TARGET:.0%} chance of a shortfall"},
            {"name": "Buyer shock", "value": f"invoices from one buyer move together (correlation {sm.RHO})"},
            {"name": "Quarter-end slip", "value": f"{sm.P_QTR_SLIP:.0%} chance payments around 31 Dec slip a week"},
            {"name": "Drawing power", "value": f"{ledger.DP_STOCK_MARGIN:.0%} margin on stock, {ledger.DP_RECV_MARGIN:.0%} on "
                                               f"receivables; receivables older than {ledger.DP_MAX_AGE} days excluded [U]"},
            {"name": "TDS", "value": f"{ledger.TDS_RATE:.0%} deducted by buyers"},
            {"name": "GST", "value": f"{ledger.GST_RATE:.0%}, due on the 20th of the next month on accrual"},
            {"name": "Kab tak rule", "value": "largest delay keeping shortfall risk at or below the risk target "
                                              "(or today's risk plus the target if already above it)"},
            {"name": "Contract terms", "value": "45 days for Buyer A, Buyer B, CPSE (MSMED s.15 cap); 30 for small customers"},
            {"name": "Data", "value": "Synthetic ledger"},
        ],
        # optional explain-the-simulation fields (additive; not in the frozen fixture)
        "n_paths": int(liq.shape[0]),
        "n_short_paths": int((sim["shortfall"].sum(axis=1) > 0).sum()),
        "sample_paths": _sample_paths(sim),
        "baseline": None if t == "status" else _baseline(),
        "arrivals": _arrivals(sim),
        "bridge": _bridge(sim, worst),
        "kab_tak_curves": [{"buyer": b, "delays": CURVE_DELAYS,
                            "p_shortfall": [round(decide._run({b: d}, order), 3) for d in CURVE_DELAYS]}
                           for b in ("Buyer A", "Buyer B", "CPSE")],
    }
    if t == "status" and not _BASE:
        _BASE.append(summary)
    return result


def _keys_match(a, f, path=""):
    # top level may carry extra optional fields; nested shapes must match exactly
    assert set(f) <= set(a) if not path else set(a) == set(f), (path, set(a) ^ set(f))
    for k, v in f.items():
        if isinstance(v, dict) and k in ("today", "fan", "worst_week", "order", "scenario"):
            if a[k] is not None:  # order is null unless the scenario has one
                _keys_match(a[k], v, k)
        elif isinstance(v, list) and v and isinstance(v[0], dict) and k in ("weeks", "obligations"):
            for r in a[k]:
                assert set(r) == set(v[0]), (k, set(r) ^ set(v[0]))


if __name__ == "__main__":
    import json, time
    f = json.load(open("fixtures/engine_result.json"))
    st = answer({"type": "status"})
    _keys_match(st, f)
    json.dumps(st)
    t0 = time.time()
    hero = answer({"type": "new_order", "party": "New buyer", "amount_inr": 1200000, "days": 90})
    secs = time.time() - t0
    _keys_match(hero, f)
    json.dumps(hero)
    assert hero["worst_week"]["p_shortfall"] >= st["worst_week"]["p_shortfall"]
    for bad in ({"type": "bogus"}, {"type": "delay_payment", "party": "Nobody", "days": 10},
                {"type": "new_order", "party": "X", "days": 30}, {"type": "sales_drop", "pct": 20, "days": 30}):
        try:
            answer(bad)
        except ValueError as e:
            print("ValueError:", e)
        else:
            raise AssertionError(bad)
    hero_order = {"party": "New buyer", "amount_inr": 1200000, "terms_days": 90, "advance_pct": 0}
    for r, o in ((st, None), (hero, hero_order)):   # explain-the-simulation fields
        assert abs(r["n_short_paths"] / r["n_paths"] - decide._run(None, o)) < 1e-9
        assert len(r["sample_paths"]) == N_SAMPLE and any(p["short"] for p in r["sample_paths"]) == (r["n_short_paths"] > 0)
        b = r["bridge"]   # reconciles: start + items = end (within rounding)
        assert abs(b["start_inr"] + sum(i["amount_inr"] for i in b["items"]) - b["end_inr"]) <= 500 * (len(b["items"]) + 2)
        # near-monotone: weekly DP recompute lets a few-day shift dodge a Monday, worth ~1 point (Buyer B +10d with the order)
        assert all(np.all(np.diff(c["p_shortfall"]) >= -0.02) for c in r["kab_tak_curves"]), "curve not monotone"
        assert all(len(a["due_by_week_inr"]) == len(a["expected_by_week_inr"]) == 13 for a in r["arrivals"])
    assert st["baseline"] is None and hero["baseline"]["worst_week"] == st["worst_week"]
    print("status worst week:", st["worst_week"], "kab_tak:", st["kab_tak"])
    print("hero worst week:", hero["worst_week"])
    print("hero kab_tak:", hero["kab_tak"])
    print("hero order:", hero["order"])
    print(f"hero answer time: {secs:.1f}s")
    print("ok")
