# data/

- `tenants/<id>/`: one folder per business (layout: [multi-tenant contract](../docs/planning/multi-tenant-contract.md) §1). All three committed ones are made up:
  - `mahesh-cnc`: the Pune CNC shop the demo and the engine defaults use. Rebuilt by `python3 -m engine.ledger` (seed 7); its `profile.json` pins "today" to 2026-10-25.
  - `shree-textiles`, `sai-snacks`: two other shapes (no overdraft; a 3-month-old business), rebuilt by `python3 data/make_demo_tenants.py`.
  - Businesses that sign up on the website are created here at run time (on the VM disk; not meant to be committed). So are `owner_entries.json` (invoices and bills added on WhatsApp) and `registry.sqlite` (which phone belongs to which business); both are git-ignored.
- `samples/`: a messy TallyPrime-style sales register (Kolhapur Auto Spares, fictional) with deliberately bad rows. The sign-up page's Excel upload does **not** take it (it takes the Kab Tak? workbook); it is a test file for a future importer. The workbooks that do upload are `ui/kabtak-template.xlsx` and `ui/kabtak-demo.xlsx` (the `mahesh-cnc` ledger), built by `ui/make_template.py`.
- `raw/`: git-ignored downloads. Never commit these.

## `raw/ibm_ar.csv`: external public dataset we didn't generate

IBM Watson Analytics sample "Accounts Receivable" (also circulated as "Finance Factoring: IBM Late Payment Histories"). Used only by `validation/ibm_backtest.py`.

| | |
|---|---|
| Source | https://raw.githubusercontent.com/pthiagu2/DataMining/master/WA_Fn-UseC_-Accounts-Receivable.csv (the copy `cashcast` uses) |
| Licence | Not stated (the mirror repo has none). IBM sample data, possibly synthetic itself. Not committed. |
| Fetch | `curl -L -o data/raw/ibm_ar.csv <source URL>`; `python3 -m validation.ibm_backtest` also fetches it if missing. |
| Rows | 2,466 invoices, all settled (no open or never-paid invoices) |
| Customers | 100 (`customerID`), 15 to 36 invoices each |
| Invoice dates | 2012-01-03 to 2013-12-02 |
| Settled dates | 2012-01-13 to 2014-01-09 |
| Terms | every invoice is 30 days (`DueDate` = `InvoiceDate` + 30) |
| Columns | `countryCode, customerID, PaperlessDate, invoiceNumber, InvoiceDate, DueDate, InvoiceAmount, Disputed, SettledDate, PaperlessBill, DaysToSettle, DaysLate` |

Dates are `m/d/Y`. `DaysToSettle` equals `SettledDate - InvoiceDate` on every row. `Disputed` is "Yes" on 561 rows, yet all of them were settled, so we ignore it.
