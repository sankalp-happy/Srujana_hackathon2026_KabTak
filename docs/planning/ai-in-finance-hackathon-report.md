# AI in Finance Hackathon: Problem Research and 5 Ideas (India)

*Prepared 19 Oct 2026. Research: 20 Claude Haiku agents, which only collected evidence. Problem selection, personas, feature cuts and technology choices: Claude Opus. Constraints: India market, 36–48h build, mixed full-stack + ML team.*

**Evidence tags:** **[P]** = an agent read the primary source · **[S]** = secondary press or a search snippet · **[U]** = unverified. Check **[S]** and **[U]** figures before they go on a slide.

---

## TL;DR

**Three problems chosen** (out of 9 areas screened):
- **A.** Scams targeting elderly Indians where the victim sends the money themselves ("digital arrest").
- **B.** Health-insurance claims that are denied or partly paid with no reason the family can check.
- **C.** Retail F&O traders who lose money every year because they follow Telegram tips.

| # | Idea | Problem | Persona | Novel tech it uses | One-line USP |
|---|---|---|---|---|---|
| 1 | **Ruko** | A | 74-yr-old retired officer, Indore | TypeSafe **Jev** (Sep 2026), conformal thresholds, Sarvam **Bulbul v4 Flash** | Detects a digital arrest from phone behaviour (a long video call while banking apps are used), without ever hearing the call |
| 2 | **Saath** | A | Adult child guarding parents' savings remotely | **AP2 mandates** (verifiable credentials) extended to require a co-signer, plus passkeys | The parent sets "my son must co-sign big transfers" while calm, and the bank enforces it on every channel, including the branch |
| 3 | **ClaimProof** ⭐ | B | Daughter of a hospitalised parent, Nagpur | LLM turns policy clauses into logic and the **Z3 solver** checks them; open OCR models (VLMs) read the documents | Replaces "the AI thinks your denial is wrong" with a checkable proof that the denial breaks IRDAI rules |
| 4 | **DischargeDesk** | B | Hospital insurance-desk executive | **ACE**, evolving playbooks (ICLR 2026) | Learns each insurer's habitual queries and enforces IRDAI's 1-hour and 3-hour clocks |
| 5 | **Asli Odds** | C | 24-yr-old first-year F&O trader, Jaipur | **Kronos** financial price-chart model (AAAI 2026), Jev | Forward any Telegram tip and see how it plays out across 1,000 simulated markets, plus that tip channel's real track record |

**Recommendation:** build **ClaimProof**. No paper we found turns insurance policy wording into logic that decides claims. Its rules come straight from IRDAI's own circular, and judges can see the proof. **Asli Odds** is a close second and has the best live demo. Choose **Ruko** if you have a strong Android developer.

**"typesafe jev" resolved:** two agents independently identified it as **TypeSafe AI's Jev**. It is a "System One" decision-only model launched around 15–18 Sep 2026. It returns typed answers (a choice, a score, or yes/no) with calibrated probabilities. Access is through OpenRouter (`typesafe/jev-latest`) and the Vercel AI Gateway. All benchmarks are vendor-reported. HiddenLayer found it easier to fool with character-level edits than large LLMs (InfoWorld, 15 Oct 2026). **Use it only where attackers don't control the input**, which is how ideas 1 and 5 use it.

---

## How this was produced

- **Round 1 (14 agents):**
  - 9 problem areas: personal finance, lending, fraud/AML, regtech, MSME operations, insurance, retail investing, accounting/audit, banking operations.
  - 5 technology scans: frontier methods, agentic payments, trustworthy/verifiable AI, finance-specific models, voice/low-friction interfaces.
- **Round 2 (6 agents):** for each chosen problem, one deep-dive on personas and competitors and one on whether the technology is buildable. An MSME deep-dive was stopped after you chose the three problems.
- **Agents were told not to propose ideas.** Every idea below was designed from their evidence in a separate step.

---

## Step 1: Research the problem

### 1.1 Screening

| Area | India pain, quantified | Evidence | Persona and gap clarity | Fit with new tech | Result |
|---|---|---|---|---|---|
| Elderly digital-arrest / UPI scams | ₹91 cr (2022) → ₹1,936 cr (2024) | Parliament reply | Very high | High | **Chosen (A)** |
| Health claim denials | ~26 lakh repudiations in FY25 | IRDAI via press | Very high | Very high | **Chosen (B)** |
| Retail F&O losses | ₹1.06 lakh cr lost in FY25 | SEBI study **[P]** | Very high | High | **Chosen (C)** |
| MSME delayed payments / credit | ₹20,979 cr pending on Samadhaan; $342bn gap | Mixed | High | Medium | Runner-up |
| NBFC compliance re-mapping | 9,445 circulars folded into ~238 Master Directions | Good | Medium (B2B, small fines) | High | Dropped |
| AML false positives | 90–95% (old PwC figure) | Weak for India | Medium | Medium | Dropped (common idea, US data) |
| Accounting / audit | 39% PCAOB deficiency rate | US only | Medium | Medium | Dropped |
| Personal finance (gig income, loan apps) | India data stops at 2021–22 | Stale | Medium | Low | Dropped |
| Failed-payment refunds / disputes | RBI already auto-compensates ₹100/day | Weak | Medium | Low | Dropped |

### 1.2 Problem A: scams where elderly Indians are tricked into sending the money ("digital arrest")

**Scale**
- Digital-arrest complaints on India's cybercrime portal (NCRP) went from **39,925 incidents and ₹91.14 cr (2022)** to **1,23,672 incidents and ₹1,935.51 cr (2024)**, about 21x in money. Jan–Feb 2025 alone: 17,718 cases, ₹210.21 cr. *(Rajya Sabha reply, 12 Mar 2025 [P via wire])*
- The Supreme Court ordered a CBI probe (1 Dec 2025). The government cited losses near **₹3,000 cr**. *(MediaNama [P])*
- UPI fraud in FY25: **12.64 lakh cases, ₹981 cr**. *(Lok Sabha, 15 Dec 2025 [S])*

