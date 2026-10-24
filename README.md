# Kab Tak? Predictive cash flow for small businesses

**Srujana Tech Fest 2026 · Finance theme · Problem statement F-03: Predictive Cash-Flow Management for Small Businesses**

> **Status: work in progress.** This repository was created during the 48-hour hackathon (24–26 Oct 2026). This README is updated as the build progresses; see [Known limitations](#known-limitations) for what is incomplete.

## What it does

A micro-business owner sends a WhatsApp voice note in Marathi, such as *"Can I take this order?"* or *"What if my biggest buyer pays a month late?"* Kab Tak? then:

1. **Forecasts cash flow as a range of outcomes.** It simulates 1,000 possible paths for the bank balance over the next 90 days.
2. **Separates expected money from received money.** Each open invoice gets a probability distribution over when it will actually arrive, not just its due date.
3. **Flags the weeks when cash may run short,** with the probability of a shortfall.
4. **Compares fixes by what they cost:** invoice discounting on TReDS, an overdraft draw, deferring a supplier payment, or a heads-up to a late-paying buyer under the MSMED Act. It recommends the cheapest set of fixes that keeps shortfall risk under a target.

The LLM only turns speech or text into a typed scenario. **The simulator and the solver make every numerical decision.**

> **Not financial or legal advice.** Kab Tak? computes and compares options; the owner decides. All demo data is **synthetic**.

## Persona

The persona is a constructed composite, not a real person: the owner of a 14-person CNC job-work shop in Pune (a micro enterprise). His CA keeps the books in TallyPrime, and he works on WhatsApp in Marathi. His weekly question is "Can I pay wages on the 7th, and should I take this new order?"

## Architecture (planned)

```
Tally export / synthetic ledger
        │
        ├─► invoice arrival model (time-to-payment)  ─┐
        ├─► scheduled obligations (payroll, EMIs, GST) ├─► Monte Carlo cash paths ─► shortfall risk per week
        └─► scenario from voice/text (typed schema) ──┘                              │
                                                                                     ▼
                                                            optimiser: cheapest set of fixes under a risk target
```

## Setup

*To be added once the first runnable version is committed.*

## Project structure

*To be added.*

## Technical decisions

*To be added. Every model will be compared against a simple baseline.*

## Validation

*To be added. Planned: calibration of invoice-arrival forecasts, shortfall lead time, and unit tests for the legal and interest calculations.*

## Known limitations

- Work in progress. Nothing below the "What it does" section is implemented yet.
- All data is synthetic. The persona is constructed and has not been validated with real business owners.
- Legal levers (MSMED Act s.15/s.16, Income-tax Act 2025 s.37(2)(g), the CGST 180-day rule) are simplified. Contested points will be shown as explicit assumptions.

## Use of AI tools (disclosure)

AI tools are used in this project, as the event rules permit. This section is updated as the build progresses.

- **Claude (Anthropic)** helped with problem research, planning, documentation and code. The team reviews all generated code and can explain it.

## Acknowledgements

Dependencies and external resources will be listed here as they are added (for example the models, solver, speech APIs and messaging APIs used).

## Team

*Names and roles to be added.*
