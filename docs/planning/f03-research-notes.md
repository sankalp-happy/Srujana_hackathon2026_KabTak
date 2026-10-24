# F-03 Research Notes (as of 24 Oct 2026)

Collected by Haiku agents and checked by the lead session. Tags: **[P]** primary, **[S]** secondary, **[U]** unverified. The build plan is in `f03-build-plan.md`. Earlier idea reports are `ai-in-finance-hackathon-report.md` (Asli Odds, digital-arrest evidence) and `ai-in-finance-hackathon-report-part2.md` (Haq, Pay45, MSME evidence §1.2). There is also a US-centric outside report at `/Users/sankalpshankar/Projects/p2p_chanakya/HACKATHON_AI_FINANCE_CASH_FLOW_REPORT.md`.

## Decision
- **PS locked: F-03, Predictive Cash-Flow Management for Small Businesses.**
- Final ranking out of 35 (wow factor added): F-03 30, F-06 25, F-01 24.
- Context: Indian hackathon, 48h build, team mixed full-stack + ML.

## Problem evidence (use only [P] on slides)
- Delayed payments to MSMEs: ₹10.7 lakh cr (2022, GAME–D&B) [P]; ₹7.34 lakh cr (Mar 2024, GAME–FISME) [P]. Razorpay cites ₹8.1 trn from the MSME Annual Report 2025-26 [S].
- MSME Samadhaan: ₹20,979 cr pending; 16% of applications unresolved for over a year (CRISIL, Aug 2026) [P]; 31.8% rejected, 16.7% never viewed [P].
- MSME credit gap: about ₹25–30 lakh cr (SIDBI and Deloitte, via press) [S].
- Not found: share of MSMEs using forecasting software; survey percentages on overdraft or cash shortfalls.
- Avoid: the "82% of small businesses fail due to cash flow" figure (U.S. Bank / Jessie Hagen). The original study was never published [U].

## Competitors
| Tool | What it does | Source |
|---|---|---|
| RazorpayX Cashflow Insights | Balances, incoming payments, runway. Beta, Connected Banking+. No multi-period forecast or what-if | razorpay.com newsroom, 1 Jun 2026 [P] |
| Xero Analytics (ANZ) | 100/180-day forecast using **predicted payment dates**; editable dates; one-off what-if items | itbrief.co.nz, Mar 2026 [S] |
| QuickBooks Intuit Intelligence | "Cashflow Forecasting 2.0": history + live bank + predictive | quickbooks.intuit.com/ca, Oct 2026 [S] |
| Zoho Books | No native forecast (open feature request); third-party Cash Flow Frog | Zoho community [S] |
| TallyPrime | No native forecasting confirmed | [U] |
| Vyapar, myBillBook, Khatabook | Billing and ledger; no forecasting found | [U] |
| Claimsio (Poland) | AI SME debt collection; MAS FinTech award winner 2025 | mas.gov.sg, 13 Nov 2025 [P] |
| MSME Guard | Listed as an ICAI AI use case (~Jul 2026). Computes the 43B(h) disallowance, s.16 interest and 45-day classification from Tally; lists "payment prioritization" and "what-if simulations" without stating a method | [S] |
| TallyPrime 4.1, Sage X3 | MSME-1 / 43B(h) compliance reports | [S] |
| Hobby prototypes, Oct 2026 Hacktoberfest | github.com/StarKnightt/cashcast (12 Oct 2026): TabPFN days-to-pay quantiles, 2,000 simulated schedules and weekly cash ranges on IBM's public AR dataset (2,466 invoices). **It admits its ranges are too narrow because it treats invoices as independent.** Also Mialy333/late-pay-radar, arindewangan/latepay, and dev.to posts on PayRadar, Payday Radar and Paydar. The PayRadar write-up found that a per-client historical average often matches TabPFN | [S] |
| Treasury vendors (Kyriba, GTreasury, Agicap, Pulse) | Only scenario / what-if features found; no fix optimisation | [U] |

Positioning ladder: Record (Tally, Vyapar) → See (RazorpayX) → Predict (Xero, QuickBooks, cashcast-style prototypes) → **Decide (us)**. MSMED/43B(h) *computation* is not new (MSME Guard, TallyPrime 4.1, Sage X3). What we do differently is use those levers as zero-cost fixes inside a risk-budgeted optimiser, with open, tested rules.

