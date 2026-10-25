"""Onboarding ingest: read an owner's invoice sheet, map its columns, parse it, write the tenant folder.

The LLM only maps column headers to our fields (one call, headers + 5 sample rows). Dates, amounts,
GST/TDS and validation are deterministic pandas. Tenant layout: docs/planning/multi-tenant-contract.md §1.

Check:  python3 ui/ingest.py
"""
import csv, io, json, re, shutil, sys
from datetime import date, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
from engine import tenants
from engine.ledger import GST_RATE, KINDS, TDS_RATE

FIELDS = ["buyer", "invoice_date", "amount", "amount_basis", "paid_date", "invoice_no"]
INV_COLS = ["invoice_no", "buyer", "invoice_date", "taxable_inr", "gst_inr", "gross_inr", "tds_inr",
            "paid_date", "disputed", "treds_accepted"]
OBL_COLS = ["date", "label", "kind", "amount_inr"]
POSITION = ["bank_inr", "od_limit_inr", "od_drawn_inr", "stock_inr", "creditors_inr"]
MAX_BUYERS = 20   # the engine copes with about 20; the long tail of small buyers is pooled
OTHER_BUYERS = "Other customers"


# ---------- read ----------
def _cell(v):
    if v is None:
        return ""
    if hasattr(v, "date"):   # Excel date cells
        return v.date().isoformat()
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def read_table(filename, raw_bytes):
    """-> (headers, rows) of strings. Header = first row with 3+ filled cells (Tally puts titles above it).
    Blank rows and total rows ("Grand Total") are dropped."""
    name = filename.lower()
    if name.endswith(".xlsx"):
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(raw_bytes), read_only=True, data_only=True)
        grid = [[_cell(c) for c in r] for r in wb.worksheets[0].iter_rows(values_only=True)]
    elif name.endswith(".csv"):
        try:
            text = raw_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw_bytes.decode("latin-1")
        grid = [[c.strip() for c in r] for r in csv.reader(io.StringIO(text))]
    else:
        raise ValueError("Upload a .csv or .xlsx file.")
    start = next((i for i, r in enumerate(grid) if sum(bool(c) for c in r) >= 3), None)
    if start is None:
        raise ValueError("Couldn't find a header row with at least 3 columns.")
    headers = grid[start]
    rows = []
    for r in grid[start + 1:]:
        r = (r + [""] * len(headers))[:len(headers)]
        first = next((c for c in r if c), "")
        if not first or re.match(r"(?i)(grand\s+)?total\b", first):
            continue
        rows.append(r)
    return headers, rows


# ---------- map columns ----------
_KEYS = {   # header keywords, most specific first; first match wins per field
    "paid_date": ["paid date", "payment date", "date of payment", "receipt date", "received", "recd", "settled", "realis", "paid on"],
    "invoice_no": ["invoice no", "invoice number", "inv no", "inv.no", "bill no", "voucher no", "vch no", "invoice #", "ref no"],
    "buyer": ["party", "buyer", "customer", "client", "particulars", "debtor", "name"],
    "invoice_date": ["invoice date", "bill date", "inv date", "voucher date", "date"],
}
_TAXABLE, _GROSS = ["taxable", "basic", "excl", "before gst", "net amount"], ["gross", "invoice value", "invoice amount", "incl", "total", "with gst"]


def _heuristic(headers):
    low, used, m = [h.lower() for h in headers], set(), dict.fromkeys(FIELDS)
    def pick(words):
        for w in words:
            for i, h in enumerate(low):
                if i not in used and w in h:
                    used.add(i)
                    return headers[i]
    for f in ("paid_date", "invoice_no", "buyer", "invoice_date"):
        m[f] = pick(_KEYS[f])
    m["amount_basis"] = "taxable"
    for words, basis in ((_TAXABLE, "taxable"), (_GROSS, "gross"), (["amount", "value", "amt"], "taxable")):
        m["amount"] = pick(words)
        if m["amount"]:
            m["amount_basis"] = basis
            break
    return m


_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": FIELDS,
    "properties": {**{f: {"type": ["string", "null"]} for f in FIELDS if f != "amount_basis"},
                   "amount_basis": {"type": "string", "enum": ["taxable", "gross"]}},
}


