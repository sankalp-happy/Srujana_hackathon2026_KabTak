# F-03 Build Plan: "Kab Tak?" (working name)

> **Living document.** Version 0.4, 25 Oct 2026. Event rules: `srujana-2026-rules.md` (Srujana Tech Fest, Chanakya University, 24–26 Oct). This is a 48-hour build: expect to change scope at every go/no-go gate. Record each change in the change log at the bottom, so the team never has to guess which version is current.
>
> Evidence tags: **[P]** primary source, **[S]** secondary, **[U]** unverified. Never put an [S] or [U] number on a slide as if it were settled.

---

## 1. One line, USP, and why now

**One line:** WhatsApp a voice note in Marathi asking *"Can I take this order?"* or *"What if Tata pays a month late?"* You see 1,000 possible futures for your bank balance, the week you're likely to run out of cash, how many days each buyer can be late before that happens, and the **cheapest set of fixes** that keeps you safe, including legal levers Indian law already gives you.

**USP, in priority order:**
1. **It prescribes, not just predicts.** It picks the cheapest mix of fixes that keeps the shortfall risk under a target: invoice discounting on TReDS, the overdraft, deferring a supplier, or an MSMED heads-up to the buyer. Xero (Mar 2026) and QuickBooks (Oct 2026) forecast cash flow from predicted payment dates [S], and so do hobby prototypes such as cashcast (TabPFN, Oct 2026) [S]. None of them ranks fixes. Tools such as MSME Guard and TallyPrime 4.1 *compute* MSMED/43B(h) amounts [S], but none weighs them as fixes inside a risk budget, with their relationship cost made explicit.
2. **It answers "kab tak?" literally.** For each buyer: how many days late they can pay before wages fail. For a new order: the longest payment terms the shop can safely accept, or the advance it needs. These are numbers the owner can use in a negotiation the same day (§5.7).
3. **It separates expected money from received money.** Each open invoice gets a probability distribution over its arrival date, not a single due date, and **invoices from the same buyer move together** (a shared buyer shock). Prototypes that treat invoices as independent produce ranges that are too narrow: cashcast's README reports weekly cash inside its 80% range in only 67.5% of 80 weeks, "because the simulation treats invoices as independent" [S]. The problem statement asks for timing uncertainty explicitly.
4. **It works where Mahesh already works:** WhatsApp voice in Marathi, with his CA's Tally data in the background.

**Why judges should believe it isn't a GPT wrapper:** in EnterpriseArena (arXiv 2603.23638 v2, May 2026), only **about 15% (15.4%) of LLM-agent trials** across 23 LLMs kept a simulated firm alive for 132 months [P]. So in our system **the LLM only turns speech into a typed scenario. The simulator and the fix search make every decision.**

---

## 2. Persona (constructed: validate with 2–3 owners and CAs before the event)

**Mahesh Patil, 46.** He runs a CNC precision-components shop in Bhosari MIDC, Pune. He buys his own bar stock, so this is contract manufacturing, not "job work" in the GST sense (where the buyer supplies the material).
- **Business:** 14 workers, turnover about ₹4.2 cr (a micro enterprise), Udyam-registered since 2021.
- **Customers:** two auto-component Tier-1 suppliers bring in 70% of revenue, plus one public-sector company (CPSE).
- **Cash position:** ₹46 L receivable, ₹27 L of it more than 45 days old. He bridges the gap with a bank overdraft (₹25 L limit, most of it already drawn).
- **Tools:** his CA keeps TallyPrime and updates it about monthly. Mahesh works on WhatsApp and the phone, Marathi first.
- **His real question each week:** "Can I pay wages on the 7th? Should I take this new order?"

---

## 3. Problem-statement coverage (for the judges' checklist)

| What the PS asks for | Where we deliver it |
|---|---|
| Current liquidity | Today card: bank balance + undrawn overdraft drawing power, receivable due vs overdue |
| Anticipate shortfalls | Fan chart; red "stress weeks" band; P(shortfall) per week (§5.3 defines shortfall) |
| Revenue, receivables, suppliers, payroll, EMIs, opex, reserves | Synthetic ledger + scheduled-obligations calendar (§6) |
| Expected vs actually received, timing uncertainty | Per-invoice arrival distribution from the hazard model (§5.1) |
| Simulate delays, expense shocks, sales drop, supplier terms, revised schedules | Voice or typed scenario → typed schema (§5.5) |
| When a shortage happens; compare responses by their financial implications | Fix search + side-by-side comparison of fixes (§5.4); "kab tak?" and longest-safe-terms numbers (§5.7) |