## Tech radar
| Item | Facts | Status |
|---|---|---|
| Chronos-2 | Oct 2025, arXiv 2510.15821, 120M parameters (`amazon/chronos-2`; `autogluon/chronos-2-small` 28M); `chronos-forecasting` 2.3.2 (8 Sep 2026). Known future covariates via `Chronos2Pipeline.predict_df(context_df, future_df, prediction_length, quantile_levels)`. **Outputs quantiles only**, so we draw the paths with our own sampler. Licence ambiguous: README says Apache-2.0, badge alt text says MIT | [P] |
| TiRex / TiRex-2 | pip `tirex-ts`; TiRex-2 adds covariates + multivariate | [S] |
| Sundial | Flow-matching; **generates sample paths** | [P]; licence [U] |
| TimesFM 2.5 / 3.0 | 2.5 quantile head + XReg covariates; 3.0 weights non-commercial | [S] |
| Toto (Datadog) | Apache-2.0, multivariate | [P] |
| TabICLv2 | arXiv 2602.11139, ICML 2026; pip `tabicl` 2.2.0 (2 Sep 2026). Code BSD-3; the Hugging Face card is tagged bsd-3-clause (weights not documented separately). Has a classifier **and** a quantile regressor. Pretrained on about 300–48K rows and up to 100 columns; benchmarked to 100K rows; **under 300 rows is untested** (watch this for per-buyer data). GPU recommended, CPU works | [P] |
| TabPFN-2.5+ | Non-commercial weights | [P] |
| Mitra-v2 / TabDPT | Apache-2.0 weights (production alternative) | [P] from earlier report |
| MAPIE | `mapie.regression.TimeSeriesRegressor` (EnbPI, ACI) | [P] |
| Conformal Risk Control | Angelopoulos et al., arXiv 2208.02814, **ICLR 2024**; bounds expected loss (e.g. rupee shortfall). **No application to cash buffers, liquidity or treasury found** | [P] |
| OR-Tools CP-SAT | No official chance-constraint example. Pattern: a yes/no z_s per scenario, Σz ≥ (1−α)S, `OnlyEnforceIf` instead of big-M, integer-scaled coefficients. No published solve times: test locally | [P] pattern; speed [U] |
| Chance-constrained cash optimisation (academic) | Chen & Archibald 2024 (Int. J. Production Economics v270; joint chance constraint, SAA); Merville & Tavis 1973; Iyengar & Ma 2009 (CVaR). Novelty is limited to SME invoice-driven fix selection; no SME product found doing it | [P] papers; "no product" [U] |
| **EnterpriseArena** ("Can LLM Agents Be CFOs?") | arXiv 2603.23638, v2 16 May 2026. 132-month firm simulator; **only 15.4% of trials survive** (say "about 15%"; the earlier 16% was wrong); bigger models don't reliably do better | [P]. Pitch hook: the LLM only turns speech into a typed scenario |
| Invoice-delay ML prior art | **Survival / hazard models for invoice timing are published**: Springer s44257-024-00013-2 (2024, discrete survival GLMM, wholesale), arXiv 1912.10828 (2019), 2008.07363 (2020), Univ. of Tartu thesis 2016 (random survival forests) [P]. **TabPFN on days-to-pay exists in hobby projects** (cashcast etc., see Competitors) [S]. No TabICL, TabDPT or Mitra use and no peer-reviewed tabular-foundation-model paper found | mixed |
| Sarvam | Saaras v3 STT: 19.31% WER averaged over 10 Indic languages (vendor figure). Marathi, third-party (Josh Talks Voice of India, Apr 2026), OI-WER: Sarvam Audio 9.4%, Saarika 2.5 10.0%, Gemini 3 Pro 10.7%. Bulbul v3 supports Marathi, under 250 ms to first byte (vendor). Pricing: ₹100 free credit; STT about ₹0.49/min; TTS Bulbul v3 ₹3 per 1K characters, v4 Flash ₹1 per 1K (sources conflict) | [P/S] |

## Data access
- **TallyPrime:** XML/JSON/ODBC. Official docs describe JSON over POST. Port 9000 comes from a third-party blog. Confirm the endpoint.
- **GST data:** needs a GSP/ASP and taxpayer OTP consent; consent logs visible since 7 Nov 2025 [S]. Sandbox not verified.
- **Account Aggregator:** needs a licensed FIU; not realistic for the hackathon.
- **Plan:** a synthetic 24-month ledger in Tally's shape (spec in build plan §6).

