"""Synthetic ledger for "Kab Tak?": Mahesh's CNC shop in Bhosari, Pune (all data is made up).

Persona update vs build plan §2: turnover is now ~Rs 3 cr (about Rs 25 L/month), not Rs 4.2 cr.
At Rs 35 L/month the planned payer speeds give ~Rs 66 L receivable but only ~Rs 17 L older than
45 days. At Rs 25 L/month, with Buyer A slipping around quarter-ends and the festival, one
disputed invoice and one CPSE invoice past 180 days, we land on the persona's
Rs 46 L receivable, ~Rs 27 L of it past 45 days.

Second persona change: the OD limit is Rs 42 L (not 25 L) and drawn ~Rs 23 L. With ~Rs 41 L of
receivables under 90 days (peaking near Rs 55-60 L as planned invoices build up), a Rs 25 L limit would cap DP, and then a late buyer could not
reduce it; below the cap, receivables ageing past 90 days cut DP (the double hit). Bank practice also
nets sundry creditors (unpaid bar-stock bills) off stock before margin: see `drawing_power`.

Run `python -m engine.ledger` to rebuild the files and run the self-check.
"""
from datetime import date, timedelta
from pathlib import Path
import json

import numpy as np
import pandas as pd

TODAY = date(2026, 10, 25)
SEED = 7
HORIZON_END = date(2027, 1, 31)
GST_RATE = 0.18
TDS_RATE = 0.02          # s.194C: buyers deduct 2% of the taxable value
MATERIAL_SHARE = 0.45    # bar stock as a share of revenue
ORDER_MARGIN_PCT = 0.09  # contribution margin on a new order
BUYERS = ["Buyer A", "Buyer B", "CPSE", "Small customers"]
KINDS = ["wages", "emi", "gst", "rent", "power", "advance_tax", "bonus", "supplier"]   # obligation kinds
DP_STOCK_MARGIN = 0.25   # bank keeps 25% back on stock...
DP_RECV_MARGIN = 0.40   # ...and 40% on receivables
DP_MAX_AGE = 90          # only receivables younger than 90 days count
OD_LIMIT = 4_200_000   # persona change: was Rs 25 L; see docstring
STOCK = 1_600_000       # bar stock + WIP on the shop floor

# True medians of the generating distributions (days from invoice to payment). Buyer A is a mix:
# base median 60, but invoices raised in a quarter-end window or Oct-Nov (festival) are paid at ~75;
# the mix's median is ~64.
PLANTED_MEDIAN_DELAY = {"Buyer A": 64, "Buyer B": 45, "CPSE": 85, "Small customers": 22}

DATA = Path(__file__).resolve().parent.parent / "data" / "synthetic"
OWNER = DATA.parent / "owner_entries.json"   # owner's real invoices and bills; build() never touches it
REVENUE = 2_400_000      # taxable Rs per month, before seasonality
SHARE = {"Buyer A": 0.40, "Buyer B": 0.30, "CPSE": 0.15, "Small customers": 0.15}
N_INV = {"Buyer A": 4, "Buyer B": 3, "CPSE": 2, "Small customers": 14}   # invoices per month
SIGMA = {"Buyer A": 0.22, "Buyer B": 0.15, "CPSE": 0.30, "Small customers": 0.40}  # lognormal spread
FESTIVE = {10: 0.80, 11: 0.85}   # Oct-Nov festival slowdown in sales


def _months(start, end):
    d = start
    while d <= end:
        yield d
        d = (d.replace(day=28) + timedelta(days=4)).replace(day=1)


def _a_slips(d):
    """Buyer A pays late for quarter-end invoices (last 10 days of Mar/Jun/Sep/Dec) and in Oct-Nov."""
    qe = d.month in (3, 6, 9, 12) and d.day >= 21
    return qe or d.month in (10, 11)


def _median(buyer, d):
    return 75 if buyer == "Buyer A" and _a_slips(d) else 60 if buyer == "Buyer A" else PLANTED_MEDIAN_DELAY[buyer]


