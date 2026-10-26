# Kab Tak? Predictive cash flow for small businesses

**Srujana Tech Fest 2026 · Finance theme · Problem statement F-03: Predictive Cash-Flow Management for Small Businesses**

Live demo: https://172-198-161-228.sslip.io (sign-up, dashboard and the WhatsApp bot).

## What it does today

An owner signs up on a website, optionally uploads an Excel workbook of invoices and bills, then asks questions on WhatsApp by text or voice note ("What if Buyer A pays a month late?", "Can I take a ₹12 lakh order on 90-day terms?", "Add invoice: Sharma Traders, 50 thousand, dated today"). Kab Tak?:

1. **Forecasts cash as a range of outcomes.** It simulates 1,000 paths for the bank balance over the next 90 days.
2. **Learns when each buyer really pays.** Each buyer gets a payment-delay curve from their own paid and still-open invoices, not a single due date.
3. **Flags the weeks when cash may run short**, with the chance of a shortfall in each week and the riskiest week.
4. **Answers decision questions:** how many days late each buyer can pay before the risk passes the 5% limit; for a new order, the longest safe payment terms and the smallest advance; what a one-off expense or a promised payment does to the risk.
5. **Saves what the owner tells it** (a real invoice or bill), with *undo* and *reset*. GST and TDS are computed in code.

The language model only turns speech or text into a typed question and phrases the answer. **The simulator makes every number.** The owner confirms a read-back ("Please confirm: Buyer A pays 30 days late. Reply yes or no") before anything runs.

> **Not financial or legal advice.** Kab Tak? computes and compares options; the owner decides. The demo businesses are **synthetic**.

## Persona

A constructed composite, not a real person: the owner of a 14-person CNC precision-components shop in Pune (a micro enterprise) that buys its own bar stock. His weekly question is "Can I pay wages on the 7th, and should I take this new order?"

## Architecture

```
owner ── WhatsApp text / voice ──► Evolution API (Baileys) ──► whatsapp/evolution_bot.py ─┐
owner ── browser ──► Caddy (HTTPS) ──► ui/server.py (landing, /onboard, dashboard, APIs) ─┤
                                                                                         ▼
   ui/llm.py: speech-to-text, question ─► typed Scenario (LLM, no numbers)        engine/answer.py
                                                                                         │
 data/tenants/<id>/ (profile, invoices, obligations, position, owner entries) ──► ledger ─┤
        arrival.py  Kaplan–Meier delay curve per buyer                                    │
        simulate.py 1,000 paths × 90 days, shared buyer shock, drawing power              │
        decide.py   "kab tak?" and safe order terms (bisection on the same random numbers)┘
                                    │
                                    ▼
          one JSON result ─► dashboard (Owner / CA / Story views) and whatsapp/reply.py (+ chart PNG)
```

A business is a folder, `data/tenants/<id>/`. Phone numbers are linked to businesses in a small SQLite file (`engine/tenants.py`); an unknown number is never answered from anyone's data, it gets the sign-up link. Details: [how the engine works](docs/planning/engine-how-it-works.md), [multi-tenant contract](docs/planning/multi-tenant-contract.md).

## Run it

**Locally (no Docker):** `pip install numpy pandas openpyxl fastapi uvicorn httpx matplotlib python-multipart`, then from the repo root:

```bash
python3 ui/server.py                                   # website + dashboard on http://localhost:8000
uvicorn whatsapp.evolution_bot:app --port 8001         # the WhatsApp bot (needs Evolution API: whatsapp/evolution/README.md)
```

Put keys in a `.env` in the repo root (not committed): `GROQ_KEY=...`, `OPENROUTER_KEY=...`. Without keys the typed form ("Or build it by hand") still works. Or `docker compose up --build` for the website alone on http://localhost:8000.

**On a VM (what is deployed):** `deploy/docker-compose.yml` runs Postgres, Redis, Evolution API, the web server, the bot and Caddy (HTTPS) on one machine. Only Caddy is public. Settings live in `deploy/.env.evolution` and `../.env` (not committed); `SITE` is the public host name.

```bash
cd deploy && docker compose --env-file .env.evolution up -d --build
docker compose exec bot python -m engine.tenants link 919999999999 mahesh-cnc   # link a phone to a business by hand
```

Self-checks (assert-based, no test framework). Set `KABTAK_DATA` to a fresh folder so real data is never touched:

```bash
export KABTAK_DATA=$(mktemp -d)
for m in engine.tenants engine.ledger engine.arrival engine.answer engine.test_owner_entries engine.test_tenants \
         whatsapp.evolution_bot whatsapp.reply ui.llm; do python3 -m $m; done
python3 ui/ingest.py
```

## Project structure

| Path | What it is |
|---|---|
| `engine/` | The engine: `ledger` (data and tenant files), `arrival` (Kaplan–Meier), `simulate` (Monte Carlo), `decide` (kab tak, order terms), `answer` (scenario to result), `tenants` (phone registry, join codes) |
| `ui/` | `server.py` (stdlib HTTP server and APIs), `onboard.html` / `terms.html`, dashboard (`index.html`, `app.js`), `ingest.py` (Excel upload), `llm.py` (speech-to-text, parser, explainer), `make_template.py` and the two downloadable workbooks |
| `whatsapp/` | `evolution_bot.py` (the bot), `reply.py` (message wording), `chart.py` (chart image); `app.py` is an unused Twilio/Meta alternative |
| `landing-page/` | The public landing page |
| `data/` | Demo businesses (`tenants/`), the generator `make_demo_tenants.py`, a messy sample register (`samples/`) |
| `deploy/` | One-VM Docker Compose and Caddyfile |
| `validation/`, `results/` | External backtest on a public dataset |
| `fixtures/` | The frozen result shape the dashboard was built against (`engine_result.json`) |
| `docs/planning/` | Plans, research, pitch and rehearsal notes (see its README for which are current) |

