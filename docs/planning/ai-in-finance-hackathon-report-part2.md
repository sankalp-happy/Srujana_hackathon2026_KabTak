# AI in Finance Hackathon, Part 2: MSME Late Payments and NBFC / Co-op Bank Compliance (4 Ideas, India)

*Prepared 20 Oct 2026. Companion to `ai-in-finance-hackathon-report.md`, which holds ideas 1–5; this report continues the numbering with ideas 6–9. Research: 13 Claude Haiku agents, which only collected evidence. Angles, personas, feature cuts and technology choices: Claude Opus. Constraints: India market, 36–48h build, mixed full-stack + ML team.*

**Evidence tags:** **[P]** = an agent read the primary source · **[S]** = secondary press, a vendor page or a search snippet · **[U]** = unverified. Check **[S]** and **[U]** figures before they go on a slide. "Our arithmetic" marks numbers we derived ourselves.

---

## TL;DR

**Two problem statements:**
- **PS-1.** Indian micro and small suppliers get paid late, and the cash gap pushes them into costly credit.
- **PS-2.** Compliance at NBFCs and co-operative banks after RBI folded 9,445 circulars into about 240 Master Directions on 28 Nov 2025, including re-KYC and CKYCR execution.

| # | Idea | PS | Persona | Novel tech it uses | One-line USP |
|---|---|---|---|---|---|
| 6 | **Haq** ⭐ ("what you're owed") | 1 | Owner of a 14-person CNC job-work shop, Pune | **Law-as-code in Catala, written by an LLM** and gated by hand-computed tests (Law to Code, ICML 2026; Catala 1.3.0); Sarvam voice | Tells the *buyer* what paying late costs the buyer (a lost tax deduction, a GST credit reversal, 17.25% compound interest), with every rupee traced to the statute. Files only claims that clear the known rejection grounds |
| 7 | **Pay45** | 1 | Head of accounts payable at a ₹650 cr auto-component maker | **TabICLv2** tabular foundation model (ICML 2026), learning from the company's own invoices in context; **conformal** coverage (MAPIE 1.6) | Flags which supplier invoices will cross the 45-day line weeks before they do, while there's still time to fix them |
| 8 | **Naksha** ("map") | 2 | Compliance officer at a Tier-2 urban co-op bank | **Graphiti** bi-temporal knowledge graph (v0.31, Oct 2026) plus **LegDiff**-style clause comparison (ACL 2026) | Maps every withdrawn circular the bank's policies cite to the paragraph that now carries it, says what changed, and answers "what applied on date X?" |
| 9 | **Nootan** ("renewal") | 2 | KYC officer at a district central co-op bank, Rajasthan | Sarvam **Voice Agents** with **Bulbul V4 Flash**, run inside a typed compliance state machine; conformal hand-off; Aadhaar offline QR verification (Dec 2025 rules); mocked **CKYCRR 2.0** | Picks the cheapest lawful re-KYC route for each customer who is due, and keeps the per-customer trail inspectors check: 3 + 3 notices, declarations, CKYCR clocks |

**Recommendation: build Haq.**
- It has the strongest primary numbers: ₹20,979 cr stuck on MSME Samadhaan, and **31.8% of applications rejected by the councils**.
- Judges get the persona in ten seconds, and the WhatsApp demo works live.
- Its novelty is easy to show: rules written by an LLM must compile and pass tests before they compute anyone's money.
- **For PS-2, Nootan is the safer build:** its rules and penalties are primary-sourced. **Naksha** is the most novel, but its pain is inferred, not measured.

**Compared with the first report:** on the same rubric Haq scores 29, just under ClaimProof and Asli Odds (31 each). Haq and ClaimProof follow the same pattern: statute → executable rules → paperwork for a cheap way to seek redress. A team that liked ClaimProof can switch domains without needing new skills.

---

## How this was produced

- **Round 1 (8 agents).** For each PS:
  - (a) persona, current workflow and competitors;
  - (b) the exact legal and regulatory text;
  - (c) data, API and sandbox access.
  - Plus two technology scans: regtech / legal AI, and MSME credit and payments.
- **Your decision midway.** You picked the two recommended angles per PS:
  - PS-1: the supplier side and the buyer side.
  - PS-2: circular re-mapping and re-KYC execution.
  - Cut: a triage tool for MSE Facilitation Councils, credit against invoices not on TReDS, a penalty self-inspection tool, and AI model-risk compliance.
- **Round 2 (5 agents):**
  - The feasibility of each idea's technology: Catala, tabular foundation models, Graphiti plus how RBI structures its documents, and the re-KYC stack.
  - One more pass on numbers for MSME pain.
- **Agents were told not to propose ideas.** Every idea below was designed from their evidence in a separate step.

---

## Step 1: Research the problem

### 1.1 Why these two were runners-up, and what changed

| | First report's verdict | What this round found |
|---|---|---|
| **PS-1** MSME late payments | Runner-up: high pain, mixed evidence, medium fit with new tech | **Primary funnel data:** 31.8% of Samadhaan applications rejected, 16.7% never viewed. **A new Act with 90-day clocks.** **Three legal levers that each cost the buyer money.** Law-as-code and tabular foundation models fit well |
| **PS-2** NBFC / co-op compliance | Dropped: B2B, small fines | **Co-op banks drew 264 of 353 RBI penalties in FY25** [S]. 2026 penalty orders keep citing the same re-KYC/CKYCR lapses. **RBI's list of withdrawn circulars has no column for the circular numbers banks actually cite.** Temporal knowledge graphs and new Indic voice agents fit |

### 1.2 PS-1: late payments to micro and small suppliers

**Scale**
- **Delayed payments to MSMEs:**
  - **₹10.7 lakh cr a year** in 2022, 5.9% of GVA, with about **80% owed to micro and small units** *(GAME–Dun & Bradstreet, May 2022 [P])*.
  - Down to **₹7.34 lakh cr by Mar 2024** *(GAME–FISME report 3.0 [P], publication date not shown)*.
- **69% of payments by public-administration buyers ran 60+ days late** (2020 data). TReDS addressed under 5% of the problem *(GAME–D&B 2022 [P])*.
- **MSME Samadhaan** *(CRISIL, 17 Aug 2026, data as of 14 Aug [P])*:
  - 2,56,892 applications covering ₹55,244 cr.
  - **₹20,979 cr pending.**
  - **40,580 applications (16%) unresolved for over a year.**
- **Load on the councils** *(CRISIL [P], not cross-checked)*:
  - Rajasthan: 9 councils averaging **1,767 applications each**.
  - Uttar Pradesh: 19 councils averaging 1,095.
  - Karnataka: 35 councils averaging 397.
- **8.84 crore enterprises are registered** on Udyam and Udyam Assist (30 Jun 2026); 99.3% of them are micro [S].
- **Who owes the money:** the claim that "40% sits with PSUs and government" is **not supported**. Shares found range from:
  - ~16%: central ministries and CPSEs against private buyers, Jan 2022 [S];
  - ~25%: state governments and CPSEs, undated [S];
  - "two-fifths" (Swarajya, Jan 2026 [S]), which doesn't reconcile with the totals.
  - **Don't put a single figure on a slide.**