**How it unfolds**
- A fake courier or telecom caller hands the victim to a fake "CBI/NIA officer".
- The victim is kept on a **continuous WhatsApp or Skype video call**, sometimes for **72+ hours**, and shown a fake court with forged orders.
- They are told to move savings to "verified" accounts.
- **Large sums leave through RTGS/NEFT transfers, early closure of FDs, PPF and mutual funds, and finally branch visits.** UPI is used only for early, small amounts.
- Example cases:
  - Delhi retired officer: ₹48.5 L, after FDs and PPF were cashed out.
  - Mumbai, 85-year-old professor: ₹9 cr over 3 weeks.
  - Jodhpur senior: ₹1.85 cr lost; branch staff stopped a further ₹33 L.
- Victims in the reported cases are mostly **75–85-year-old retirees**, in metros and tier-2 cities (Indore, Jodhpur, Mangaluru, Kochi). *[P/S, round-2 case list]*

**Current defences and what they miss**

| Defence | What it acts on | What it misses |
|---|---|---|
| Truecaller / blocking SIMs (7.81 cr blocked by Feb 2025 [S]) | Caller number | Scammers rotate numbers and use WhatsApp/Skype video |
| 1930 helpline / NCRP / Chakshu | Reports after the fact | Haryana froze **60%** of stolen money when the complaint came within 6 hours, **19%** after that [P]. Victims under "arrest" don't report in time |
| RBI MuleHunter.AI | The account receiving the money | Acts only after the money has landed |
| Google on-device call scam detection | Call audio | **Pixel 9 and later only, under 1% of Indian phones** (TechCrunch, Nov 2025 [P]); doesn't cover app video calls |
| RBI 2026 discussion paper: 1-hr hold, co-authoriser for seniors above ₹50k, 24-hr cool-off on trusted-contact changes | Person-to-person transfers | **Not final; known only from secondary sources [S]**. Doesn't cover branch RTGS or early FD closure |
| Alert bank staff | Human judgement | **This works.** Branch staff stopped transfers in Kochi, Mangaluru (₹84 L), Navi Mumbai, Hyderabad (₹46 L) and Jodhpur (₹33 L). But nothing systematically prompts them to act |

**Android constraint:** no third-party Android app can read live call audio, for either normal or WhatsApp calls. Google Play has banned accessibility-service call recording since May 2022. *[P/S]*

**The gap:** every defence keys on who is calling, on reports filed afterwards, or on the receiving account. None keys on the one pattern every digital-arrest scam shares: **a senior kept on a long call while liquidating savings to new payees.** The one fix that has worked, a trusted person interrupting, has nothing to trigger it.

### 1.3 Problem B: health claims denied or partly paid, with no reason the family can check

**Scale**
- FY25: **3.26 crore health claims**. 87% settled, **8% repudiated (~26 lakh)**, ~5% pending. *(IRDAI Annual Report via Insurance Business, 27 Jul 2026 [S])*
- **IRDAI holds no data on why claims are denied.** *(Lok Sabha reply [S])*
- LocalCircles (30,366 policyholders, Jan 2025, self-selected): 25% fully approved, **33% partly approved, 36% rejected** [S].
- 73% of dissatisfied claimants were given no clear reason (Policybazaar 2026 [S]).
- **₹15,100 cr** of claims denied on policy terms in FY24 [S].
- 76% of reimbursement claimants borrowed money or sold investments to pay the hospital [S].
- Average out-of-pocket cost per hospitalisation: **₹34,064** (NSS 80th round, 2025).
- At discharge, 6 in 10 families waited **6–48 hours** (LocalCircles). Hospital case studies show 4–6 hours. *[S]*

**Families who push back usually win:** health complaints decided by the Ombudsman in FY25:

| Outcome | Count |
|---|---|
| Disposed | 29,017 |
| For the policyholder | 6,126 |
| Recommended for settlement | 9,417 |

That is **~54% in the policyholder's favour or sent to settlement**, our arithmetic. The press headline says 41%. *(CIO data via Cafe Mutual [S])* Filing is **free**, covers up to ₹50 L, and must happen within 1 year *(cioins.co.in [P])*. Yet only ~29k health cases reach the Ombudsman against ~26 lakh repudiations.

**The rules are precise and can be encoded** (IRDAI Master Circular, 29 May 2024 [P]):
- **Cl.13:** after **60 months of continuous cover**, a claim can't be contested for non-disclosure or misrepresentation, *except established fraud*.
- **Cl.15(b):** cashless decision within **1 hour**.
- **Cl.16(a):** final discharge authorisation within **3 hours**. **Cl.16(b):** extra hospital charges caused by the delay are paid by the insurer from shareholders' funds.
- **Cl.17(a):** no repudiation without approval from a Claims Review Committee. **Cl.17(b):** a rejection must give "full details giving reference to the specific terms and conditions".
- **Standard exclusion codes Excl01–Excl18**, plus 12 exclusions that are banned outright (2019 guideline [P]).
- **Non-payable items:** about 199 items listed in Annexure I of the 2016 guideline [P].
- **Waiting-period cap for pre-existing diseases:** reportedly cut from 48 to 36 months from 1 Apr 2024 **[S, verify]**.

**Current helpers miss** two things. No helper with a verified fee structure was found, and ClaimBuddy's footer says it is not IRDAI-registered. NHCX (the National Health Claims Exchange) is not mandatory for hospitals.

**The gap:** policyholder and insurer know very different amounts. The insurer must cite a clause; the family can't tell whether that clause actually applies. A free route to redress exists and mostly works, but almost nobody can build a case for it.

### 1.4 Problem C: retail F&O traders who keep losing

