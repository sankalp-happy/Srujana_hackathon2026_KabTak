# F-03 Build Plan: "Kab Tak?" (working name)

> **Living document.** Version 0.3, 24 Oct 2026. Event rules: `srujana-2026-rules.md` (Srujana Tech Fest, Chanakya University, 24–26 Oct). This is a 48-hour build: expect to change scope at every go/no-go gate. Record each change in the change log at the bottom, so the team never has to guess which version is current.
>
> Evidence tags: **[P]** primary source, **[S]** secondary, **[U]** unverified. Never put an [S] or [U] number on a slide as if it were settled.

---

## 1. One line, USP, and why now

**One line:** WhatsApp a voice note in Marathi asking *"Can I take this order?"* or *"What if Tata pays a month late?"* You see 1,000 possible futures for your bank balance, the week you're likely to run out of cash, and the **cheapest set of fixes** that keeps you safe, including legal levers Indian law already gives you.

**USP, in priority order:**
1. **It prescribes, not just predicts.** It picks the cheapest mix of fixes that keeps the shortfall risk under a target: invoice discounting on TReDS, an overdraft draw, deferring a supplier, or an MSMED heads-up to the buyer. Xero (Mar 2026) and QuickBooks (Oct 2026) forecast cash flow from predicted payment dates [S], and so do hobby prototypes such as cashcast (TabPFN, Oct 2026) [S]. None of them ranks fixes. Tools such as MSME Guard and TallyPrime 4.1 *compute* MSMED/43B(h) amounts [S], but none uses them as zero-cost fixes inside a risk budget.
2. **It separates expected money from received money.** Each open invoice gets a probability distribution over its arrival date, not a single due date, and **invoices from the same buyer move together** (a shared buyer shock). Prototypes that treat invoices as independent produce ranges that are too narrow; cashcast admits this itself [S]. The problem statement asks for timing uncertainty explicitly.
3. **It works where Mahesh already works:** WhatsApp voice in Marathi, with his CA's Tally data in the background.

**Why judges should believe it isn't a GPT wrapper:** in EnterpriseArena (arXiv 2603.23638, May 2026), only **about 15% (15.4%) of LLM-agent trials** kept a simulated firm alive for 132 months [P]. So in our system **the LLM only turns speech into a typed scenario. The simulator and the solver make every decision.**

---

## 2. Persona (constructed: validate with 2–3 owners and CAs before the event)

**Mahesh Patil, 46.** He runs a CNC job-work shop in Bhosari MIDC, Pune.
- **Business:** 14 workers, turnover about ₹4.2 cr (a micro enterprise), Udyam-registered since 2021.
- **Customers:** two auto-component Tier-1 suppliers bring in 70% of revenue, plus one public-sector company (CPSE).
- **Cash position:** ₹46 L receivable, ₹27 L of it more than 45 days old. He bridges the gap with a bank overdraft.
- **Tools:** his CA keeps TallyPrime. Mahesh works on WhatsApp and the phone, Marathi first.
- **His real question each week:** "Can I pay wages on the 7th? Should I take this new order?"

---

## 3. Problem-statement coverage (for the judges' checklist)

| What the PS asks for | Where we deliver it |
|---|---|
| Current liquidity | Today card: bank + overdraft headroom, receivable due vs overdue |
| Anticipate shortfalls | Fan chart; red "stress weeks" band; P(shortfall) per week |
| Revenue, receivables, suppliers, payroll, EMIs, opex, reserves | Synthetic ledger + scheduled-obligations calendar (§6) |
| Expected vs actually received, timing uncertainty | Per-invoice arrival distribution from the hazard model (§5.1) |
| Simulate delays, expense shocks, sales drop, supplier terms, revised schedules | Voice or typed scenario → typed schema (§5.5) |
| When a shortage happens; compare responses by their financial implications | CP-SAT action plan + side-by-side comparison of fixes (§5.4) |

---

## 4. The 3-minute demo script (hero journey: rehearse this one path until it's flawless)