def map_columns(headers, sample_rows):
    """One LLM call: headers + 5 sample rows -> {our_field: their_header | None}; amount_basis is
    "taxable" | "gross". Any LLM failure (or no key) falls back to the keyword heuristic."""
    m = _heuristic(headers)
    try:
        import llm
        sample = [dict(zip(headers, r)) for r in sample_rows[:5]]
        out = llm._chat([
            {"role": "system", "content": (
                "Map the columns of an Indian small business's sales/invoice sheet to our fields. Answer with the exact "
                "header text of the best column, or null if there is none. buyer = customer/party name; invoice_date = "
                "date the invoice was raised; amount = the invoice amount; amount_basis = taxable if that amount is before "
                "GST, gross if it includes GST; paid_date = date the customer paid (null if none); invoice_no = invoice number.")},
            {"role": "user", "content": json.dumps({"headers": headers, "sample_rows": sample}, ensure_ascii=False)}], _SCHEMA)
        for f in FIELDS:
            if f != "amount_basis" and out.get(f) in headers:
                m[f] = out[f]
            elif f in ("paid_date", "invoice_no"):
                m[f] = None   # trust the LLM's null on optional columns; keep the heuristic for required ones
        m["amount_basis"] = out.get("amount_basis") if out.get("amount_basis") in ("taxable", "gross") else m["amount_basis"]
    except Exception as e:
        print("ingest: column mapping by keywords (LLM unavailable):", e, file=sys.stderr)
    return m


# ---------- parse ----------
def _amount(s):
    """'₹1,25,000.00', 'Rs. 4,500 Dr', '(500)' -> int rupees; None if unreadable."""
    t = re.sub(r"(?i)₹|rs\.?|inr|\s|,|dr$|cr$", "", str(s))
    neg = t.startswith("(") and t.endswith(")") or t.startswith("-")
    t = t.strip("()-")
    try:
        return int(round(float(t))) * (-1 if neg else 1)
    except ValueError:
        return None


def _date(s):
    d = pd.to_datetime(str(s).strip(), dayfirst=True, errors="coerce", format="mixed") if str(s).strip() else pd.NaT
    return None if pd.isna(d) else d.date()


def parse_invoices(headers, rows, mapping):
    """Deterministic parse. -> {"rows": [one per input row: contract §1 fields + "row" (1-based) + "errors"],
    "errors": [{"row", "errors"}], "buyers": [{"buyer", "invoices", "revenue_inr"}] by revenue, valid rows only}."""
    col = lambda f: headers.index(mapping[f]) if mapping.get(f) in headers else None
    ib, idt, iam, ipd, ino = (col(f) for f in ("buyer", "invoice_date", "amount", "paid_date", "invoice_no"))
    gross_basis = mapping.get("amount_basis") == "gross"
    get = lambda r, i: r[i].strip() if i is not None else ""
    out, seen = [], set()
    for n, r in enumerate(rows, 1):
        errs, buyer = [], re.sub(r"\s+", " ", get(r, ib))
        d, p, amt = _date(get(r, idt)), _date(get(r, ipd)), _amount(get(r, iam))
        if not buyer:
            errs.append("missing buyer")
        if d is None:
            errs.append("bad date")
        if amt is None or amt <= 0:
            errs.append("bad amount")
        if get(r, ipd) and p is None:
            errs.append("bad paid date")
        elif p and d and p < d:
            errs.append("paid before invoiced")
        no = get(r, ino) or f"UP-{n:04d}"
        if no in seen:
            errs.append("duplicate invoice no")
        seen.add(no)
        tax = int(round(amt / (1 + GST_RATE))) if gross_basis and amt and amt > 0 else (amt or 0)
        gross = amt if gross_basis and amt and amt > 0 else tax + int(round(tax * GST_RATE))
        out.append({"row": n, "errors": errs, "invoice_no": no, "buyer": buyer,
                    "invoice_date": d.isoformat() if d else "", "taxable_inr": tax, "gst_inr": gross - tax,
                    "gross_inr": gross, "tds_inr": int(round(tax * TDS_RATE)), "paid_date": p.isoformat() if p else "",
                    "disputed": 0, "treds_accepted": 0})
    # merge buyers that differ only by case, keeping the first spelling
    first = {}
    for x in out:
        first.setdefault(x["buyer"].casefold(), x["buyer"])
    for x in out:
        x["buyer"] = first[x["buyer"].casefold()]
    ok = pd.DataFrame([x for x in out if not x["errors"]], columns=["buyer", "taxable_inr"])
    g = ok.groupby("buyer").taxable_inr.agg(invoices="count", revenue_inr="sum").sort_values("revenue_inr", ascending=False)
    buyers = [{"buyer": b, "invoices": int(x.invoices), "revenue_inr": int(x.revenue_inr)} for b, x in g.iterrows()]
    return {"rows": out, "errors": [{"row": x["row"], "errors": x["errors"]} for x in out if x["errors"]], "buyers": buyers}


