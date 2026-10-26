# Round 2 rehearsal pack: Kab Tak? (F-03)

Companions: [done / next sheet](round2-done-next.md) (what is built and not built) and [how the engine works](engine-how-it-works.md) (algorithms and assumptions).
Every number below came from the engine on 25 Oct 2026 (seed 0, 1,000 paths, 90 days) or is marked [P] in `f03-build-plan.md`. Re-run if the ledger or engine changes.

> **Updated 26 Oct.** The §1 numbers were re-run on the pinned demo business (`mahesh-cnc`, "today" = 25 Oct) and still match. The demo now also runs through the website sign-up and WhatsApp: see [multi-tenant-demo.md](multi-tenant-demo.md). The bug list in §1 is from 25 Oct and was not re-checked. WhatsApp is merged and deployed, not "a stretch" (Q5 below). Fix search is still not built: say so before a judge asks.

---

## 1. Smoke test of the demo path (API run, localhost:8000, 25 Oct 2026)

Calls were spaced ~10 s apart. Timings are wall-clock for one call.

| | Question | Parsed as | Parse | Answer | Explain |
|---|---|---|---|---|---|
| a | Marathi hero: बजाजची १२ लाखांची ऑर्डर ९० दिवसांच्या मुदतीवर घेऊ का? | `new_order`, Bajaj, ₹12,00,000, 90 days, lang mr | 1.2–3.5 s | 1.9 s (7.5 s on a cold first run) | 1.9 s |
| b | What if Buyer A pays a month late? | `delay_payment`, Buyer A, 30 days, en | 1.2 s | 0.1 s | 2.2 s |
| c | Can I spend 2 lakh in the next 15 days? | `expense_shock`, ₹2,00,000 on 9 Nov, en | 1.3 s | 0.0 s | 2.7 s |
| d | Status check ("how are we doing") | `status` | n/a | 0.0 s | 2.4 s |

Speech-to-text (macOS text-to-speech clip, English): 2.3 s, correct. Whole hero path by voice is about 5–8 s of waiting, not counting the owner's confirm tap.

### Key numbers

Today card (same in every case): bank ₹4.0 L; overdraft limit ₹42 L, drawn ₹23.8 L; drawing power ₹29.1 L, so headroom ₹5.3 L; owed by buyers ₹47.1 L, of which ₹26.4 L is older than 45 days. Persona note: the old plan said ₹25 L limit; the engine uses ₹42 L (see `engine/ledger.py` docstring).

| | Overall chance of any shortfall (90 days) | Worst week | Chance in worst week | Weeks with risk |
|---|---|---|---|---|
| d Status | 34 of 1,000 paths (3.4%) | week of 9 Nov (power 10 Nov, bar stock 14 Nov) | 2% | 9 Nov 2%, 14 Dec 2% |
| a Hero order | 536 of 1,000 (53.6%) | week of 9 Nov | 51% | 2 Nov 14%, 9 Nov 51%, 16 Nov 2% |
| b Buyer A +30 days | 440 of 1,000 (44%) | week of 9 Nov | 28% | 9 Nov 28%, 7 Dec 7%, 14 Dec 25% |
| c Spend ₹2 L | 143 of 1,000 (14.3%) | week of 9 Nov | 10% | 9 Nov 10%, 14 Dec 7% |

**Kab tak** (longest delay that keeps risk within the 5% target):
- Status, (b) and (c) (all share the no-order baseline): Buyer A 3 days, Buyer B 11 days, CPSE 11 days.
- Hero case (with the order added): Buyer A 2 days, Buyer B 11 days, CPSE 3 days.