**Scale**
- FY25: **91% of individual traders lost money, ₹1,05,603 cr in total** *(SEBI, Jul 2025 [P])*.
- FY26: ₹91,685 cr across 78.6 lakh traders, **average loss ₹1,16,654** *(Rajya Sabha via Moneylife, Aug 2026 [P])*.
- **Losses get more likely with experience:** 90.97% lost in year 1, **96.5% in year 4** *(SEBI FY25–26 study via Outlook Money [P])*.
- FY22–24: more than 75% of loss-makers kept trading [S].

**Who they are** (SEBI FY26 data via FPJ/Mint [P])
- Under-30s are **43%** of traders, and 89% of them lost.
- About **two-thirds live outside the top-30 cities**.
- About **three-quarters earn under ₹5 L** a year.
- **77% trade with under ₹1 L of peak margin**, and about 90% of those lost.
- **59% of index-options turnover happens on expiry day.**

**Where the ideas come from**
- About 59% of investors take advice from finfluencers, friends or online groups, and 62% of those who follow influencers acted on it *(SEBI Investor Survey 2025 [P])*.
- Only **6% of finfluencers are SEBI-registered** *(CFA Institute 2026 [P])*.
- About **985 registered investment advisers for ~21 cr demat accounts** [S].
- Enforcement shows the format: Avadhut Sathe, **₹546 cr impounded**, paid WhatsApp "mentorship" groups posting entry, target and stop-loss (SL) levels [P]. Asmita Patel, about ₹53 cr [S].

**What existing tools show**
- Sensibull shows payoff charts and a **per-trade** probability of profit.
- **No tool tracks a tip channel's record, the odds of ruin over months, or how much costs eat into returns.**
- SEBI says its own curbs had a limited effect, at least in the short term.

**The gap:** the trader sees each tip as one exciting bet. Nobody shows them the distribution of outcomes, or the track record the channel hides.

---

## Step 4: Technology radar

*Placed here because each idea below picks from it.*

| Technology | Date / source | What it is | Usable in 48h? | Used in |
|---|---|---|---|---|
| **TypeSafe Jev** | Sep 2026; OpenRouter `typesafe/jev-latest` | Decision-only model: typed choices, scores, yes/no answers with calibrated probabilities | Yes, early-access key. Fallback: any LLM with structured output | 1, 5 |
| **LLM → SMT (Z3) autoformalization** | arXiv 2601.06181 (Jan 2026: statutes to SMT constraints, 86.2% correct); PolicyLLM (ICML 2026 workshop); "Know Your Limits" arXiv 2606.16118 | LLM turns rule text into logic; a solver decides. "Know Your Limits" found the main failure is unjustified hidden assumptions | Yes (z3-solver 5.3.1, MIT) | 3 |
| **Conformal prediction with abstention** | arXiv 2604.13991, 2605.04295 (2026) | Calibrates a threshold so accepted outputs have a stated error bound; abstains otherwise | Yes, with a small labelled set | 1, 3 |
| **ACE: Agentic Context Engineering** | arXiv 2510.04618, ICLR 2026; github.com/ace-agent/ace (Apache-2.0) | A playbook that improves itself through generator, reflector and curator steps; incremental bullet edits with helpful/harmful counters; no training | Yes, API-based | 4 |
| **Kronos** | arXiv 2508.02739, AAAI 2026; MIT; HF `NeoQuasar/Kronos-small` (24.7M, context 512) | Turns price candles into tokens and generates future candle sequences | Yes, with one patch: `predict()` averages its samples, so paths must be pulled out before averaging | 5 |
| **Google AP2 mandates** | 16 Sep 2025; Apache-2.0 SDK | Signed, scoped spending authorisations (Intent / Cart / Payment) issued as verifiable credentials | Yes, with mocked payment rails. No multi-signer pattern exists, so we extend it | 2 |
| **Sarvam Saaras v3 (speech-to-text) and Bulbul v4 Flash (text-to-speech)** | Bulbul v4 Flash, Oct 2026 | 22-language streaming STT (₹30/hr); TTS with under 250 ms to first audio (vendor claim), 11 languages | Yes, API key | 1, 3 |
| **PaddleOCR-VL / DeepSeek-OCR / Sarvam Doc Digitization** | Oct 2025 / Oct 2025 / May 2026 | Small open models for document parsing; Sarvam's hosted service is ₹0.5/page | Yes | 3, 4 |
| **Outlines 1.3.3 / XGrammar 0.2.8 / Pydantic 2.14** | Aug–Oct 2026 | Forces model output to valid JSON | Yes | 3, 4, 5 |

**Considered and rejected:**
- **Chronos-2 and TimesFM:** they output quantiles, not sample paths. Stop-loss and target exits depend on the path a price takes, so they can't be simulated with these. TimesFM 3.0 weights are also non-commercial.
- **LLM-JEPA:** no evidence of finance use.
- **Recursive Language Models:** policy wordings already fit in a context window.
- **zkML / FHE:** too heavy for 48h.
- **x402 / ACP / Stripe's Machine Payments Protocol:** no fit with Indian payment rails.
- **AWS Automated Reasoning checks:** generally available, so low novelty.
- **The Lean-gate paper:** most novel, but can't be built in 48h.

---

## Steps 2–4: the five ideas

Each idea follows the same structure: **persona (Step 2) → what the user is up against and the UX choice → USP and 2–3 core features with an explicit cut list (Step 3) → novel tech (Step 4) → build plan, demo and risks.**

Team shorthand used in the build plans: **FS1/FS2** = full-stack developers, **ML1/ML2** = ML engineers.

---

### Idea 1: Ruko ("Wait") — catches a digital arrest from phone behaviour, without listening to the call

**Problem A.**

**Step 2: Persona.**
- Mr. Sharma, 74, retired state-government officer in **Indore**.
- ₹38 L in FDs and PPF at a public-sector bank.
- Uses WhatsApp video daily with his grandchildren, and PhonePe and YONO for small payments.
- Hindi-first; reads English slowly. His son is in Pune, his daughter in Dubai.

