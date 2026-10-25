# Kab Tak? Round 2: Done / Next (Srujana 2026, F-03)

Data is a synthetic Pune CNC shop, labelled synthetic everywhere. Rule we hold: the LLM only parses and phrases. It never computes.

## Built (works today)
**Engine (`engine/`)**
- Kaplan-Meier payment-delay curve per buyer; unpaid invoices are counted as censored, not ignored.
- 1,000-path Monte Carlo over 90 days. One shared shock per buyer, so a late buyer is late on every invoice.
- Drawing power (bank limit) excludes receivables older than 90 days, so a late buyer both delays cash and shrinks the limit.
- GST on accrual, TDS on receipts, wages/EMI/rent/power/bonus/advance tax as dated obligations.
- "Kab tak?" per buyer: the longest delay that keeps shortfall risk within the 5% target.
- `order_terms`: longest safe payment terms and minimum advance for a new order.

**App (`ui/`)**
- Owner, CA and Story views.
- Ask by voice or text in Marathi, Hindi or English; the owner confirms the read-back before anything runs.
- Speech-to-text: elevenlabs/scribe-v2 via OpenRouter, Groq Whisper as fallback.
- Parsing and phrasing: Groq gpt-oss-120b.
- Plain-language summary with a graded verdict (yes / yes but tight / risky / no).
- Number check: a sentence with a number the engine did not produce is dropped; if the first sentence fails, a fixed template is shown instead. It checks digits only, not numbers spelled as words.
- `docker compose up` runs the whole thing.

## Not built yet
- **The fix search. This is the next step and our main differentiator.** Today `fixes: []` and `plan: null` in `engine/answer.py`. We tell you the risk and the limits; we do not yet propose a bundle of fixes.
- WhatsApp: the webhook on main is not connected to the engine. An Evolution API adapter that calls the engine exists on branch `claude/evolution-whatsapp-860fe1`, unmerged.
- Legal levers (MSMED s.16 interest etc.), TReDS discounting, the Xero-style comparison.
- External validation, for example on the IBM sample. No backtest yet.
- Hazard model with features: we use plain per-buyer KM.
- Scenario types sales_drop, supplier_terms, schedule_change, payment_received: parsed, then "not supported yet".

## Honest caveats
- Everything is synthetic. The model is checked against values we planted, not real data.
- Buyer correlation 0.6, quarter-end slip 0.3, drawing-power margins and the 90-day rule are our assumptions, not fitted. Not validated on real data.

## Next 20 hours (ordered; video due at hour 36)
1. Fix search, hours 0-8 (hard stop at 8): greedy search over fix bundles, scored on the same 1,000 paths. Version 1 covers only what the engine already models: deferring a payment (overdraft-aware), asking for an advance, changing order terms. If it is not working by hour 8, we ship the risk answer without fixes and say so.
2. Wire fixes into the UI and summary, hours 8-11.
3. Validation slide, hours 11-13: say plainly what is and is not validated.
4. Demo video, hours 13-17, so it is done well before hour 36.
5. Rehearsal and Q&A prep, hours 17-20.
6. Anything left (WhatsApp merge, legal levers) only if time remains. Otherwise it stays on the Not built list.
