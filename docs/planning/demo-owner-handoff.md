# Handoff: demo owner

> 25 Oct 2026. The video round is cancelled, so the live demo in front of the jury is everything. **Your job is to make sure it works first time, and that every number we say is true.** You don't write code. You test, write things down, and send bugs to the right person.

## Who does what

| Person | Owns | Send them |
|---|---|---|
| Sankalp | WhatsApp bot, engine (all numbers) | WhatsApp bugs, any wrong number |
| Deploy person | The hosted app, Docker | "site down", slow loads, deploy errors |
| UI person | The web page (Owner / CA / Story views) | layout bugs, confusing text, broken buttons |
| **You** | The demo runbook, testing, the number audit, jury drill | — |

## Rules

1. **Don't edit code or other people's files.** Your files go in `docs/demo/` (create it). Work on branch `demo`, push it, and tell Sankalp.
2. **Numbers come from the engine on the day.** If the engine and a slide disagree, the engine wins and the slide is a bug. Never fix a number by guessing.
3. **All data is synthetic.** Say so in the demo, and never use a real customer's data.
4. **Voices:** only record people who agreed. Don't write their names in the repo ("voice 1", "voice 2").
5. **Report a bug in this format** so the owner can fix it without asking you anything:
   ```
   What I did: …   (exact message, button, URL)
   What I expected: …
   What happened: …   (screenshot attached)
   When / where: time, deployed URL or localhost, browser
   ```

## Read first (20 min)

- [round2-rehearsal.md](round2-rehearsal.md): the current demo script (§2), plan B, the numbers from the last engine run (§1), and 10 jury answers (§3). **Your runbook builds on this; don't start from scratch.**
- [round2-done-next.md](round2-done-next.md): what's built and what isn't.
- [engine-how-it-works.md](engine-how-it-works.md): skim only, so you can answer "how does it work?".

**Run it locally:** from the repo root, `docker compose up --build` (or `python3 ui/server.py`), then open http://localhost:8000. The deploy person will give you the hosted URL.

---

## Task 1: Demo runbook (first, ~1.5 h)

**Deliverable:** `docs/demo/runbook.md`. Someone who has never seen the app should be able to run the demo from this file alone.

It must have:

1. **Setup checklist (T−30 min):**
   - laptop charged plus charger;
   - phone hotspot as a backup network;
   - browser zoom set so the projector shows the numbers;
   - microphone allowed in Chrome;
   - WhatsApp open on the demo phone;
   - the hero question run once to warm up (the first answer is slow, ~7.5 s);
   - notifications off.
2. **The click path:** every step, in order, with the exact thing to type or say. Use the four questions from rehearsal §1: the Marathi hero order, "Buyer A pays a month late", "spend 2 lakh in 15 days", and the status check. Do it on both the web UI and WhatsApp.
3. **Expected numbers at each step:** re-run each question on the day and write what the engine shows, e.g. "worst week 9 Nov, 51%". If they differ from rehearsal §1, tell Sankalp; the engine may have changed.
4. **What to say at each step:** take it from rehearsal §2, trimmed to whatever time limit the organisers announce.
5. **Plan B for each failure:**

   | If this fails | Do this |
   |---|---|
   | Hosted site down | localhost via Docker on the backup laptop |
   | WhatsApp bot doesn't reply | do the same question on the web UI |
   | Mic or speech-to-text wrong | type it, or use "Or build it by hand" |
   | Network down | local app; the engine works offline, only the summary text degrades |

6. **Timing:** minutes per section, and the total.

**Done when:** a teammate who hasn't seen the app runs the whole demo from the runbook alone, and you write down where they got stuck.

## Task 2: WhatsApp test partner for Sankalp (when he's ready, ~1 h, repeat after each fix)

**2a. Test inputs.** Record each sentence as a WhatsApp voice note, in 2–3 voices, and also send it as typed text:

| # | Sentence | Expected |
|---|---|---|
| 1 | बजाजची १२ लाखांची ऑर्डर ९० दिवसांच्या मुदतीवर घेऊ का? | new order, Bajaj, ₹12,00,000, 90 days |
| 2 | ७ तारखेला पगार देता येईल का? | status check |
| 3 | जर बायर A ने एक महिना उशिरा पैसे दिले तर काय होईल? | Buyer A, 30 days late |
| 4 | पुढच्या १५ दिवसांत २ लाख खर्च करू शकतो का? | expense, ₹2,00,000 |
| 5 | Same as 1, in Hindi and in English | same as 1 |
| 6 | Something unclear, e.g. "what if he pays late?" | bot asks **one** follow-up question |
| 7 | Say "नाही" (no) at the read-back | bot asks again, doesn't run |

**2b. Log every message** in `docs/demo/whatsapp-test-log.md`:

| Time | Voice / text | Exact message sent | Bot's read-back | Bot's answer | Matches the web UI? | Pass / fail | Note |
|---|---|---|---|---|---|---|---|

A pass means three things: the read-back shows the right party, amount and days; the answer's numbers match the web UI for the same question; and the reply arrives in under ~15 s.

**Done when:** every row passes twice in a row, or each failure has been sent to Sankalp in the bug format.

## Task 3: Smoke test every 2 hours (~15 min each)

Run the click path from your runbook on **the hosted URL** and on **localhost**. Keep a running file, `docs/demo/bugs.md`:

| # | Found | Where | Bug (one line) | Owner | Severity | Status |
|---|---|---|---|---|---|---|

Severity levels:
- **blocker:** the demo can't continue;
- **visible:** the jury would notice;
- **minor.**

Chase blockers in person, not just on chat.

**Done when:** the last two runs before the final have no blockers.

## Task 4: Number audit (~45 min)

Check every number in these files:
- `docs/planning/round2-slides.html`;
- `docs/planning/round2-pitch-script.md` (ask Sankalp for it if it isn't pushed yet);
- the rehearsal pack;
- the README.

Every number must either match today's engine output or carry a source tag ([P] / [S]). Write `docs/demo/number-audit.md`:

| File | Line / slide | Number as written | Today's engine value or source | OK / fix |
|---|---|---|---|---|

Known traps to check:
- **Overdraft limit:** the old plan says ₹25 L; the engine now uses ₹42 L.
- **The "₹4.2 L advance":** it comes from the summary text code, not the engine. Make sure it matches 30% of the invoice including GST.
- **"Wages fail":** the 51% answer is about *a payment* failing (bar stock and power), not wages. Say "a payment".
- **Turnover:** the persona says ₹4.2 cr; the engine is ~₹2.9 cr.
- **Any claim that Tally or Zoho "can't forecast":** both can. Cut it.
- **Any slide implying we already recommend fixes:** we don't yet.

**Done when:** every row is OK or has been sent to its owner.

## Task 5: Jury drill (last, ~45 min, with the whole team)

Use rehearsal §3 plus these three, which the teammates' research made likely:

- **"Doesn't TallyPrime already do cash-flow projection?"** Answer: "Yes. Tally projects one balance with a fixed overdraft limit. We show the range of outcomes, which week, why, and how many days each buyer can be late, and our overdraft limit shrinks as invoices age."
- **"Where are the recommended fixes?"** Answer honestly with whatever is true on the day.
- **"Have you talked to any real owners?"** Answer honestly.

Ask each person 3–4 questions with a timer: 20 seconds per answer. In `docs/demo/drill-notes.md`, write every answer that was too long, wrong or hesitant, and who gave it. Then re-drill only those.

**Done when:** every question has been answered by at least one person in under 20 seconds, correctly.

---

## Order and timing

| When | What |
|---|---|
| Now | Read (20 min) → runbook draft (Task 1) |
| As soon as Sankalp says the bot is up | Task 2, then again after each fix |
| Every 2 hours | Task 3 smoke test |
| Between smoke tests | Task 4 number audit |
| Last 2 hours before the final | Task 5 drill, final smoke test, update the runbook numbers |

## Hand-in

Push branch `demo`. Send Sankalp three lines:
1. Is the runbook done, and did the dry run pass?
2. Open blockers, with owners.
3. The numbers that changed since rehearsal §1.
