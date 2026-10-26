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


def _group(n) -> str:  # Indian digit grouping: 2000000 -> 20,00,000
    s = str(int(n))
    if len(s) <= 3:
        return s
    head, tail, parts = s[:-3], s[-3:], []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    return ",".join(([head] if head else []) + parts + [tail])


_full = lambda iso: f"{date.fromisoformat(iso).day} {date.fromisoformat(iso):%b %Y}"
_money = lambda s: None if s.get("amount_inr") is None else (
    f"₹{round(s['amount_inr'] / 1e5, 2):g} L (₹{_group(s['amount_inr'])})" if s["amount_inr"] >= 1e5 else f"₹{_group(s['amount_inr'])}")
_n = lambda s, k, unit: s.get(k) is not None and f"{s[k]}{unit}"
# type -> (title, fields as (label, value) built only from the parsed Scenario)
FIELDS = {
    "status": ("Cash status check", lambda s: []),
    "new_order": ("New customer order", lambda s: [("Buyer", s.get("party")), ("Order value", _money(s)), ("Payment terms", _n(s, "days", " days"))]),
    "delay_payment": ("Buyer pays late", lambda s: [("Buyer", s.get("party")), ("Delay", _n(s, "days", " days"))]),
    "expense_shock": ("One-off expense", lambda s: [("Amount", _money(s)), ("Date", s.get("date") and _full(s["date"]))]),
    "sales_drop": ("Sales drop", lambda s: [("Drop", _n(s, "pct", "%")), ("Lasting", _n(s, "days", " days"))]),
    "supplier_terms": ("Supplier payment terms change", lambda s: [("Supplier", s.get("party")), ("New terms", _n(s, "days", " days"))]),
    "schedule_change": ("Move a payment date", lambda s: [("Payment", s.get("obligation") and s["obligation"].upper()),
                                                          ("New date", s.get("date") and _full(s["date"]))]),
    "payment_received": ("Incoming payment (a Buyer invoice being paid)", lambda s: [
        ("Buyer", s.get("party")), ("Amount", _money(s)), ("Date", s.get("date") and _full(s["date"]))]),
}


def readback(s: dict, gst_rate: float = 0.18) -> str:
    t, p = s["type"], s.get("party")
    on = lambda w: f"\n• {w}: *{_d(s['date'])}*" if s.get("date") else ""
    if t in ("add_invoice", "add_obligation"):
        what = (f"Add invoice\n• Buyer: *{p}*\n• Amount: *{_inr(s['amount_inr'] or 0)}* + {gst_rate * 100:g}% GST{on('Dated')}"
                if t == "add_invoice" else
                f"Add bill\n• *{p or s.get('obligation')}*: *{_inr(s['amount_inr'] or 0)}*{on('Due')}")
        return f"Save this?\n\n{what}\n\nReply *yes* or *no* (text or voice). Later, *undo* removes it."
    title, rows = FIELDS.get(t, (t, lambda s: [(k, s[k]) for k in ("party", "amount_inr", "days", "pct", "date", "obligation") if s.get(k) is not None]))
    what = f"*{title}*\n" + "\n".join(f"• {k}: *{v}*" for k, v in rows(s) if v)
    return f"Please confirm:\n\n{what}\n\nReply *yes* or *no* (text or voice)."


def format_reply(r: dict) -> str:
    out = _reply(r)
    if any(a["name"] == "Payment timing" for a in r.get("assumptions") or []):   # default or pooled payment curve
        out += "\n\n_Forecasts get sharper as you add more invoices. For now some buyers use a standard payment pattern._"
    return out


def _reply(r: dict) -> str:
    w, s = r["worst_week"], r["scenario"]
    ok = w["p_shortfall"] <= r["risk_target"]
    line1 = (f"✅ *Riskiest week: {_d(w['week_start'])}*\n{round(w['p_shortfall'] * 100)}% chance of running short, "
             f"inside your {round(r['risk_target'] * 100)}% limit" if ok else
             f"⚠️ *Riskiest week: {_d(w['week_start'])}*\n{round(w['p_shortfall'] * 100)}% chance of running short")
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
                 else f"Even payment on delivery isn't safe. Ask for at least *{o['min_advance_pct']}%* advance."
                 if not o["max_safe_terms_days"] else
                 f"Safe terms: *{o['max_safe_terms_days']} days*\nMinimum advance: *{o['min_advance_pct']}%*")
    elif s["type"] == "delay_payment":
        k = next((k for k in r.get("kab_tak") or [] if k["buyer"] == s["party"]), None)
        line2 = f"{s['party']} can pay at most *{k['max_delay_days']} days* late before risk rises." if k else ""
    elif s["type"] == "payment_received" and r.get("baseline"):
        line2 = (f"Riskiest-week risk vs current forecast: {round(r['baseline']['worst_week']['p_shortfall'] * 100)}% → "
                 f"*{round(w['p_shortfall'] * 100)}%*\n_Its oldest open invoices are paid on that day; nothing is saved._")
    elif r.get("plan"):
        pl = r["plan"]
        line2 = f"Fix costs *{_inr(pl['total_cost_inr'])}*; risk falls to *{round(pl['p_shortfall_after'] * 100)}%*."
    else:
        line2 = "" if ok else f"Acceptable limit: {round(r['risk_target'] * 100)}%."
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
    assert _group(2000000) == "20,00,000" and _group(9000) == "9,000" and _group(123456) == "1,23,456"
    for t in FIELDS:
        assert "• " in readback({"type": t, "party": "Buyer A", "amount_inr": 2000000, "days": 5, "pct": 20, "date": "2026-11-03", "obligation": "emi"}) or t == "status"
    rb = readback({"type": "add_invoice", "party": "Buyer A", "amount_inr": 200000, "date": "2026-10-25"})
    assert "Save this?" in rb and "₹2 L" in rb and "25 Oct" in rb and "+ 18% GST" in rb
    assert "+ 5% GST" in readback({"type": "add_invoice", "party": "Om Traders", "amount_inr": 200000, "date": None}, 0.05)
    assert "Save this?" in readback({"type": "add_obligation", "party": None, "obligation": "supplier", "amount_inr": 200000, "date": None})
    inv = {"table": "invoices", "row": {"invoice_no": "OWN-0001", "buyer": "Buyer A", "taxable_inr": 200000,
                                        "gross_inr": 236000, "invoice_date": "2026-10-25"}}
    pr = dict(r, scenario={**r["scenario"], "type": "payment_received"}, baseline={"worst_week": {"p_shortfall": 0.02}})
    assert "2% → *77%*" in format_reply(pr)
    assert format_reply(r).startswith("⚠️") and "Safe terms: *60 days*" in format_reply(r) and "sharper" not in format_reply(r)
    safe = dict(r, worst_week={**r["worst_week"], "p_shortfall": 0.03}, plan=None, scenario={**r["scenario"], "type": "status"}, order=None)
    assert format_reply(safe).startswith("✅") and "3% chance of running short, inside your 5% limit" in format_reply(safe) and "⚠️" not in format_reply(safe)
    cash = dict(r, order={**r["order"], "max_safe_terms_days": 0, "min_advance_pct": 30})
    assert "Even payment on delivery isn't safe. Ask for at least *30%* advance." in format_reply(cash) and "Safe terms" not in format_reply(cash)
    assert "_Forecasts get sharper" in format_reply(dict(r, assumptions=[{"name": "Payment timing", "value": "default curve"}]))
    assert "₹2.36 L" in entry_text(inv) and _inr(4_612_345) == "₹46.12 L"
    print("ok")