---

## 4. The 3-minute demo script (hero journey: rehearse this one path until it's flawless)

All numbers below are **placeholders**. Replace each with what the engine outputs before recording; never script a number the engine didn't produce.

1. **(0:00) Hook.** *"₹7.34 lakh crore owed to Indian MSMEs is paid late [P, GAME–FISME–C2FO Delayed Payments Report 3.0, Nov 2025; figure as of Mar 2024]. Mahesh is profitable and still can't sleep before payday."*
2. **(0:20) Today.** The dashboard loads Mahesh's books. Fan chart of 1,000 paths over the next 90 days. Red band on a wage week: *"Week of 7 Dec: 38% chance you can't pay wages on the 7th."* (Wages fall on the 7th, so the band must sit on a week that contains a wage date.)
3. **(0:50) The hero moment.** Live, a Marathi voice note on WhatsApp: *"Should I take Bajaj's ₹12 L order on 90-day terms?"* The bot reads it back for confirmation. About 10 s later the fan chart redraws: bar-stock spend comes forward, GST on the invoice falls due on the 20th of the next month (about two months before Bajaj pays), the inflow lands 90+ days out, and the dip deepens to a 61% chance of a shortfall.
4. **(1:30) Fix it.** The engine returns: *"You can safely take this order on terms of up to 60 days. At 90 days, discount the Tata invoice on TReDS (₹6.6k) and run ₹4 L more on the overdraft for 3 weeks (₹2.4k). Shortfall risk falls to 4%. Total cost ₹9k, against ₹1.1 L margin on the order. Tata can pay up to 38 days late before wages fail."* Show the fixes side by side. The lever calendar shows, as a fact, the s.16 interest Tata already owes on invoices past day 45.
5. **(2:10) Why should I trust this?** Tap the ₹6.6k figure: you see the invoice's arrival distribution and the interest arithmetic behind it. Then the validation slide (§9): weekly-cash coverage on the IBM sample against cashcast's 67.5%, and the Xero-style plan's real shortfall rate on the same 1,000 paths.
6. **(2:40) Reply.** A one-line Marathi text reply arrives on the phone. Close: *"From 'I hope' to 'I know, and here's the cheapest fix.'"*

**Backup:** a pre-recorded video of the same journey, plus an offline mode with cached model outputs.

---

## 5. How it works (stack plus a fallback for each layer)

```
Tally-shaped CSV  or  synthetic ledger
        │
        ├─► [5.1] Arrival-date model per open invoice  ──┐
        ├─► [5.2] Seasonal bootstrap for small flows   ──┤
        └─► Scheduled obligations (payroll, EMI, GST) ──┤
                                                         ▼
              [5.3] Monte Carlo: 1,000 daily cash paths (shared buyer shock, drawing power)
                                                         │
                          [5.3b] Empirical cash buffer ──┤
                                                         ▼
               [5.4] Fix search (greedy; CP-SAT stretch) + [5.7] decision outputs
                                                         ▲
   WhatsApp voice → Sarvam STT → [5.5] LLM → typed Scenario → confirm ┘   → Marathi text reply
```

### 5.1 Arrival-date model (ML1): a discrete-time hazard model
- **Why hazard:** open invoices are *censored* (not paid *yet*). A plain regression on paid invoices ignores them and is biased towards fast payers.
- **Rows:** one row per invoice per week while it is still unpaid. The label is "paid in this week?" (discrete-time survival: Singer & Willett 1993, J. Educational Statistics 18(2):155–195 [P]).
- **Features:** buyer; amount (log); weeks since invoice; days past due; month-end or quarter-end flag; the buyer's trailing DSO; accepted, disputed or GRN-pending flag; festival-month flag.
- **Model:** logistic regression on the hazard rows. It is fast, and its coefficients can be shown to a judge. **TabICLv2 is a stretch goal:** add it only as an extra row in the validation table, never on the main path. (Code BSD-3, Hugging Face card tagged bsd-3-clause [P]; untested below 300 rows [P], so pool all buyers.)
- **Prior art (say it first):** invoice-payment prediction goes back at least to Zeng et al., KDD 2008 (doi:10.1145/1401890.1402014) [P]. Discrete-time hazard models for receivables are published (Springer 2024, doi:10.1007/s44257-024-00013-2; arXiv 1912.10828, 2008.07363) [P]. We don't claim the model is new; we claim what it feeds.
- **Output:** chain the weekly hazards into an arrival distribution per invoice, and sample from it in §5.3.
- **Baselines:** (a) paid on the due date (the villain), (b) **per-client historical average days-to-pay** (the PayRadar write-up found this often matches TabPFN [S], so it is the baseline to beat honestly).
- **External check:** also fit and score on IBM's Watson "Accounts Receivable" sample, also called "Finance Factoring: IBM Late Payment Histories" (2,466 invoices, 100 clients, 2012–13 [S, per cashcast's README]). We didn't generate it, which breaks the circularity of validating on our own synthetic ledger. cashcast doesn't say where its mirror is, so finding the CSV is an H0–6 task.
- **Fallback:** a Kaplan–Meier survival curve per buyer, using `lifelines`.