**What he's up against → UX choice.**
- Mid-scam he is terrified and told to tell no one, so **he will not open an app or press a button.**
- The tool must therefore be **passive: it triggers with no action from him, speaks Hindi, and pulls in his son.**
- The son installs and configures it. The father only has to listen and tap one of two large buttons.

**Step 3: USP.** It uses only phone metadata and never needs call audio. It fires on what every digital arrest shares: a long video or VoIP call while banking apps are opened and savings are being moved.

**Core features (build only these):**

1. **Tripwire**, an Android service. It raises a risk event when these signals combine:
   - **VoIP call in progress for more than N minutes.** Detected by `AudioManager` mode `MODE_IN_COMMUNICATION`.
   - **Banking or UPI app in the foreground** during or right after the call. Detected through `UsageStatsManager`.
   - **Bank notification text**, such as "FD closed", "beneficiary added" or "RTGS". Read through `NotificationListenerService`.
2. **Calibrated decision.**
   - The event state goes to **Jev** with one question: `risk = {ignore, check_in, interrupt_now}`. It returns a probability for each answer.
   - The threshold comes from **conformal calibration** on about 200 labelled scenarios. Scam scenarios are built from the documented cases above. Normal ones include a grandchild's video call or paying the electricity bill.
   - This lets the pitch state: *"Our calibration set misses at most X% of scams at this threshold."*
3. **Interrupt and bring in the family.**
   - A full-screen Hindi voice prompt plays through **Bulbul v4 Flash**, for example: *"Koi bhi police ya CBI video call par 'digital arrest' nahi karti — call kaatiye."* (Delhi Police: digital arrest has no basis in Indian law.)
   - At the same moment the son gets a WhatsApp message with context: *"Papa: 2h14m on WhatsApp video · YONO opened · 'FD closed ₹12,00,000'."*
   - The message has one-tap **Call Papa** and **Dial 1930** buttons.

**Cut list (later):**
- A "golden-hour" responder that auto-drafts the NCRP complaint and a bank freeze letter (the 6-hour window means 60% vs 19% frozen).
- Spoken Q&A with Saaras.
- A mode for branch staff.
- Deepfake voice detection.

**Step 4: Why it's novel.**
- It uses the newest typed-decision model (Jev) where **attackers don't control the input**, because the input is metadata, not scammer text. That avoids Jev's known adversarial weakness.
- It sets its threshold with conformal calibration rather than a guessed number.
- It speaks Indian languages on low latency with Bulbul v4 Flash.
- Pitch line: "It needs no call recording and no Pixel phone, and works on the ~99% of phones Google's feature misses."

**48h plan:**
- **H0–4:** go/no-go spike on two real phones. Can the app see `MODE_IN_COMMUNICATION` during a WhatsApp call, the foreground app, and bank notifications? *(This is our inference from Android APIs. The agents did not verify it.)*
- **H4–16:** ML1/ML2 build the scenario set, Jev questions and conformal threshold. FS1 builds the Android service and overlay. FS2 builds the alert backend (WhatsApp Cloud API test number; Telegram or SMS fallback).
- **H16–36:** integrate, play Bulbul audio, render the context card, tune false alarms.
- **H36–48:** rehearse the demo and finish the pitch.

**Demo (3 min):**
1. A teammate "CBI officer" calls the "elder" phone on WhatsApp video. Demo threshold: 2 minutes.
2. The elder opens YONO, and a mock bank notification arrives.
3. The Hindi interruption plays, and the son's phone buzzes in front of the judges.

**Metric for judges:** time from the first sign of money moving to a human stepping in. **Under 60 seconds**, versus the hours or days victims are held today.

**Risks → mitigations:**
- **Long calls are normal for seniors** → the trigger needs a long call *and* a finance app or bank notification.
- **Play Store policy on special permissions** → ship as a sideloaded APK or a bank-distributed app. Note it as a production issue.
- **Jev access not granted** → fall back to the same typed questions on any LLM with structured output.

---

### Idea 2: Saath ("Together") — a guardian co-sign mandate the bank enforces

**Problem A.**

**Step 2: Persona.**
- Rahul, 38, software engineer in **Bengaluru**, who manages his parents' finances remotely.
- His parents (72 and 68) live in **Mangaluru** with ₹40 L across FDs at one bank.
- He can watch, but **he cannot stop a transfer.**
- Secondary user: the branch officer at the parents' bank.

**What he's up against → UX choice.**
- The parent's judgement fails only *during* the scam.
- So the parent **pre-commits while calm** (a deliberate "bind my own hands" arrangement), and the bank enforces it at the ledger, where every channel ends up.
- Rahul approves with a passkey on his phone. The parent sees nothing new until a transfer is held.

**Step 3: USP.** Holds that only cover UPI miss where digital-arrest money actually goes: RTGS, early FD closure and branch withdrawals. Saath's mandate is checked on every debit channel. It turns RBI's own proposed **senior co-authoriser (above ₹50k) and 24-hour cool-off** into a working, interoperable protocol.

**Core features:**

1. **Issue a mandate.**
   - Parent and guardian jointly create a signed **AP2-style IntentMandate** (an SD-JWT verifiable credential).
   - **We add a `required_cosigners` field to AP2.**
   - Rules: transfers to a new payee above ₹50k, early closure of FD or PPF, adding a beneficiary.
   - Changing or revoking the mandate needs a **24-hour cool-off**, mirroring the RBI proposal.
2. **Enforce on every debit channel.**
   - A mock core-banking system with UPI, net-banking RTGS, a branch teller and FD-closure endpoints.
   - Every debit passes through a verifier. A match triggers a **1-hour hold** and sends a co-sign request.
   - Rahul's request comes with a context card: payee account age, first-time payee, amount compared with 12 months of history.
   - He **approves or denies with a passkey (WebAuthn)**, or taps to call his parent.
