"""Self-check for owner entries (real invoices and bills added over WhatsApp).

Run: python3 -m engine.test_owner_entries   (also collected by pytest). Works on a freshly built demo tenant in a temp folder, never data/.
"""
import json
import tempfile
from datetime import timedelta
from pathlib import Path

from engine import answer as A, ledger, tenants

T = ledger.TODAY


def test_owner_entries():
    real = tenants.DATA_ROOT
    tenants.DATA_ROOT = Path(tempfile.mkdtemp())   # the demo tenant is rebuilt there (seed 7), no owner entries
    A.reload()
    try:
        base = A.answer({"type": "status"})
        same = lambda r: json.dumps(r, sort_keys=True) == json.dumps(base, sort_keys=True)

        # open invoice dated today: receivables and drawing power go up; GST/TDS computed in code
        inv = A.answer({"type": "add_invoice", "party": "Buyer A", "amount_inr": 200_000, "date": T.isoformat()})
        row = inv["entry"]["row"]
        assert (row["gst_inr"], row["gross_inr"], row["tds_inr"]) == (36_000, 236_000, 4_000), row
        assert row["invoice_no"] == "OWN-0001" and ledger.load()[0].source.iloc[-1] == "owner"
        assert inv["today"]["receivable_inr"] == base["today"]["receivable_inr"] + 236_000
        assert inv["today"]["drawing_power_inr"] > base["today"]["drawing_power_inr"]
        assert inv["baseline"]["worst_week"] == base["worst_week"]
        print("invoice  receivable", base["today"]["receivable_inr"], "->", inv["today"]["receivable_inr"],
              " drawing power", base["today"]["drawing_power_inr"], "->", inv["today"]["drawing_power_inr"])
        assert A.undo()["row"] == row and same(A.answer({"type": "status"}))   # undo: baseline back exactly
        assert A.undo() is None

        # a real bill in the riskiest week raises the chance of a shortfall
        due = (T + timedelta(days=16)).isoformat()   # 10 Nov
        bill = A.answer({"type": "add_obligation", "party": "Machine repair", "obligation": "supplier",
                         "amount_inr": 500_000, "date": due})
        p0, p1 = base["n_short_paths"] / base["n_paths"], bill["n_short_paths"] / bill["n_paths"]
        assert p1 > p0 and bill["worst_week"]["p_shortfall"] > base["worst_week"]["p_shortfall"]
        assert any(o["label"] == "Machine repair" and o["date"] == due for o in bill["obligations"])
        print(f"bill     p_shortfall {p0:.3f} -> {p1:.3f}  worst week {base['worst_week']['p_shortfall']} -> "
              f"{bill['worst_week']['p_shortfall']}")
        A.answer({"type": "add_invoice", "party": "CPSE", "amount_inr": 100_000, "date": (T + timedelta(days=20)).isoformat()})
        assert A.answer({"type": "status"})["n_short_paths"] != base["n_short_paths"]   # later questions see the entries
        assert A.reset() == 2 and not ledger._owner(tenants.DEFAULT).exists() and same(A.answer({"type": "status"}))

        # rejected before anything is written
        for bad in ({"type": "add_invoice", "party": "Bajaj", "amount_inr": 100_000, "date": T.isoformat()},
                    {"type": "add_obligation", "party": "x", "obligation": "supplier", "amount_inr": 1, "date": T.isoformat()},
                    {"type": "add_obligation", "party": "x", "obligation": "repair", "amount_inr": 1, "date": due},
                    {"type": "add_invoice", "party": "Buyer B", "amount_inr": 0, "date": T.isoformat()}):
            try:
                A.answer(bad)
            except ValueError as e:
                print("rejected:", e)
            else:
                raise AssertionError(bad)
        assert ledger.owner_entries() == []
    finally:
        tenants.DATA_ROOT = real
        A.reload()


if __name__ == "__main__":
    test_owner_entries()
    print("ok")
