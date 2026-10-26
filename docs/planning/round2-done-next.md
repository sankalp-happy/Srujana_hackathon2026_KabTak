# Kab Tak? Round 2: Done / Next (Srujana 2026, F-03)

*Updated 26 Oct 2026.* The demo businesses are synthetic and labelled so. Rule we hold: the LLM only parses and phrases. It never computes.

## Built (works today)
**Engine (`engine/`)**
- Kaplan-Meier payment-delay curve per buyer; unpaid invoices are counted as censored, not ignored. Thin history falls back to a pooled or default curve and says so.
- 1,000-path Monte Carlo over 90 days. One shared shock per buyer, so a late buyer is late on every invoice.
- Drawing power (bank limit) excludes receivables older than 90 days, so a late buyer both delays cash and shrinks the limit.
- GST on accrual, TDS on receipts, wages/EMI/rent/power/bonus/advance tax as dated obligations.
- "Kab tak?" per buyer: the longest delay that keeps shortfall risk within the 5% target.
- `order_terms`: longest safe payment terms and minimum advance for a new order.
- **Multi-tenant (done):** a business is a folder under `data/tenants/`; every engine call takes a tenant; phones are linked to businesses in a SQLite registry. Owner entries (invoices and bills added on WhatsApp) are saved per business, with undo and reset. The engine re-reads a business's files when they change on disk, so the bot and the web server stay in step.

**Website (`/`, `/onboard`, `/dashboard`)**
- Landing page, then a two-step sign-up: name, business, WhatsApp number; then upload the Kab Tak? Excel workbook (template and demo workbook on the page) or skip with a disclaimer and a Terms tick.
- Dashboard with Owner, CA and Story views; ask by voice or text in Marathi, Hindi or English with a confirm step; "Or build it by hand" form for the supported scenario types.
- Speech-to-text: elevenlabs/scribe-v2 via OpenRouter, Groq Whisper as fallback (Hindi heard as Urdu script is redone as Hindi). Parsing and phrasing: Groq gpt-oss-120b.
- Number check: a summary sentence with a number the engine did not produce is dropped (digits only, not numbers spelled as words).

**WhatsApp (merged, deployed)**
- `whatsapp/evolution_bot.py` on Evolution API: text and voice notes, read-back and yes/no (English, Hindi, Marathi), riskiest-week reply with a chart, add invoice / bill, undo, reset.
- The first message from the sign-up number links it to the business; an unknown number gets the sign-up link and no data. Replies are English only.
- One VM runs it all (`deploy/`): Postgres, Redis, Evolution, web, bot and Caddy (HTTPS) at https://172-198-161-228.sslip.io.

**Validation:** an external backtest on the IBM sample (not better than the published cashcast figure; see `validation-ibm.md`).

## Not built yet
- **The fix search. Still the next step and our main differentiator.** Today `fixes: []` and `plan: null` in `engine/answer.py`. We tell you the risk, the riskiest week and the limits; we do not propose fixes, and the site, dashboard and docs say "coming next".
- Legal levers (MSMED s.16 interest etc.) and TReDS discounting as numbers in the product.
- Tally or Zoho import: only our Excel layout is read.
- Scenario types sales_drop, supplier_terms, schedule_change: parsed, then "not supported yet" (hidden from the dashboard form).
- Replies in Hindi or Marathi on WhatsApp.
- A dashboard login, a lawyer-reviewed Terms of Service, the official WhatsApp Cloud API.
- Validation on real businesses, and a hazard model with features (we use plain per-buyer KM).

## Honest caveats
- The demo data is synthetic. The model is checked against values we planted, plus one external dataset where we did not beat the published number.
- Buyer correlation 0.6, quarter-end slip 0.3, drawing-power margins and the 90-day rule are our assumptions, not fitted. Not validated on real data.

## Next (in order)
1. Fix search: greedy search over fix bundles, scored on the same 1,000 paths. Version 1 covers only what the engine already models: deferring a payment, asking for an advance, changing order terms.
2. Wire fixes into the dashboard and the WhatsApp reply.
3. Replies in the owner's language on WhatsApp.
4. A login for the dashboard; Cloud API instead of the unofficial protocol.
