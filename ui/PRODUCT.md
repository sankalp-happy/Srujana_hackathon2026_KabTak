# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Static HTML/CSS/JS page (charts in SVG), served by a stdlib Python server (`ui/server.py`) that calls `engine.answer.answer(scenario)` and falls back to `KABTAK_RESULT` / `fixtures/engine_result.json`. No npm, no build step.

## Users

- **Owner**: runs a 14-worker CNC job shop in Pune. Asks "can I pay wages / take this order?" and needs one verdict and one action, never "P(shortfall)".
- **CA (chartered accountant)**: checks the working: fan chart, weekly risk, fixes, assumptions.
- **Judges** (Srujana 2026, problem F-03) watch the demo on a projector; the rubric rewards working, validated, accessible UX.

## Purpose

Kab Tak? ("how long?") is predictive cash flow for a micro-enterprise. A 1,000-path Monte Carlo of available liquidity (bank + undrawn drawing power) gives weekly shortfall risk, how many days each buyer can pay late before a shortfall, the longest safe terms for a new order, and the cheapest set of fixes that brings risk under the 5% target.

## Constraints

- Every number comes from the engine result (shape frozen in `fixtures/engine_result.json`); the UI never computes or invents figures, and no LLM produces numbers.
- All data is synthetic and must be labelled so. Disclaimer: "Computes and compares options, not financial or legal advice. Synthetic data."
- Colour is never the only signal; stress weeks carry a text label.
- Owner verdict is in English plus a templated Hindi sentence (numbers filled from the result).
- Money in Indian notation (₹ lakh), dates as day-month.

## Terminology

Kab tak = how long; TReDS = invoice discounting exchange; OD = overdraft; drawing power = OD limit allowed against receivables; MSMED = MSME payment-delay law.
