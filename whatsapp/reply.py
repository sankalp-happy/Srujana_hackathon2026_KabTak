"""English read-back and 2-line reply. Every number comes from the Scenario / EngineResult; nothing is computed here."""
from datetime import date

_d = lambda iso: f"{date.fromisoformat(iso).day} {date.fromisoformat(iso):%b}"
_inr = lambda n: f"₹{n / 1e5:g} L" if n >= 1e5 else f"₹{n:,.0f}"


def readback(s: dict) -> str:
    t, p = s["type"], s.get("party")
    what = {
        "status": "Current cash status",
        "new_order": f"New order from *{p}*\n• Value: *{_inr(s['amount_inr'] or 0)}*\n• Payment terms: *{s['days']} days*",
        "delay_payment": f"*{p}* pays *{s['days']} days* late",
        "expense_shock": f"Expense of *{_inr(s['amount_inr'] or 0)}*" + (f" on *{_d(s['date'])}*" if s.get("date") else ""),
    }.get(t, f"{t}: " + ", ".join(f"{k}={s[k]}" for k in ("party", "amount_inr", "days", "pct", "date", "obligation") if s.get(k) is not None))
    return f"Please confirm:\n\n{what}\n\nReply *yes* or *no* (text or voice)."


def format_reply(r: dict) -> str:
    w, s = r["worst_week"], r["scenario"]
    line1 = f"⚠️ *Riskiest week: {_d(w['week_start'])}*\n{round(w['p_shortfall'] * 100)}% chance of running short"
    line1 += f" _({w['obligation']})_" if w["obligation"] else ""
    o = r.get("order")
    if o and s["type"] == "new_order":
        line2 = ("✅ Safe on these terms." if o["max_safe_terms_days"] >= o["terms_days"]
                 else f"Safe terms: *{o['max_safe_terms_days']} days*\nMinimum advance: *{o['min_advance_pct']}%*")
    elif s["type"] == "delay_payment":
        k = next((k for k in r.get("kab_tak") or [] if k["buyer"] == s["party"]), None)
        line2 = f"{s['party']} can pay at most *{k['max_delay_days']} days* late before risk rises." if k else ""
    elif r.get("plan"):
        pl = r["plan"]
        line2 = f"Fix costs *{_inr(pl['total_cost_inr'])}*; risk falls to *{round(pl['p_shortfall_after'] * 100)}%*."
    else:
        line2 = f"Acceptable limit: {round(r['risk_target'] * 100)}%."
    return f"{line1}\n\n{line2}".strip()


if __name__ == "__main__":
    import json
    from pathlib import Path
    r = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "engine_result.json").read_text())
    assert "49%" in format_reply(r)
    r["worst_week"]["p_shortfall"] = 0.77
    r["plan"] = None
    assert "77%" in format_reply(r)
    assert "confirm" in readback({"type": "new_order", "party": "Bajaj", "amount_inr": 1200000, "days": 90})
    print("ok")