### 5.2 Small daily flows (ML2)
- **Model:** seasonal bootstrap of past weeks (resample same-month weeks) for walk-in receipts, scrap sales, power and consumables.
- **Why not Chronos-2 (cut in v0.4):** these flows are about 15% of revenue. A foundation model adds install, GPU and licence risk for little of the variance, and the rubric gives no credit for complexity.

### 5.3 Monte Carlo (ML2)
- 1,000 paths × 90 days, vectorised in numpy.
- `cash[t] = cash[t-1] + sampled invoice receipts + small inflows − scheduled outflows − variable outflows`.
- **Dependence:** each path draws one delay shock per buyer (plus a quarter-end shock shared by all buyers) that shifts every open invoice of that buyer together. Survival analysis calls this a *shared frailty* (Vaupel, Manton & Stallard 1979, Demography 16(3):439–454 [P]). It is the fix for the too-narrow ranges cashcast admits [S]. Validation shows weekly-cash coverage with and without the shared shock.
- **Cash mechanics every path must include:**
  - **Shortfall:** an obligation that cash plus undrawn overdraft drawing power can't cover. It is *not* "cash < 0": an overdraft account runs negative routinely.
  - **Drawing power:** recompute it weekly from stock plus receivables after margin, dropping receivables older than about 90 days (bank practice, varies [U]: confirm with a banker or CA). The late buyer that delays the inflow also shrinks the overdraft. That's the double hit generic forecasters miss.
  - **GST on accrual:** GST on each invoice is due by the 20th of the next month, whether or not the buyer has paid.
  - **TDS:** buyers deduct TDS on contract work, so receipts arrive slightly below invoice value.
- **Outputs:** fan chart (P10/P50/P90), P(shortfall) per week, and the expected shortfall.

### 5.3b Cash buffer (ML1)
- **Method:** the empirical quantile of shortfall across the Monte Carlo paths. On screen: *"Keep ₹3.2 L in reserve."*
- **Why the Conformal Risk Control guarantee was cut (v0.4):** CRC (Angelopoulos et al., ICLR 2024, arXiv 2208.02814 [P]) needs (n/(n+1))·R̂ + B/(n+1) ≤ α, where B is the maximum loss. With about 12 monthly backtest origins and rupee loss capped at the ₹25 L overdraft limit, the B/(n+1) term alone is ≈ ₹1.9 L, against a ₹25k target. The bound would be vacuous, and overlapping rolling windows aren't exchangeable either. Say this if an ML judge asks; it shows we understand the method.
- **Honesty:** never say "guaranteed won't bounce."

### 5.4 Fix search (FS2 + ML1)
- **Tool:** greedy search over fix bundles, evaluated on the Monte Carlo paths; exhaustive search where the bundle count is small. **CP-SAT is a stretch goal:** claim it only if a test case shows greedy picking a worse plan.
- **Decisions:**
  - TReDS discount for each eligible invoice (yes/no). An invoice is eligible only if the buyer is registered on TReDS and has accepted it, and the shop is already onboarded. Otherwise list it under "set up for next time", not as a fix this week;
  - supplier deferral per bill (0, 15 or 30 days, with a relationship-cost penalty);
  - MSMED heads-up per buyer (yes/no). **Default speed-up effect = 0**, and the owner sets it. It isn't free: it carries a relationship penalty with a buyer worth up to 40% of revenue. The RBI's U.K. Sinha committee (June 2019) noted that small firms hesitate to enforce MSMED rights because of weak bargaining power [P];
  - accept or reject the new order, and its terms (§5.7).
