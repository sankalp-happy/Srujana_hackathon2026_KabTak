"""English read-back and 2-line reply. Every number comes from the Scenario / EngineResult; nothing is computed here."""
from datetime import date

_d = lambda iso: f"{date.fromisoformat(iso).day} {date.fromisoformat(iso):%b}"
_inr = lambda n: f"₹{round(n / 1e5, 2):g} L" if n >= 1e5 else f"₹{n:,.0f}"


def entry_text(e: dict) -> str:
    """One line for a saved owner entry (as stored by engine.ledger)."""
    r = e["row"]
    if e["table"] == "invoices":
        return (f"Invoice {r['invoice_no']}: *{r['buyer']}*, {_inr(r['taxable_inr'])} + GST = *{_inr(r['gross_inr'])}*, "
                f"dated {_d(r['invoice_date'])}")
    return f"Bill: *{r['label']}*, *{_inr(r['amount_inr'])}*, due {_d(r['date'])}"


def readback(s: dict) -> str:
    t, p = s["type"], s.get("party")
    on = lambda w: f"\n• {w}: *{_d(s['date'])}*" if s.get("date") else ""
    if t in ("add_invoice", "add_obligation"):
        what = (f"Add invoice\n• Buyer: *{p}*\n• Amount: *{_inr(s['amount_inr'] or 0)}* + 18% GST{on('Dated')}"
                if t == "add_invoice" else
                f"Add bill\n• *{p or s.get('obligation')}*: *{_inr(s['amount_inr'] or 0)}*{on('Due')}")
        return f"Save this?\n\n{what}\n\nReply *yes* or *no* (text or voice). Later, *undo* removes it."
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
    if e := r.get("entry"):   # owner entry saved: show what changed against the data before it
        b, t = r["baseline"], r["today"]
        out = [f"✅ Saved. {entry_text(e)}",
               f"Riskiest-week risk: {round(b['worst_week']['p_shortfall'] * 100)}% → *{round(w['p_shortfall'] * 100)}%*"]
        if t["receivable_inr"] != b["today"]["receivable_inr"]:
            out.append(f"Buyers owe you: {_inr(b['today']['receivable_inr'])} → *{_inr(t['receivable_inr'])}*")
        if t["headroom_inr"] != b["today"]["headroom_inr"]:
            out.append(f"Overdraft room: {_inr(b['today']['headroom_inr'])} → *{_inr(t['headroom_inr'])}*")
        return "\n".join(out) + f"\n\n{line1}"
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
    rb = readback({"type": "add_invoice", "party": "Buyer A", "amount_inr": 200000, "date": "2026-10-25"})
    assert "Save this?" in rb and "₹2 L" in rb and "25 Oct" in rb
    assert "Save this?" in readback({"type": "add_obligation", "party": None, "obligation": "supplier", "amount_inr": 200000, "date": None})
    inv = {"table": "invoices", "row": {"invoice_no": "OWN-0001", "buyer": "Buyer A", "taxable_inr": 200000,
                                        "gross_inr": 236000, "invoice_date": "2026-10-25"}}
    assert "₹2.36 L" in entry_text(inv) and _inr(4_612_345) == "₹46.12 L"
    print("ok")