3. **Branch check card.**
   - The teller screen shows a banner: "Saath mandate active, co-sign pending".
   - It also shows a 3-question script in Hindi or Kannada for spotting a digital-arrest victim. Branch staff interventions are the proven fix (₹84 L, ₹46 L and ₹33 L saved).

**Cut list:**
- k-of-n guardians.
- Using Ruko's risk signal to tighten rules automatically.
- An NPCI Unified Agent Protocol adapter.

**Step 4: Why it's novel.**
- **It repurposes AP2 mandates, built for AI shopping agents in Sep 2025, for delegation between people.** It adds co-signers, which nobody has done.
- The verifiable credential gives an audit trail usable in disputes.
- It points the same way as NPCI's 2026 Unified Agent Protocol proposal: registered, verifiable, delegated authority on Indian payment rails.

**48h plan:**
- **H0–8:** mandate schema, ES256 SD-JWT signing, passkeys.
- **H8–24:** mock bank (FastAPI) with three debit channels, verifier and hold queue.
- **H24–40:** guardian PWA, Hindi screen for the parent, teller screen.
- **H40–48:** audit log and demo.

**Demo:**
1. Try a ₹12 L RTGS from net banking. It is held.
2. Try an early FD closure at the "branch". It is also held, and the teller sees the script.
3. Rahul's phone shows a passkey prompt. He taps Deny, and both attempts are blocked with a reason logged.

**Metric:** coverage, meaning the share of documented digital-arrest money routes the mandate intercepts. Show it as **4 of 4 routes**, against **1 of 4** for a UPI-only hold.

**Risks → mitigations:**
- **The RBI paper is known only from secondary sources** → verify before pitching, and frame it as "aligned with the regulator's proposal".
- **Needs a bank to adopt it** → pitch to co-operative and small-finance banks as an open standard.
- **Elder autonomy** → the mandate is voluntary, created by the parent, and revocable after the 24-hour cool-off.

---

### Idea 3: ClaimProof ⭐ — appeals for denied health claims that come with a checkable proof

**Problem B.**

**Step 2: Persona.**
- Priya, 34, a school teacher in **Nagpur**. Her father, 63, has just had an angioplasty.
- Their family-floater policy (₹5 L) has been **renewed every year since 2019, about 84 months of continuous cover.**
- The insurer cut ₹1.1 L, citing "non-disclosure of hypertension" plus a proportionate deduction for room rent.
- She has a one-page English letter and a 60-page policy PDF.
- She reads English but not legal wording, speaks Marathi and Hindi at home, and does everything on WhatsApp and her phone camera.

**What she's up against → UX choice.**
- She has photos, not files.
- **WhatsApp bot:** she sends photos of the letter and policy schedule.
- She gets back a short voice note in her language and a PDF appeal letter. A web-upload page is the fallback.

**Step 3: USP.** Every other "AI claim helper" offers an opinion. ClaimProof outputs a **proof**: the exact IRDAI and policy clauses the denial contradicts, found by a logic solver. When a fact is missing, it says exactly what evidence to collect instead of guessing.

**Core features:**

1. **Read the paperwork.**
   - OCR with PaddleOCR-VL or Sarvam Document Digitization.
   - **Typed extraction** (Pydantic with Outlines-constrained JSON) of: policy start date, continuity, sum insured, room-rent cap, the clause the denial cites, amount disallowed, diagnosis and dates.
2. **Compile and check, using two tiers of rules.**
   - **Regulatory tier**, written by hand once and unit-tested: Cl.13 moratorium, Cl.17(b) clause-citation duty, Cl.16(b) delay charges, the banned exclusions, Excl01–18 definitions, and the waiting-period cap for pre-existing diseases.
   - **Policy tier:** the policy's own clauses are **turned into typed rule JSON by an LLM, then into Z3 constraints**. A round-trip check has the LLM restate each rule next to the original clause text.
   - Z3 then answers: **does the policy plus regulation, given these facts, actually allow this denial?**
     - If not (UNSAT), the **unsat core** (the smallest set of rules that conflict) *is* the argument.
     - If the answer depends on an unknown fact (for example, was hypertension diagnosed before 2019?), it **abstains** and asks for that document. This addresses the "unjustified hidden assumptions" failure that "Know Your Limits" reports.
3. **Appeal pack.**
   - A grievance letter to the insurer first (required before the Ombudsman), then an Ombudsman complaint.
   - Both cite the exact clauses and include the proof trace.
   - A tracker for the 1-year deadline.
   - A plain-language voice note through Bulbul.

```python
# Regulatory tier (hand-verified), Z3 sketch
s.add(Implies(And(ground == NON_DISCLOSURE, cont_months >= 60, Not(established_fraud)),
              Not(denial_valid)))                       # Cl.13 moratorium
s.add(Implies(Not(letter_cites_specific_clause), Not(denial_valid)))  # Cl.17(b)
s.add(denial_valid == insurer_claims_valid)             # the insurer's position
# s.check() == unsat  →  s.unsat_core() names the clauses the denial breaks
```

**Cut list:**
- **"Policy X-ray" before buying:** simulate common hospitalisations against a policy to estimate out-of-pocket cost.
- Hospital-side integration.
- Fetching data through NHCX.

**Step 4: Why it's novel.**
- **Our scan found no paper that turns insurance policy wording into logic for deciding claims.** The closest is statutes-to-SMT (arXiv 2601.06181, Jan 2026).
- It applies the newest solver-in-the-loop approach (PolicyLLM, ICML 2026) to a gap where policyholder and insurer know very different amounts, and where users can win redress for free.
- It reduces its own risk by design: regulations are verified by hand, policy clauses are generated but flagged, and it abstains when unsure.