## Cost inputs for the optimiser (verify before use)
- Bank Rate 5.75% from 7 Oct 2026 [P, earlier report] → MSMED interest at 3× = 17.25%, compounding monthly. Agents found the repo rate quoted as both 5.50% and 5.25%; re-check.
- MSME overdraft/cash credit: 8.75–11.5% public-sector banks, 9.5–14% private (Razorpay blog 2026) [S]. Federal Bank repo-linked overdraft 7.45–9.60% [S].
- TReDS discount: about 10% per year, illustrative only [U]. RXIL facilitated ₹80,500 cr in FY25 with 44k+ MSMEs [S].
- Legal levers (from Haq, report part 2):
  - MSMED s.15: payment due within 45 days, or 15 days without a written agreement;
  - s.16: interest at 3× the Bank Rate, compounding monthly;
  - IT Act 2025 s.37(2)(g): the buyer's deduction is allowed only when the invoice is paid;
  - CGST s.16(2): the buyer reverses its input tax credit at day 180 if unpaid;
  - MSMED Amendment 2026 status [S]: verify in the Gazette.

## Hackathon judging and demo advice
- **Actual rubric (Srujana 2026 rules [P], `srujana-2026-rules.md`):** problem 15, technical depth 20, functional completeness 15, **domain correctness 20**, validation 10, UX/accessibility 10, originality/presentation 10. No bonus for complexity or AI by itself. A demo video at H36 shortlists 10 Finance teams.
- Generic rubrics weight innovation and technical execution highest; presentation is usually lowest (vendor guides) [S].
- Consistent advice: **one flawless user journey beats many half-working features**; pre-fill data; mock slow APIs; never claim features that don't exist (JetBrains Jun 2026, snippet only [S]).
- No verified Indian finance-hackathon winners found.

## Innovations (disclosure: hold 3 and 4 from the H12/H24 progress evaluations; the H36 shortlist video shows all)
**Reframe after P3 (24 Oct):** no single model is new: hazard models for invoices are published, TabPFN days-to-pay prototypes exist, and chance-constrained cash optimisation is academic prior art. **What's new is the combination, tied to Indian law:** (a) payment timing that is *dependent* across invoices, which fixes the weakness cashcast itself admits; (b) a risk-budgeted optimiser whose fixes include zero-cost legal levers aimed at the buyer; (c) a CRC rupee bound, which nobody has applied to cash; (d) a voice UX that starts from the owner's decision. Name the prototypes before judges do: "hobby prototypes predict; we decide."

1. **From forecast to decision:** cheapest fix plan within a risk budget (chance-constrained). *Reveal.*
2. **"Not paid yet" counts as information, and invoices move together:** a censored hazard model per invoice with a shared buyer-level shock. Don't claim the foundation model is novel or much more accurate. *Reveal lightly.*
3. **Delay costs the buyer:** MSMED/tax/GST levers as zero-cost fixes; a compliance heads-up to the buyer's CFO. *Hold for round 2 (tease only).*
4. **Start from the owner's decision:** "Should I take Bajaj's ₹12 L order on 90-day terms?" *Hold for round 2.*
5. **Uncertainty you can check:** a rupee risk bound, drill-down on every number, the LLM never calculates. *Reveal.*
6. **Channel:** CA's Tally + Marathi WhatsApp voice; the CA as the distribution channel. *Partly reveal.*

## What the p2p_chanakya report contributed (and what we rejected)
- Adopted:
  - treat payment timing as survival / censored data;
  - Conformal Risk Control for the buffer;
  - CP-SAT for choosing fixes;
  - the "can I take this load/order?" voice check.
- Rejected:
  - US verticals and US statistics;
  - "incumbents use naive due dates" (out of date);
  - outdated "SOTA" (DeepHit, GFlowNets, SPO+);
  - Z3 covenant proofs;
  - "a 99% guarantee".

## Open research tracks (team, in progress)
1. Competitors (person 1)
2. Problem evidence (person 2)
3. ~~Tech + prior art (person 3)~~: **merged 24 Oct** (see Tech radar, Competitors, Innovations reframe)
4. User and persona: how MSME owners actually manage cash and late payers; validate Mahesh (person 4)
