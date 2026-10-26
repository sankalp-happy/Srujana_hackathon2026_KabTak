"""Self-check for multi-tenancy: three tiny businesses in a temp data root, answered in turn.

Run: python3 -m engine.test_tenants   (also collected by pytest). Never touches data/.
"""
import json
import os
import tempfile
from datetime import date, timedelta
from pathlib import Path

os.environ["KABTAK_DATA"] = tempfile.mkdtemp()   # before the engine reads it
from engine import answer as A, ledger, tenants

tenants.DATA_ROOT = Path(os.environ["KABTAK_DATA"])   # also right when another test imported the engine first
TODAY = date(2026, 6, 1)
STATUS = {"type": "status"}
ORDER = {"type": "new_order", "party": "Walk-in", "amount_inr": 400_000, "days": 60}


def make(tid, buyers, paid, open_, bills, position, params=None):
    """paid = [(buyer, invoice date, days to pay, taxable)], open_ = [(buyer, invoice date, taxable)]."""
    d = tenants.tenant_dir(tid)
    d.mkdir(parents=True)
    rows = [(b, i, i + timedelta(days=n), t) for b, i, n, t in paid] + [(b, i, None, t) for b, i, t in open_]
    lines = ["invoice_no,buyer,invoice_date,taxable_inr,gst_inr,gross_inr,tds_inr,paid_date,disputed,treds_accepted"]
    for n, (b, i, p, t) in enumerate(sorted(rows, key=lambda r: r[1])):
        lines.append(f"T-{n:03d},{b},{i},{t},{t * 18 // 100},{t * 118 // 100},{t * 2 // 100},{p or ''},0,0")
    (d / "invoices.csv").write_text("\n".join(lines) + "\n")
    (d / "obligations.csv").write_text("date,label,kind,amount_inr\n" + "".join(f"{x},{y},{k},{a}\n" for x, y, k, a in bills))
    (d / "position.json").write_text(json.dumps(position))
    (d / "profile.json").write_text(json.dumps({"tenant_id": tid, "business_name": tid, "buyers": buyers,
                                                "today": TODAY.isoformat(), "synthetic": True, "params": params or {}}))


def history(buyer, median, n, taxable, start=date(2025, 10, 1)):
    return [(buyer, start + timedelta(days=9 * k), median + (3 * k) % 7 - 3, taxable) for k in range(n)
            if start + timedelta(days=9 * k + median + 3) <= TODAY]


def build_tenants():
    day = lambda n: (TODAY + timedelta(days=n)).isoformat()
    # tiny: 2 buyers, 3 paid invoices in all, no overdraft and no stock, bills due soon
    make("tiny-shop", ["Shiv Traders", "Om Stores"],
         [("Shiv Traders", date(2026, 3, 1), 40, 90_000), ("Om Stores", date(2026, 3, 5), 55, 60_000),
          ("Shiv Traders", date(2026, 3, 20), 35, 80_000)],
         [("Shiv Traders", date(2026, 5, 10), 120_000), ("Om Stores", date(2026, 5, 20), 70_000)],
         [(day(10), "Wages", "wages", 60_000), (day(25), "Rent", "rent", 30_000)],
         {"bank_inr": 50_000, "od_limit_inr": 0, "od_drawn_inr": 0, "stock_inr": 0, "creditors_inr": 0})
    # big-works: 3 buyers with plenty of history, an overdraft and stock
    paid = history("Alpha", 30, 24, 150_000) + history("Beta", 50, 24, 200_000) + history("Gamma", 70, 24, 120_000)
    make("big-works", ["Alpha", "Beta", "Gamma"], paid,
         [("Alpha", date(2026, 5, 20), 150_000), ("Beta", date(2026, 5, 12), 200_000), ("Gamma", date(2026, 4, 28), 120_000)],
         [(day(7), "Wages", "wages", 200_000), (day(15), "EMI", "emi", 90_000), (day(40), "GST", "gst", 150_000)],
         {"bank_inr": 100_000, "od_limit_inr": 800_000, "od_drawn_inr": 500_000, "stock_inr": 600_000, "creditors_inr": 100_000})
    # mixed: Delta is new (2 paid invoices -> pooled curve), no bills at all, own tax rates and risk target
    make("mixed-bag", ["Alpha", "Delta"], history("Alpha", 30, 24, 150_000) + [("Delta", date(2026, 3, 1), 20, 50_000),
                                                                                ("Delta", date(2026, 3, 9), 25, 40_000)],
         [("Delta", date(2026, 5, 25), 90_000)], [],
         {"bank_inr": 20_000, "od_limit_inr": 0, "od_drawn_inr": 0, "stock_inr": 0, "creditors_inr": 0},
         {"gst_rate": 0.05, "tds_rate": 0.01, "risk_target": 0.1})


def dump(r):
    return json.dumps(r, sort_keys=True)


