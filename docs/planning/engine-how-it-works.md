# How the Kab Tak? engine works (as built; written 25 Oct 2026, updated 26 Oct)

Written from the code in `engine/` (numpy + pandas only). Since 25 Oct the engine is multi-tenant: every function takes `tenant=` (a folder under `data/tenants/`, default `mahesh-cnc`), and caches are dropped when a tenant's files change on disk; the sections below describe the demo business. Where this disagrees with `f03-build-plan.md`, this file is right. The plan describes intent; this describes what runs.

## 0. The one-paragraph version

Each buyer's payment delays are fitted with a **Kaplan–Meier survival curve** that uses unpaid invoices correctly (censoring). A **1,000-path Monte Carlo** draws a payment date for every open and planned invoice from those curves, with one **shared shock per buyer** so a late buyer is late on every invoice. Each path then runs a **90-day daily cash loop**: receipts, then obligations (wages, EMI, GST, rent, power, bar stock, advance tax, bonus), against **bank balance + undrawn drawing power**. A *shortfall* is an obligation that this liquidity can't cover. Everything the owner sees (weekly risk, fan chart, "kab tak?", safe order terms) is a statistic of those 1,000 paths or a **bisection search** that re-runs them. The LLM never touches any of it.

```
ledger.py (synthetic invoices, obligations, position)
   └─► arrival.py  Kaplan–Meier per buyer ─► sample_delay (conditional inverse CDF)
          └─► simulate.py  1,000 paths × 90 days, shared buyer shock, drawing power
                 └─► decide.py  kab_tak, order_terms (bisection / scan, same random numbers)
                        └─► answer.py  packs it all into one JSON result for the UI
```

## 1. Data (`ledger.py`): synthetic, labelled so

- Seed 7, deterministic. 24 months of invoices (Nov 2024 to today, 25 Oct 2026) plus planned future invoices to 31 Jan 2027.
- Buyers and revenue share: Buyer A 40%, Buyer B 30%, CPSE 15%, small customers 15%. Base revenue about ₹24 L a month, with an Oct–Nov festival slowdown.
- **Planted payment behaviour** (median days invoice to payment): Buyer A 64 (60, but 75 for quarter-end and Oct–Nov invoices), Buyer B 45, CPSE 85 (long tail), small customers 22. Lognormal spread per buyer.
- Planted exceptions: one disputed Buyer A invoice (never paid in the horizon), one CPSE invoice 190+ days old, two recent Buyer A invoices flagged TReDS-accepted (the flag exists in the data; nothing uses it yet).
- Invoice maths: GST 18%, TDS 2% of taxable value (s.194C), so a receipt is gross minus TDS.
- Obligations (known cash-outs): wages ₹3.4 L on the 7th, EMI ₹1.2 L on the 5th, rent ₹60 k on the 1st, power about ₹1.5–1.7 L on the 10th, bar stock in two tranches a month on 30-day terms (45% of revenue, plus GST), **GST on accrual** on the 20th of the next month (net of input credit on bar stock), Diwali bonus ₹2.8 L on 5 Nov, advance tax ₹1.5 L on 15 Dec.
- Position today: bank ₹4.0 L, overdraft limit ₹42 L, drawn ₹23.8 L, stock ₹16 L. **Persona changed from the plan**: OD limit ₹42 L (plan: ₹25 L) and turnover about ₹3 cr (plan: ₹4.2 cr). The `ledger.py` docstring says why: at ₹25 L the cap would hide the "late buyer shrinks your limit" effect.
- **Drawing power** (recomputed weekly): `min(limit, 0.75 × (stock − unpaid supplier bills) + 0.60 × receivables younger than 90 days)`. Margins 25% and 40% are our assumption **[U]**, as is the 90-day exclusion. Verify with a banker or CA before claiming either as bank practice.

## 2. Payment-delay model (`arrival.py`): Kaplan–Meier

