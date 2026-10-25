# Sprint 1 handoff: research and no-code work (Person C)

> 25 Oct 2026. Written for a teammate joining with no background. Read this file top to bottom before starting (10 min). Sankalp checks every deliverable afterwards, against the "Done when" lines.

---

## 1. What Kab Tak? is (2-minute version)

We're building for the Srujana 2026 hackathon, problem **F-03: predictive cash flow for small businesses**. The user is a constructed persona: Mahesh, who owns a 14-person CNC precision-components shop in Pune (a micro enterprise). He works on WhatsApp in Marathi, and his CA keeps his books in TallyPrime.

Each week he asks: *"Can I pay wages on the 7th? Should I take this new order?"* Kab Tak? simulates 1,000 possible futures for his bank balance and finds the weeks where he might run short. It then compares fixes by their rupee cost:

- discounting an invoice on TReDS;
- using the bank overdraft;
- paying a supplier later;
- reminding a buyer of their legal duty under the MSMED Act.

**Where things stand:**

| Part | Status |
|---|---|
| Engine | Built (Sankalp), not committed yet |
| WhatsApp channel | Person A, in progress |
| UI | Person B, in progress |

Your work makes the numbers **correct and believable**. Domain correctness is the single biggest judging criterion (20 of 100 points), and "problem understanding" is another 15.

**Background reading, only if you have time:**

- [f03-build-plan.md](f03-build-plan.md): §2 persona, §4 demo script, §6 synthetic ledger, §11 jury questions.
- [srujana-2026-rules.md](srujana-2026-rules.md): §7 rubric, §11 integrity.

## 2. Rules (please read; breaking these can disqualify the team)

1. **Every fact needs a source.** Tag each one:
   - **[P]** primary: the law, a regulator or government site, or the company's own page;
   - **[S]** secondary: news, blogs, law-firm explainers;
   - **[U]** couldn't confirm.

   Never write a number without a tag, and never upgrade a [U] to sound certain. The rules list fabricated claims as grounds for disqualification.
2. **Write down the date you checked** each source. Rates change.
3. **People you talk to:** ask permission before taking notes. Keep them anonymous ("a Pune CA with ~40 MSME clients") unless they agree in writing to be named. Don't record calls without consent.
4. **Never ask anyone for real client data or documents**, and never store any. All our data is synthetic.
5. **Work on branch `research`.** Only add files under `docs/planning/` and `docs/demo/`. Don't edit code, `README.md` or other people's files. Put proposed README text in a separate file (task 5).
6. **AI tools are allowed, but verify everything.** If an AI tool gave you a fact, open the source it cites and check it yourself; AI tools invent citations. Note which deliverables used AI help in your final commit message.

---

## 3. Your tasks, in priority order

Do 1 → 2 → 3 first. They fix real gaps in the engine and the pitch. Tasks 4–6 come after.

| # | Task | Type | Time | Needs |
|---|---|---|---|---|
| 1 | Domain assumptions sheet | Desk research | ~1.5 h | Internet |
| 2 | One or two CA / owner calls | Interviews | ~1 h | A phone, a contact |
| 3 | Realistic numbers for the synthetic business | Desk research (+ the call) | ~45 min | Internet |
| 4 | Demo assets: voice clips, Marathi check, storyboard | No-code | ~1.5 h | A phone, a Marathi speaker |
| 5 | README draft: acknowledgements, AI use, limitations | Writing | ~45 min | Repo access |
| 6 | Jury rehearsal partner | No-code | 30–60 min, later | The team |

---

### Task 1: Domain assumptions sheet

**Why:** the engine's money maths uses these values, and the jury includes finance and legal people. One wrong rate in front of them costs credibility.

**Deliverable:** `docs/planning/domain-assumptions.md`, one table with the columns below. Start from these rows; the "value we use now" column shows what the plan assumes today.