**48h plan:**
- **H0–6:** pull 3 real policy wordings from policyholder.gov.in (1,820 products listed). ML1 writes 8–10 regulatory rules in Z3 with tests. FS1 writes 10 synthetic denial letters, some valid and some invalid.
- **H6–20:** OCR and typed extraction. Clause-to-rule compiler with the round-trip check.
- **H20–32:** solver, unsat core turned into an argument, abstention, letter templates.
- **H32–40:** WhatsApp front end and voice note.
- **H40–48:** run all 10 cases, score precision, rehearse.

**Demo:**
1. Send Priya's letter photos live on WhatsApp.
2. About 40 seconds later, the reply: *"Denial contradicts IRDAI Master Circular Cl.13: 84 months of continuous cover is more than 60. Non-disclosure can't be raised unless the insurer proves fraud."*
3. Show the appeal PDF and the unsat core next to it.
4. Then show a valid denial, where ClaimProof correctly says it **can't** help.

**Metric:** on the labelled set, precision of "denial is inconsistent" findings, the abstention rate, and time to a draft appeal (minutes, against days with a consultant).

**Risks → mitigations:**
- **Mistakes in the LLM-generated rules** → the two-tier design, a side-by-side clause view, and abstention.
- **Seen as legal advice** → position it as a free tool that helps people use a free grievance right. Charge no fee on recovered amounts, which would invite intermediary rules.
- **The 36-month waiting-period cap is unverified** → leave it out of the regulatory tier until the primary text is confirmed.

---

### Idea 4: DischargeDesk — a copilot for hospital insurance desks that learns each insurer's habits

**Problem B.**

**Step 2: Persona.**
- Ramesh, 29, insurance/TPA desk executive at a **120-bed private hospital in Indore**.
- Handles 15–30 cashless files a day across 20+ insurers and third-party administrators (TPAs), each with its own portal and quirks.
- Works on a desktop: Excel tracker, email, insurer portals, and WhatsApp with TPA staff.
- Families blame him for 4–6-hour discharges.
- ⚠ **We found no direct survey of this role.** These details come from hospital case studies (Apollo Ahmedabad, Jaslok). Validate them with 2–3 desk interviews before the hackathon.

**What he's up against → UX choice.**
- He works on a desktop with many tabs open.
- **A browser side panel / web app next to his tracker.** No new workflow, just a check before he submits a file and a clock dashboard.

**Step 3: USP.** Insurer queries come in loops, and each one adds hours. DischargeDesk **learns each insurer's habitual queries from past cases** and flags them before submission. It also turns IRDAI's clocks into a tool for the hospital: under Cl.16(b), delay charges fall on the insurer.

**Core features:**

1. **Pre-submission check.**
   - OCR the bundle (discharge summary, itemised bill).
   - Check it against this insurer's playbook and IRDAI's non-payable items list (Annexure I).
   - Example flags: *"Insurer X always asks for indoor case papers on stays over 3 days"*, *"'Admission kit' is non-payable, so collect it from the family upfront."*
2. **An ACE playbook for each insurer.**
   - Every query or deduction received is fed back through ACE's reflector and curator as **incremental bullet edits with helpful/harmful counters**.
   - The playbook improves without retraining and stays readable and auditable.
3. **IRDAI clock and escalation.**
   - Timers for the 1-hour cashless decision (Cl.15(b)) and the 3-hour discharge authorisation (Cl.16(a)).
   - On a breach, it drafts an escalation email citing the clause and noting that delay charges are the insurer's to pay.
   - The family gets status texts.

**Cut list:**
- NHCX FHIR claim-bundle submission (no public sandbox found).
- Analytics across hospitals.

