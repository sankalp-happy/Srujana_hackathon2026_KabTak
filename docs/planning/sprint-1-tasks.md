# Sprint 1 (3 hours): engine, channel, UI

> 25 Oct 2026. Scope comes from [f03-build-plan.md](f03-build-plan.md) v0.4. **Engine and all maths: Sankalp. Channel: Person A. UI and data: Person B.** Each section below is self-contained, so you can paste it to that person.

**Goal at 3:00:** a typed or spoken question gets a confirmed `Scenario`. The engine (or the shared fixture, if the engine isn't merged yet) turns it into a result. That result shows up as a Marathi reply on the phone and as four panels in the UI.

---

## 0. Before anyone starts (Sankalp, 10 min)

1. Commit and push `whatsapp/`, `fixtures/engine_result.json` and this file, so A and B can pull.
2. A works on branch `channel`, B on branch `ui`. Sankalp merges both at 3:00.

## 1. Ground rules (everyone)

- **Ownership:** only edit your own folders (table below). Need something changed elsewhere? Ask the owner.
- **Contracts are frozen this sprint.** The two JSON shapes in §2 and the file `fixtures/engine_result.json` change only through Sankalp.
- **Run everything from the repo root.**
- **No secrets in git.** Keys go in `.env` (already git-ignored); add the variable names to `whatsapp/.env.example`.
- **The LLM never produces a number** that the engine didn't compute. It only extracts what the owner said.
- **AI disclosure:** list your AI-assisted files in your branch's last commit message, and be ready to explain every line (event rules §4.7).
- **Placeholder data:** everything in the fixture is synthetic. Fixture buyers use neutral names ("Buyer A", "CPSE"). Sankalp decides before the video whether the demo uses real brand names.

| Path | Owner |
|---|---|
| `engine/`, `data/synthetic/` | Sankalp |
| `whatsapp/` | Person A |
| `ui/`, `data/README.md`, `data/raw/` (git-ignored), `tests/legal_cases.csv` | Person B |
| `fixtures/engine_result.json` | shared, frozen |

---

## 2. Contracts

### 2.1 `Scenario`: Person A produces it, the engine consumes it

```json
{
  "type": "new_order",
  "party": "New buyer",
  "amount_inr": 1200000,
  "days": 90,
  "pct": null,
  "date": null,
  "obligation": null,
  "transcript": "नवीन बायरची १२ लाखांची ऑर्डर ९० दिवसांच्या मुदतीवर घेऊ का?",
  "needs_clarification": false,
  "question": null
}
```

| `type` | Required fields | Meaning of `days` | Example question |
|---|---|---|---|
| `status` | none | — | "Can I pay wages on the 7th?" |
| `new_order` | `party`, `amount_inr`, `days` | payment terms offered | "Should I take Bajaj's ₹12 L order on 90-day terms?" |
| `delay_payment` | `party`, `days` | extra days late | "What if Buyer A pays a month late?" |
| `expense_shock` | `amount_inr`, `date` | — | "The spindle motor needs ₹2 L next week" |
| `sales_drop` | `pct`, `days` | how long the drop lasts | "What if sales fall 20% for two months?" |
| `supplier_terms` | `party`, `days` | new supplier terms | "The steel supplier wants payment in 15 days" |
| `schedule_change` | `obligation` (`wages`, `emi`, `gst` or `rent`), `date` | — | "Can I move the EMI to the 15th?" |
| `payment_received` | `party`, `amount_inr`, `date` | — | "Buyer A paid 8 lakh today" |

- **Units:** `amount_inr` is an integer in rupees (₹12 L becomes `1200000`); `pct` runs 0–100; dates are `YYYY-MM-DD`.
- **Unused fields** are `null`.
- **Missing information:** if a required field is missing or the request is unclear, set `needs_clarification: true` and put exactly **one** follow-up question in `question`, in the owner's language.

### 2.2 `EngineResult`: the engine produces it, A and B consume it

Interface: `from engine.answer import answer` then `answer(scenario: dict) -> dict`. It raises `ValueError(message)` on bad input, such as an unknown party.

The full example is [`fixtures/engine_result.json`](../../fixtures/engine_result.json). **Its numbers are placeholders** (`"placeholder": true`), but the shape is the contract.

| Key | What it holds |
|---|---|
| `as_of`, `synthetic`, `placeholder`, `risk_target` | metadata; `risk_target` 0.05 = 5% shortfall chance |
| `scenario` | echo of the input `Scenario` |
| `today` | `bank_inr`, `od_limit_inr`, `od_drawn_inr`, `drawing_power_inr`, `headroom_inr`, `receivable_inr`, `overdue_45_inr` |
| `fan` | `dates`, `p10`, `p50`, `p90` (90 days each). The values are **available liquidity = bank + undrawn drawing power**; below 0 means a payment can't be made |
| `obligations` | `[{date, label, amount_inr}]`: wages, EMI, GST, advance tax… |
| `weeks` | 13 × `{week_start (Monday), p_shortfall, expected_shortfall_inr}` |
| `worst_week` | `{week_start, p_shortfall, obligation}` |
| `kab_tak` | `[{buyer, max_delay_days}]`: how late each buyer can pay before a shortfall |
| `order` | `{party, amount_inr, terms_days, max_safe_terms_days, min_advance_pct, margin_inr}`, or `null` if the scenario has no order |
| `fixes` | `[{id, kind, label, cost_inr, p_shortfall_after, available_now, why}]`; `kind` is one of `treds`, `overdraft`, `supplier_deferral`, `msmed_headsup`, `order_terms`. **May be `[]`** |
| `plan` | `{fix_ids, total_cost_inr, p_shortfall_before, p_shortfall_after}`, **or `null`** |
| `assumptions` | `[{name, value}]`, shown so the owner can see and challenge them |

Probabilities run 0–1. Money is integer rupees.

---

## 3. Sankalp: engine (all maths)

Order matters: E5 is what unblocks A and B at integration, so a thin E5 beats a perfect E3.

| # | Deliverable | Done when |
|---|---|---|
| E1 | `engine/ledger.py`: 24-month synthetic ledger per build plan §6 (fixed seed) → `data/synthetic/invoices.csv` and `obligations.csv` | `python -m engine.ledger` asserts receivable ≈ ₹46 L (±5%) and >45-day ≈ ₹27 L (±10%), i.e. the §6 reconciliation is done |
| E2 | `engine/arrival.py`: per-buyer arrival sampler for open invoices, conditional on age (Kaplan–Meier first; logistic hazard if time) | Sampled median delay per buyer is close to the planted one |
| E3 | `engine/simulate.py`: 1,000 × 90 liquidity paths with shared buyer shock, drawing power (receivables >90 days drop out), GST on accrual, TDS | Self-check: with zero variance the path equals the deterministic schedule; the shared shock widens the weekly-inflow P10–P90 compared with independent invoices |
| E4 | `engine/decide.py`: `kab_tak` bisection per buyer; `max_safe_terms_days` / `min_advance_pct` for `new_order` | Self-check: a shorter delay is never riskier than a longer one (monotone) |
| E5 | `engine/answer.py`: `answer(scenario) -> dict` in the §2.2 shape. Return `fixes: []` and `plan: null` until the greedy search exists (next sprint) | The key-match check in §6 passes |

---

## 4. Person A: WhatsApp channel and scenario parsing

**You own `whatsapp/`.** It already has a working webhook for Twilio Sandbox and Meta Cloud API (`whatsapp/app.py`; `handle()` is the stub to replace). Run it from the repo root: `uvicorn whatsapp.app:app --port 8000`. Update the docstring and imports for that (`from whatsapp.scenario import …`), and keep `python -m whatsapp.app` printing `ok`.

**Until the engine is merged**, use the fixture:
```python
try:
    from engine.answer import answer as engine_answer
except ImportError:  # engine not merged yet
    engine_answer = lambda s: json.load(open("fixtures/engine_result.json"))
```

| # | Time | Deliverable | Acceptance |
|---|---|---|---|
| A1 | 0:00–1:15 | `whatsapp/scenario.py`: `parse_scenario(text: str) -> dict`, returning the §2.1 shape. Use a Pydantic model with your LLM's structured/JSON-schema output at temperature 0 (any provider the team has a key for). The prompt says: extract only, never calculate; convert लाख/crore and Devanagari digits to rupees; if a required field is missing, ask one question | Output always validates against the model, and every type in the §2.1 table is reachable |
| A2 | (with A1) | `whatsapp/scenario_cases.json` + `whatsapp/eval_scenarios.py`: **at least 14 cases**. Cover every type at least once; at least 4 in Marathi (including Devanagari digits and "लाख"), 3 in Hindi and 3 in English; plus **2 ambiguous** cases (e.g. "double the last order", "what if he pays late?"). Each case is `{"text", "lang", "expect": {…fields to check…}}` | `python -m whatsapp.eval_scenarios` prints PASS/FAIL per case and a total. Pass mark: **≥ 12/14**, and both ambiguous cases set `needs_clarification` with exactly one question |
| A3 | 1:15–2:00 | **Confirm step** in `handle()`. Parse, then read the scenario back in Marathi ("New order, New buyer, ₹12 L, 90 days. Correct?"). Then: "हो / होय / हां / yes / ok" → call `engine_answer` and reply; "नाही / no" → ask again; `needs_clarification` → send the one question. Keep pending scenarios in a dict keyed by sender (fine for the demo). Catch `ValueError` from the engine and reply with its message | `python -m whatsapp.app` self-check covers: parse → read-back → yes → reply, and no → re-ask |
| A4 | 2:00–2:40 | **Voice:** `transcribe(audio: bytes) -> str` with Sarvam speech-to-text (Saaras, Marathi `mr-IN`; check Sarvam's docs for the endpoint). WhatsApp voice notes are OGG/Opus; if Sarvam rejects them, convert to 16 kHz mono WAV with ffmpeg. Wire it into `handle()` before `parse_scenario` | The hero sentence ("…१२ लाखांची ऑर्डर ९० दिवसांच्या मुदतीवर घेऊ का?") recorded 3 times gives the right amount and terms 3/3 times. Note the transcripts in your commit message |
| A5 | 2:40–3:00 | `whatsapp/reply.py`: `format_reply(result: dict) -> str`. At most 2 lines in Marathi, Latin digits, rupees in lakh (₹4 L) or with Indian grouping (₹9,000). **Every number comes from `result`.** From the fixture it should say something like: "Week of 14 Dec: 49% chance of running short (advance tax + GST). Fix: discount Buyer A's INV-2041 on TReDS and run ₹4 L more overdraft for 3 weeks. Cost ₹9,000; risk falls to 4%." When `plan` is `null`, report only the risk and the worst week. Have a Marathi speaker read the templates once | Self-check: change `worst_week.p_shortfall` in a copy of the fixture to 0.77 and "77%" appears in the reply; set `plan` to `null` and it still works |

**Hand-in at 3:00:** push branch `channel`. Send Sankalp a screen recording from a real phone: voice note → read-back → "हो" → reply.

---

## 5. Person B: UI and external data

**You own `ui/`, `data/README.md` and `data/raw/`** (git-ignored). Use Streamlit, with Altair for charts (Altair ships with Streamlit). If the team has already started a Next.js app, tell Sankalp before you switch.

Streamlit puts `ui/` on the import path, not the repo root. So start `ui/app.py` with:
```python
import json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
RESULT = os.environ.get("KABTAK_RESULT", "fixtures/engine_result.json")
```
Until the engine is merged, read `RESULT`. After that, call `engine.answer.answer(scenario)` when it imports (same try/except pattern as Person A).

| # | Time | Deliverable | Acceptance |
|---|---|---|---|
| B1 | 0:00–0:30 (hard stop) | **IBM receivables sample**, also called "Accounts Receivable" or "Finance Factoring: IBM Late Payment Histories" (expected: 2,466 invoices, 100 customers, 2012–13). Find a reputable public copy (Kaggle or IBM), save it as `data/raw/ibm_ar.csv` (don't commit it), and write `data/README.md` with the source URL, licence or terms, row count, column names, unique-customer count and date range. If no trustworthy copy turns up in 30 minutes, write that down and move on | The counts in `data/README.md` match the file; the source URL opens |
| B2 | 0:30–2:30 | `ui/app.py` + `ui/requirements.txt`, with these panels in this order: **(1) Today card** from `today` (bank, undrawn headroom, receivable, overdue >45 days). **(2) Fan chart**: a P10–P90 band and P50 line over `fan.dates`; a labelled zero line ("can't pay below this"); markers for `obligations`; the `worst_week` shaded and labelled with its percentage. **(3) Fixes**: a table of `fixes` (label, cost, risk after, "available now" or "set up for next time"), the chosen `plan` highlighted, and `why` in an expander. **(4) Kab tak?**: each buyer's `max_delay_days`, plus the `order` box (longest safe terms, minimum advance) when `order` isn't null. Add an **owner/CA toggle**: owner view shows only a big verdict for `worst_week` and the plan's first action; CA view shows everything plus `assumptions`. Add a **disclaimer banner**: "Computes and compares options, not financial or legal advice. Synthetic data." | `streamlit run ui/app.py` renders all four panels. Colour is never the only signal: stress weeks carry a text label |
| B3 | (with B2) | **Scenario panel** (sidebar): a `type` dropdown that shows only that type's fields (§2.1 table) and builds a `Scenario` dict. Show the dict as JSON; call the engine when it's available, otherwise keep showing the fixture | Every type in §2.1 can be built; the JSON matches §2.1 exactly |
| B4 | 2:30–3:00 | **Robustness pass** | Point `KABTAK_RESULT` at edited copies of the fixture: worst-week risk 0.95 → the verdict changes; `fixes: []` and `plan: null` → "no fixes needed" with no crash; `order: null` → the order box disappears |
| B5 | stretch | `tests/legal_cases.csv`: **30 hand-computed cases** done in a spreadsheet: 8 × s.15 due date (15 days without a written agreement, agreed days capped at 45 with one), 10 × s.16 interest (3 × Bank Rate, compounded monthly), 6 × GST credit reversal at day 180, 6 × s.37(2)(g)/43B(h) (unpaid at 31 March?). Columns: `case_id, rule, invoice_date, acceptance_date, written_agreement, agreed_days, amount_inr, paid_date, bank_rate_pct, expected, working`. State the part-month convention you used in the first row's `working` | 30 rows, each with its `working`; Sankalp spot-checks 3 by hand |

B5 is the one piece of maths handed out, on purpose: test cases written by someone other than the person who implements them catch mistakes. Skip it if Sankalp would rather keep it.

**Hand-in at 3:00:** push branch `ui`, and send screenshots of owner view, CA view and the B4 edge cases.

---

## 6. Verification checklist (Sankalp, after the sprint)

| Who | Run | Passes if |
|---|---|---|
| A | `python -m whatsapp.app` | prints `ok` |
| A | `python -m whatsapp.eval_scenarios` | ≥ 12/14, both ambiguous cases ask one question |
| A | read `whatsapp/scenario_cases.json` | every §2.1 type appears; ≥ 4 Marathi with Devanagari digits |
| A | `git grep -niE -e 'sk-[a-z0-9]{8}' -e 'key *= *.[a-z0-9]{8}' -e 'token *= *.[a-z0-9]{8}' -- whatsapp/` | no output (no keys committed) |
| A | phone recording | voice → read-back → हो → reply, all within ~15 s |
| B | `streamlit run ui/app.py` | four panels, toggle, banner, scenario panel |
| B | `grep -nE "[0-9]{4,}" ui/app.py` | no hard-coded rupee amounts or results (layout constants only) |
| B | B4 edge cases with `KABTAK_RESULT=…` | verdict changes; no crash on `[]` / `null` |
| B | `data/README.md` vs the CSV | counts match; source and terms recorded |
| E | `python -c "import json; from engine.answer import answer; a=answer({'type':'status'}); f=json.load(open('fixtures/engine_result.json')); assert set(a)==set(f), set(a)^set(f)"` | no error |

## 7. Integration at 3:00 (15 min)

1. Merge `channel` and `ui` into `main`.
2. Run the §6 checks.
3. Send "७ तारखेला पगार देता येईल का?" from a phone. Check that the reply and the UI (scenario `status`) show the same `worst_week`.
4. Anything that fails goes into the next sprint; nobody patches someone else's folder.