- **Overdraft:** drawn automatically up to drawing power. Its interest is a cost in every plan, not a decision.
- **Chance constraint (CP-SAT stretch):** a yes/no variable z_s for each scenario; Σ z_s ≥ 0.95·S; `cash_s,t + headroom_s,t ≥ 0` enforced with `OnlyEnforceIf(z_s)` (no big-M); integer-scaled rupee coefficients. This is the sample-approximation formulation of Luedtke & Ahmed 2008 (SIAM J. Optim. 19(2):674–699) [P]. Closest modern relative: Chen & Archibald 2024, "Maximizing the survival probability in a cash flow inventory problem with a joint service level constraint", IJPE 270:109191 [P]. Our novelty is SME invoice-level fix selection.
- **Objective:** minimise rupee cost (discount fees + overdraft interest + penalties), minus the margin on the order if accepted.
- **Cost inputs** (verify before the event):
  - overdraft 8.75–14% per year [S, by bank type];
  - TReDS discount around 10% per year [U];
  - MSMED interest at 3× the Bank Rate = 17.25%, with Bank Rate 5.75% from 7 Oct 2026 [P]. The agents found conflicting repo-rate figures, so re-check.
- **Legal levers:** reuse Haq's rule sketch in **plain Python behind 30 hand-computed tests**: s.15 due date, s.16 interest, the GST credit reversal at day 180, and the buyer losing its tax deduction under s.37(2)(g) (the Income-tax Act 2025 successor to 43B(h); mapping [S], verify). Catala is cut (see the cut list).
- **Lever timing (gets domain points):**
  - s.16 interest accrues from the day after the s.15 deadline (45 days with a written agreement, 15 without);
  - the buyer's GST input credit is reversed at day 180 (the CPSE invoice);
  - **43B(h) / s.37(2)(g) only bites if the dues are still unpaid at 31 March**. A late payment made within the same financial year keeps the deduction in that year [S]. So in a November demo, don't lean on the tax argument; use s.16 interest and the day-180 reversal.
- **Fallback:** greedy is already the main path. If even that is slow, cut to 200 paths.

### 5.5 Voice and scenario layer (FS1)
- **Channel:** WhatsApp (Twilio Sandbox or Cloud API test number; `whatsapp/app.py` supports both). Speech-to-text with Sarvam Saaras v3. **Reply as Marathi text**; a Bulbul text-to-speech reply is cut until everything else works.
- **LLM output:** a Pydantic `Scenario` with type `new_order | delay_payment | expense_shock | sales_drop | supplier_terms | schedule_change | payment_received` and typed parameters, produced with structured output.
- **Confirm before computing:** read back the parsed scenario (*"New order, Bajaj, ₹12 L, 90 days. Correct?"*). This catches mis-heard amounts (lakh/crore, Marathi numerals) before any number is computed.
- **Event logging (stretch):** *"Tata paid 8 lakh today"* becomes a `payment_received` scenario that updates the ledger between the CA's monthly Tally updates.
- **Ambiguity:** if the request is unclear, the LLM asks **one** follow-up question.
- **The LLM never produces numbers itself.**
- **Fallback:** a web chat with a mic button, in Hindi or English.