| # | Item | Value we use now | Value you found | Source URL | Date checked | Tag |
|---:|---|---|---|---|---|---|
| 1 | RBI **Bank Rate** (not repo rate) as of today | 5.75% from 7 Oct 2026 | | | | |
| 2 | RBI repo rate as of today | conflicting: 5.50% / 5.25% | | | | |
| 3 | MSMED Act s.16 interest = 3 × Bank Rate, compounded monthly | 17.25% | | | | |
| 4 | MSMED Act s.15: payment deadline with and without a written agreement | 45 days / 15 days | | | | |
| 5 | TReDS discount rate range (RXIL, M1xchange, Invoicemart). Look for published ranges or recent news | ~10% p.a. [U] | | | | |
| 6 | TReDS: which buyers must register (turnover threshold; CPSEs?) | ₹500 cr (2018) or ₹250 cr (Nov 2024)? | | | | |
| 7 | MSME overdraft / cash-credit interest, public vs private banks | 8.75–14% [S] | | | | |
| 8 | Drawing power: are receivables older than N days excluded? What margins on stock and receivables? | 90 days; margins unknown [U] | | | | |
| 9 | RBI rule: overdraft/CC account "out of order" for 90 days → NPA (IRACP master circular) | assumed | | | | |
| 10 | Income-tax Act 2025: the section that replaced 1961 Act s.43B(h) (MSE payments) | s.37(2)(g)? [S] | | | | |
| 11 | 43B(h): a late payment within the same financial year keeps the deduction in that year | yes [S] | | | | |
| 12 | CGST Act s.16(2): buyer reverses input tax credit if the supplier is unpaid after 180 days | yes | | | | |
| 13 | GST rate on machined parts for motor vehicles, after the 2025 rate changes | unknown | | | | |
| 14 | TDS rate a company buyer deducts on payments for contract work / manufacturing to a company supplier (Income-tax Act 2025 section) | 2%? | | | | |
| 15 | GST due date for a ~₹3–5 cr business (monthly GSTR-3B by the 20th, or QRMP option?) | 20th | | | | |
| 16 | Micro-enterprise definition (investment and turnover limits) as of today | turnover ≤ ₹10 cr? | | | | |
| 17 | MSMED (Amendment) Act 2026: passed? notified in the Gazette? what changed? | unknown [S] | | | | |
| 18 | Payment of Bonus Act / Code on Wages: does a 14-worker factory pay statutory bonus? Usual timing (Diwali)? | customary [U] | | | | |

**Where to look first** (check that each link still works):

- **RBI:** `rbi.org.in`, for current rates, the IRACP master circular and the Bank Rate press releases.
- **Income Tax Department:** `incometaxindia.gov.in`.
- **GST:** `cbic-gst.gov.in`, for rates and notifications.
- **Gazette:** `egazette.gov.in`, for the MSMED Amendment.
- **Ministry of MSME:** `msme.gov.in`, for the TReDS mandate notifications and the Udyam definition.
- **TReDS platforms:** `rxil.in`, `m1xchange.com`, `invoicemart.com`.
- **Law-firm and CA explainers** (taxguru, cleartax and similar) are fine as [S], but find the [P] source behind them where you can.

**Done when:**

- [ ] All 18 rows are filled. "Couldn't confirm" is fine; leave the tag [U] and say what you tried.
- [ ] Every row with a value has a working link and a date.
- [ ] A short **"Changes for the engine"** list at the bottom names every row where the value you found differs from "value we use now". Sankalp needs exactly this list.

---

### Task 2: One or two CA or MSME-owner calls

**Why:** nobody on the team has talked to a real user yet. One real quote on a slide is worth more than any chart for "problem understanding" (15 points). The answers also fix the engine's unrealistic assumptions.

**Who:** a chartered accountant with small-business clients is best, then an owner of a small manufacturing or engineering business. Family friends are fine. Any city is fine.

**Opening line (adapt it):** *"I'm a student at a hackathon, building a tool that helps small manufacturers see cash shortfalls coming. Could I ask you six quick questions, about 15 minutes? I won't use your name or any client details, and I'll only take notes if that's OK."*