# ---------- write ----------
def _nonneg(v, what):
    if isinstance(v, bool) or not isinstance(v, int) or v < 0:
        raise ValueError(f"{what} must be a whole number of rupees, 0 or more.")
    return v


def _obligations(recurring, today):
    """Expand (label, kind, amount, day-of-month) bills to dated rows for the next 120 days."""
    rows, end = [], today + timedelta(days=120)
    for b in recurring:
        kind, day, amt = b.get("kind"), b.get("day"), _nonneg(b.get("amount"), "Bill amount")
        if kind not in KINDS + ["other"]:
            raise ValueError(f"Bill kind {kind!r} is not one of {KINDS + ['other']}.")
        if isinstance(day, bool) or not isinstance(day, int) or not 1 <= day <= 28:
            raise ValueError("Bill day of month must be 1 to 28.")
        label = str(b.get("label") or "").strip() or kind.replace("_", " ").title()
        d = today.replace(day=1)
        while d <= end:
            due = d.replace(day=day)
            if amt and today < due <= end:
                rows.append([due.isoformat(), label, kind, amt])
            d = (d + timedelta(days=32)).replace(day=1)
    return sorted(rows)


def write_tenant(name, position, recurring, invoices):
    """Create data/tenants/<new_id>/ per contract §1 and return the tenant id. `invoices` are valid parsed
    rows (parse_invoices rows without errors); buyers past the top 19 by revenue are pooled as 'Other customers'."""
    name = re.sub(r"\s+", " ", str(name or "")).strip()
    if not 0 < len(name) <= 80:
        raise ValueError("Business name is required (80 characters at most).")
    pos = {k: _nonneg(position.get(k, 0), k) for k in POSITION}
    obl = _obligations(recurring or [], date.today())
    inv = pd.DataFrame(invoices or [], columns=INV_COLS)
    rev = inv.groupby("buyer").taxable_inr.sum().sort_values(ascending=False)
    if len(rev) > MAX_BUYERS:
        keep = set(rev.index[:MAX_BUYERS - 1])
        inv["buyer"] = inv.buyer.where(inv.buyer.isin(keep), OTHER_BUYERS)
        rev = inv.groupby("buyer").taxable_inr.sum().sort_values(ascending=False)
    tid = tenants.new_id(name)
    final = tenants.tenant_dir(tid)
    tmp = final.with_name(final.name + ".tmp")
    tmp.mkdir(parents=True)
    try:
        inv.to_csv(tmp / "invoices.csv", index=False)
        pd.DataFrame(obl, columns=OBL_COLS).to_csv(tmp / "obligations.csv", index=False)
        (tmp / "position.json").write_text(json.dumps(pos, indent=2))
        (tmp / "profile.json").write_text(json.dumps({
            "tenant_id": tid, "business_name": name, "buyers": list(rev.index), "today": None,
            "synthetic": False, "params": {}}, indent=2, ensure_ascii=False))
        tmp.rename(final)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    return tid