### 5.6 Front end (FS2)
- Next.js (or Streamlit if we're behind) with four screens: **Today card**, **fan chart with a stress band**, **scenario panel with sliders**, and **fix comparison with "why this number?" drill-downs**.
- **Two audiences:** the owner gets one Marathi sentence and one action ("Yes, wages are safe; discount the Tata invoice"). The CA gets the fan chart and the assumption toggles. The owner never has to read "P(shortfall)".
- A WhatsApp-style phone panel on the right, mirroring the real WhatsApp flow for the stage.

### 5.7 Decision outputs: ranked novelty additions (v0.4)

Ranked by impact ÷ effort. **D** = demoable, **P** = pitch only. Everything reuses the §5.3 simulator.

| # | Output | What the owner sees | D/P | Effort | Gate |
|---:|---|---|:-:|---|---|
| 1 | **"Kab tak?" reverse stress test** + **longest safe terms** | "Tata can pay up to 38 days late before wages fail." "Take Bajaj at up to 60 days, or ask for a 20% advance." (Bisection over delay days or payment terms) | D | 1–2 h | H24 |
| 2 | **Xero-style plan vs ours** | Plan built from single predicted payment dates, run on the 1,000 paths: its real shortfall rate next to ours. This is the value of the stochastic solution (Birge 1982, Math. Programming 24:314–325 [P]) and answers "how is this different from Xero?" | D | ~2 h | H24 |
| 3 | **Head-to-head on cashcast's data** | Weekly-cash 80% coverage on the IBM sample, with and without the shared shock, against cashcast's reported 67.5% [S]. Quote our number only after measuring it | D | 3–4 h incl. finding the CSV | H30 |
| 4 | **Overdraft double hit** | Drawing-power headroom shrinking as a late buyer's invoices pass ~90 days (§5.3) | D | ~1 h | H24 |
| 5 | **Collection priority by risk** | Open invoices ranked by how much P(shortfall) drops if each is paid on time: "Call Tata today, not the CPSE" | D | 1–2 h | H30 |
| 6 | **Lever calendar** | Per invoice: day 46 s.16 interest starts, day 180 GST credit reversal, 31 March 43B(h). The s.16 interest owed is shown as a rupee fact | D-lite | ~1 h | H30 |
| 7 | **GST before cash** | The new order's GST outflow ~2 months before its inflow (§5.3). Correctness more than novelty, but judges notice | D | 30 min | H24 |
| 8 | **Voice event log** | "Tata paid 8 lakh" updates the forecast (§5.5) | P unless WhatsApp is stable | 2–3 h | — |
| 9 | **CA portfolio view** | One CA sees every client's red weeks (distribution story) | P | — | — |
| 10 | **Account Aggregator ingestion** | Real bank data with consent | P | — | — |

---

## 6. Data: the synthetic Mahesh ledger (FS1, ready by H6)

Generate 24 months of history with planted behaviour, so the models have something real to find:

| Item | Spec |
|---|---|
| Revenue | ~₹35 L/month; 3 anchor buyers (Tier-1 A 40%, Tier-1 B 30%, CPSE 15%) + ~20 small customers (15%) |
| Payment behaviour | A: pays ~day 60 and slips at quarter-end; B: ~day 45, pays reliably; CPSE: 75–120 days, long tail; small customers: mostly within 30 days |
| Receivable today | ₹46 L, ₹27 L of it past 45 days (matches the persona). **Reconcile:** the payment behaviour above implies ~56 weighted days to pay, i.e. ~₹65 L receivable at ₹35 L/month. Lower the revenue, speed up the payers, or update the persona until it matches (a CA on the jury will do this sum in their head) |
| Payroll | 14 workers, ~₹3.4 L on the 7th of each month |
| Raw material | Bar stock bought by the shop, ~45% of revenue; suppliers on 30-day terms |
| Fixed costs | Rent, power (~₹1.8 L, with summer spikes), CNC machine EMI ₹1.2 L on the 5th |
| Statutory | GST on each invoice payable by the 20th of the next month, paid or not; TDS deducted by buyers on receipts; advance tax in Jun, Sep, Dec and Mar |
| Facilities | Overdraft limit ₹25 L, most of it drawn; drawing power recomputed from stock + receivables under ~90 days after margin; current-account balance ~₹4 L. Tune so headroom + cash is about one payroll plus one GST payment, so the stress week is plausible |
| Events | Festival-month slowdown (Oct–Nov); **Diwali bonus** paid before Diwali (customary, and often statutory for a factory this size [U]); one disputed invoice; one CPSE invoice at 180+ days |

Export it as a Tally-shaped CSV (Tally's column names), so that "connect your CA's Tally" is a believable claim. Tally XML only if time allows.

---

## 7. 48-hour timeline with go/no-go gates

**Fixed by the rules** (hours from the organisers' official start): progress evaluations about every 12 h (≈H12, H24, H36); **demo video due H36, and it decides the shortlist** (10 Finance teams go to the final); full repo + README + working demo due H48; final = live presentation + Q&A. So the product must be demoable at every evaluation and **video-ready by H30**, not H40.

| Hours | FS1 | FS2 | ML1 | ML2 |
|---|---|---|---|---|
| **0–6** | Ledger generator (§6 mechanics); WhatsApp test number | Next.js skeleton; fan chart on dummy data | Hazard-row builder; logistic hazard; find the IBM AR CSV | Monte Carlo skeleton with shared buyer shock |
| **Gate H6** | **Logistic hazard + Monte Carlo run end to end on the generated ledger? If not, switch to Kaplan–Meier now.** |||
| **6–12** | STT → LLM → Scenario schema + confirm step | Today card; scenario sliders | Hazard model + due-date and per-client baselines | Drawing power, GST accrual, TDS; stress weeks |
| **Gate H12 (eval 1)** | **Show: ledger → fan chart → stress week, reacting to a typed scenario. One CA call done and quoted. If not, cut WhatsApp and go web-only.** |||
| **12–24** | Voice → Scenario on the web mic; Marathi copy | Fix-comparison UI; drill-downs | Legal-lever rules + 30 tests; IBM backtest | Greedy fix search; "kab tak?" + longest safe terms (§5.7 #1) |
| **Gate H24 (eval 2)** | **Hero journey runs end to end on the web. Greedy plan in under 5 s.** |||
| **24–30** | WhatsApp loop with text reply on a real phone | Polish; offline cache mode; accessibility pass | Xero-style vs ours (§5.7 #2); coverage vs cashcast (#3); TabICLv2 row (stretch) | Hero-scenario tuning; edge cases; collection priority (#5); CP-SAT (stretch) |
| **H30** | **Feature freeze for the video.** |||
| **30–34** | Record the demo video (3 takes) | Edit video; captions | Validation slide for the video | Rehearse hero path |
| **H34** | **Submit the video (2 h buffer before H36).** |||
| **36–48** | README: setup, deps, decisions, limitations, AI-use disclosure | Slides; fixes only | Judge Q&A prep; domain-assumption sheet | Rehearse ×5; submit repo by H46 |

---

## 8. Cut list (do not build unless every gate is green early)

- **Cut in v0.4:**
  - Chronos-2 (seasonal bootstrap instead, §5.2);
  - the Conformal Risk Control guarantee (empirical buffer instead, §5.3b);
  - Bulbul voice reply (Marathi text instead);
  - Tally XML (CSV with Tally column names instead).
- **Moved to stretch in v0.4:** TabICLv2 (validation-table row only) and CP-SAT (only if it beats greedy on a case we can show).
- Catala law-as-code (Haq's novelty). Keep the rules in Python, with tests.
- A live Tally connection. Use an exported file instead.
- ODR claim pack PDF, and the full escalation ladder from Haq.
- Account Aggregator or bank-statement ingestion.
- GST portal or GSP integration.
- Multi-business support, logins, accounts.
- Training or fine-tuning any foundation model.
- Score of buyer payment records from public data.

---

## 9. What we show judges as proof

1. **Arrival-date calibration** on the external IBM sample and on the synthetic ledger: how often actual arrival dates fall inside our 80% intervals, compared with the due-date and per-client-average baselines.
2. **Weekly-cash coverage**, the metric that matters for the decision: how often actual weekly cash falls inside the 80% band, with and without the shared buyer shock. cashcast reports 67.5% on the IBM sample [S].
3. **Xero-style plan vs ours:** the realised shortfall rate of a plan built from single predicted dates, against ours, on the same 1,000 paths (§5.7 #2).
4. **Shortfall lead time** in the backtest: days of warning before a real cash crunch. Compare us, "due date", and "due date + average delay".
5. **Cost of the fixes** compared with a naive rule ("draw the overdraft whenever cash goes negative"), and the time to produce a plan.
6. **Rule tests:** 30 of 30 hand-computed legal and interest cases pass, run live with `pytest`.

If we only tie the per-client-average baseline on arrival dates, say so. The shared shock is meant to improve weekly-cash coverage, not per-invoice accuracy.

---

## 10. Risks, and what we do about each

| Risk | Mitigation |
|---|---|
| Synthetic data looks fake | Plant realistic mechanisms; reconcile the receivable sum (§6); ask a CA friend for one anonymised Tally export |
| IBM AR CSV mirror not found | Validate on synthetic only and say so: "we validate the pipeline, not real-world accuracy" |
| TabICLv2 install trouble | It's stretch only; logistic hazard is the main path |
| WhatsApp approval or webhook flakiness on stage | Web phone panel mirror + backup video |
| Marathi STT error on stage | Pre-test the exact hero sentence; confirm step; typed fallback |
| Fix search too slow | Cut to 200 paths; cache the hero scenario |
| Demo numbers that the engine didn't produce | Script placeholders only; replace them with engine output before recording |
| A judge asks "isn't this legal or financial advice?" | It computes and compares options; the owner decides and sends. Show the assumptions as visible toggles |
| An ML judge asks for a guarantee | We don't claim one. The buffer is an empirical quantile; explain why CRC would be vacuous at our sample size (§5.3b) |
| Wrong figures for rates or law | Re-check the Bank Rate, TReDS rates, the s.37(2)(g) mapping, the TReDS mandate threshold and the MSMED Amendment 2026 status before the final |

---

## 11. Likely judge questions (prepare answers)

**The five toughest, with ~20-second answers:**
1. *Are the simulations random and synthetic?* "Random, not arbitrary. Each of 1,000 paths draws when each invoice is paid from that buyer's fitted delay distribution, with one shared shock per buyer, so a late Tata is late on every invoice. Wages, EMI and GST are fixed on their real dates. The ledger is synthetic and labelled so. [If done:] The arrival model is also checked on IBM's public 2,466-invoice sample, which we didn't generate."
2. *How accurate is it?* "We don't promise a date; we promise a calibrated range: does our 80% band contain the actual weekly cash 80% of the time? A public prototype on the same data reports 67.5% because it treats invoices as independent. We fix that with the shared buyer shock and report against due-date and per-client-average baselines." Quote our number only once it's measured.
3. *Why not just use the overdraft?* "Often it is the answer, and we say so with its rupee cost. But the overdraft isn't a fixed buffer: drawing power usually excludes receivables older than about 90 days, so the late buyer also shrinks your limit. And staying over drawing power for 90 days makes the account an NPA [U: verify in the RBI IRACP master circular]. A flat limit misses both."
4. *Is WhatsApp safe for financial data?* "The ledger never goes to WhatsApp; it stays on our server. WhatsApp carries only the question and a one-line answer. On the Cloud API, Meta processes messages on the business's behalf [U], so we don't call it end-to-end. In production: consent and purpose limitation under the DPDP Act 2023 (Rules notified 13 Nov 2025, most duties from 13 May 2027 [S]), and a web app for anyone who prefers it. Demo data is synthetic."
5. *Does it scale?* "Compute is cheap: 1,000×90 numpy paths per business, [measured time] per scenario. The bottleneck is data: a Tally export today, Account Aggregator consent next. Distribution scales through CAs, since one CA serves dozens of MSMEs."

**Others:**
- *How is this different from Xero or QuickBooks forecasting?* They forecast from predicted payment dates; we prescribe the cheapest survival plan. Then show it: the Xero-style plan's real shortfall rate on our 1,000 paths (§5.7 #2).
- *Isn't this just cashcast / PayRadar?* Hobby prototypes predict; we decide. They also treat invoices as independent, which makes their ranges too narrow (cashcast says so: 67.5% coverage). We model shared buyer shocks and show a per-client-average baseline.
- *MSME Guard and Tally already compute 43B(h).* Yes, as reports. We use the same rules, open and tested, as fixes that the search weighs against TReDS and overdraft costs, with their relationship cost made explicit.
- *Hazard models and chance constraints aren't new.* Right, and we cite them (Zeng et al. 2008; Singer & Willett 1993; Luedtke & Ahmed 2008). What's new is the combination, applied to one Indian micro-business's invoices, and outputs forecasting tools don't give: "kab tak?" per buyer and the longest safe terms for an order.
- *Why not let GPT do it?* EnterpriseArena: about 15% of agent trials survive. Our LLM only writes typed scenarios, and the owner confirms them.
- *Where does real data come from?* The CA's Tally (XML/JSON over HTTP); later, Account Aggregator.
- *Business model?* A CA-led channel (one CA serves dozens of MSMEs), a TReDS or lender referral fee, or a bank white-label for MSME overdraft customers.
- *What if a buyer gets angry about the MSMED heads-up?* That's why its default effect is zero and it carries a relationship penalty. It's optional, and the owner approves every message.
- *Why not lean on 43B(h)?* It only bites if the dues are unpaid at 31 March. Outside Feb–March, s.16 interest and the day-180 GST reversal are the levers that matter.

---

## 11b. Rubric map (100 points, from the rules) and compliance

| Criterion | Pts | What earns it here | Gap to close |
|---|---:|---|---|
| Problem understanding and relevance | 15 | §3 coverage table; expected vs received money; Mahesh's real question; "kab tak?" and longest-safe-terms answers | **Zero user conversations so far:** one CA call before H12, quoted on a slide |
| Technical depth and implementation | 20 | Censored hazard model, Monte Carlo with shared buyer shock, fix search, Xero-style vs ours comparison | Rules say complexity earns nothing by itself: **every model must beat its baseline on a slide** |
| Functional completeness and reliability | 15 | All six PS scenario types work (sliders/typed), hero path flawless | Voice covers only the hero; sliders must cover the rest |
| Domain analysis and correctness | 20 | MSMED s.15/s.16, s.37(2)(g) timing, CGST day-180, drawing power, GST on accrual, TDS, overdraft and TReDS cost arithmetic, 30 tests | Verify Bank Rate, TReDS rates and mandate threshold, s.37(2)(g) mapping, Amendment 2026 Gazette status; one-page domain-assumption sheet |
| Validation and robustness | 10 | External IBM calibration, weekly-cash coverage vs cashcast, Xero-style comparison, rule tests | Edge cases: buyer with no history, zero receivables, overdraft maxed, disputed invoice, mis-heard amount |
| User experience and accessibility | 10 | Marathi voice in, one Marathi sentence out; confirm step; CA view with toggles | Readable, colour-blind-safe fan chart; plain-language labels |
| Originality and presentation | 10 | Forecast → cheapest fix, "kab tak?" per buyer, buyer-side legal levers | Video at H36 is the shortlist gate |

**Compliance (disqualification risks):**
- Write no code before the official start; the plan and research docs are fine.
- README must disclose AI-tool use and acknowledge Sarvam, the WhatsApp provider (Twilio or Meta), the IBM AR sample, the synthetic data, and OR-Tools / TabICLv2 if used. Each teammate must be able to explain their own part and say what is incomplete.
- Show a "computes and compares options, not financial or legal advice" note on screen. Never say "guaranteed".
- Label the ledger as synthetic everywhere. Fabricated claims are grounds for disqualification, so [S]/[U] figures never go on a slide as fact.

## 12. First hours of the event (was "before the hackathon"; owner in brackets)

- [ ] Read the organisers' judging rubric; re-weight this plan to match it
- [ ] Find a mirror of IBM's AR sample CSV; check it has a customer ID column
- [ ] Sarvam API credits; test Marathi STT on the hero sentence
- [ ] WhatsApp test number + webhook (ngrok or Cloudflare tunnel)
- [ ] Verify: Bank Rate and repo rate as of Oct 2026, current TReDS discount rates and mandate threshold, typical MSME overdraft rate and drawing-power practice, s.37(2)(g) mapping, MSMED Amendment Act 2026 Gazette status
- [ ] At least one CA call before H12 (2–3 owner or CA conversations ideally) to validate the persona and the "can I take this order?" question
- [ ] Stretch: TabICLv2 install check on a laptop or Colab

---

## Change log

| Date / hour | Change | Why |
|---|---|---|
| 25 Oct 2026 | v0.4: Self-critique merged. **Cut** Chronos-2, the CRC guarantee, the Bulbul reply and Tally XML; **moved to stretch** TabICLv2 and CP-SAT (greedy is the main path). **Domain fixes:** persona is a precision-components supplier, not job work; shortfall = cash + undrawn drawing power; drawing power drops receivables older than ~90 days; GST on accrual; TDS; Diwali bonus; 43B(h) only bites at 31 March; TReDS needs buyer acceptance and onboarding; MSMED heads-up defaults to zero effect with a relationship penalty; the receivable total must reconcile; the stress band sits on a wage week; demo numbers are placeholders. **Added** §5.7 ranked decision outputs ("kab tak?" per buyer, longest safe terms, Xero-style vs ours, cashcast head-to-head, collection priority, lever calendar), confirm step, two-audience UI, external IBM validation, five tough jury answers. Citations checked on Crossref/arXiv | The rubric gives no credit for complexity; the CRC bound is vacuous at n≈12; validating only on our own synthetic data is circular; a CA or domain judge would catch the domain gaps. Supersedes v0.2b "no cuts" |
| 24 Oct 2026 | v0.3: P3 merged. Dropped the "nobody uses foundation models / encodes MSMED" claims; reframed the novelty as the combination (dependent timing + legal-lever optimiser + CRC bound + decision-first voice). Added a shared buyer shock to the Monte Carlo, a per-client average baseline, CP-SAT `OnlyEnforceIf`, and pooled TabICLv2 rows. EnterpriseArena 16% → about 15% (15.4%). New judge Q&A on cashcast, MSME Guard and prior art | P3 found TabPFN days-to-pay prototypes (cashcast etc.), published hazard models, and MSMED calculators (MSME Guard, TallyPrime 4.1) |
| 24 Oct 2026 | v0.2b: No cuts; full stack kept, and the H12/H24 gates decide fallbacks. The H36 video shows all innovations (1–5); 3 and 4 are held back only from the H12/H24 progress evaluations | User decision |
| 24 Oct 2026 | v0.2: Re-timed to the rules: freeze H30, video submitted H34 (due H36, shortlist gate), evals ≈H12/H24/H36 become gates, H40–48 is README/slides/rehearsal. Greedy solver now built before CP-SAT. Added §11b rubric map + compliance | Rules (`srujana-2026-rules.md`): video decides shortlist; rubric weights domain correctness and technical depth highest; AI disclosure required |
| 24 Oct 2026 | v0.1: F-03 locked. Stack: hazard TabICLv2 + Chronos-2 + Monte Carlo + CRC + CP-SAT + Marathi voice | Ranking 30/35; added survival, CRC, CP-SAT and "take this order?" from the p2p_chanakya report |