**Where claims end up: the Samadhaan funnel** *(samadhaan.msme.gov.in homepage [P]; no as-of date, but the total matches CRISIL's 14 Aug 2026 figure; shares are our arithmetic)*

| Status | Applications | Share |
|---|---|---|
| **Rejected by the council** | **81,761** | **31.8%** |
| Disposed | 63,366 | 24.7% |
| Under consideration | 44,646 | 17.4% |
| **Not yet viewed by the council** | **42,879** | **16.7%** |
| Settled by mutual agreement | 24,240 | 9.4% |
| **Total** | **2,56,892** | 100% |

- **Councils don't publish why they reject.** Grounds the courts have upheld:
  - **The supplier must be registered on the contract date.** Registering later only helps from then on *(Silpi Industries v. KSRTC, SC, 29 Jun 2021, para 26 [P])*. Also *Gujarat State Civil Supplies v. Mahakali Foods*, SC, 31 Oct 2022 [S].
  - **The Limitation Act applies** to MSEFC arbitration *(Silpi, para 18 [P])*. A later SC case revisited the point; check it before relying on this [S].
  - **Trader-only registrations** are described as falling outside Secs 15, 16, 23 and 43B(h) [S].
  - **Territorial jurisdiction** is contested between High Courts. Kerala reads the supplier's location as the only forum; Bombay limits a council to its own territory [S].
- **Filing has moved to the MSME ODR portal:**
  - Since 15 Oct 2025 new claims go through the ODR portal (live 27 Jun 2025), and Samadhaan takes no new filings [S].
  - No national ODR statistics were found. Telangana reports about 800 cases filed and 85 resolved (Aug 2026 [S]).

**The levers the law already gives the supplier**

| Lever | Rule | What the delay costs the buyer | Evidence |
|---|---|---|---|
| **MSMED Act s.15** | Pay by the agreed date, **at most 45 days** from acceptance or deemed acceptance; **15 days** without a written agreement. Acceptance is deemed if there's no written objection within 15 days | Starts every other clock | [S] (sources differ on whether the clock starts at delivery or at acceptance) |
| **MSMED s.16 and s.23** | **Compound interest, monthly rests, at 3× the RBI Bank Rate**, regardless of the contract. The interest is **not tax-deductible** | Bank Rate is **5.75% from 7 Oct 2026** [P] (repo rate 5.50%) → **17.25% a year, compounding monthly** (our arithmetic) | [P] rate; [S] Act text |
| **Income-tax Act 2025 s.37(2)(g)** (formerly s.43B(h)) | Late payments to MSEs are deductible **only when actually paid**. Paying before the return due date doesn't rescue the year | If unpaid at the buyer's year-end, the whole amount is disallowed that year: about **25% of the invoice in extra tax** for a company at the 25.17% rate (our arithmetic) | [S] Rajya Sabha reply, 21 Jul 2026 |
| **Form 3CD clause 22** (from AY 2025-26) | The tax auditor reports MSE payables, split into paid within and beyond the limit | Visible to the auditor and the tax department | [S] (clause numbering conflicts; a new Form 26 may replace 3CD from FY 2026-27 [U]) |
| **CGST s.16(2), 2nd proviso / Rule 37** | The buyer reverses input tax credit (ITC) if the supplier is unpaid **180 days after the invoice date**, with interest, and reclaims it on payment | The GST on the invoice, e.g. ₹90k on a ₹5.9 L invoice at 18%. **Applies to every supplier, MSE or not** | [S] ICAI CA Journal, Aug 2026 |
| **MCA MSME Form I** | Specified companies report MSE dues older than 45 days every half-year (April and October) | A disclosure; reported penalty amounts conflict | [S] |
| **MSMED (Amendment) Act 2026** | Mediation within 90 days; arbitration within 30 days after that; award within 90 days; **75% pre-deposit to challenge an award**, with at least half released after 6 months; **CPSEs to settle MSE invoices on TReDS** | Stalling gets slower to do and more expensive | [S] Reportedly Act No. 16 of 2026, mostly in force from **15 Oct 2026** (S.O. 5575(E), 12 Oct 2026). CRISIL's 17 Aug release still called it a proposed bill [P]. **Verify the Gazette** |

**Current defences and what they miss**

| Defence | What it acts on | What it misses |
|---|---|---|
| **Samadhaan → MSME ODR** | A statutory claim against the buyer | 31.8% rejected and 16.7% never viewed [P]. The supplier has to decide to fight its own customer, and gets no check of the claim before filing |
| **TReDS** (₹3.47 lakh cr discounted in FY26 [S]; RXIL alone financed ₹80,500 cr in FY25 with 44k+ MSMEs [S]) | Discounting of invoices the buyer has accepted | The buyer must upload or accept the invoice, so the supplier can't start it. RXIL had 44k+ MSMEs registered [S], against 4.72 crore Udyam-portal registrations [S]. In 2022 TReDS addressed under 5% of the problem [P] |
| **The 45-day tax rule** | The buyer's tax deduction | Works only if the buyer's finance team tracks it invoice by invoice. The SME Chamber says buyers pressured suppliers to drop Udyam registration instead [S]. A 40,000-cancellations claim is [U] |
| **Billing apps** (Vyapar, myBillBook reminders [S]) | "Please pay" WhatsApp/SMS nudges | Don't tell the buyer what the delay costs **the buyer**. No eligibility check, no claim preparation |
| **CredFlow-type receivables dashboards** (2021 [S]) | Tracking and reminders | No dispute filing or statute engine found in their public descriptions [S] |

**The gap.**
- The levers already exist, but they sit in three different laws, each with its own clock: 15/45 days, 180 days, and the buyer's year-end.
- The supplier's only visible moves are a "please pay" message or a legal claim against its own customer.
- **Nothing connects the supplier's invoice to the buyer's own cost of delay, and nothing checks a claim before a third of claims get rejected.**
- On the buyer's side, the same clocks are tracked **after the fact, at tax-audit time.**

### 1.3 PS-2: compliance at NBFCs and co-operative banks after the consolidation

**What changed on 28 Nov 2025**
- **RBI issued function-wise Master Directions (MDs) for 11 types of regulated entity** *(Press Release 2025-2026/1588 [P])*:
  - The release says "238 function-wise Master Directions" in one place and **244** elsewhere. The 244 includes 7 new Digital Banking Channels MDs.
- **9,445 circulars were withdrawn** *(RBI/2025-26/100 [P])*.
  - One press figure says 5,673 were repealed [S]; this doesn't reconcile.
  - The drafts were posted on 10 Oct 2025 and drew 770+ comments [S].
- **Savings clause:** anything done under a withdrawn circular stays governed by it [P]. An inspection that looks back across that date needs both the old text and the new.
- **The list of withdrawn circulars is a web listing with columns Date | Subject | Department, and no circular-number column** [P]. Banks' policies cite numbers like "DBR.AML.BC.No.81/14.01.001/2015-16", so the list can't be searched by the reference a bank actually holds.
- **MDs are updated in place.** For example, the UCB Cash Reserve Ratio / Statutory Liquidity Ratio Directions page reads "Updated as on October 09, 2026" [P].
- A separate supervisory consolidation (628 circulars into 64 MDs, effective 31 Jul 2026) is reported by one source only [U].

**Who carries it**
- **1,457 urban co-operative banks (UCBs)** at end-March 2025, provisional *(RBI Report on Trend and Progress [P])*:

  | UCB tier (by deposits) | Banks | Share |
  |---|---|---|
  | Tier 1 (≤ ₹100 cr, plus unit and salary earners' banks) | 838 | 57.5% |
  | **Tier 2 (₹100–1,000 cr)** | **535** | **36.7%** |
  | Tier 3 (₹1,000–10,000 cr) | 78 | 5.4% |
  | Tier 4 (> ₹10,000 cr) | 6 | 0.4% |

  Tier definitions: RBI/DOR/2025-26/269, 4 Dec 2025 [P].
- **NBFCs:**
  - 15 NBFCs in the Upper Layer for 2024-25 [P]. Base- and middle-layer counts were not found.
  - The Chief Compliance Officer mandate covers only the upper and middle layers; **the base layer is exempt** [P].
- **Compliance load:**
  - A single-state NBFC faces **621 compliances**.
  - **94% of NBFC compliance officers say they lack visibility and control** *(TeamLease RegTech report, 2023–24 [S])*.

**Where penalties land**
- **FY25: 353 RBI penalties totalling ₹54.78 cr** *(Business Standard, 1 Jun 2025 [S])*:
  - **co-op banks: 264** (₹15.63 cr);
  - NBFCs and ARCs: 37 (₹7.29 cr).
  - FY26 totals are unverified.
- **2026 examples:**

| Entity | Amount | Date | KYC-related lapse | Tag |
|---|---|---|---|---|
| Shree Laxmi Co-op Bank, Pune | ₹2 L (4 charges in total) | Order 22 May 2026 | **No periodic review of risk categories; CKYCR upload late** | [P] |
| Ganganagar Kendriya Sahakari Bank (district central co-op bank), Rajasthan | ₹3 L | 9 Feb 2026 | **No six-monthly risk review; incomplete periodic KYC updation** | [S] |
| Sambalpur district central co-op bank | ₹8 L | Jul 2026 roundup | No periodic review of risk categories | [S] |
| Nawada central co-op bank | ₹50k | Jul 2026 roundup | Late CKYCR upload | [S] |
| Kedarnath UCB, Latur | ₹40k | Aug 2026 | Late CKYCR upload (plus deposit-rate breach) | [S] |
| Progfin; Fusion (NBFCs) | ₹2.70 L each | Aug 2026 | No periodic review of risk categories | [S] |
| Shri Ram Finance (NBFC) | ₹8.10 L | Aug 2026 | Late CKYCR uploads; missing risk tiers (plus a director appointment) | [S] |

- **KYC or CKYCR lapses appear in 8 of the 14 penalty cases our agents found.** This is a sample selected from the news, not a census [S].

**The re-KYC and CKYCR rules, exactly**
*(These come from the 2016 KYC MD as amended on 12 Jun 2025. The Nov 2025 consolidation re-issued KYC directions for each type of entity [S], and their paragraph numbers were not verified.)*

| Obligation | Rule | Source |
|---|---|---|
| How often KYC must be updated | High risk: at least once every **2 years**; medium: every **8**; low: every **10** | 2016 MD para 38 [P] |
| **Notices** | **At least 3 advance notices, at least one of them by letter.** After the due date, **at least 3 reminders, at least one by letter.** Letters must say how to update, where to get help, and the consequences. **In force by 1 Jan 2026** | Amendment of 12 Jun 2025, new para 38(e) [P] |
| Low-risk grace | All transactions allowed. Update within 1 year of the due date or **by 30 Jun 2026, whichever is later** | Para 4(i) [P]. No extension found after 30 Jun 2026 |
| Business correspondent (BC) route | A BC may take a self-declaration for "no change" or "address-only change" after **biometric e-KYC** | New para 38(a)(iia) [P] |
| Responsibility | "ultimate responsibility for periodic updation of KYC remains with the bank" | Para 38(c) [P] |
| **CKYCR clocks** | **Upload within 10 days** of opening the account; **updates within 7 days** | Paras 56(b), 56(h) [P] |
| No re-collection | Don't ask again for KYC records available on CKYCR, except in 4 listed cases (details changed, record incomplete, document expired, verification needed) | Para 56(j) [P] |
| Review of risk categories | Periodic; penalty orders cite a **six-monthly** review | Penalties [P/S]; paragraph not retrieved |
| **CKYCRR 2.0** | CERSAI onboarded regulated entities and ran mock tests (search / create / download / update via web, API, bulk, SFTP) from 10 Aug 2026; go-live date not stated | CERSAI notice, 4 Aug 2026 [S] |
| Aadhaar offline verification | Amendment Regulations 2025 (9 Dec 2025) recognise three methods: **QR code**, paperless offline e-KYC, and the Aadhaar Verifiable Credential. **The QR route needs no registration as an offline verification-seeking entity (OVSE), but the entity must validate UIDAI's digital signature.** The other two need OVSE registration (Reg 13A) | [S] Vinod Kothari, Dec 2025; UIDAI OVSE FAQ, Jun 2026 [P] |

**Current defences and what they miss**

| Defence | What it does | What it misses |
|---|---|---|
| **RBI's withdrawn-circulars list** | Says what was withdrawn | **No circular numbers, and no pointer to the paragraph that now carries each obligation** [P] |
| **MD web pages** | Current consolidated text with an "updated as on" date [P] | We found no side-by-side view of past versions [U] |
| **Compliance trackers** (TeamLease RegTech claims 3,300+ client entities [S]) | Compliance calendars, task tracking, alerts | No public description found of mapping old citations to new paragraphs, or of answering "as of" questions |
| **KYC vendors** (Signzy, IDfy, HyperVerge; ₹10–50 a check by blog estimates [S]) | Identity verification APIs, built for onboarding | Running a re-KYC campaign (3 + 3 notices with letters, BC declarations, CKYCR clocks, risk reviews) isn't described in any source found |
| **Branch letters and camps** (Jan Dhan camps, Jul–Sep 2025 [S]) | Mass outreach | Evidence is kept by hand. 2026 penalty orders still cite missed risk reviews and late CKYCR uploads |

**The gap.**
- **Re-mapping.** RBI says what was withdrawn, not where each obligation went, and its list can't be matched against the circular numbers in banks' own documents. Because MDs change in place, the question "what applied when this loan was sanctioned?" needs a versioned record.
- **Re-KYC.** The rules now require a **trail for each customer**: 3 + 3 notices with letters, BC declarations, the 10-day and 7-day CKYCR clocks, and periodic risk reviews. **These are exactly the lapses in 2026 penalty orders.** Nothing found runs that trail customer by customer at a cost a small bank can bear.

---

## Step 4: Technology radar (this round)

*Placed here because each idea below picks from it.*

| Technology | Date / source | What it is | Usable in 48h? | Used in |
|---|---|---|---|---|
| **Catala 1.3.0** and **LLM → Catala** | Release dated "01 Oct" (year not printed; presumed 2026) [P]; Law to Code (ICML 2026 AI-for-Law poster: 6,867-statute graph, German corporate-tax sections, 86 test scenarios, no accuracy reported) [P]; NLLP 2025 tax-law-to-Catala benchmark [P] | A programming language for law with date, duration and money types. Compiles to Python, Java, C and OCaml; records traces in Python, Java and OCaml [P]. Apache-2.0 | **Yes, after a 2-hour install spike.** README: "The compiler is yet unstable" [P]. LLMs reach about 88.8% syntactically valid Catala (GPT-4.1, French tax) [S], with no semantic-accuracy figure | 6 |
| **TabICLv2** | arXiv 2602.11139, ICML 2026; `pip install tabicl` 2.2.0 (2 Sep 2026) [P] | Tabular foundation model: classification and regression by in-context learning, with no training run. Code BSD-3; **weights licence not stated** [P] | **Yes.** Fit and predict on 50k rows × 100 features in under 10 s on an H100 (vendor claim); tested up to 100k rows [P] | 7 |
| **Mitra-v2 / TabDPT** | Mitra-v2 arXiv 2609.04540 (Sep 2026), HF `autogluon/mitra-classifier-2`; TabDPT 1.3.1 (Sep 2026) [P] | Alternative tabular foundation models with **Apache-2.0 weights** [P]. Mitra needs a CUDA GPU | Yes: a comparison that is safe to license | 7 |
| **MAPIE 1.6.0** | 19 Oct 2026, BSD-3 [P] | Conformal prediction: turns scores into sets or lists with a stated coverage | Yes | 7, 9 |
| **Graphiti v0.31.1** | 15 Oct 2026, Apache-2.0 [P] | Temporal knowledge graph. Each edge carries `valid_at` / `invalid_at` / `expired_at` / `created_at`; search filters take date comparisons; contradicted facts are invalidated, not deleted. Runs on Neo4j 5.26 or FalkorDB with OpenAI, Anthropic or Gemini; ships an MCP server [P] | Yes. No named "as of" parameter exists; build it from date filters (our inference) | 8 |
| **LegDiff / SLeDoC** | ACL 2026 Student Research Workshop (Jul 2026); github.com/s-nlp/SLeDoC [P] | Span-level semantic comparison of legal paragraphs (Contradiction / Addition / Equivalent; Russian data [S]) | Yes, for the label scheme and method | 8 |
| **GraphCompliance** | arXiv 2510.26309 (Oct 2025, v2 Oct 2026); MIT code [P] | Aligns a policy graph built from regulation text with a context graph. MCC 0.68–0.80 on its own benchmarks | Design reference | 8 |
| **bge-m3 / Qwen3-Embedding** | MIT / Apache-2.0 [S] | Open embedding models for long English legal text (8k tokens for bge-m3) | Yes | 8 |
| **Sarvam Voice Agents, Bulbul V4 Flash, Saaras, sarvam-105b** | Sep–Oct 2026 [P/S] | Voice agents "from ₹3 per minute" [P]. Bulbul V4 Flash text-to-speech in 11 languages, ₹20 per 10k characters standard [S]. Saaras v3 speech-to-text, 22 languages, streaming [P]. sarvam-105b at ₹15 / ₹60 per million input / output tokens [P] | Yes, with API credits (new users get ₹100) | 6, 9 |
| **Aadhaar offline QR verification + pyaadhaar** | Amendment Regulations, 9 Dec 2025 [S]; pyaadhaar, MIT [P] | Decodes the Secure QR. **The library doesn't check UIDAI's signature; we must add that** [P] | Yes for QR. The Verifiable Credential route needs OVSE registration | 9 |
| **CKYCRR 2.0** | CERSAI, Jun–Aug 2026 [S] | Real-time search / download / upload APIs for regulated entities | **Mock only:** access is for regulated entities | 9 |
| **TallyPrime integration** | Tally help pages [P] | XML/JSON over HTTP (default port 9000), plus ODBC | Yes | 6, 7 |

**Considered and rejected:**
- **Chronos-2 / TimesFM 2.5 cash forecasting:** cut from Pay45 to keep it to one model. TimesFM 3.0 weights are non-commercial [P].
- **TabPFN-2.5 / 3.5 and LimiX-2:** non-commercial weights [P]. Fine for internal benchmarking, not for a product pitch.
- **LLM negotiation agents** (Microsoft Magentic Marketplace, Oct 2025): frontier agents showed "severe first-proposal bias" and got worse at scale [P]. Not trusted with a supplier's relationship with its customer.
- **Graph neural networks on GST invoice networks:** no 2024–26 work or accessible data found.
- **Agentic UPI / UPI Reserve Pay:** mandates are capped at ₹10,000 [P, PSP docs], and the focus is consumer-to-merchant.
- **Account Aggregator, ULI, the PSB digital-footprint model:** these serve the lending angle you cut.
- **Aadhaar Verifiable Credentials:** need OVSE registration. **V-CIP deepfake / injection detection:** only vendor or press evidence, no open models.
- **Recursive Language Models:** only needed to read the whole MD corpus in one pass; aligning one MD at a time fits in a context window.
- **LLM → Z3** (used by ClaimProof): **Catala fits better when the output is an amount or a date** rather than a yes/no consistency check.

---

## Steps 2–4: the four ideas

Each idea follows the first report's structure: **persona (Step 2) → what the persona is up against and the UX choice → USP and 2–3 core features with an explicit cut list (Step 3) → novel tech (Step 4) → build plan, demo and risks.** Team shorthand: **FS1/FS2** = full-stack developers, **ML1/ML2** = ML engineers.

---

### Idea 6: Haq ⭐ ("what you're owed") — shows the buyer what paying late costs the buyer, and builds claims that hold up

**PS-1, supplier side.**

**Step 2: Persona.**
- **Mahesh Patil, 46**, owns a CNC job-work shop in **Bhosari MIDC, Pune**.
  - 14 workers; turnover about ₹4.2 cr, which is micro under the April 2025 limits (turnover up to ₹10 cr).
  - Udyam-registered since 2021.
- **His customers:** he machines brackets and housings for two auto-component Tier-1s (₹300–900 cr turnover) and one CPSE. The two Tier-1s bring in 70% of his revenue.
- **His dues:** ₹46 L receivable, of which **₹27 L is past 45 days.** He bridges the gap with a bank overdraft.
- **How he works:** his CA keeps TallyPrime and files GST. Mahesh runs the business on WhatsApp and the phone, in Marathi first, then Hindi and some English.
- **He has never filed on Samadhaan or ODR.**
- ⚠ *Constructed persona. We found no survey of how suppliers chase dues or why they don't file. Validate with 2–3 owners and their CAs.*

**What he's up against → UX choice.**
- He won't open a dashboard, so **he uses WhatsApp:** he forwards a PO or invoice photo and gets a Marathi voice note and a one-screen card back.
- **His CA connects Tally once** (XML over HTTP).
- **What the buyer receives is an email with a PDF to its accounts or tax team.** That's where the 45-day tax and clause 22 pain sits.
- **Mahesh approves every message before it goes out.**

**Step 3: USP.** Every billing app already sends "please pay" [S]. Haq sends the buyer's finance team a **compliance heads-up**: the deduction they will lose, the date their GST credit must be reversed, and the interest building up. Each number is traced to its section, and they are the same numbers the buyer's tax auditor has to report. If that fails, Haq builds the ODR claim, and **tells Mahesh honestly when a claim would be rejected.**

**Core features (build only these):**

1. **Dues clock.**
   - Pull invoices from Tally, or read forwarded PO and invoice photos with a vision-language model into typed JSON (Pydantic).
   - For each invoice, compute:
     - the acceptance date and the s.15 due date;
     - **day 180** for GST;
     - the buyer's financial-year end;
     - the eligibility facts: Udyam date against PO date, category, and activity.
2. **Statute engine and reminders that show the buyer's cost.**
   - **Catala scopes** for s.15 (due date), s.16 (monthly rests; splitting the period when the Bank Rate changes), s.37(2)(g) (tax at risk) and the CGST s.16(2) proviso.
   - **The LLM writes the Catala from the statute text, the compiler checks it, and it must pass 30 hand-computed test cases**, with up to 3 repair loops. A human reviews the four scopes once before the demo.
   - **The escalation ladder:**
     - day 30: a friendly reminder;
     - day 46: a compliance heads-up with a statement of account;
     - day 90: an interest invoice;
     - day 120: notice of intent to file on ODR.
   - Each step reaches Mahesh as a Marathi voice note (Bulbul V4 Flash) explaining what will go out.
3. **ODR pack, with a check for known rejection grounds before filing.**
   - Checks:
     - registered before the contract (*Silpi*);
     - micro or small on the contract date;
     - not trader-only;
     - within limitation.
     - Jurisdiction is flagged as contested.
   - Output: a claim summary, statement of account, **the interest computation with its trace**, and a checklist (invoices, the PO showing the credit period, proof of delivery or acceptance, ledger [S]), ready to paste into odr.msme.gov.in.

**Worked example** *(illustrative, our arithmetic)*:
- **The invoice:** ₹5,90,000 (₹5,00,000 + 18% GST), dated and accepted 1 Jul 2026, on a 45-day PO term. Due 15 Aug.
- **Interest by 20 Oct ≈ ₹17,600:** 16.5% a year until 6 Oct, then 17.25%, monthly rests. The day-count convention and how a mid-delay rate change is handled are modelling choices; show them as explicit settings.
- **ITC: ₹90,000** must be reversed on **28 Dec 2026** if still unpaid.
- **Tax: ≈ ₹1.26 L** extra if still unpaid on 31 Mar 2027 (25.17% of ₹5 L).

```
# Rule sketch, not real Catala syntax: one scope per section; each output keeps its trace
appointed_day   = acceptance_date + (min(agreed_days, 45) if written_agreement else 15)   # MSMED s.15
interest        = compound_monthly(amount, 3 * bank_rate(t), from=appointed_day + 1)      # s.16, split on rate changes
itc_reversal_on = invoice_date + 180 days                                                 # CGST s.16(2) 2nd proviso
tax_at_risk     = amount_ex_gst * buyer_tax_rate   if unpaid at buyer_fy_end              # IT Act 2025 s.37(2)(g)
eligible_msmed  = udyam_date <= contract_date and category in {micro, small} and not trader_only   # Silpi (SC 2021)
```

**Cut list:**
- TReDS discounting suggestions.
- Scores of buyers' payment records from Samadhaan's public buyer-level reports.
- A negotiation agent.
- Collective claims by several suppliers against one buyer.
- Voice calls to the buyer.

**Step 4: Why it's novel.**
- **Law-as-code written by an LLM and gated by tests.** The only 2025–26 work found is the Law to Code pipeline (ICML 2026) and the NLLP 2025 benchmark, both on German or French tax law. **Our scan found no Catala or rules-as-code encoding of the MSMED Act or the 45-day rule.**
- **Catala's trace recording** (1.3.0, Python backend) means "why ₹17,600?" is answered by an execution trace through s.15 and s.16, not by an LLM's after-the-fact explanation.
- **The product insight is the incentive reframe.** The technology is what makes the buyer-facing numbers trustworthy enough to send.
- Pitch line: *"A chatbot can get compound interest wrong. Haq's numbers compile, and they've passed 30 tests."*

**48h plan:**
- **H0–2:** go/no-go spike. Install Catala (opam or Docker), compile a 10-line scope to Python, and run it.
- **H2–8:**
  - ML1 hand-computes 30 test cases in a spreadsheet: 15-day vs 45-day terms, a rate change mid-delay, year-end crossings, day 180.
  - FS1 sets up a WhatsApp Cloud API test number and a sample Tally company.
  - FS2 builds 20 synthetic cases with seeded rejection grounds: registered after the PO, trader-only, older than 3 years, no written agreement.
- **H8–20:**
  - ML2 builds the LLM → Catala loop (statute text plus Catala docs → compile → test → repair) and logs the pass rate.
  - ML1 builds photo extraction into typed JSON.
- **H20–32:** reminder ladder templates, the rejection pre-check, the claim-pack PDF, and Marathi voice notes.
- **H32–42:** the full WhatsApp flow, and a trace viewer ("why this number").
- **H42–48:** rehearse.

**Demo (3 min):**
1. "Mahesh" forwards a PO photo and an invoice PDF.
2. About 30 seconds later, he gets a Marathi voice note and a card: *"Buyer A: ₹5.9 L, 66 days past the agreed date. Interest so far ≈ ₹17.6k at 3× the Bank Rate. Unpaid on 31 Mar, Buyer A loses a ₹5 L deduction (≈ ₹1.26 L tax). ITC reversal of ₹90k is due on 28 Dec."*
3. Tap **"Send heads-up"** and show the polite email to Buyer A's finance head.
4. **A second invoice predates his Udyam registration.** Haq says the MSMED claim would likely be rejected (*Silpi*, SC 2021), **but the GST 180-day lever still applies.** The tool knows when it can't help.
5. Tap **"ODR pack"** on a third invoice and show the PDF. Click ₹17,600 to show the Catala trace.

**Metrics:**
- 30 of 30 hand-computed cases match.
- **LLM → Catala pass rate**, stated honestly (for example, rules correct within 3 repairs).
- 100% of the seeded rejection grounds caught across 20 cases.
- Under 1 minute from forwarding to claim pack.

**Risks → mitigations:**
- **Catala is "yet unstable"** → the H0–2 spike. Fallback: the same rules in Python behind the same tests; the novelty claim drops to "test-gated rules-as-code".
- **Contested law** (when the clock starts, rate changes mid-delay, jurisdiction) → show each as a labelled assumption with a toggle, plus a "contested" badge in the claim pack.
- **Seen as legal advice or harassment** → Haq computes and drafts; the owner approves and sends. No success fee. It contacts only the buyer's listed accounts contact.
- **Buyers drop MSE suppliers** (the SME Chamber's concern [S]) → frame it as a heads-up, not a threat. The GST lever doesn't depend on MSE status.
- **The Amendment Act's status is [S]** → verify the Gazette and S.O. 5575(E) before quoting any 90-day clocks.

---

### Idea 7: Pay45 — warns a buyer's finance team weeks before an MSE invoice crosses the 45-day line

**PS-1, buyer side.**

**Step 2: Persona.**
- **Kavita Rao, 41**, head of finance operations (accounts payable) at a **₹650 cr auto-component maker in Chakan, Pune**.
  - Three plants, about 380 micro and small suppliers, about 2,500 supplier invoices a month, and a 5-person AP team.
- **Tools:** the ERP (SAP or TallyPrime; validate which), Excel trackers and email. The company is on TReDS under the ₹250 cr mandate [S].
- **What she owns:** the two half-yearly MSME Form I filings and the clause 22 schedule the tax auditor asks for.
- **What it cost last year:** ₹6 cr of MSE payables were past their limit at year-end, roughly **₹1.5 cr of extra tax that year** *(illustrative, our arithmetic)*.
- ⚠ *We found no survey of this role. One data point: 44% of buyers named credit terms longer than 45 days as the most common reason for delay (GAME–D&B, citing MCA data [S]). Validate with 2 AP heads.*

**What she's up against → UX choice.**
- She hears about a breach only when the invoice reaches her approval queue, or at the audit.
- **The delay happens upstream:** the goods receipt (GRN) isn't posted, a quality check is on hold, the price doesn't match the PO, or an approver is on leave.
- **So: a weekly web list beside the ERP, plus automatic nudges to whoever is holding each invoice.** Suppliers do nothing new.

**Step 3: USP.** Today 45-day compliance is reported after the fact, by the auditor. **Pay45 turns it into a weekly to-do list that comes with a stated coverage guarantee.**

**Core features:**

1. **The MSE register as it stood on each invoice date.**
   - Read Udyam certificates (OCR; each certificate's QR links to a portal page [P]) and the vendor master.
   - Record category and activity with dates. Apply the April 2025 limits and the rule for moving between categories [S].
   - Exclude trader-only suppliers and supplies made before registration [S].
2. **Breach forecast with a guarantee.**
   - For every open invoice: the **probability it gets paid after the statutory limit**, from **TabICLv2** conditioned on the last 12–24 months of closed invoices.
   - Features: days since delivery, GRN posted, quality-check status, PO price mismatch, plant, approver backlog, month-end, and the supplier's dispute history.
   - **There's no training job: the history *is* the context.**
   - **MAPIE conformal calibration** on recent months gives the list a stated coverage: *"this list contains at least 90% of next month's breaches."*
   - Baselines: LightGBM, and the rule "open for more than 30 days".
3. **Weekly action run and filings.**
   - The list is ranked by **cost of breach:** 25.17% tax on the amount, the s.16 interest (not deductible), and the ITC due for reversal at day 180.
   - One click to **nudge whoever holds the invoice** (the quality-check head or the approver), **export a TReDS upload batch**, or add it to the next payment run.
   - **MSME Form I and the clause 22 schedule** are generated from the same data.

**Cut list:**
- Cash forecasting with Chronos-2, and optimising the payment run under a cash cap.
- A supplier self-service portal.
- Matching against e-invoices and the GST Invoice Management System (IMS).
- Dynamic early-payment discounts.

**Step 4: Why it's novel.**
- **Tabular foundation models** (TabICLv2, ICML 2026; Mitra-v2, Sep 2026) predict from a few thousand labelled rows **with no training pipeline**. That suits a mid-size company with no data-science team.
  - TabICLv2 reports beating tuned XGBoost, CatBoost and LightGBM on about 80% of TabArena datasets (self-reported [P]).
- **Our scan found no 2024–26 paper testing tabular foundation models on invoice payment delays.** The prior work we found used gradient boosting (2019–2023) [S].
- **Conformal coverage makes the list auditable.** What goes to the CFO is a bound, not a score.
- **Licence choice:** TabICLv2's weights licence isn't stated, and TabPFN-2.5 is non-commercial [P]. **A production pitch should run on Mitra-v2 or TabDPT (Apache-2.0).**

**48h plan:**
- **H0–6:**
  - FS2 writes a synthetic AP-ledger generator: 24 months, 380 suppliers, about 60k invoices, with planted delay mechanisms (quality holds, approver leave, month-end, price mismatch, one slow plant).
  - ML1 builds the MSE register with Udyam dates and categories, plus 3 sample certificates for OCR.
- **H6–18:**
  - ML1: TabICLv2, compared with TabDPT and Mitra-v2 (GPU) and a LightGBM baseline, on a time-based split.
  - ML2: MAPIE calibration and the precision/recall curve at a fixed weekly review budget.
- **H18–30:** the cost-of-breach engine (**shared with Haq's statute engine**), the weekly list, and the Form I / clause 22 generators.
- **H30–42:** FS1 builds the web list, CSV/Tally import, nudge emails and the TReDS batch export.
- **H42–48:** rehearse.

**Demo:**
1. **It's 1 Oct.** Pay45 lists the open invoices likely to cross the limit in the next 21 days. Most of them sit on a quality hold at Plant 2 (synthetic data).
2. Nudge the Plant 2 quality-check head, and push 8 invoices into a TReDS batch.
3. **Replay to 31 Mar:** show the tax disallowance with and without acting on the lists.
4. Show the calibration slide: breaches caught at a fixed review budget, Pay45 against the "older than 30 days" rule.

**Metrics:**
- Breach recall at a fixed weekly review budget.
- Lead time in days before the limit.
- Rupees of tax disallowance avoided in the backtest.

**Risks → mitigations:**
- **Synthetic data only** → before the hackathon, get one anonymised real AP ledger through a CA or a friendly company.
- **Does payment through TReDS count as payment for the 45-day tax rule?** No CBDT or ICAI view was found → show TReDS as an option with a caveat.
- **Weak evidence for the persona** → 2 AP-head interviews.
- **Overlaps with ERP vendors** → position it as an add-on reading an export, not a replacement.

---

### Idea 8: Naksha ("map") — maps every withdrawn circular a bank cites to where its obligation lives now

**PS-2, regulatory change.**

**Step 2: Persona.**
- **Sunil Deshpande, 52**, compliance officer at a **Tier-2 urban co-operative bank in Kolhapur**: about ₹600 cr in deposits, 18 branches, one assistant.
  - **One of 535 Tier-2 UCBs** [P].
- **What he maintains:**
  - about 40 board-approved policies: KYC/AML, lending, investments, asset-liability management, fraud, IT, outsourcing;
  - the internal-audit and concurrent-audit checklists;
  - the tracker of compliance with RBI inspection findings.
- **Tools:** Word, Excel and email. He reads notifications on rbi.org.in.
- **Since 28 Nov 2025 most citations in those documents point to withdrawn circulars.** The next RBI inspection will look back over periods governed by both the old text and the new (savings clause [P]).
- ⚠ *His workload is inferred. No article measuring the re-mapping effort was found. Validate with 2 UCB compliance officers.*

**What he's up against → UX choice.**
- **He needs a document he can put before the board, not a chat.**
- **So: a desktop web app.** He uploads a policy (DOCX or PDF) and gets it back annotated. A date picker sets "as of".

**Step 3: USP.** RBI says *what* was withdrawn. **Naksha says *where* each obligation went, what changed in it, and which version applied on any date.**

**Core features:**

1. **Citation sweep.**
   - Regex for the formats our agents saw in real RBI text [P]:
     - `DBOD.BP.BC.92/C.469-76`
     - `DBR.AML.BC.No.81/14.01.001/2015-16`
     - `DNBR(PD).CC.No.034/03.10.42/2014-15`
     - `RBI/2025-26/100`
     - `DOR`/`DoR` (both casings occur)
   - Plus an LLM pass for obligations stated without any citation. Everything is split into single obligations.
2. **Old → new alignment with labels.**
   - **Candidate paragraphs** come from embeddings (bge-m3) over the MDs that apply to UCBs.
   - **An LLM judge assigns LegDiff-style labels**: **Equivalent / Changed / Added / Dropped**, with both texts side by side.
   - **Low-confidence items go to a review queue.**
   - **Joining citations to the withdrawn list:** that list has no number column [P], so citations are matched on date plus subject. Where they exist, the repeal appendices of older MDs (circular number plus date, e.g. 255 rows in the 2016 KYC MD [P]) give an exact join.
3. **As-of graph and impact alerts.**
   - MD paragraphs, old circulars and the bank's policy clauses go into **Graphiti**, with `valid_at` / `invalid_at` on each edge.
   - **"What applied on 15 Mar 2026?" becomes a date-filtered search.**
   - When a new RBI notification arrives (RBI's RSS feed [P]), the affected edges are invalidated, and **Naksha lists the policy clauses that cite the changed paragraph.**

**Cut list:**
- Redrafting policies automatically.
- Mapping regulatory returns (CIMS/XBRL).
- Tracking inspection findings and Risk Mitigation Plans.
- Entity types beyond UCBs.
- Reading the whole MD corpus with Recursive Language Models.

**Step 4: Why it's novel.**
- **A bi-temporal knowledge graph applied to regulation versions.** Graphiti keeps *when a rule was in force* separate from *when we learned of it*, and invalidates contradicted facts instead of deleting them [P].
  - **Our scan found no paper applying a temporal knowledge graph to versions of a regulation.** The closest is an LRMoo graph of Brazil's constitution, with no metrics and no code [P].
- **LegDiff** (ACL 2026) supplies the span-level labels and a public benchmark to sanity-check our judge.
- **GraphCompliance** (Oct 2025) supports the design of aligning a policy graph with a regulation graph.
- **The perfect demo case is in RBI's own text:** the 3 + 3 notice rule was **published on 12 Jun 2025 but in force only from 1 Jan 2026** [P]. That is a single fact with two different dates, which is exactly what a bi-temporal model is for.
- **Honest note:** a bitemporal SQL table also answers "as of" queries. Graphiti adds the entity links (obligation → policy clause → MD paragraph) and handles contradictions. If its LLM extraction is noisy, create nodes deterministically and use Graphiti for the edges and search.

**48h plan:**
- **H0–4:** download a small corpus **by hand, with no bulk scraping** (rbi.org.in robots.txt returned HTTP 418, and PDFs sit behind a CAPTCHA [P]). Use the HTML pages of:
  - the list of withdrawn circulars;
  - 6–8 MDs that apply to UCBs;
  - the 2016 KYC MD with its repeal appendix;
  - the 12 Jun 2025 amendment.
  - Then write 3 synthetic bank policies with old citations, or use public UCB KYC policies [U].
- **H4–16:** citation regex and LLM extraction; embedding candidates; the LLM judge with LegDiff labels; the review queue.
- **H16–30:** Graphiti on Neo4j or FalkorDB with deterministic paragraph nodes, edges with validity dates, the as-of endpoint, and a simulated RSS notification.
- **H30–42:** FS1 builds the UI: the policy with inline chips (Equivalent / Changed / Dropped), a side-by-side panel, and an as-of slider.
- **H42–48:** label 50 citations by hand for evaluation, then rehearse.

**Demo:**
1. Upload a 2019-style KYC policy with 14 old citations. About 40 seconds later, each one carries a chip.
2. **One is "Changed":** the re-KYC section has no notice rule.
3. **Slide the date:** the 3 + 3 notice obligation appears on 1 Jan 2026, though it was published on 12 Jun 2025.
4. **Simulate a new RBI amendment.** An alert reads: *"Affects KYC policy §7.2 and audit checklist item 31."*

**Metrics:**
- Precision and recall of the mapping on 50 hand-labelled citations.
- Correct answers on 20 date-specific questions.
- Minutes per policy against doing it by hand.

**Risks → mitigations:**
- **Access to RBI's site** → a small corpus downloaded by hand. For production, use the HTML pages and RSS, and ask RBI for bulk access.
- **The list of withdrawn circulars lacks numbers** → match on date and subject, and use repeal appendices where they exist. Show the confidence of each match.
- **Wrong mappings** → human review below a confidence threshold, with both texts always visible.
- **Unproven pain** → interviews. Also check whether the reported 2026 supervisory consolidation (628 → 64) happened [U]; if it did, re-mapping is a recurring job, which strengthens the pitch.

---

### Idea 9: Nootan ("renewal") — re-KYC run customer by customer, with the trail inspectors check

**PS-2, re-KYC / CKYCR execution.**

**Step 2: Persona.**
- **Rakesh Bishnoi, 38**, KYC and compliance officer at a **district central co-operative bank in Sri Ganganagar, Rajasthan**.
  - About 1.8 lakh accounts across 30 branches, mostly savings and crop-loan (Kisan Credit Card) accounts of farmers who receive direct benefit transfers.
  - Many customers use basic phones and speak Hindi or Rajasthani.
  - Branches have 3–5 staff each; banking correspondents (bank mitras) serve the villages.
- **How re-KYC runs today:** from a core-banking export in Excel, with letters typed at the branches. **He can't prove which customer got which notice.**
- **A bank in the same district** (Ganganagar Kendriya Sahakari Bank) was penalised ₹3 L in Feb 2026 for missed six-monthly risk reviews and incomplete periodic KYC updation [S].
- ⚠ *Constructed persona; account and staff numbers are illustrative.*

**What he's up against → UX choice.**
- **Rakesh:** a web dashboard at head office.
- **Customers:** a **phone call in Hindi** (works on any phone), an SMS and a letter.
- **Banking correspondents:** a small Android web app to scan an Aadhaar QR.
- **Nobody installs anything except the banking correspondent.**

**Step 3: USP.** Re-KYC "campaigns" treat every due customer the same way. **Nootan routes each customer to the cheapest lawful path and produces the evidence trail as a by-product**: the notices, the declaration and the CKYCR timestamps that 2026 penalty orders show inspectors check.

**Core features:**

1. **From the due list to a lawful path.**
   - From the core-banking export, compute:
     - due dates by risk category (2 / 8 / 10 years);
     - **the notice calendar** (3 before the due date and 3 after, each set including a letter);
     - the six-monthly risk-review clock.
   - Then route each customer:
     - **(a) CKYCR record current** → no re-collection (para 56(j)); just a declaration.
     - **(b) No change** → self-declaration, confirmed by OTP from the registered mobile [U, see risks], or through a banking correspondent with biometric e-KYC [P].
     - **(c) Address change** → a banking correspondent scans the Aadhaar QR.
     - **(d) Anything else** → the branch.
2. **Notices that count, in Hindi.**
   - **Letters:** Hindi and English PDFs carrying the how / where / consequence content the amendment requires [P].
   - **SMS:** text written for DLT-registered templates.
   - **Outbound voice calls** through **Sarvam Voice Agents (Bulbul V4 Flash voice)**: *"Aapka KYC update baaki hai. Agar aapki jaankari mein koi badlaav nahi hai, to SMS mein aaye OTP se pushti kijiye."*
   - **The LLM runs inside a typed state machine.** It can explain, answer FAQs, trigger an OTP declaration or book a correspondent's visit. **It can't record a declaration itself.**
   - **A conformal intent classifier** (MAPIE) hands off to staff when it isn't sure.
   - **Every attempt is logged** with its channel and timestamp.
3. **Offline Aadhaar QR and CKYCR clocks.**
   - **Scanning:** the banking correspondent scans the Secure QR. The app decodes it (pyaadhaar) and **validates UIDAI's signature**, which is required when using the QR route without OVSE registration [S].
   - **Data:** it pre-fills the new address and **stores only a masked Aadhaar number.**
   - **CKYCR:** it queues the update against a **mock CKYCRR 2.0 API** on the 7-day clock.
   - **Dashboard:** the 10-day and 7-day upload clocks, the six-monthly reviews, and a **one-click inspection pack per account.**

**Cost check** *(our arithmetic)*: voice agents cost from ₹3 a minute [P]. Three 2-minute calls per customer come to about **₹18**, against a branch visit or an unanswered letter.

**Cut list:**
- Video KYC (V-CIP).
- Aadhaar Verifiable Credentials (needs OVSE registration).
- Deepfake and camera-injection detection (no open models found).
- A WhatsApp channel.
- Reactivating dormant accounts, and unclaimed deposits.
- An India Post API: it needs a contract worth at least ₹10k a month [S], so letters are printed at the branch.

**Step 4: Why it's novel.**
- **It is built for the rules as they stand in Oct 2026:**
  - 3 + 3 notices with letters (in force 1 Jan 2026);
  - declarations through banking correspondents;
  - the Aadhaar offline-verification amendment (Dec 2025);
  - CKYCRR 2.0 (onboarding from Aug 2026).
  - No vendor description found covers this combination.
- **Indic voice agents only became cheap and fast in Sep–Oct 2026:** Bulbul V4 Flash, Sarvam Voice Agents from ₹3 a minute, and sarvam-105b.
- **The guardrail design:** the LLM proposes and a typed state machine decides; the conformal hand-off rate is reported.
- **Honest scoring:** the novelty rests on new launches, not research papers, so it scores 3/5 below.

**48h plan:**
- **H0–6:**
  - FS2 builds a synthetic core-banking export: 20k accounts with risk categories, last-KYC dates, mobiles and CKYC numbers.
  - ML1 writes the rules engine: due dates, the notice calendar, risk reviews, the CKYCR clocks.
  - FS1 builds the mock CKYCRR 2.0 API (search / download / update).
- **H6–20:**
  - ML2: the Sarvam voice agent in Hindi, with the state machine and OTP declaration.
  - ML1: the intent classifier plus MAPIE calibration on 100 recorded Hindi replies.
- **H20–32:** the letter and SMS generators and the evidence log; the correspondents' web app with QR decoding and signature check.
- **H32–42:** the dashboard and the inspection-pack export.
- **H42–48:** rehearse.

**Demo:**
1. **Dashboard:** 2,140 accounts due in November and how they split across the four paths (synthetic data).
2. **A live voice call to a judge's phone** in Hindi. The judge says *"kuch nahi badla"*, receives an OTP SMS, and the declaration is logged.
3. **A correspondent scans a consenting teammate's Aadhaar QR** (shown masked). The signature verifies, the address is pre-filled, and the CKYCR update is queued with its 7-day clock.
4. **Export the inspection pack** for one account: 3 notices with dates and channels, one of them a letter; the declaration; the CKYCR upload date.

**Metrics:**
- The share of due accounts closed without a branch visit.
- **Notice completeness: 100%** (every due account has 3 + 3 notices, including letters, logged).
- **Zero CKYCR clock breaches.**
- Intent accuracy and hand-off rate on 100 recorded Hindi replies.

**Risks → mitigations:**
- **Is an OTP from the registered mobile a valid "no change" declaration?**
  - Our reading of the 2016 MD's para 38(a)(i) is that it allows email, registered mobile, ATM, digital channels and letters. **Our agents did not verify this [U].**
  - The 2025 amendment adds the banking-correspondent route [P].
  - Verify before the demo; if in doubt, send everyone to a correspondent.
- **CKYCR and Aadhaar access is only for regulated entities** → mock both in the demo. A real pilot runs through a partner bank, as its vendor.
- **Handling Aadhaar** → never store the full number, always verify the signature, show a consent screen, follow the DPDP Act.
- **Calling farmers** → calling-hour windows and consent; DLT templates for SMS.
- **Dialects** → Hindi only. Rajasthani support isn't confirmed.

---

## Comparison and recommendation

Scores out of 5. For **Risk**, 5 = lowest risk.

| | Pain | Evidence | Persona sharpness | Novelty | Buildable in 48h | Demo impact | Risk | **Total** |
|---|---|---|---|---|---|---|---|---|
| **6 Haq** | 5 | 4 | 4 | 4 | 4 | 5 | 3 | **29** |
| **9 Nootan** | 4 | 4 | 4 | 3 | 4 | 4 | 3 | **26** |
| **8 Naksha** | 3 | 3 | 4 | 5 | 3 | 4 | 3 | **25** |
| **7 Pay45** | 4 | 3 | 3 | 4 | 4 | 3 | 3 | **24** |

**Which to build:**
- **Haq.** It has the highest pain score backed by primary numbers (the Samadhaan funnel), a sympathetic persona, a live WhatsApp moment, and novelty judges can check: the rules compile and pass tests.
- **Nootan,** if the hackathon has a bank or regtech sponsor track. It rests on primary RBI text and real 2026 penalties, and it's the most buildable PS-2 idea.
- **Naksha,** if judges weight novelty most. Book two UCB interviews first, because its pain is inferred.
- **Pay45** works best as the "other side" slide in Haq's pitch. The two ideas share the statute engine, so a team that builds Haq can mention Pay45 as the B2B revenue path.

---

## Validation checklist before the hackathon

1. **Primary-source checks:**
   - The Gazette text of the MSMED (Amendment) Act 2026 and S.O. 5575(E) (Haq).
   - The text of s.37(2)(g) of the Income-tax Act 2025, and the CGST s.16(2) proviso (Haq, Pay45).
   - Where the 45-day clock starts under MSMED s.2 and s.15 (Haq).
   - Para 38(a)(i) declaration channels, and the matching paragraphs in the 2025 KYC Directions for co-op banks (Nootan).
   - Whether the new MDs carry repeal appendices (Naksha).
   - The go-live date of CKYCRR 2.0 (Nootan).
2. **Access spikes:**
   - Catala install and compile to Python (Haq, H0–2).
   - `pip install tabicl tabdpt` plus a GPU for Mitra-v2 (Pay45).
   - Graphiti with Neo4j or FalkorDB in Docker (Naksha).
   - Sarvam API credits and Voice Agents (Haq, Nootan).
   - A WhatsApp Cloud API test number (Haq).
3. **Interviews:**
   - 2 micro-unit owners and their CA (Haq).
   - 2 AP heads (Pay45).
   - 2 UCB compliance officers (Naksha).
   - 1 KYC officer at a co-op bank (Nootan).
4. **Data:**
   - One anonymised AP ledger (Pay45).
   - 2–3 real bank KYC policies (Naksha).
   - A consenting teammate's Aadhaar QR (Nootan).
5. **Legal framing:**
   - **Haq:** a computation and drafting tool; the owner files; no success fee.
   - **Nootan:** Aadhaar Act storage limits; DPDP consent.

## Evidence caveats

- **Master Direction count:** 238 vs 244 in the same RBI press release (244 includes 7 new Digital Banking Channels MDs). **Circulars withdrawn:** 9,445 [P] vs 5,673 / 9,446 [S].
- **Samadhaan money:** ₹55,244 cr counts applications; the homepage's ₹31,722 cr counts cases. They don't reconcile, so quote one with its basis.
- **"40% of dues owed by PSUs / government"** is unsupported (see 1.2).
- **Status of the MSMED Amendment Act 2026:** passed, assented and in force by secondary sources, but CRISIL (17 Aug, primary) still called it a bill.
- **Bank Rate vs repo:** the Bank Rate is 5.75% and the repo rate 5.50% (7 Oct 2026 [P]). Sec 16 uses the **Bank Rate**.
- **TReDS FY26 total** (₹3.47 lakh cr) comes from one secondary source. RXIL's FY26 ₹1.21 lakh cr is [U].
- **Sarvam:** the changelog lists Saaras v4 GA on 2 Sep 2026, but a second agent couldn't find it. Bulbul V4 pricing is [S].
- **WhatsApp utility message price:** ₹0.115–0.145 [S]. Meta's INR rate card wasn't read.
- **Form 3CD clause 22 vs 26**, and whether Form 26 replaces it from FY 2026-27, are unconfirmed.
- **TabICLv2's weights licence** isn't stated. **Catala 1.3.0's release year** isn't printed.
- **MSME Form I penalty amounts** conflict between sources.
- **FY26 RBI penalty totals** are unverified; the FY25 figures are [S].
- The **TeamLease figures** (621 compliances, 94%) are vendor research from 2023–24.
- **Personas are constructed from the evidence**; none comes from a survey of that exact role.

## Key sources

**PS-1: MSME late payments**
- CRISIL, Samadhaan figures (17 Aug 2026): https://intelligence.crisil.com/en/homepage/newsroom/press-releases/2026/08/executed-well-msme-bill-can-be-an-ibc-moment-for-delayed-payments.html
- MSME Samadhaan portal (funnel): https://samadhaan.msme.gov.in/
- GAME–Dun & Bradstreet, Delayed Payments (May 2022): https://www.dnb.co.in/file/reports/Delayed-Payments-Report.pdf
- GAME–FISME report 3.0 (₹7.34 lakh cr): https://fisme.org.in/study/delayed-payments-to-msmes-decline-from-rs-10-lakh-cr-to-rs-7-lakh-cr-but-challenges-persist-game-fisme-report/
- PRS summary, MSMED (Amendment) Bill 2026: https://prsindia.org/billtrack/prs-products/prs-bill-summary-1785320093
- Commencement, S.O. 5575(E) (secondary): https://teamleaseregtech.com/updates/article/60351/ministry-of-msme-commencement-of-provisions-of-the-msmed-amendment-act/
- RBI policy rates, 7 Oct 2026 (Bank Rate 5.75%): https://www.rbi.org.in/scripts/BS_PressReleaseDisplay.aspx?prid=63742
- 43B(h) → s.37(2)(g), Rajya Sabha reply (21 Jul 2026): https://taxguru.in/income-tax/finance-ministry-clarifies-section-43bh-45-day-msme-payment-rule.html
- GST 180-day ITC reversal (ICAI CA Journal, Aug 2026): https://cajournal.icai.org/article-details/itc-reversal-and-re-availment-under-gst-gstr-3b-guide
- Silpi Industries v. KSRTC (SC, 2021): https://www.supremecourtcases.com/silpi-industries-etc-v-kerala-state-road-transport-corporation-and-another/amp/
- Sec 15 buyer liability FAQ: https://taxmann.com/post/blog/faqs-liability-of-buyer-u-s-15-of-msmed-act-to-make-timely-payments-to-mse-suppliers
- Revised MSME classification (Apr 2025): https://www.taxmann.com/post/blog/revised-msme-classification
- Form 3CD clause 22: https://www.taxmann.com/post/blog/opinion-form-3cd-clause-22-msme-payment-reporting-post-utility-release/
- TReDS:
  - SIDBI page: https://www.sidbi.in/en/treds
  - RXIL FY25: https://www.outlookbusiness.com/industry/rxil-msme-invoice-financing-2lakh-crore-fy25
  - FY26 total and CPSE mandate: https://www.angelone.in/news/market-updates/government-mandates-treds-for-msme-invoice-settlement-by-cpses
  - ₹250 cr mandate: https://singhania.in/blog/mandatory-treds-registration-for-companies-above-250-crore-turnover
- Udyam 8.84 crore (Jul 2026): https://knnindia.co.in/news/newsdetails/msme/over-884-crore-msmes-registered-on-udyam-platforms-mos-karandlaje
- SME Chamber and FISME on 43B(h): https://ts.yourstory.com/smbstory/continue-45-day-msme-payment-rule-industry-body-fm-nirmala-sitharaman
- Tally integrations: https://help.tallysolutions.com/getting-started-with-tally-integrations/

**PS-2: NBFC / co-op bank compliance**
- RBI consolidation press release (28 Nov 2025): https://rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=61705
- Withdrawal circular RBI/2025-26/100: https://www.rbi.org.in/Scripts/BS_CircularIndexDisplay.aspx?Id=13170
- List of withdrawn circulars: https://rbi.org.in/Scripts/NotificationUserWithdrawnCircular.aspx
- KYC (Amendment) Directions, 12 Jun 2025: https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=12866
- KYC Master Direction 2016 (paras 38, 56; repeal appendix): https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=11566
- UCB tier framework (4 Dec 2025): https://rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=13203
- UCB CRR/SLR Directions (updated in place): https://rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=13031
- RBI Trend and Progress, co-operative banks (UCB tiers): https://rbi.org.in/Scripts/PublicationsView.aspx?id=23640
- FY25 penalties: https://www.business-standard.com/amp/finance/news/rbi-imposed-penalties-on-353-banks-other-regulated-entities-in-fy25-125060100307_1.html
- Penalties:
  - Shree Laxmi Co-op Bank: https://rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=62815
  - Co-op bank roundup (14 Jul 2026): https://www.moneylife.in/article/5-cooperative-banks-penalised-4480-lakh-for-kyc-and-governance-failures/81054.html
  - NBFC roundup (21 Aug 2026): https://fintechbiznews.com/govtregulators/penalty-imposed-on-5-nbfcs
- CCO circular for NBFCs (2022): https://www.rbi.org.in/Scripts/BS_CircularIndexDisplay.aspx?Id=12290
- TeamLease RegTech NBFC figures: https://startup.outlookindia.com/sector/fintech/nbfcs-have-performed-well-in-providing-loans-to-unbank-and-underbanked-sections-teamlease-regtech-report-news-7217
- CKYCRR 2.0 onboarding (Aug 2026): https://teamleaseregtech.com/updates/article/58460/ckyc-issued-res-onboarding-and-performing-mock-run-before-final-go-live-of-ckycrr-2-0/
- Aadhaar offline verification:
  - Amendment explainer: https://vinodkothari.com/2025/12/a-new-way-to-verify-aadhaar-offline-introduction-of-face-matching/
  - UIDAI OVSE FAQ: https://www.uidai.gov.in/ovse-faq
- RBI RSS feeds: https://www.rbi.org.in/Scripts/Rss.aspx

**Technology**
- Catala: https://github.com/CatalaLang/catala · releases: https://github.com/CatalaLang/catala/releases
- Law to Code (ICML 2026): https://icml.cc/virtual/2026/80583 · NLLP 2025 benchmark: https://aclanthology.org/2025.nllp-1.4
- TabICLv2: https://arxiv.org/abs/2602.11139 · https://github.com/soda-inria/tabicl · https://pypi.org/project/tabicl/
- Mitra-v2: https://arxiv.org/abs/2609.04540 · https://huggingface.co/autogluon/mitra-classifier-2 · TabDPT: https://pypi.org/project/tabdpt/
- MAPIE: https://pypi.org/project/MAPIE/
- Graphiti: https://github.com/getzep/graphiti
- LegDiff: https://aclanthology.org/2026.acl-srw.86/ · https://github.com/s-nlp/SLeDoC
- GraphCompliance: https://arxiv.org/abs/2510.26309
- Sarvam: https://docs.sarvam.ai/api/pricing · https://docs.sarvam.ai/changelog
- pyaadhaar: https://github.com/tanmoysrt/pyaadhaar
- Magentic Marketplace (rejected): https://arxiv.org/abs/2510.25779
- WhatsApp pricing: https://developers.facebook.com/docs/whatsapp/pricing