if __name__ == "__main__":
    import tempfile
    CSV = """Sales Register,,,,,,
Shree Textiles Pvt Ltd,,,,,,
Date,Particulars,Vch No.,Taxable Value,Gross Total,Payment Date,Narration
05-04-2026,Raj Fabrics,INV-1,"₹1,25,000.00","₹1,47,500.00",20-05-2026,
12/04/2026,raj fabrics,INV-2,"2,00,000",,,
15-04-2026,Meena Garments,INV-3,"Rs. 80,000.00",,10-04-2026,paid before invoice
31-02-2026,Meena Garments,INV-4,"50,000",,,bad date
20-04-2026,Meena Garments,INV-2,"10,000",,,duplicate invoice no
,,,,,,
,Nobody,INV-6,"-500",,,negative
22-04-2026,,INV-7,"9,000",,,no buyer
Grand Total,,,"4,64,000",,,
"""
    headers, rows = read_table("sales.csv", CSV.encode())
    assert headers[:3] == ["Date", "Particulars", "Vch No."] and len(rows) == 7, (headers, len(rows))
    m = _heuristic(headers)   # the LLM answer is checked by hand; the offline fallback is what the demo relies on
    assert m == {"buyer": "Particulars", "invoice_date": "Date", "amount": "Taxable Value", "amount_basis": "taxable",
                 "paid_date": "Payment Date", "invoice_no": "Vch No."}, m
    assert _heuristic(["Bill Date", "Customer Name", "Invoice Value", "Receipt Date"])["amount_basis"] == "gross"
    assert _amount("₹1,25,000.00") == 125000 and _amount("4,500 Dr") == 4500 and _amount("(500)") == -500 and _amount("x") is None
    assert _date("05-04-2026") == date(2026, 4, 5) and _date("2026-04-05") == date(2026, 4, 5) and _date("31-02-2026") is None

    p = parse_invoices(headers, rows, m)
    r = {x["row"]: x for x in p["rows"]}
    assert r[1]["errors"] == [] and (r[1]["taxable_inr"], r[1]["gst_inr"], r[1]["gross_inr"], r[1]["tds_inr"]) == (125000, 22500, 147500, 2500)
    assert r[1]["invoice_date"] == "2026-04-05" and r[1]["paid_date"] == "2026-05-20"
    assert r[2]["errors"] == [] and r[2]["buyer"] == "Raj Fabrics" and r[2]["paid_date"] == ""   # case-merged
    assert r[3]["errors"] == ["paid before invoiced"] and r[4]["errors"] == ["bad date"]
    assert r[5]["errors"] == ["duplicate invoice no"] and r[6]["errors"] == ["bad date", "bad amount"] and r[7]["errors"] == ["missing buyer"]
    assert p["buyers"] == [{"buyer": "Raj Fabrics", "invoices": 2, "revenue_inr": 325000}], p["buyers"]
    assert [e["row"] for e in p["errors"]] == [3, 4, 5, 6, 7]
    g = parse_invoices(headers, rows[:1], {**m, "amount": "Gross Total", "amount_basis": "gross"})["rows"][0]
    assert (g["taxable_inr"], g["gst_inr"], g["gross_inr"]) == (125000, 22500, 147500), g

    tenants.DATA_ROOT = Path(tempfile.mkdtemp())   # same effect as KABTAK_DATA=<tmp>: tenant_dir reads it per call
    pos = {"bank_inr": 250000, "od_limit_inr": 0, "od_drawn_inr": 0, "stock_inr": 0, "creditors_inr": 30000}
    bills = [{"label": "Wages", "kind": "wages", "amount": 90000, "day": 7}, {"label": "Rent", "kind": "rent", "amount": 0, "day": 1},
             {"label": "", "kind": "other", "amount": 5000, "day": 28}]
    tid = write_tenant("Shree Textiles!", pos, bills, [x for x in p["rows"] if not x["errors"]])
    d = tenants.tenant_dir(tid)
    assert tenants.exists(tid) and not d.with_name(d.name + ".tmp").exists()
    assert list(pd.read_csv(d / "invoices.csv").columns) == INV_COLS and len(pd.read_csv(d / "invoices.csv")) == 2
    ob = pd.read_csv(d / "obligations.csv")
    assert list(ob.columns) == OBL_COLS and set(ob.kind) == {"wages", "other"} and 3 <= (ob.kind == "wages").sum() <= 5, ob   # ~4 months in 120 days
    assert ob.date.min() > date.today().isoformat() and ob.date.max() <= (date.today() + timedelta(days=120)).isoformat()
    assert (ob[ob.kind == "wages"].date.str[-2:] == "07").all() and ob[ob.kind == "other"].label.iloc[0] == "Other"
    assert json.loads((d / "position.json").read_text()) == pos
    prof = json.loads((d / "profile.json").read_text())
    assert prof == {"tenant_id": tid, "business_name": "Shree Textiles!", "buyers": ["Raj Fabrics"], "today": None,
                    "synthetic": False, "params": {}}, prof
    assert not (d / "owner_entries.json").exists()
    t2 = write_tenant("No History Co", {}, [], [])   # no upload, all-zero position: header-only invoices
    assert list(pd.read_csv(tenants.tenant_dir(t2) / "invoices.csv").columns) == INV_COLS
    assert json.loads((tenants.tenant_dir(t2) / "profile.json").read_text())["buyers"] == []
    many = [{**r[1], "buyer": f"B{i}", "taxable_inr": 1000 + i, "invoice_no": f"X{i}"} for i in range(30)]
    t3 = tenants.tenant_dir(write_tenant("Many", {}, [], many))
    assert len(json.loads((t3 / "profile.json").read_text())["buyers"]) == MAX_BUYERS
    for bad in [lambda: write_tenant("", {}, [], []), lambda: write_tenant("x", {"bank_inr": -1}, [], []),
                lambda: write_tenant("x", {"bank_inr": 1.5}, [], []), lambda: write_tenant("x", {}, [{"kind": "tax", "amount": 1, "day": 1}], []),
                lambda: write_tenant("x", {}, [{"kind": "rent", "amount": 1, "day": 29}], []),
                lambda: write_tenant("x", {}, [{"kind": "rent", "amount": "5", "day": 1}], []), lambda: read_table("a.pdf", b"")]:
        try:
            bad()
            raise AssertionError("accepted bad input")
        except ValueError:
            pass
    print("ok")
