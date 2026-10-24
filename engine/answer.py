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

    return {
        "as_of": ledger.TODAY.isoformat(), "synthetic": True, "placeholder": False, "risk_target": RISK_TARGET,
        "scenario": {k: scenario.get(k) for k in KEYS},
        "today": {k: int(v) for k, v in sim["today"].items()},
        "fan": {"dates": [d.isoformat() for d in sim["dates"]], "p10": _pct(p10), "p50": _pct(p50), "p90": _pct(p90)},
        "obligations": obligations,
        "weeks": weeks,
        "worst_week": _worst(weeks, obligations),
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
            {"name": "Data", "value": "Synthetic ledger"},
        ],
    }


def _keys_match(a, f, path=""):
    assert set(a) == set(f), (path, set(a) ^ set(f))
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
    print("status worst week:", st["worst_week"], "kab_tak:", st["kab_tak"])
    print("hero worst week:", hero["worst_week"])
    print("hero kab_tak:", hero["kab_tak"])
    print("hero order:", hero["order"])
    print(f"hero answer time: {secs:.1f}s")
    print("ok")
