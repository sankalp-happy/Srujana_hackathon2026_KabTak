# Multi-tenant contract

Every parallel workstream builds against this file. If you need to change it, stop and say so in your report; don't change it silently.

**Goal:** one onboarding page, one WhatsApp bot and one engine. Each business gets its own data, and nobody gets answers from someone else's ledger.

## 1. A tenant is a folder

```
data/tenants/<tenant_id>/
  profile.json         business details + per-tenant settings (below)
  invoices.csv         same columns as today: invoice_no,buyer,invoice_date,taxable_inr,gst_inr,gross_inr,tds_inr,paid_date,disputed,treds_accepted
  obligations.csv      same columns as today: date,label,kind,amount_inr   (kind in engine.ledger.KINDS, which gains "other")
  position.json        {"bank_inr", "od_limit_inr", "od_drawn_inr", "stock_inr", "creditors_inr"}  all ints, 0 allowed (no overdraft = 0/0)
  owner_entries.json   invoices/bills added over WhatsApp (git-ignored)
```

- `tenant_id`: `[a-z0-9-]{1,40}`. Make it with `engine.tenants.new_id(name)` and resolve it with `engine.tenants.tenant_dir(tid)`.
- The demo tenant is `mahesh-cnc`, whose data lives in `data/tenants/mahesh-cnc/` (it moved there from `data/synthetic/`).
- Dates are `YYYY-MM-DD`. Amounts are whole rupees. An empty `paid_date` means the invoice is still open.

`profile.json`:
```json
{
  "tenant_id": "mahesh-cnc",
  "business_name": "Mahesh Precision Components",
  "buyers": ["Buyer A", "Buyer B", "CPSE", "Small customers"],
  "today": "2026-10-25",
  "synthetic": true,
  "params": {}
}
```
- `buyers`: the names the parser accepts as a party, in display order. It must cover every buyer in invoices.csv.
- `today`: pinned "as of" date. `null` means the real date (`date.today()`). Only synthetic tenants pin it.
- `params`: optional overrides of engine constants, by lowercase name: `gst_rate, tds_rate, dp_stock_margin, dp_recv_margin, dp_max_age, rho, p_qtr_slip, risk_target, order_margin_pct`. A missing key means the engine's default.

## 2. Registry: `engine/tenants.py` (done, frozen)
`tenant_dir`, `exists`, `new_id`, `new_join_code(tid, phone=None) -> "123456"` (with `phone`, only that number can use it), `claim(code, phone) -> tid | None`, `claim_phone(phone) -> tid | None` (links a number from its latest unused code), `unclaimed(code, tid) -> bool`, `link(phone, tid)`, `tenant_for(phone) -> tid | None`, `first_time(msg_id) -> bool`.
It stores state in SQLite at `data/registry.sqlite` (git-ignored). `KABTAK_DATA` overrides the data root, so tests use a temp folder.

## 3. Engine API (workstream A delivers it; everyone else calls it)
Every public entry point takes `tenant=` and defaults to `engine.tenants.DEFAULT`, so existing callers keep working.
- `engine.answer.answer(scenario, tenant=DEFAULT) -> dict`: same result shape as today. It adds `result["tenant"]`, plus a `result["assumptions"]` entry when a buyer uses a fallback payment curve.
- `engine.answer.undo(tenant=DEFAULT)`, `reset(tenant=DEFAULT)`, `reload(tenant=None)`. `None` clears every tenant's cache.
- `engine.ledger.profile(tenant=DEFAULT) -> dict`: profile.json with `today` as a `date`, and `params` merged over the defaults.
- `engine.ledger.load(tenant=DEFAULT) -> (invoices, obligations, position)`.
- The engine must cope with: no overdraft (`od_limit_inr = 0`), no stock, any number of buyers (1 to about 20), buyers with little or no paid history, and empty obligations.
- **Cold start:** a buyer with fewer than 5 paid invoices uses the curve pooled across the tenant's buyers. A tenant with fewer than 10 paid invoices in total uses a default curve (lognormal, median 45 days, sigma 0.4). Both are labelled in `assumptions`.
- No module-level state may leak between tenants. Caches are keyed by tenant, and a tenant's caches are dropped when the modification time or size of its `profile.json`, `invoices.csv`, `obligations.csv`, `position.json` or `owner_entries.json` changes. The bot and the web server are separate processes, so a write by one is picked up by the other on its next answer.
- Dates: a what-if (`expense_shock`, `payment_received`) dated today counts as tomorrow; otherwise the date must fall within the next 90 days.

## 4. Parser: `ui/llm.py` (signature done)
`llm.parse(text, buyers=None, today=None)`. Pass `profile["buyers"]` and `profile["today"]`; `None` means Mahesh's. The parser resolves "today" and "next week" from `max(today, the real date)`, because a demo tenant pins `today` to the past.

## 5. WhatsApp: `whatsapp/evolution_bot.py` (workstream B)
1. Drop repeated provider message ids with `tenants.first_time(data["key"]["id"])`. Acknowledge the webhook at once and do the work in a background task.
2. The first message from the number given at sign-up links it (`tenants.claim_phone`), and the bot then answers that message, starting with a welcome that names the business. This is checked before the existing link, so a number that signs up again moves to the new business. `JOIN <6 digits>` still works as a fallback (`tenants.claim()`).
3. An unknown sender gets the onboarding link (env `ONBOARD_URL`, default `http://localhost:8000/onboard`). They are never answered from any tenant's data.
4. For a known sender, `tid = tenants.tenant_for(sender)`, and every engine and parser call passes that tenant. Every type except `status` is read back and needs a yes (English, Hindi or Marathi) before it runs; `status` saves nothing and is answered at once. A WhatsApp document gets a pointer to the sign-up page. Replies are English only.

## 6. Sign-up web (workstream C, simplified)
- `GET /` serves the landing page (`landing-page/index.html`), and its CTAs link to `/onboard`. `GET /dashboard?tenant=<tid>` opens the dashboard for that tenant.
- **Step 1** collects the owner's name, the business name, the WhatsApp number (10 digits, stored as `91XXXXXXXXXX`) and an optional bank balance. `POST /api/signup` creates an empty tenant (§1, no invoices, no bills) and returns `{tenant_id, join_code, bot_number}`.
- **Step 2** offers two options. (1) Upload the Kab Tak? Excel workbook: sheets `invoices`, `obligations` and `position` with exactly the §1 columns; other sheets are ignored. `POST /api/onboard/excel {tenant_id, join_code, filename, content_b64}` (`ui/ingest.py`) checks each row, skips and reports bad rows, replaces the business's ledger and returns the first forecast. It is accepted only while the sign-up's join code is unused, so it works before the number is linked and not after. The page offers `/kabtak-template.xlsx` (blank, with two example rows) and `/kabtak-demo.xlsx` (the `mahesh-cnc` ledger), both written by `ui/make_template.py` from `ui/ingest.py`'s column lists. (2) WhatsApp: a `wa.me/<BOT_NUMBER>` link pre-filled with "What is the status of my current cash flow?". Without an upload, a disclaimer and a Terms tick must be accepted first.
- **The join code is bound to the signup number:** `tenants.claim` refuses it from any other number.
- **A tenant with no data:** the bot asks for invoices and bills before answering any what-if. `add_invoice` may name a new buyer, who is then added to `profile.json`.

## 7. Demo tenants (workstream D)
`mahesh-cnc` (moved by A) and a second business with a different shape: no overdraft, different buyers, a different season. There is also a messy TallyPrime-style sample register in `data/samples/`; the upload does not take it (only the Kab Tak? layout), so it is a test file for a future importer.