**The six questions** (keep to these; follow up only if there's time):

1. How often is the accounting (Tally or other) actually updated for a small client: daily, weekly, monthly, only at GST filing?
2. When an owner gets a big order on long payment terms (say 90 days), how do they decide whether to take it? Who do they ask?
3. For a business that uses an overdraft or cash credit, how much of the limit is usually drawn? Do they often hit the limit?
4. How does the bank set drawing power? Are older receivables excluded (after how many days)? What margins on stock and receivables?
5. Roughly how many days of stock (raw material plus work in progress) does a small CNC or engineering shop carry?
6. If a WhatsApp bot answered *"Can I pay wages on the 7th?"* in Marathi, would an owner use it, or would they still call the CA? What would make them trust it?

Last question: *"Is there one sentence about cash-flow problems I could quote anonymously on a slide?"*

**Deliverable:** `docs/planning/user-validation.md`, with one section per call:

```markdown
## Call 1: <role, e.g. "CA, Pune, ~40 MSME clients">, <date>, ~<minutes> min
Consent to notes: yes · Consent to quote: yes/no · Named: no
1. Tally update frequency: …
2. Order decisions: …
3. Overdraft usage: …
4. Drawing power: … (days excluded: …; margins: …)
5. Stock days: …
6. WhatsApp bot: …
Quote (only if consented): "…"
Surprises / things we got wrong: …
```

**Done when:**

- [ ] At least one call is done and written up within ~2 hours of starting. If nobody is reachable in time, write down who you tried and move on to task 3.
- [ ] Consent is recorded for each call.
- [ ] "Surprises / things we got wrong" isn't empty. There is always something.

---

### Task 3: Realistic numbers for the synthetic business

**Why:** the engine currently assumes things a CA would spot as unrealistic, such as only ₹60k of stock. As a result the business looks too fragile: Buyer A can be only ~3 days late before wages fail. Sankalp needs realistic ranges to re-tune it.

**Deliverable:** add a section **"Ledger parameters"** to `docs/planning/domain-assumptions.md`, as a table with the columns *parameter · typical range · source / basis · tag*:

| Parameter | Notes on what to find |
|---|---|
| Annual turnover of a 14-worker CNC components shop | Currently ~₹2.9 cr in the engine vs ₹4.2 cr in the persona. Which is more typical? |
| Stock held (days of sales or ₹) | Raw bar stock + work in progress + finished goods |
| Payment terms large auto Tier-1 buyers give small suppliers (days), and how late they really pay | Delayed-payment reports, MSME association surveys |
| How late public-sector buyers (CPSEs) pay | The GAME–FISME–C2FO delayed payments report says ~40% of delayed dues are owed by government buyers and PSUs [S] |
| Raw material as % of revenue for CNC machining | Currently 45% |
| Power cost as % of revenue | |
| Monthly wage per CNC operator in Pune (₹) | 14 workers; payroll currently ~₹3.4 L/month |
| Typical machine EMI for a used / new VMC or CNC lathe | Currently ₹1.2 L/month |
| Overdraft / cash-credit limit for a business this size | Currently ₹25 L |

Use your task-2 call answers where they fit (tag them "interview, n=1").

**Done when:**

- [ ] Every row has a range (not a single number) and a basis.
- [ ] One sentence at the top says which three parameters matter most for making the business less fragile (likely stock, overdraft limit, buyer delays).

---

### Task 4: Demo assets (no code)

**Why:** the demo video (due at H36) decides whether we reach the final. The Marathi voice and text must be right.

**4a. Voice clips** for testing speech-to-text. Record each sentence as a **WhatsApp voice note** (that's the format the bot receives), spoken naturally, in 2–3 different voices if possible (different ages or genders help):

| File name | Sentence |
|---|---|
| `hero-order-<voice>.ogg` | नवीन बायरची १२ लाखांची ऑर्डर ९० दिवसांच्या मुदतीवर घेऊ का? |
| `status-wages-<voice>.ogg` | ७ तारखेला पगार देता येईल का? |
| `buyer-late-<voice>.ogg` | जर बायर A ने एक महिना उशिरा पैसे दिले तर काय होईल? |
| `payment-received-<voice>.ogg` | बायर A ने आज ८ लाख दिले. |

Save them to `docs/demo/audio/` (export from WhatsApp: open the chat → long-press the voice note → share/save). Add `docs/demo/audio/README.md` listing each file, the speaker as "voice 1/2/3" (no names), and what was said. Use only voices of people who agreed.

**4b. Marathi check.** Person A writes the bot's Marathi reply templates in `whatsapp/reply.py` (branch `channel`). Ask a native Marathi speaker to read them, and write corrections into `docs/demo/marathi-review.md` as *original · corrected · why*. Don't edit Person A's code yourself. If the templates aren't pushed yet, review these English meanings for tone and natural phrasing instead:

- *"Week of 14 Dec: 49% chance of running short (advance tax + GST). Fix: discount Buyer A's invoice on TReDS and use ₹4 L more overdraft for 3 weeks. Cost ₹9,000; risk falls to 4%."*
- *"New order, ₹12 lakh, 90 days. Is that right?"*

**4c. Video storyboard**, `docs/demo/storyboard.md`. A 3-minute video following build plan §4, one row per shot:

| Time | What's on screen | What we say (voice-over) | Caption text | Who records |
|---|---|---|---|---|

Rules:

- **Leave every number as `<engine>`.** The real numbers come from the engine at recording time, never from the script.
- Start with the problem (₹7.34 lakh crore of delayed MSME payments [P, GAME–FISME–C2FO Delayed Payments Report 3.0, Nov 2025; figure as of Mar 2024]).
- Show the phone and the dashboard side by side for the hero moment.
- End with the "not financial or legal advice · synthetic data" note.

**Done when:**

- [ ] At least 2 voices × 4 sentences of audio are saved, with the README.
- [ ] The Marathi review has at least one round of corrections (or a signed-off "no changes needed").
- [ ] The storyboard adds up to ≤ 3:00, and every number in it is `<engine>`.

---

### Task 5: README draft (writing)

**Why:** the final submission needs a README with setup, dependencies, technical decisions, known limitations and an AI-use disclosure. Missing acknowledgements can count as presenting others' work as ours.

**Deliverable:** `docs/planning/readme-draft.md`, proposed text for three README sections. Sankalp pastes it in.

1. **Acknowledgements:** every external dependency, API and dataset, with its licence or terms and a link. Check each project's own page for the licence. At minimum:
   - Python libraries: look at `whatsapp/requirements.txt`, `ui/requirements.txt` and anything the engine imports (`engine/*.py`, `import` lines);
   - Sarvam (speech-to-text);
   - WhatsApp providers (Twilio Sandbox, Meta Cloud API, Evolution API);
   - Streamlit / Altair;
   - IBM's "Accounts Receivable / Finance Factoring" sample dataset (Person B is tracking down its source);
   - the GAME–FISME–C2FO report and other sources quoted on slides.
2. **Use of AI tools:** what each teammate used AI for (ask each person), and the line "the team reviewed all generated code and can explain it".
3. **Known limitations:** honest bullets. All data is synthetic. The persona isn't validated beyond your calls. Legal rules are simplified (list which). Forecasts aren't checked against real businesses. Evolution API uses an unofficial WhatsApp protocol. Anything still unfinished at H46.

**Done when:**

- [ ] Every library in every `requirements.txt` and every engine `import` appears in Acknowledgements with a licence.
- [ ] Every teammate has confirmed their AI-use line.

---

### Task 6: Jury rehearsal partner (later, around H40)

Play the jury. Use the questions in build plan §11 (top five first), plus one you make up from your research. Time each answer: **20 seconds maximum**. In `docs/planning/rehearsal-notes.md`, write down every answer that was too long, wrong or hesitant, and who gave it.

**Done when:** every §11 question has been asked at least once, and the notes list what to fix.

---

## 4. Hand-in

1. Push branch `research` with everything under `docs/planning/` and `docs/demo/`.
2. Message Sankalp three lines:
   - which tasks are done;
   - the **"Changes for the engine"** list from task 1;
   - the single most surprising thing from the calls.
3. If you're stuck for more than 15 minutes on any one fact, tag it [U], note what you tried, and move on.

## 5. How Sankalp will check it

| Deliverable | Check | Passes if |
|---|---|---|
| `domain-assumptions.md` | Open 3 random links | Each link supports the stated value and has a date and tag |
| `domain-assumptions.md` | Read "Changes for the engine" | Present, specific, matches the table |
| `user-validation.md` | Read it | Consent recorded; ≥ 1 call; surprises listed |
| Ledger parameters | Read it | Ranges with a basis for every row |
| `docs/demo/audio/` | Play 2 clips | Clear speech, sentence matches the README |
| `storyboard.md` | Sum the times; search for digits | ≤ 3:00; numbers are `<engine>` (except the sourced ₹7.34 lakh crore) |
| `readme-draft.md` | Compare with the `requirements.txt` files | Every dependency acknowledged |
