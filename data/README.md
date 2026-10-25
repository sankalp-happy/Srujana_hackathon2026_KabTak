# data/

- `synthetic/`: the made-up Pune CNC-shop ledger the engine runs on (see `engine/ledger.py`).
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