## Key technical decisions

- **The LLM never computes.** It fills a typed Scenario, the owner confirms it, and the engine runs. The plain-language summary drops any sentence containing a number the engine did not produce (a digit check only; numbers spelled as words get through).
- **Kaplan–Meier per buyer, not an average.** An unpaid invoice is "not paid yet", not "never paid". An average of paid delays flatters slow payers.
- **Monte Carlo with a shared shock per buyer** (correlation 0.6, an assumption): a buyer that is late is late on every invoice, so the range is not too narrow.
- **The bank limit moves.** Drawing power is recomputed each week and excludes receivables older than 90 days (an assumption), so a late buyer delays cash and shrinks the limit at once.
- **Same random numbers in every run**, so risk is monotone in delay and terms, and "kab tak?" and the safe terms are found by bisection.
- **Thin history is stated, not hidden.** A buyer with fewer than 5 paid invoices uses the curve pooled across buyers; a business with fewer than 10 paid invoices uses a default curve (median 45 days). The result lists this under assumptions.
- **A business is a folder**, so a new business needs no migration. The bot and the web server are separate processes; the engine re-reads a business's files when their modification time changes.
- **Plain stdlib server and plain JS** for the dashboard: no build step. FastAPI only for the bot's webhook.
- **Fixed-layout Excel upload, no LLM**: columns are known, so it is plain parsing; bad rows are skipped and reported, never guessed.

## Validation

Details and caveats: [docs/planning/validation-ibm.md](docs/planning/validation-ibm.md). Reproduce with `python3 -m validation.ibm_backtest`.

- **Internal checks.** The fitted payment curves recover the medians we planted in the synthetic ledger (within about 15%), and the fast simulator matches a plain day-by-day loop to within ₹1. These are circular: the data is ours.
- **External test, one public dataset** (IBM's 2,466-invoice accounts-receivable sample, which may itself be synthetic). Our weekly cash band held the actual cash in about 62% of 80 weeks, against 67.5% published for the cashcast prototype: **not better, and short of the 80% we aim for.** With 80 weeks the two are not statistically separable. Simple baselines that assume independent invoices did better (72–78%). The per-buyer curves are too narrow on that data (71% of actual payment dates fell inside our 80% interval).
- **The shared buyer shock is not validated.** That dataset has almost no shared delay, so it can neither confirm nor refute the idea; it did no harm.
- **Not validated at all:** the shortfall probabilities on real businesses, the 90-day drawing-power rule and the other assumptions above, and the owners' experience. No real owner has used it.

## Known limitations

- **No fix search.** The result carries `fixes: []` and `plan: null`. Kab Tak? tells you the risk, the riskiest week and how late each buyer can be; it does not yet price or rank ways out (TReDS discounting, advance, deferring a payment, MSMED notice). This is the next build.
- **Synthetic demo data.** Mahesh's shop and the two other demo businesses are made up. The persona has not been validated with real owners.
- **No dashboard login.** `/dashboard?tenant=<id>` shows that business to anyone who knows the id (a business name plus a 4-character random suffix: guessable, and not a login). Do not put real data behind it yet.
- **Prototype Terms of Service** (`/terms`): not reviewed by a lawyer.
- **WhatsApp replies are English only.** Questions can be asked in English, Hindi or Marathi (text or voice); replies are English. The dashboard summary can also be shown in Marathi and Hindi.
- **Unofficial WhatsApp protocol.** Evolution API in Baileys mode can get the number banned; use a spare SIM. The official Cloud API is the production path.
- **Excel upload takes our workbook layout only** (download the template on `/onboard`). There is no Tally or Zoho import, and the upload works only before the number is linked.
- **Unsupported what-ifs:** sales drop, supplier terms change, moving a payment date. They are parsed, then refused as "not supported yet".
- One message at a time in the bot (a global lock), and speech-to-text can mishear amounts (hence the read-back).
- Legal levers (MSMED Act s.15/s.16, Income-tax Act s.37(2)(g), the CGST 180-day rule) are only in the research notes, not in the product.

## Use of AI tools (disclosure)

AI tools were used in this project, as the event rules permit.

- **Claude (Anthropic)**, through Claude Code, helped with research, planning, documentation and most of the code. The team reviews generated code and can explain it.
- **In the product,** Groq `openai/gpt-oss-120b` (fallback `gpt-oss-20b`) parses questions and phrases summaries; speech-to-text is `elevenlabs/scribe-v2` via OpenRouter with Groq Whisper as the fallback. None of them produces a number the owner sees.

## Acknowledgements

numpy, pandas, openpyxl, FastAPI, uvicorn, httpx, matplotlib; Evolution API, PostgreSQL, Redis, Caddy; Groq and OpenRouter for the model calls. The IBM Watson sample "Accounts Receivable" (public mirror; licence not stated, not committed) is used only by the backtest, compared with the published cashcast prototype.

## Team

- Sankalp Shankar
- *Other team members and roles: to be added by the team.*