1. **(0:00) Hook.** *"₹7.34 lakh crore owed to Indian MSMEs is paid late [P, GAME–FISME, Mar 2024]. Mahesh is profitable and still can't sleep before payday."*
2. **(0:20) Today.** The dashboard loads Mahesh's books. Fan chart of 1,000 paths over the next 90 days. Red band: *"Week of 17 Nov: 38% chance you can't pay wages."*
3. **(0:50) The hero moment.** Live, a Marathi voice note on WhatsApp: *"Should I take Bajaj's ₹12 L order on 90-day terms?"* About 10 s later the fan chart redraws: raw-material spend comes forward, the inflow lands 90+ days out, and the dip deepens to a 61% chance of a shortfall.
4. **(1:30) Fix it.** The solver returns: *"Take the order. Discount the Tata invoice on TReDS (₹6.6k), draw ₹4 L on the overdraft for 3 weeks (₹2.4k), and send Buyer A an MSMED heads-up. Shortfall risk falls to 4%. Total cost ₹9k, against ₹1.1 L margin on the order."* Show the fixes side by side.
5. **(2:10) Why should I trust this?** Tap the ₹6.6k figure: you see the invoice's arrival distribution and the legal and interest arithmetic behind it. Then the backtest slide: our arrival forecasts against a due-date baseline.
6. **(2:40) Reply.** A Marathi voice-note answer plays. Close: *"From 'I hope' to 'I know, and here's the cheapest fix.'"*

**Backup:** a pre-recorded video of the same journey, plus an offline mode with cached model outputs.

---

## 5. How it works (stack plus a fallback for each layer)

```
Tally XML/JSON  or  synthetic ledger
        │
        ├─► [5.1] Arrival-date model per open invoice  ──┐
        ├─► [5.2] Chronos-2 for small daily flows      ──┤
        └─► Scheduled obligations (payroll, EMI, GST) ──┤
                                                         ▼
                              [5.3] Monte Carlo: 1,000 daily cash paths
                                                         │
                     [5.3b] Conformal Risk Control buffer ┤
                                                         ▼
                              [5.4] CP-SAT: cheapest fix set (chance constraint)
                                                         ▲
   WhatsApp voice → Sarvam STT → [5.5] LLM → typed Scenario ┘   → Bulbul TTS reply
```

### 5.1 Arrival-date model (ML1): a discrete-time hazard model
- **Why hazard:** open invoices are *censored* (not paid *yet*). A plain regression on paid invoices ignores them and is biased towards fast payers.
- **Rows:** one row per invoice per week while it is still unpaid. The label is "paid in this week?".
- **Features:** buyer; amount (log); weeks since invoice; days past due; month-end or quarter-end flag; the buyer's trailing DSO; accepted, disputed or GRN-pending flag; festival-month flag.
- **Model:** TabICLv2 classifier learning in context from 24 months of history; no training run. Code is BSD-3 and the Hugging Face card is tagged bsd-3-clause [P]. Pool all buyers into one table with buyer as a feature: TabICLv2 is untested below 300 rows [P]. For the production story, name Mitra-v2 or TabDPT (Apache-2.0).
- **Prior art (say it first):** discrete-time hazard models for invoices are published (Springer 2024, arXiv 1912.10828, 2008.07363) [P]. We don't claim the model is new; we claim what it feeds.
- **Output:** chain the weekly hazards into an arrival distribution per invoice, and sample from it in §5.3.
- **Baselines:** (a) paid on the due date (the villain), (b) **per-client historical average days-to-pay** (the PayRadar write-up found this often matches TabPFN [S], so it is the baseline to beat honestly), (c) LightGBM hazard model.
- **Fallback:** a Kaplan–Meier survival curve per buyer, using `lifelines`.

### 5.2 Small daily flows (ML2)
- **Model:** Chronos-2 (Oct 2025; `Chronos2Pipeline.predict_df` with a `future_df` of covariates [P]) for walk-in job-work receipts, scrap sales, power and consumables. Licence is ambiguous (README Apache-2.0, badge alt text MIT) [P]: cite both in the README.
- **Known future covariates:** working days, festival calendar, month-end.
- **Output:** quantiles only [P], so our own sampler draws paths from them.
- **Fallback:** seasonal bootstrap of past weeks.

### 5.3 Monte Carlo (ML2)
- 1,000 paths × 90 days, vectorised in numpy.
- `cash[t] = cash[t-1] + sampled invoice receipts + small inflows − scheduled outflows − variable outflows`.
- **Dependence:** each path draws one delay shock per buyer (plus a quarter-end shock shared by all buyers) that shifts every open invoice of that buyer together. This is the fix for the too-narrow ranges cashcast admits [S]. Validation shows the fan width with and without the shared shock.
- **Outputs:** fan chart (P10/P50/P90), P(cash < 0) per week, and the expected shortfall.

### 5.3b Buffer from Conformal Risk Control (ML1, stretch for H18–30)
- **Method:** Conformal Risk Control (Angelopoulos et al., arXiv 2208.02814, ICLR 2024 [P]; no prior use on cash buffers found [S]). Backtest with rolling forecast origins over the last 12 months, where the loss is the rupee shortfall. Choose the buffer λ so that **expected shortfall ≤ ₹25k**.
- **On screen:** *"Keep ₹3.2 L in reserve."*
- **Honesty:** the guarantee holds on average and assumes the data is exchangeable. Never say "guaranteed won't bounce."
- **Fallback:** take the buffer as an empirical quantile of shortfall across the Monte Carlo paths.