def test_tenants():
    build_tenants()
    A.reload()
    run = lambda tid: [A.answer(s, tid) for s in (STATUS, ORDER, {"type": "delay_payment", "party": "Alpha" if tid != "tiny-shop"
                                                                    else "Om Stores", "days": 15})]
    a1, b1, c1 = run("tiny-shop"), run("big-works"), run("mixed-bag")
    assert dump(a1[0]) != dump(b1[0])
    assert [r["tenant"] for r in a1] == ["tiny-shop"] * 3 and b1[0]["tenant"] == "big-works"

    # tiny: no overdraft, no stock, 3 paid invoices -> default curve, and it says so
    st = a1[0]
    assert st["today"]["od_limit_inr"] == st["today"]["drawing_power_inr"] == st["today"]["headroom_inr"] == 0
    note = next(a["value"] for a in st["assumptions"] if a["name"] == "Payment timing")
    assert "default curve" in note and "median 45 days" in note, note
    assert [a["buyer"] for a in st["arrivals"]] == ["Shiv Traders", "Om Stores"]
    assert [k["buyer"] for k in st["kab_tak"]] == ["Shiv Traders", "Om Stores"]
    assert a1[1]["order"]["party"] == "Walk-in" and 0 <= st["worst_week"]["p_shortfall"] <= 1

    # big: everyone on their own history, so no fallback line
    assert not any(a["name"] == "Payment timing" for a in b1[0]["assumptions"])
    assert [k["buyer"] for k in b1[0]["kab_tak"]] == ["Alpha", "Beta", "Gamma"] and b1[0]["today"]["od_limit_inr"] == 800_000
    assert ledger.profile("big-works")["buyers"] == ["Alpha", "Beta", "Gamma"]

    # mixed: Delta pooled, no bills, own params everywhere
    note = next(a["value"] for a in c1[0]["assumptions"] if a["name"] == "Payment timing")
    assert note.startswith("Delta:") and "pooled" in note and "default" not in note, note
    assert c1[0]["obligations"] == [] and c1[0]["worst_week"]["p_shortfall"] == 0 and c1[0]["risk_target"] == 0.1
    assert any(a["name"] == "GST" and a["value"].startswith("5%") for a in c1[0]["assumptions"])
    inv = A.answer({"type": "add_invoice", "party": "Delta", "amount_inr": 100_000, "date": TODAY.isoformat()}, "mixed-bag")
    assert (inv["entry"]["row"]["gst_inr"], inv["entry"]["row"]["tds_inr"]) == (5_000, 1_000)   # the tenant's own rates
    assert ledger.owner_entries("mixed-bag") and not ledger.owner_entries("big-works")
    assert A.undo("mixed-bag")["row"] == inv["entry"]["row"] and dump(A.answer(STATUS, "mixed-bag")) == dump(c1[0])

    # answering other tenants in between never changes a tenant's answer (caches are per tenant)
    assert dump(run("tiny-shop")) == dump(a1) and dump(run("big-works")) == dump(b1)
    A.reload("tiny-shop")   # a reload drops one tenant's cache only, and the answer comes back identical
    assert "tiny-shop" not in A.sm._CACHE and "big-works" in A.sm._CACHE and dump(run("tiny-shop")) == dump(a1)

    # an unknown party raises, naming that tenant's buyers and nobody else's
    for tid, party in (("tiny-shop", "Alpha"), ("big-works", "Shiv Traders")):
        try:
            A.answer({"type": "delay_payment", "party": party, "days": 5}, tid)
        except ValueError as e:
            assert all(b in str(e) for b in ledger.profile(tid)["buyers"]), e
            assert "Buyer A" not in str(e)
            print("ValueError:", e)
        else:
            raise AssertionError(party)
    try:
        A.answer(STATUS, "no-such-shop")
    except ValueError as e:
        print("ValueError:", e)
    else:
        raise AssertionError("unknown tenant")

    # a business that has only just started: no invoices, no bills
    make("fresh-start", ["Solo"], [], [], [], {"bank_inr": 10_000, "od_limit_inr": 0, "od_drawn_inr": 0, "stock_inr": 0, "creditors_inr": 0})
    (tenants.tenant_dir("fresh-start") / "invoices.csv").write_text("")
    r = A.answer(ORDER, "fresh-start")
    assert r["today"]["receivable_inr"] == 0 and "default curve" in r["assumptions"][-1]["value"] and r["order"]

    # signed up on the website with no data at all: no buyers either. Status and an order still answer, and the
    # first invoice for a new buyer adds that buyer to the profile
    make("signed-up", [], [], [], [], {"bank_inr": 50_000, "od_limit_inr": 0, "od_drawn_inr": 0, "stock_inr": 0, "creditors_inr": 0})
    (tenants.tenant_dir("signed-up") / "invoices.csv").write_text("")
    assert A.answer(STATUS, "signed-up")["today"]["bank_inr"] == 50_000 and A.answer(ORDER, "signed-up")["order"]
    A.answer({"type": "add_invoice", "party": "Sharma Traders", "amount_inr": 50_000, "date": TODAY.isoformat()}, "signed-up")
    assert ledger.profile("signed-up")["buyers"] == ["Sharma Traders"]
    assert A.answer({"type": "delay_payment", "party": "Sharma Traders", "days": 30}, "signed-up")["today"]["receivable_inr"] > 0
    A.reload()


if __name__ == "__main__":
    test_tenants()
    print("ok")