**Step 4: Why it's novel.** ACE (ICLR 2026) has only been tested on agent tasks and XBRL tagging. This applies it to a claims operations workflow it hasn't been tested on, with a playbook ops staff can read. *(ACE's paper reports finance-task gains; the code defaults to DeepSeek-V3.1 through SambaNova.)*

**48h plan:**
- **H0–8:** synthetic history of 3 insurers × 15 cases with their queries, plus the non-payable list encoded.
- **H8–24:** run ACE offline on that history to build each playbook. Build the pre-submission checker.
- **H24–36:** OCR, clock dashboard, escalation drafts.
- **H36–48:** demo.

**Demo:** replay 5 past cases for Insurer X, watching the playbook gain bullets. The 6th case is flagged before it is sent. Then trigger a clock breach that drafts an escalation.

**Metric:** query loops avoided on held-out cases, and minutes saved per file.

**Risks:** the persona has weak evidence; real query data is needed to beat synthetic data. *This is the weakest of the five. Keep it as the B2B alternative to ClaimProof.*

---

### Idea 5: Asli Odds ("Real Odds") — forward any Telegram tip and see its real odds

**Problem C.**

**Step 2: Persona.**
- Rohit, 24, salesman at a mobile-phone showroom in **Jaipur**, earning ₹28k a month.
- Eight months into F&O with **₹60k of margin**. Trades Nifty weekly options **on expiry day**.
- In 3 Telegram "VIP" channels, one of them paid (₹4,999), and watches Hindi trading YouTube.
- Down ₹41k but feels he is "close to cracking it". Speaks Hinglish and lives on his phone.

**What he's up against → UX choice.**
- He already lives in Telegram, and **forwarding a tip is one tap.**
- So: **a Telegram bot.** No new app, no sign-up, nothing to fill in.

**Step 3: USP.** Rohit sees every tip as one exciting bet. Asli Odds shows him **1,000 simulated outcomes of that exact tip**, costs included, and **the real track record of the channel that sent it**, the number SEBI's data implies and no channel shows.

**Core features:**

1. **Forward and parse.**
   - The bot records `forward_origin` (the source channel and time; Bot API 10.3).
   - It extracts {underlying, strike, CE/PE, entry, SL, target, expiry} as typed fields with Jev or constrained JSON.
   - If something is ambiguous, it asks one follow-up question.
2. **1,000 futures.**
   - Kronos-small generates 1,000 Nifty price paths up to expiry.
   - **Engineering trick:** the paths depend only on Nifty, not on the tip. So they are generated once every 15 minutes in the background, and each tip is just a fast vectorised repricing.
   - The option is repriced along every path with Black–Scholes (`vollib`), using India VIX as the volatility input.
   - SL/target exits are applied along each path, along with the **full 2026 cost stack**: STT 0.15% of sell-side premium from 1 Apr 2026, exchange charges about 0.0355%, stamp duty 0.003% on buys, SEBI fee ₹10/cr, 18% GST, ₹20 brokerage per order.
   - Sample output: *"In 1,000 futures: target hit 212, SL hit 655, expired 133. Average after costs: −₹1,840 per lot. Take every tip like this for 3 months and there's an 81% chance your ₹60k falls below ₹30k."*
   - The output uses a **gain/loss visual**. A Korean randomised field trial found that visualising gains and losses reduced risky product purchases.
3. **Channel ledger.**
   - Every forwarded tip is timestamped against its channel.
   - After expiry, the real outcome is checked against market data.
   - A **private scorecard** builds up, for example *"VIP Nifty King: 47 tips tracked, 14 hit target. Net −₹23,400 per lot if you'd followed them all."*

**Cut list:**
- Importing his own Zerodha Console tradebook to show his personal loss curve.
- A SEBI-registration lookup for the tipster.
- Pooled crowd scorecards (only with consent, and careful about defamation).

**Step 4: Why it's novel.**
- **It flips a finance foundation model from prediction to risk communication.** Kronos (AAAI 2026) is used to show the spread of outcomes, not to find trading edge.
- It has to be a *generative* model. Stop-loss and target exits depend on the path a price takes, so models that only output quantiles (Chronos-2, TimesFM) can't simulate them. That is the technical reason to choose Kronos.
- It is benchmarked honestly against a stationary block bootstrap of historical returns.

**48h plan:**
- **H0–6:** get Nifty 15-minute history (yfinance for recent data, or Kite Connect historical at ₹500/month). Patch Kronos to return each path separately. Generate 1,000 paths. Check realism: fat tails and volatility clustering against history.
- **H6–18:** ML1 tries zero-shot, then fine-tunes on Nifty if needed. ML2 builds the bootstrap baseline. FS1 builds the Telegram intake and parser.
- **H18–30:** repricing, SL/target logic, cost stack, histogram image.
- **H30–40:** the ledger, backtested on a synthetic channel of 30 tips.
- **H40–48:** Hinglish copy and rehearsal.

**Demo:**
1. Forward a realistic tip live.
2. About 5 seconds later: a histogram and a Hinglish verdict.
3. Open the scorecard for a channel with a 30-tip history.
4. Close on the slide: *"91% lose. Now he can see why before he trades."*

**Metric:** response time; how close the generated paths' statistics are to real Nifty data; and, in a hallway test, how many people say they would change their trade.

**Risks → mitigations:**
- **SEBI research-analyst rules** → it never says buy or sell. It only describes the distribution of a plan the user brings, framed as investor education. Get a legal check before launch.
- **Kronos may not be realistic on Nifty data** → show the validation slide, with the bootstrap as a fallback.
- **A single implied volatility ignores skew and understates tail losses** → say so on screen. It's conservative, because real losses are worse.

---

## Comparison and recommendation

Scores out of 5. For **Risk**, 5 = lowest risk.

| | Pain | Evidence | Persona sharpness | Novelty | Buildable in 48h | Demo impact | Risk | **Total** |
|---|---|---|---|---|---|---|---|---|
| **3 ClaimProof** | 4 | 5 | 5 | 5 | 4 | 4 | 4 | **31** |
| **5 Asli Odds** | 5 | 5 | 5 | 4 | 4 | 5 | 3 | **31** |
| **1 Ruko** | 5 | 4 | 5 | 4 | 3 | 5 | 3 | **29** |
| **2 Saath** | 5 | 3 | 4 | 4 | 3 | 4 | 3 | **26** |
| **4 DischargeDesk** | 3 | 2 | 3 | 3 | 3 | 3 | 3 | **20** |

**Which to build:**
- **ClaimProof breaks the tie.** Its novelty is the easiest to defend (no prior paper), its rules come from primary regulatory text, and its proof is something judges can inspect.
- **Asli Odds** if the team wants the strongest live moment and the hardest-hitting numbers.
- **Ruko** only if the Android check at H0–4 passes.

---

## Validation checklist before the hackathon

1. **Primary-source checks:**
   - RBI's 2026 discussion paper on the cooling period and senior co-authoriser (Saath).
   - The 36-month waiting-period cap for pre-existing diseases (ClaimProof).
   - The IRDAI FY25 figure of 8% repudiated.
2. **Access:**
   - A Jev key through OpenRouter (`typesafe/jev-latest`); fall back to any LLM with structured output.
   - Sarvam API credits.
   - A WhatsApp Cloud API test number.
   - A Telegram bot token.
3. **Ruko:** test VoIP-call detection with `AudioManager` on 2 real Android phones (Android 14–16) during a WhatsApp video call.
4. **Asli Odds:** patch Kronos so `predict()` returns each sampled path instead of the average; confirm a Nifty data source and NSE's terms of use.
5. **DischargeDesk (if chosen):** 2–3 interviews with hospital insurance-desk staff.
6. **Legal framing:** ClaimProof (claim consultancy, no fees) and Asli Odds (SEBI research-analyst and finfluencer rules).

## Evidence caveats

- **RBI bank-fraud totals for FY25 conflict:** 23,953 cases / ₹36,014 cr versus 11,615 cases / ₹3,497 cr. Don't use either without checking.
- **Ombudsman:** the press headline says 41%; the counts give 54%. Show the counts.
- **Self-selected or vendor samples:** LocalCircles and Policybazaar figures, and Chargebacks911-style data.
- **Jev:** latency, price and accuracy figures are all vendor-reported. The "System One adapter" for other LLMs could not be confirmed.
- **Kronos:** the abstract's claim of 22% better "generative fidelity" has no defined metric and no test on Indian data.
- **Digital-arrest case amounts** come mostly from press reports. Some differ, for example ₹1.05 cr vs ₹1.5 cr for the Ambala couple.
- **Ruko's Android approach** is our own inference and has not been verified.

## Key sources

**Problem A: elderly scams**
- Rajya Sabha reply on digital arrests (12 Mar 2025): https://www.theweek.in/wire-updates/national/2025/03/12/del54-rsq-cybercrime.html
- Supreme Court CBI probe: https://www.medianama.com/2025/12/223-supreme-court-cbi-probe-digital-arrest-scams/
- Haryana 60% vs 19% freeze: https://www.tribuneindia.com/news/haryana/dgp-police-froze-60-of-cyber-fraud-money-606091
- Google scam-detection gaps in India: https://techcrunch.com/2025/11/20/google-steps-up-ai-scam-protection-in-india-but-gaps-remain
- RBI cooling-period proposal (secondary): https://amlegals.com/digital-payment-fraud-in-india-analysing-rbis-1-hour-delay-proposal-and-its-legal-impact/
- Branch saves:
  - Kochi: https://www.onmanorama.com/news/kerala/2025/12/18/never-seen-so-panicked-kochi-bank-manager-saved-elderly-customer-losing-4-5-lakh-digital-arrest-scam.amp.html
  - Mangaluru: https://www.deccanherald.com/amp/story/india%2Fkarnataka%2Fmangaluru%2Falert-bank-manager-mulki-police-foil-rs-84-lakh-digital-arrest-fraud-attempt-3820300
  - Hyderabad: https://telanganatoday.com/hyderabad-alert-sbi-staff-avert-digital-arrest-scam-being-perpetrated-save-46-lakh-of-elderly-couple
- UPI fraud (Lok Sabha): https://www.freepressjournal.in/amp/tech/india-reports-805-crore-upi-fraud-till-nov-fy26-amid-rising-digital-payments

**Problem B: health claims**
- IRDAI Master Circular on Health (29 May 2024): https://irdai.gov.in/document-detail?documentId=4942918
- Standardised exclusions (2019): https://irdai.gov.in/documents/37343/365525/Guidelines+on+Standardization+of+Exclusions+in+Health+Insurance+Contracts.pdf/39629f3a-a65b-7cea-f045-ca50f66ce6d0?version=1.1&t=1665918387659&download=true
- IRDAI can't explain denials / FY25 claims: https://www.insurancebusinessmag.com/asia/news/life-insurance/irdai-cannot-explain-why-health-insurance-claims-go-unpaid-583814.aspx
- Ombudsman FY25 health outcomes: https://cafemutual.com/news/industry/36635-41-of-health-insurance-complaints-were-resolved-in-favour-of-policyholders-in-fy25
- Ombudsman (CIO) portal: https://www.cioins.co.in/
- LocalCircles claims survey: https://www.businesstoday.in/amp/personal-finance/insurance/story/insurance-claims-over-50-health-cover-claims-faced-rejection-or-partial-approval-says-survey-459394-2025-01-02
- IRDAI product and wording list: https://policyholder.gov.in/web/guest/health-insurance-products

**Problem C: F&O losses**
- SEBI FY25 study: https://moneylife.in/article/91-percentage-of-retail-traders-lost-money-in-derivatives-losses-in-fo-surged-41-percentage-to-rs105-lakh-crore-in-fy25-sebi-study/77613.html
- FY26 losses: https://www.moneylife.in/article/retail-fo-traders-lose-91685-crore-in-fy2526-despite-sebi-curbs-average-loss-hits-117-lakh-govt/81318.html
- Losses rise with experience: https://www.outlookmoney.com/invest/sebi-futures-options-study-retail-traders-trading-losses-experience
- Young and tier-2 traders: https://www.freepressjournal.in/amp/business/89-of-young-fo-traders-lose-money-finds-sebi-study
- SEBI Investor Survey 2025: https://moneylife.in/article/just-1-in-10-indian-households-invests-in-stocks-finfluencers-driving-retail-trends-sebi-survey/78471.html
- CFA "Clicks and Credibility 2.0": https://rpc.cfainstitute.org/research/reports/2026/clicks-and-credibility-2-0
- Avadhut Sathe order: https://www.storyboard18.com/amp/how-it-works/sebi-bans-finfluencer-avadhut-sathe-impounds-rs-546-crore-for-running-unregistered-advisory-85392.htm
- 2026 STT change: https://www.icicidirect.com/ilearn/futures-and-options/articles/stt-changes-in-budget-2026-what-f-o-traders-should-know

**Technology**
- Jev: https://www.infoworld.com/article/4236103/typesafes-jev-even-more-susceptible-to-attack-than-llms-says-security-vendor.html · https://openrouter.ai/typesafe · https://vercel.com/changelog/ai-gateway-now-supports-typesafe-clients-and-http-api-for-jev
- Statutes to SMT: https://arxiv.org/abs/2601.06181
- PolicyLLM: https://icml.cc/virtual/2026/78632
- Conformal abstention: https://arxiv.org/abs/2605.04295
- ACE: https://arxiv.org/abs/2510.04618 · https://github.com/ace-agent/ace
- Kronos: https://arxiv.org/abs/2508.02739 · https://github.com/shiyu-coder/Kronos
- AP2: https://github.com/google-agentic-commerce/AP2 · https://ap2-protocol.org/
- Sarvam: https://docs.sarvam.ai/ · https://www.sarvam.ai/blogs/bulbul-v4-flash/
- PaddleOCR-VL: https://arxiv.org/abs/2510.14528
- Telegram Bot API: https://core.telegram.org/bots/api