### 5.4 Fix solver (FS2 + ML1)
- **Tool:** OR-Tools CP-SAT over **200 scenarios at weekly steps for 13 weeks**.
- **Decisions:**
  - TReDS discount for each eligible invoice (yes/no; only accepted invoices from buyers registered on TReDS);
  - overdraft draw per week (in ₹10k units, up to the limit);
  - supplier deferral per bill (0, 15 or 30 days, with a relationship-cost penalty);
  - MSMED heads-up per buyer (yes/no). Its effect, an earlier hazard, is an **assumption the user can see and change**;
  - accept or reject the new order.
- **Chance constraint:** a yes/no variable z_s for each scenario; Σ z_s ≥ 0.95·S; `cash_s,t ≥ 0` enforced with `OnlyEnforceIf(z_s)` (no big-M); integer-scaled rupee coefficients. No official example or published solve times, so time it in the H6–12 spike [P/U]. Prior art: Chen & Archibald 2024 (IJPE v270) on chance-constrained working capital [P]; our novelty is SME invoice-level fix selection.
- **Objective:** minimise rupee cost (discount fees + overdraft interest + penalties), minus the margin on the order if accepted.
- **Cost inputs** (verify before the event):
  - overdraft 8.75–14% per year [S, by bank type];
  - TReDS discount around 10% per year [U];
  - MSMED interest at 3× the Bank Rate = 17.25%, with Bank Rate 5.75% from 7 Oct 2026 [P]. The agents found conflicting repo-rate figures, so re-check.
- **Legal levers:** reuse Haq's rule sketch in **plain Python behind 30 hand-computed tests**: s.15 due date, s.16 interest, the GST credit reversal at day 180, and the buyer losing its tax deduction under s.37(2)(g). Catala is cut (see the cut list).
- **Fallback:** greedy search over small fix bundles, evaluated on the Monte Carlo paths.

### 5.5 Voice and scenario layer (FS1)
- **Channel:** WhatsApp Cloud API test number. Speech-to-text with Sarvam Saaras v3; text-to-speech with Bulbul V4 Flash (Marathi).
- **LLM output:** a Pydantic `Scenario` with type `new_order | delay_payment | expense_shock | sales_drop | supplier_terms | schedule_change` and typed parameters, produced with structured output.
- **Ambiguity:** if the request is unclear, the LLM asks **one** follow-up question.
- **The LLM never produces numbers itself.**
- **Fallback:** a web chat with a mic button, in Hindi or English.