**Order answer (hero):** margin on the order ₹1.08 L; longest safe payment terms **0 days** (the cash gap happens before the invoice, so shorter terms alone can't fix it); smallest safe advance **30%** (the summary says ₹4.2 L: that is 30% of the invoice including 18% GST, computed in `ui/llm.py`, not the engine).

**Kab tak curves** (chance of a shortfall by extra days late, 0 / 5 / 10 / 15 / 20 / 25 / 30), status case:
- Buyer A: 3.4% → 5.9% → 11.7% → 19.6% → 34.1% → 38.2% → 44.0%
- Buyer B: 3.4% → 4.4% → 5.0% → 6.6% → 16.9% → 17.6% → 18.5%
- CPSE: 3.4% → 4.3% → 4.6% → 5.7% → 7.5% → 9.6% → 12.8%

### Summaries the owner sees

- (a) Marathi: "बजाजची १२ लाखांची ऑर्डर ९० दिवसांच्या मुदतीवर घेणे सध्या योग्य नाही… सर्वात धोकादायक आठवड्यात पैसे कमी होण्याची शक्यता ५१% आहे, जी ५% मर्यादेपेक्षा खूप जास्त आहे. … किमान ४.२ लाखांची आगाऊ रक्कम मागावी, जी ३०% किमान आगाऊ टक्केवारीशी जुळते." Verdict "no, not as things stand" because 51% is above 50%.
- (b) "…you will likely run short because you only have three days of leeway… the chance of running short in the riskiest week is 28%, far above the 5% limit…"
- (c) "Yes, you can spend ₹2 L in the next 15 days, but the chance of running short in the riskiest week is 10%, which is above the acceptable limit of 5%…"
- (d) "Yes, you are safe and the risk is within the acceptable limit… 2% chance of running short in the week that starts 9 Nov… overdue ₹26 L…"

### Not tested

- **The mic.** There is no real microphone in this session. The recording path (`ui/app.js`, `/api/transcribe`) was tested only with a synthetic audio clip. Marathi and Kannada speech-to-text were not tested at all; there is no Marathi voice on this Mac.
- The UI visually (the browser pane was declined). All results are from the API, which is what the UI calls.

### 3-step mic check for you (2 minutes, do it before the jury)

1. Restart the server so it uses the current code (`python3 ui/server.py` from the repo root, or `docker compose up --build`), open http://localhost:8000 in Chrome and allow the microphone when asked.
2. Press **Speak**, say the hero sentence in Marathi at normal pace, press **Stop**. Check that the box shows बजाज / १२ लाख / ९० दिवस correctly and that the read-back shows Bajaj, ₹12,00,000, 90 days.
3. Say it once more in a noisier setting, and once in English. If the Marathi comes out wrong twice, plan to type it or use "Or build it by hand" (see section 2, plan B).

### Bugs and rough edges (not fixed, per the brief)

1. **Status summary says "you … have used the full overdraft".** The engine shows ₹5.3 L headroom left. Repro: open the app (status check) or `GET /api/result`, then `POST /api/explain` with that result, `lang: "en"`. Cause is probably the prompt line "the forecast already assumes the owner uses all the overdraft left". Don't read this sentence aloud; fix `EXPLAIN_PROMPT` if you can.
2. **Summaries suggest fixes the engine didn't produce.** (b) says "postpone non-essential bills such as the power bill on 10 Nov or the bar-stock bill on 14 Nov". That is the LLM improvising: `fixes` is empty. The number check only inspects digits, so this passes. Repro: parse and answer "What if Buyer A pays a month late?", then explain.
3. **(c) opens "Yes, you can spend ₹2 L" while giving 10%, above the 5% limit.** Matches the graded verdict ("yes, but tight") but the flat "Yes" will sound wrong to a jury. Say it as "yes, but tight".
4. **Worst week is not a wage week.** Wages are on the 7th. In every case the worst week is 9 Nov (power and bar stock), and the wage week (2 Nov) only shows 14% in the hero case. Don't say "wages fail" for the 51%; say "a payment fails".
5. **Two risk numbers can confuse.** "Overall" (53.6%) and "worst week" (51%) are different. The UI and summaries quote the worst week. Pick one when you speak.
6. **English speech-to-text slip** on the synthetic clip: "Bajaj S12 lakh". The confirm step exists exactly for this; use it on stage.
7. **The party name doesn't matter for an order's payment slip.** Any name (e.g. Bajaj) is modelled with Buyer B's delay curve for its balance slip. If asked: "a new buyer has no history, so we borrow our most reliable payer's behaviour".
8. Doc mismatch: `f03-build-plan.md` says Sarvam speech-to-text, a ₹25 L overdraft and a hazard model. The code uses scribe-v2 via OpenRouter, ₹42 L and Kaplan–Meier. Don't quote the plan's tech list.

---

## 2. Demo script (about 3.5 minutes, spoken)

Use only these numbers. Words in brackets are actions.

**Hook (0:00–0:25).** "₹7.34 lakh crore is owed to Indian MSMEs in late payments [P: GAME–FISME–C2FO, Nov 2025, figure as of March 2024]. Meet Mahesh, who runs a 14-person CNC shop in Pune. His books look fine, but he has ₹26 lakh older than 45 days, ₹4 lakh in the bank, and a wage run every month. His question every week is: can I pay, and can I take this order? Everything you will see is synthetic data, labelled so."

**Today view (0:25–0:55).** [Open the Owner view.] "Today: ₹4 lakh in the bank, buyers owe him ₹47 lakh, and he has ₹5 lakh of overdraft room left. We simulated 1,000 possible next 90 days. On a normal day, the chance he can't pay something is 3.4%. The week of 9 November is the tightest, at 2%."

**Hero question by voice (0:55–1:50).** [Press Speak.] Say in Marathi: "बजाजची १२ लाखांची ऑर्डर ९० दिवसांच्या मुदतीवर घेऊ का?" [Show the read-back: Bajaj, ₹12,00,000, 90 days; confirm.] "The system reads back what it heard, so a wrong amount is caught before anything runs. Then the answer: the chance of a shortfall in the worst week, 9 November, jumps from 2% to 51%. Why? The bar stock for the order is paid up front, GST is due on the 20th of the next month, and Bajaj pays 90 days after invoicing. The money goes out before it comes in. The answer: even on very short terms it isn't safe without an advance. He needs at least 30% advance, about ₹4.2 lakh, on a ₹1.08 lakh margin order." [Be straight:] "What we do not do yet is propose the full set of fixes. That is our next build."

**CA view (1:50–2:40).** [Switch to the CA view.] "For his accountant: the fan chart is the spread of the 1,000 futures; P10, median, P90. Weekly risk shows 2 November at 14% and 9 November at 51% once the order is added. And the kab tak curves answer 'how late can each buyer be?' With the order, Buyer A can be only 2 days late, CPSE 3 days, Buyer B 11 days, before the risk rises by 5 points. Without the order, Buyer A can be 3 days late and the other two 11. At 30 days late, Buyer A takes the chance of any shortfall from 3.4% to 44%."

**Why trust it (2:40–3:25).** "The language model does two jobs only: it turns speech into a typed question, and it phrases the answer. Every number comes from the engine: Kaplan–Meier payment curves for each buyer, which count unpaid invoices correctly; 1,000 Monte Carlo paths where invoices from one buyer move together; the overdraft limit that shrinks as receivables pass 90 days; GST on the invoice date; TDS. A number check drops any sentence that quotes a number the engine didn't produce. It checks digits, not spelled-out numbers, and we say so. The model is checked against the payment behaviour we planted; it is not validated on real data yet."

**Close (3:25–3:40).** "Next: the fix search, so Mahesh sees not just 'no' but 'here is the cheapest way to make it yes.'"

### Plan B

- **Network or Groq down, or the mic fails:** open **"Or build it by hand"** in the ask panel. Choose "New order", party Bajaj, amount 12,00,000, terms 90 days, run. The engine and charts work with no network, since they are local; only the plain-language summary falls back to a one-line template sentence ("The riskiest week starts 9 Nov: a 51% chance of running short (limit 5%)").
- **Speech misheard:** correct it at the read-back box, or type the sentence.
- **Whole app down:** `docker compose up --build` on the other laptop, or show the Story view and the screenshots.
- Pre-warm: run the hero once before going in (the cold first answer takes about 7.5 s).

---

## 3. Likely jury questions (about 20 seconds each)

1. **Isn't this a GPT wrapper?** "No. The model only turns speech into a typed scenario and phrases the result. The decisions come from a simulator: survival curves per buyer, 1,000 Monte Carlo paths, drawing-power rules, GST and TDS. In a public benchmark, EnterpriseArena, only about 15% of LLM-agent trials kept a simulated firm alive [P], which is why we don't let the model decide. A check drops any sentence quoting a number the engine didn't produce."
2. **Is the data real?** "No, it is a synthetic ledger and labelled synthetic everywhere. We planted realistic behaviour: Buyer A slips at quarter-end, CPSE has a long tail, GST on accrual, a disputed invoice. The model recovers those planted medians within about 15%. Real data would be the owner's own invoices in our Excel layout (there is no Tally import); we haven't tested with real businesses and have not yet talked to real owners."
3. **How accurate is it?** "We don't promise a date; we give a range. What we can say today is narrow: the fast vectorised simulator matches a plain day-by-day loop to within ₹1, and the fitted payment curves match what we planted. We have not validated against real or external data, so we make no accuracy claim beyond that. That is on our next-steps list."
4. **Why not just use the overdraft?** "The forecast already assumes he uses all the overdraft room. And the limit isn't flat: we assume banks drop receivables older than 90 days from drawing power [assumption, to verify], so a late buyer delays cash and shrinks the limit at once. For Mahesh, ₹5 lakh is left, and one late buyer can burn through that."
5. **What's next?** "The fix search: greedy search over fixes, scored on the same 1,000 paths, covering deferring a payment, asking for an advance, changing terms. Then wiring it into the dashboard and the WhatsApp reply. WhatsApp itself is already live: the bot runs on Evolution API on our VM, links a number on its first message, and answers text and voice in English. Replies in Hindi and Marathi, and a login for the dashboard, come after."
6. **Business model?** "A CA-led channel, since one CA serves dozens of small businesses; or a referral fee from invoice-discounting platforms and lenders; or a white-label for a bank's MSME overdraft customers. These are hypotheses we haven't tested with customers yet."
7. **How is this different from Xero or QuickBooks?** "Those forecast from predicted payment dates. We model each buyer's lateness as a distribution, move one buyer's invoices together, and answer decision questions: how many days late can each buyer be, and what terms can I accept. The prescribing part, ranking fixes, is our next build, so today we are a better question-answerer, not yet a full advisor." (Don't quote their feature claims as fact; plan marks them [S].)
8. **Why Kaplan–Meier and Monte Carlo?** "Unpaid invoices are censored: not paid *yet* is information. A plain average of paid delays flatters slow payers. Kaplan–Meier uses them correctly. Monte Carlo then gives a probability for each week, not one date; invoices from the same buyer share a shock so the range isn't too narrow."
9. **What does the LLM do wrong?** "It can phrase things loosely. Our number check drops any sentence with an unproduced number, but it checks digits only. We found it occasionally suggesting actions the engine didn't compute, like postponing bills. The next step makes fixes engine-produced so the model doesn't improvise."
10. **Is it financial or legal advice?** "No. It computes and compares options; the owner decides. We show that note on screen and never say 'guaranteed'."

---

## 4. Report back

**File:** `docs/planning/round2-rehearsal.md` (this file); companions `docs/planning/round2-done-next.md` and `docs/planning/engine-how-it-works.md`. Nothing committed for this file or the done/next sheet.

**Top 3 to rehearse**
1. The hero by voice in Marathi, end to end, including the confirm step and the switch to "Or build it by hand" if the mic or network fails. Run the mic check above first.
2. The honest line on the 51% answer: "a payment fails" (not "wages fail"), the 30% advance, and "we don't propose fixes yet; that is next". Say it before a judge asks.
3. The honesty answers: synthetic data, not validated on real data, assumptions not fitted (correlation 0.6, 90-day drawing-power rule), and that the number check covers digits only.

**Bugs:** see section 1 (items 1–3 matter most: "used the full overdraft", improvised fixes, and the flat "Yes" at 10%).