def _invoices(rng):
    rows = []
    for m in _months(date(2024, 11, 1), HORIZON_END):
        month_factor = FESTIVE.get(m.month, 1.0) * rng.uniform(0.92, 1.08)
        last = (m.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        for b in BUYERS:
            n = N_INV[b]
            w = rng.lognormal(0, 0.35, n)
            amounts = SHARE[b] * REVENUE * month_factor * w / w.sum()
            for amt in amounts:
                d = m.replace(day=int(rng.integers(1, last.day + 1)))
                delay = int(round(_median(b, d) * rng.lognormal(0, SIGMA[b])))
                rows.append([b, d, int(round(amt, -2)), delay])
    df = pd.DataFrame(rows, columns=["buyer", "invoice_date", "taxable_inr", "delay"])
    df["paid_date"] = [d + timedelta(days=int(x)) if d <= TODAY and d + timedelta(days=int(x)) <= TODAY else None
                       for d, x in zip(df.invoice_date, df.delay)]
    df["disputed"] = 0
    df["treds_accepted"] = 0
    # planted exceptions: a disputed old Buyer A invoice, and a CPSE invoice 190+ days old, both still open
    extra = pd.DataFrame([
        ["Buyer A", date(2026, 5, 12), 220_000, 0, None, 1, 0],
        ["CPSE", date(2026, 4, 12), 300_000, 0, None, 0, 0],
    ], columns=df.columns)
    df = pd.concat([df, extra], ignore_index=True).sort_values("invoice_date", kind="stable").reset_index(drop=True)
    # two recent open Buyer A invoices were accepted on TReDS
    open_a = df[(df.buyer == "Buyer A") & df.paid_date.isna() & (df.invoice_date > date(2026, 9, 1))
                & (df.invoice_date <= TODAY)]
    df.loc[open_a.index[:2], "treds_accepted"] = 1
    df["gst_inr"] = (df.taxable_inr * GST_RATE).round().astype(int)
    df["gross_inr"] = df.taxable_inr + df.gst_inr
    df["tds_inr"] = (df.taxable_inr * TDS_RATE).round().astype(int)
    df["invoice_no"] = [f"INV-{i + 1:04d}" for i in range(len(df))]
    return df[["invoice_no", "buyer", "invoice_date", "taxable_inr", "gst_inr", "gross_inr", "tds_inr",
               "paid_date", "disputed", "treds_accepted"]]


def _obligations(inv):
    """Known cash-outs TODAY+1 .. HORIZON_END."""
    rows = []
    fut = lambda d: TODAY < d <= HORIZON_END
    add = lambda d, label, kind, amt: rows.append([d, label, kind, int(round(amt, -3))]) if fut(d) else None
    inv_month = inv.groupby(pd.to_datetime(inv.invoice_date).dt.to_period("M")).taxable_inr.sum()
    for m in _months(date(2026, 9, 1), HORIZON_END):
        rev = inv_month.get(pd.Period(m, "M"), 0)
        add(date(m.year + (m.month == 12), m.month % 12 + 1, 20), "GST", "gst", GST_RATE * rev * (1 - MATERIAL_SHARE))
        for day in (1, 15):   # bar stock bought in two tranches a month, paid on 30-day terms
            add(m.replace(day=day) + timedelta(days=30), "Bar stock (supplier)", "supplier",
                MATERIAL_SHARE * rev / 2 * (1 + GST_RATE))
        add(m.replace(day=7), "Wages", "wages", 340_000)
        add(m.replace(day=5), "Machine EMI", "emi", 120_000)
        add(m.replace(day=1), "Rent", "rent", 60_000)
        add(m.replace(day=10), "Power", "power", {11: 170_000, 12: 150_000, 1: 150_000}.get(m.month, 160_000))
    add(date(2026, 11, 5), "Diwali bonus", "bonus", 280_000)   # Diwali is 8 Nov 2026
    add(date(2026, 12, 15), "Advance tax", "advance_tax", 150_000)
    return pd.DataFrame(sorted(rows), columns=["date", "label", "kind", "amount_inr"])


def drawing_power(stock_inr, recv_under_90_inr):
    """Weekly DP: (stock - sundry creditors) and young receivables after margins, capped at the OD limit.
    Creditors are held constant at today's value (position.json); fine for a 13-week horizon."""
    paid_stock = np.maximum(0, stock_inr - _creditors())
    return np.minimum(OD_LIMIT, (1 - DP_STOCK_MARGIN) * paid_stock + (1 - DP_RECV_MARGIN) * recv_under_90_inr)


_CRED = []


def _creditors():
    if not _CRED:
        if not (DATA / "position.json").exists():
            build()
        _CRED.append(json.loads((DATA / "position.json").read_text())["creditors_inr"])
    return _CRED[0]


def build():
    rng = np.random.default_rng(SEED)
    inv = _invoices(rng)
    obl = _obligations(inv)
    # Position: stock is solved so DP - drawn (headroom) is ~Rs 6 L, i.e. bank + headroom ~ a payroll + a GST bill.
    hist = inv[(inv.invoice_date <= TODAY) & inv.paid_date.isna()]
    age = (pd.Timestamp(TODAY) - pd.to_datetime(hist.invoice_date)).dt.days
    young = hist.gross_inr[age < DP_MAX_AGE].sum()
    # creditors = bar-stock bills raised up to today but not yet due (30-day terms)
    cred = int(obl[(obl.kind == "supplier") & (obl.date <= TODAY + timedelta(days=30))].amount_inr.sum())
    stock = STOCK
    dp = (1 - DP_STOCK_MARGIN) * max(0, stock - cred) + (1 - DP_RECV_MARGIN) * young
    drawn = int(round(dp - 530_000, -4))   # most of the limit drawn; headroom ~Rs 5.3 L
    DATA.mkdir(parents=True, exist_ok=True)
    inv.to_csv(DATA / "invoices.csv", index=False)
    obl.to_csv(DATA / "obligations.csv", index=False)
    (DATA / "position.json").write_text(json.dumps(
        {"bank_inr": 400_000, "od_limit_inr": OD_LIMIT, "od_drawn_inr": drawn, "stock_inr": int(stock), "creditors_inr": cred}, indent=2))


def owner_entries():
    """[{"table": "invoices" | "obligations", "row": {...}}, ...] in the order they were added."""
    return json.loads(OWNER.read_text()) if OWNER.exists() else []


def _save_entries(es):
    if es:
        OWNER.write_text(json.dumps(es, indent=2))
    else:
        OWNER.unlink(missing_ok=True)   # no entries = exactly the synthetic base data


def _add(table, row):
    e = {"table": table, "row": row}
    _save_entries(owner_entries() + [e])
    return e


def add_invoice(buyer, taxable_inr, invoice_date):
    """Owner's real invoice: GST, gross and TDS use the synthetic ledger's rates and rounding."""
    n = sum(e["table"] == "invoices" for e in owner_entries()) + 1
    gst = int(round(taxable_inr * GST_RATE))
    return _add("invoices", {"invoice_no": f"OWN-{n:04d}", "buyer": buyer, "invoice_date": invoice_date.isoformat(),
                             "taxable_inr": taxable_inr, "gst_inr": gst, "gross_inr": taxable_inr + gst,
                             "tds_inr": int(round(taxable_inr * TDS_RATE)), "paid_date": None, "disputed": 0,
                             "treds_accepted": 0})


def add_obligation(d, label, kind, amount_inr):
    return _add("obligations", {"date": d.isoformat(), "label": label, "kind": kind, "amount_inr": amount_inr})


def undo_entry():
    """Remove the last owner entry; returns it, or None if there was none."""
    es = owner_entries()
    last = es.pop() if es else None
    _save_entries(es)
    return last


def reset_entries():
    """Drop all owner entries (back to the synthetic base); returns how many were removed."""
    n = len(owner_entries())
    _save_entries([])
    return n


def load():
    if not all((DATA / f).exists() for f in ("invoices.csv", "obligations.csv", "position.json")):
        build()
    own = owner_entries()

    def merge(df, table):   # base rows untouched when there are no entries, so the baseline is exact
        rows = [e["row"] for e in own if e["table"] == table]
        df = df.assign(source="synthetic")
        return pd.concat([df, pd.DataFrame(rows).assign(source="owner")], ignore_index=True) if rows else df

    inv = merge(pd.read_csv(DATA / "invoices.csv"), "invoices")
    for c in ("invoice_date", "paid_date"):
        inv[c] = pd.to_datetime(inv[c]).dt.date
    inv["paid_date"] = inv.paid_date.astype(object).where(inv.paid_date.notna(), None)
    obl = merge(pd.read_csv(DATA / "obligations.csv"), "obligations")
    obl["date"] = pd.to_datetime(obl["date"]).dt.date
    return inv, obl, json.loads((DATA / "position.json").read_text())


if __name__ == "__main__":
    build()
    inv, obl, pos = load()
    cols = ["invoice_no", "buyer", "invoice_date", "taxable_inr", "gst_inr", "gross_inr", "tds_inr",
            "paid_date", "disputed", "treds_accepted"]
    assert list(inv.columns) == cols + ["source"] and list(obl.columns) == ["date", "label", "kind", "amount_inr", "source"]
    assert set(inv.buyer) == set(BUYERS)

    open_ = inv[(inv.invoice_date <= TODAY) & inv.paid_date.isna()]
    age = open_.invoice_date.map(lambda d: (TODAY - d).days)
    recv, over45 = int(open_.gross_inr.sum()), int(open_.gross_inr[age > 45].sum())
    assert abs(recv - 4_600_000) <= 0.05 * 4_600_000, recv
    assert abs(over45 - 2_700_000) <= 0.10 * 2_700_000, over45

    paid = inv[inv.paid_date.notna()]
    emp = paid.assign(d=[(p - i).days for p, i in zip(paid.paid_date, paid.invoice_date)]).groupby("buyer").d.median()
    for b in ("Buyer A", "Buyer B", "Small customers"):
        assert abs(emp[b] - PLANTED_MEDIAN_DELAY[b]) <= 0.15 * PLANTED_MEDIAN_DELAY[b], (b, emp[b])
    # CPSE is right-censored (slow payers are still open), so its paid-only median reads low
    assert 0.6 * PLANTED_MEDIAN_DELAY["CPSE"] <= emp["CPSE"] <= 1.05 * PLANTED_MEDIAN_DELAY["CPSE"], emp["CPSE"]

    assert set(obl.kind) == set(KINDS)
    assert obl.date.min() > TODAY and obl.date.max() <= HORIZON_END
    assert all(d.day == 20 for d in obl[obl.kind == "gst"].date)
    assert all(d.day == 7 for d in obl[obl.kind == "wages"].date)
    assert all(d.day == 5 for d in obl[obl.kind == "emi"].date)
    assert (inv.invoice_date > TODAY).any() and inv[inv.invoice_date > TODAY].paid_date.isna().all()

    young = open_.gross_inr[age < DP_MAX_AGE].sum()
    assert 1_500_000 <= pos["stock_inr"] <= 3_000_000 and pos["bank_inr"] == 400_000
    dp = float(drawing_power(pos["stock_inr"], young))
    assert dp <= 0.9 * pos["od_limit_inr"], dp   # uncapped, so ageing past 90 days really cuts DP
    headroom = dp - pos["od_drawn_inr"]
    assert 500_000 <= headroom <= 700_000, headroom
    monthly = inv.groupby(pd.to_datetime(inv.invoice_date).dt.to_period("M")).taxable_inr.sum()
    print(f"receivable={recv:,} overdue_45={over45:,} ({over45 / recv:.0%}) DP={dp:,.0f} headroom={headroom:,.0f} stock={pos['stock_inr']:,} creditors={pos['creditors_inr']:,} limit={pos['od_limit_inr']:,} drawn={pos['od_drawn_inr']:,}")
    print("empirical paid median:", emp.round(1).to_dict())
    print("monthly taxable revenue (Rs L):", {str(k): round(v / 1e5, 1) for k, v in monthly.items()})
    print("ok")