- Delay = payment date − invoice date, per buyer. **Open invoices are right-censored** at their current age, so slow payers who haven't paid yet still count as "survived this long". A plain average of paid delays would be biased fast.
- `_km`: at each event day t, S ← S × (1 − deaths / at-risk). Output: sorted event days `t` and survival `S(t) = P(delay > t)`.
- **Sampling** (`sample_delay`): for an invoice already `age` days old, draw a delay by inverse CDF of the *conditional* curve S(t)/S(age): the smallest t where `S(t) ≤ (1 − u) × S(age)`. So a 60-day-old CPSE invoice is never sampled as "paid on day 20", and the result is always > age. If the KM tail never gets that low (CPSE's slowest invoices are still open), it returns `NEVER = 10,000`, meaning not paid inside any horizon. Monotone in u.
- Self-check: fitted and sampled medians match the planted medians within 15% (or 6 days), and conditional draws always exceed the age.
- **Not built**: the plan's discrete-time hazard / logistic model with features (amount, month-end flag, DSO). We use plain per-buyer KM, which the plan names as its own fallback. No baseline comparison and no external IBM data.

## 3. Monte Carlo (`simulate.py`)

**Randomness, drawn up front in a fixed order from `seed`** so that every scenario sees the same random numbers (common random numbers). That is what makes comparisons clean and the searches monotone.
- Per path and buyer: `z_b ~ N(0,1)`. Per path and invoice: `z_i ~ N(0,1)`. Uniform `u = Φ(ρ·z_b + √(1−ρ²)·z_i)` with **ρ = 0.6** (a Gaussian copula). All of a buyer's invoices share `z_b`, so they move together. This is the shared-frailty idea. ρ = 0.6 is our assumption, not fitted. `shared=False` sets ρ = 0 for comparison. Φ is an erf approximation, error below 1.5e-7.
- Quarter-end shock: per path, with probability **0.3**, every payment landing in the last 10 days of a quarter slips to the first week of the next one, for all buyers together.
- Disputed invoices are never paid within the horizon.

**Scenario inputs**
- `extra_delay` {buyer: days}: added to every open and future invoice of that buyer (the delay_payment question, and the kab_tak search).
- `extra_obligations`: a dated one-off outflow (the expense_shock question, e.g. "spend 2 lakh in 15 days").
- `order` {party, amount, terms_days, advance_pct}: bar stock (45% of amount) paid on day 7, advance received on day 7, **invoice raised on day 30** (`ORDER_LEAD_DAYS`; dispatch lead time), GST on the invoice due the 20th of the next month (net of input credit on the bar stock), balance (minus TDS) received `terms_days` after the invoice plus a slip sampled from Buyer B's curve above its median. So the order's GST and bar-stock outflows land before its inflow: the cash gap.

**Daily loop (vectorised, 90 days × 1,000 paths).** Per day: receipts first, then obligations.
`liquidity[t] = (bank − OD drawn) + cumulative(inflow − outflow) + DP[t]`
- **DP[t]** recomputed on day 1 and every Monday: gross unpaid receivables with invoice age < 90 days on that date, through the drawing-power formula above. A late buyer both delays the inflow and, as invoices pass 90 days, shrinks the limit: the "double hit".
- **Shortfall** on day t = `max(0, −liquidity[t])` **only on days that have an obligation**. Negative liquidity carried over counts again at the next obligation day. An overdraft account running negative is not a shortfall by itself.
- `p_shortfall` = share of paths with any shortfall in 90 days. `weekly()` = per week (Mondays from 26 Oct), the share of paths with a shortfall that week, plus expected rupee shortfall.
- Check: with `noise=False` (all u = 0.5, no quarter shock) the vectorised loop equals a plain-Python reference loop to within ₹1. The shared shock widens the cumulative inflow band by more than 15% against independent draws.
- Speed: about 0.1 s per scenario call after the first. The hero answer takes about 7.5 s end to end because it runs a few dozen simulations for the searches (cached afterwards).

## 4. Decisions (`decide.py`)

All use seed 0 and 1,000 paths, so risk is (nearly) monotone in delay, terms and advance.

- **Risk target**: 5% chance of a shortfall in the horizon. **Threshold** = target if today's risk ≤ 5%, otherwise today's risk + 5 points ("how far can things slip before risk rises 5 points above where it already is"). Shown on screen as an assumption.
- **`kab_tak`**: per buyer (A, B, CPSE), bisection over 0–120 extra days for the largest delay d with `p_shortfall(extra_delay={b: d}) ≤ threshold`. Re-run with the order included when the question is a new order.
- **`order_terms`**: the largest payment terms (0 to those requested, cap 180) that keep risk ≤ threshold, where the threshold comes from the no-order risk; and the smallest advance (steps of 5%, 0–100) at the requested terms that does. If even terms of 0 don't work it returns terms 0 and searches the advance anyway.
- Caveat in `answer.py`: the weekly drawing-power recompute makes risk *near*-monotone, not strictly (a few-day shift can dodge a Monday; worth about 1 point), so the self-check allows a 0.02 dip.

## 5. Output (`answer.py`)

`answer(scenario, tenant)` supports `status`, `new_order`, `delay_payment`, `expense_shock`, `payment_received` (a what-if: that buyer pays that much on that day), and `add_invoice` / `add_obligation` (these save an owner entry, then answer status against the data before it). `sales_drop`, `supplier_terms` and `schedule_change` are parsed but raise "not supported yet". A what-if dated today counts as tomorrow. It returns one JSON: today card, fan chart (P10/P50/P90 of liquidity), 30 sample paths, weekly risk, worst week, kab_tak per buyer, order terms, kab_tak curves (risk vs. days late, in 5-day steps to 60), expected-vs-contractual arrivals per buyer, a bridge that reconciles start + receipts − obligations ± drawing-power change = end, and the assumptions list. **`fixes: []` and `plan: null`**: the fix search is not built.

## 6. The LLM layer (`ui/llm.py`): only parses and phrases

- `parse`: speech or text → typed scenario (JSON schema, strict), `openai/gpt-oss-120b` on Groq, falling back to `gpt-oss-20b` on a 429. The owner confirms the read-back before anything runs.
- Speech-to-text: `elevenlabs/scribe-v2` via OpenRouter, falling back to Groq Whisper large-v3. (The plan said Sarvam; the code doesn't use it.)
- `explain`: the model writes 3–4 sentences from a dictionary of **engine numbers already formatted** (`facts()`), with a verdict graded by worst-week risk (≤5% yes; <25% "yes, but tight"; <50% risky; otherwise "no"). **A number check keeps only sentences whose every number is a fact value or in the question**; if the first sentence fails, a template sentence replaces the whole answer.
- Limits to say out loud: the check compares digits only, so numbers spelled as words, or a real number used for the wrong thing, can slip through (the prompt and self-describing fact names guard that). One sum, the advance in rupees (order × 1.18 × advance %), is done in `llm.py`, not the engine.

## 7. Assumptions and simplifications (the honest list)

- The demo data is synthetic. The model is checked against its own planted values, and once against a public dataset (IBM sample; [validation-ibm.md](validation-ibm.md): we did not beat the published figure). Not validated on real businesses; no Xero-style comparison.
- ρ = 0.6, the quarter-end slip of 0.3, the drawing-power margins and the 90-day rule are assumptions **[U]**, not fitted or verified.
- One risk definition for everything: any obligation not covered by bank + undrawn drawing power. No cash buffer or CRC.
- Stock and supplier bills are held constant over the horizon. Small daily flows (walk-in receipts, scrap) are not modelled separately.
- No legal levers (MSMED s.16 interest, day-180 GST reversal, s.37(2)(g)), no TReDS discounting, no supplier deferral. The only legal reference in the output is the "MSMED s.15 45-day cap" used as the contractual due date in the expected-vs-due view.
- The new order is invoiced on day 30; its balance slip uses Buyer B's curve whichever party the owner names.

## 8. Reproduce

```bash
python -m engine.ledger      # build data + checks
python -m engine.arrival     # KM fit vs planted medians
python -m engine.simulate    # reference-loop equality, shared-shock band, base risk
python -m engine.decide      # monotonicity and bisection boundaries
python -m engine.answer      # output shape, hero timing
```
