# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Static HTML/CSS/JS, no npm and no build step. The dashboard (`ui/`) is served by a stdlib Python server. The landing page lives in `landing-page/`.

## Users

- **Owner** (primary): runs a micro-enterprise, such as a 14-worker CNC job shop in Pune. Works on WhatsApp in Marathi or Hindi. Each week they ask "Can I pay wages on the 7th?" and "Should I take this order?" They need one verdict and one action, not probabilities or accounting terms.
- **CA (chartered accountant)**: keeps the books (often in TallyPrime; there is no Tally import) and checks the working.
- **Judges** (Srujana 2026, problem F-03): evaluate the product.

## Product Purpose

Kab Tak? ("how long?") is predictive cash flow for micro-businesses. The owner asks a question by WhatsApp voice note in their own language. The engine simulates 1,000 possible paths for the bank balance over 90 days, flags the weeks where cash may run short and how likely that is, and says how late each buyer can pay before the risk passes the 5% limit. Recommending the cheapest set of fixes is the next build; it is not built yet.

## Positioning

Other tools give a single forecast line on a dashboard. Kab Tak? gives a range of 1,000 futures and the odds of running short, and you ask for it in Marathi on WhatsApp. The LLM only turns speech into a typed scenario; the simulator makes every number.

## Operating Context

The owner sends a WhatsApp voice note. Invoice payments are modelled as distributions over arrival dates, not due dates. Planned fixes (not built yet) are TReDS invoice discounting, an overdraft draw within drawing power, deferring a supplier payment, or a heads-up to a late buyer under the MSMED Act. Onboarding at `/onboard` takes the Kab Tak? Excel workbook (a template is on the page) or nothing, then links the owner's WhatsApp number.

## Capabilities and Constraints

- Every number comes from the engine; no LLM produces numbers.
- All demo data is synthetic and must be labelled so. Disclaimer: "Computes and compares options, not financial or legal advice."
- Money in Indian notation (₹ lakh); dates day-month.
- Colour is never the only signal.

## Brand Commitments

Name: **Kab Tak?** (with the question mark). Plain, warm voice; English with Hindi/Marathi lines.

## Evidence on Hand

Synthetic demo businesses in `data/tenants/`, engine result fixture in `fixtures/engine_result.json`. No real customers, testimonials, or benchmarks exist: none may be invented.

## Product Principles

1. One verdict, one action: answer the owner's question, then show the working for the CA.
2. Honest uncertainty: show the range, never a single confident line.
3. The owner's language and channel, not ours.
4. Cost-ranked fixes, not just alerts (the goal; not built yet, so the product says "coming next").