### 5.6 Front end (FS2)
- Next.js (or Streamlit if we're behind) with four screens: **Today card**, **fan chart with a stress band**, **scenario panel with sliders**, and **fix comparison with "why this number?" drill-downs**.
- A WhatsApp-style phone panel on the right, mirroring the real WhatsApp flow for the stage.

---

## 6. Data: the synthetic Mahesh ledger (FS1, ready by H6)

Generate 24 months of history with planted behaviour, so the models have something real to find:

| Item | Spec |
|---|---|
| Revenue | ~₹35 L/month; 3 anchor buyers (Tier-1 A 40%, Tier-1 B 30%, CPSE 15%) + ~20 small customers (15%) |
| Payment behaviour | A: pays ~day 60 and slips at quarter-end; B: ~day 45, pays reliably; CPSE: 75–120 days, long tail; small customers: mostly within 30 days |
| Receivable today | ₹46 L, ₹27 L of it past 45 days (matches the persona) |
| Payroll | 14 workers, ~₹3.4 L on the 7th of each month |
| Raw material | ~45% of revenue; suppliers on 30-day terms |
| Fixed costs | Rent, power (~₹1.8 L, with summer spikes), CNC machine EMI ₹1.2 L on the 5th |
| Statutory | GST payable on the 20th; TDS; advance tax in Jun, Sep, Dec and Mar |
| Facilities | Overdraft limit ₹25 L; opening balance ~₹4 L |
| Events | Festival-month slowdown (Oct–Nov); one disputed invoice; one CPSE invoice at 180+ days |

Export it in the Tally XML shape, so that "connect your CA's Tally" is a believable claim.

---

## 7. 48-hour timeline with go/no-go gates

**Fixed by the rules** (hours from the organisers' official start): progress evaluations about every 12 h (≈H12, H24, H36); **demo video due H36, and it decides the shortlist** (10 Finance teams go to the final); full repo + README + working demo due H48; final = live presentation + Q&A. So the product must be demoable at every evaluation and **video-ready by H30**, not H40.

| Hours | FS1 | FS2 | ML1 | ML2 |
|---|---|---|---|---|
| **0–6** | Ledger generator; WhatsApp test number | Next.js skeleton; fan chart on dummy data | TabICLv2 install spike; hazard-row builder | Chronos-2 spike; Monte Carlo skeleton |
| **Gate H6** | **TabICLv2 + Chronos-2 run end to end on the generated ledger? If not, switch to the fallbacks (KM / bootstrap) now.** |||
| **6–12** | STT → LLM → Scenario schema | Today card; scenario sliders | Hazard model + due-date baselines | Monte Carlo wired up; stress weeks |
| **Gate H12 (eval 1)** | **Show: ledger → fan chart → stress week, reacting to a typed scenario. If not, cut WhatsApp and go web-only.** |||
| **12–24** | Voice → Scenario on the web mic; Marathi copy | Fix-comparison UI; drill-downs | Legal-lever rules + 30 tests; backtest | Greedy fix search first, then CP-SAT |
| **Gate H24 (eval 2)** | **Hero journey runs end to end on the web. Solver plan in under 5 s, else ship greedy.** |||
| **24–30** | WhatsApp loop + Bulbul reply on a real phone | Polish; offline cache mode; accessibility pass | CRC buffer (stretch); validation numbers | Hero-scenario tuning; edge cases |
| **H30** | **Feature freeze for the video.** |||
| **30–34** | Record the demo video (3 takes) | Edit video; captions | Validation slide for the video | Rehearse hero path |
| **H34** | **Submit the video (2 h buffer before H36).** |||
| **36–48** | README: setup, deps, decisions, limitations, AI-use disclosure | Slides; fixes only | Judge Q&A prep; domain-assumption sheet | Rehearse ×5; submit repo by H46 |

---

## 8. Cut list (do not build unless every gate is green early)

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

1. **Arrival-date calibration:** how often actual arrival dates fall inside our 80% intervals, compared with the due-date baseline.
2. **Shortfall lead time** in the backtest: days of warning before a real cash crunch. Compare us, "due date", and "due date + average delay".
3. **Buffer from Conformal Risk Control:** realised expected shortfall against the ₹25k target, on held-out months.
4. **Solver speed** and **cost of the fixes** compared with a naive rule ("draw the overdraft whenever cash goes negative").
5. **Rule tests:** 30 of 30 hand-computed legal and interest cases pass.

---

## 10. Risks, and what we do about each

| Risk | Mitigation |
|---|---|
| Synthetic data looks fake | Plant realistic mechanisms; ask a CA friend for one anonymised Tally export before the event |
| TabICLv2 or Chronos-2 install or GPU trouble | H6 gate; KM and bootstrap fallbacks; get a cloud GPU (Colab or Modal) set up in advance |
| WhatsApp Cloud API approval or webhook flakiness on stage | Web phone panel mirror + backup video |
| Marathi STT error on stage | Pre-test the exact hero sentence; typed fallback |
| CP-SAT too slow | Cut to 100 scenarios, or use the greedy fallback |
| A judge asks "isn't this legal or financial advice?" | It computes and compares options; the owner decides and sends. Show the assumptions as visible toggles |
| An ML judge challenges the guarantee | State it precisely: averaged, assumes exchangeable data, backtested |
| Wrong figures for rates or law | Re-check the Bank Rate, TReDS rates and the MSMED Amendment 2026 status in the Gazette before the event |

---

## 11. Likely judge questions (prepare answers)

- *How is this different from Xero or QuickBooks forecasting?* They forecast; we prescribe the cheapest survival plan, with Indian legal levers, in the owner's language.
- *Isn't this just cashcast / PayRadar?* Hobby prototypes predict; we decide. They also treat invoices as independent, which makes their ranges too narrow (cashcast says so). We model shared buyer shocks and show a per-client-average baseline.
- *MSME Guard and Tally already compute 43B(h).* Yes, as reports. We use the same rules, open and tested, as zero-cost fixes that the optimiser weighs against TReDS and overdraft costs.
- *Hazard models and chance constraints aren't new.* Right, and we cite them. What's new is the combination, applied to one Indian micro-business's invoices, with a CRC rupee bound nobody has applied to cash.
- *Why not let GPT do it?* EnterpriseArena: about 15% of agent trials survive. Our LLM only writes typed scenarios.
- *Where does real data come from?* The CA's Tally (XML/JSON over HTTP); later, Account Aggregator.
- *Business model?* A CA-led channel (one CA serves dozens of MSMEs), a TReDS or lender referral fee, or a bank white-label for MSME overdraft customers.
- *What if a buyer gets angry about the MSMED heads-up?* It's framed as a compliance heads-up, it's optional, and the owner approves every message.

---

## 11b. Rubric map (100 points, from the rules) and compliance

| Criterion | Pts | What earns it here | Gap to close |
|---|---:|---|---|
| Problem understanding and relevance | 15 | §3 coverage table; expected vs received money; Mahesh's real question | Persona is constructed: ask a mentor or CA to sanity-check it |
| Technical depth and implementation | 20 | Censored hazard model, Monte Carlo, chance-constrained solver | Rules say complexity earns nothing by itself: **every model must beat its baseline on a slide** |
| Functional completeness and reliability | 15 | All six PS scenario types work (sliders/typed), hero path flawless | Voice covers only the hero; sliders must cover the rest |
| Domain analysis and correctness | 20 | MSMED s.15/s.16, s.37(2)(g), CGST day-180, overdraft and TReDS cost arithmetic, 30 tests | Verify Bank Rate, TReDS rates, Amendment 2026 Gazette status; one-page domain-assumption sheet |
| Validation and robustness | 10 | Calibration, shortfall lead time, CRC realised loss, rule tests | Edge cases: buyer with no history, zero receivables, overdraft maxed, disputed invoice |
| User experience and accessibility | 10 | Marathi voice, one-screen answers | Text alternative to every voice reply; readable, colour-blind-safe fan chart; plain-language labels |
| Originality and presentation | 10 | Forecast → cheapest fix, buyer-side legal levers | Video at H36 is the shortlist gate |

**Compliance (disqualification risks):**
- Write no code before the official start; the plan and research docs are fine.
- README must disclose AI-tool use and acknowledge TabICLv2, Chronos-2, OR-Tools, Sarvam, WhatsApp Cloud API and the synthetic data. Each teammate must be able to explain their own part and say what is incomplete.
- Show a "computes and compares options, not financial or legal advice" note on screen. Never say "guaranteed".
- Label the ledger as synthetic everywhere. Fabricated claims are grounds for disqualification, so [S]/[U] figures never go on a slide as fact.

## 12. First hours of the event (was "before the hackathon"; owner in brackets)

- [ ] Read the organisers' judging rubric; re-weight this plan to match it
- [ ] TabICLv2: check the weights licence; test TabICLv2 and Chronos-2 on a laptop or Colab
- [ ] Sarvam API credits; test Marathi STT and TTS on the hero sentence
- [ ] WhatsApp Cloud API test number + webhook (ngrok or Cloudflare tunnel)
- [ ] Verify: Bank Rate and repo rate as of Oct 2026, current TReDS discount rates, typical MSME overdraft rate, MSMED Amendment Act 2026 Gazette status
- [ ] 2–3 MSME owner or CA conversations to validate the persona and the "can I take this order?" question

---

## Change log

| Date / hour | Change | Why |
|---|---|---|
| 24 Oct 2026 | v0.3: P3 merged. Dropped the "nobody uses foundation models / encodes MSMED" claims; reframed the novelty as the combination (dependent timing + legal-lever optimiser + CRC bound + decision-first voice). Added a shared buyer shock to the Monte Carlo, a per-client average baseline, CP-SAT `OnlyEnforceIf`, and pooled TabICLv2 rows. EnterpriseArena 16% → about 15% (15.4%). New judge Q&A on cashcast, MSME Guard and prior art | P3 found TabPFN days-to-pay prototypes (cashcast etc.), published hazard models, and MSMED calculators (MSME Guard, TallyPrime 4.1) |
| 24 Oct 2026 | v0.2b: No cuts; full stack kept, and the H12/H24 gates decide fallbacks. The H36 video shows all innovations (1–5); 3 and 4 are held back only from the H12/H24 progress evaluations | User decision |
| 24 Oct 2026 | v0.2: Re-timed to the rules: freeze H30, video submitted H34 (due H36, shortlist gate), evals ≈H12/H24/H36 become gates, H40–48 is README/slides/rehearsal. Greedy solver now built before CP-SAT. Added §11b rubric map + compliance | Rules (`srujana-2026-rules.md`): video decides shortlist; rubric weights domain correctness and technical depth highest; AI disclosure required |
| 24 Oct 2026 | v0.1: F-03 locked. Stack: hazard TabICLv2 + Chronos-2 + Monte Carlo + CRC + CP-SAT + Marathi voice | Ranking 30/35; added survival, CRC, CP-SAT and "take this order?" from the p2p_chanakya report |
