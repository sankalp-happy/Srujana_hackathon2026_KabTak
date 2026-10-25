"""Marathi read-back and 2-line reply. Every number comes from the Scenario / EngineResult; nothing is computed here."""
from datetime import date

MON = "जाने फेब्रु मार्च एप्रि मे जून जुलै ऑग सप्टें ऑक्टो नोव्हें डिसें".split()
_d = lambda iso: f"{date.fromisoformat(iso).day} {MON[date.fromisoformat(iso).month - 1]}"
_inr = lambda n: f"₹{n / 1e5:g} L" if n >= 1e5 else f"₹{n:,.0f}"


def readback(s: dict) -> str:
    t, p = s["type"], s.get("party")
    what = {
        "status": "सध्याची स्थिती",
        "new_order": f"नवीन ऑर्डर: {p}, {_inr(s['amount_inr'] or 0)}, {s['days']} दिवसांची मुदत",
        "delay_payment": f"{p} {s['days']} दिवस उशिरा पैसे देईल तर",
        "expense_shock": f"{_inr(s['amount_inr'] or 0)} खर्च, {_d(s['date']) if s.get('date') else ''}",
    }.get(t, f"{t}: " + ", ".join(f"{k}={s[k]}" for k in ("party", "amount_inr", "days", "pct", "date", "obligation") if s.get(k) is not None))
    return f"{what}. बरोबर आहे का? (हो / नाही)"


def format_reply(r: dict) -> str:
    w, s = r["worst_week"], r["scenario"]
    line1 = f"{_d(w['week_start'])} च्या आठवड्यात पैसे कमी पडण्याची शक्यता {round(w['p_shortfall'] * 100)}%"
    line1 += f" ({w['obligation']})." if w["obligation"] else "."
    o = r.get("order")
    if o and s["type"] == "new_order":
        line2 = ("या मुदतीवर ऑर्डर सुरक्षित आहे." if o["max_safe_terms_days"] >= o["terms_days"]
                 else f"सुरक्षित मुदत {o['max_safe_terms_days']} दिवस; किमान आगाऊ {o['min_advance_pct']}%.")
    elif s["type"] == "delay_payment":
        k = next((k for k in r.get("kab_tak") or [] if k["buyer"] == s["party"]), None)
        line2 = f"{s['party']} जास्तीत जास्त {k['max_delay_days']} दिवस उशीर सहन होतो." if k else ""
    elif r.get("plan"):
        pl = r["plan"]
        line2 = f"उपाय खर्च {_inr(pl['total_cost_inr'])}; धोका {round(pl['p_shortfall_after'] * 100)}% वर येतो."
    else:
        line2 = f"मान्य मर्यादा {round(r['risk_target'] * 100)}%."
    return f"{line1}\n{line2}".strip()


if __name__ == "__main__":
    import json
    from pathlib import Path
    r = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "engine_result.json").read_text())
    assert "49%" in format_reply(r)
    r["worst_week"]["p_shortfall"] = 0.77
    r["plan"] = None
    assert "77%" in format_reply(r)
    assert "हो" in readback({"type": "new_order", "party": "Bajaj", "amount_inr": 1200000, "days": 90})
    print("ok")
