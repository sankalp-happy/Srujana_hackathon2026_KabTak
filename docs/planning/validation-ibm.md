# External validation on a public dataset (IBM accounts receivable)

Everything else we have validated runs on our own synthetic ledger, which is circular. This is the one test on
data we didn't generate. Reproduce: `python3 -m validation.ibm_backtest` (about 3 seconds, fixed seed, writes
`results/ibm_validation.json` and refreshes the table below). Data notes: [`data/README.md`](../../data/README.md).

## Result, in plain English

**We did not beat cashcast's 67.5%, and we did not reach 80%.** Our weekly cash band held the actual cash in
about 6 weeks out of 10 (61–63%, 80 weeks). That is below cashcast's published 67.5%, but with 80 weeks the 95%
interval is roughly ±10 points, so the two are not statistically separable. **The shared buyer shock did not
fix it on this data**: it moved coverage by one week in 80 (61.3% to 62.5%) and widened the band by 1.5%.

Why, from the numbers:

- **The shock has little to work with here.** In this dataset, two invoices to the same customer in the same
  month pay with a correlation of only 0.08 (1,307 pairs; `shock_diagnostic` in the JSON). The delays look
  close to independent, so a shared shock cannot help. It also means "independent invoices" is *not* the main
  reason cashcast missed: simple baselines that treat invoices as independent reach 72–78% weekly coverage.
  Whether the shock earns its keep on real small-business ledgers (a buyer that pays everyone late at
  quarter-end) is still untested; this dataset can't show it.
- **The bigger problem is our per-customer Kaplan–Meier curves.** With 15–36 invoices per customer, the tails
  of a per-customer curve are noisy, and the 80% interval is too narrow: 71.0% of actual payment dates fell
  inside it, not 80%. The engine was built for a few buyers with many invoices each, not 100 customers with a
  couple of dozen.
- **A post-hoc diagnostic points the same way.** Swapping in one pooled curve for all customers gives 82.0%
  per-invoice and 76.2% weekly (last table row). We ran this *after* seeing the headline, so it explains the
  gap but is **not a result and not a claim**. We did not change the engine or the headline method.

## Table

Same protocol for every row: 10 origins, 8 weeks each, 80 weeks, band = P10 to P90 of 2,000 simulated weekly
totals. "Weekly band width" is the mean P90 minus P10, in the dataset's invoice currency units (it has none);
the mean actual week is 693.5, the same figure cashcast's replay reports, which is a check that our weekly
actuals are the same. CRPS is lower-is-better (a score for the whole forecast distribution, not only the band).

<!-- TABLE -->
| Model | Per-invoice 80% interval hit | Weekly cash 80% band hit | Weekly band width | Weekly CRPS |
|---|---|---|---|---|
| Ours, invoices independent | 71.0% | 61.3% (95% CI 50% to 71%) | 406 (59% of mean week) | 142.3 |
| Ours, shared buyer shock (RHO=0.6) | 71.0% | 62.5% (95% CI 52% to 72%) | 412 (59% of mean week) | 141.7 |
| Baseline: paid on the due date | 82.2% | 77.5% (95% CI 67% to 85%) | 445 (64% of mean week) | 110.8 |
| Baseline: per-customer average delay | 74.8% | 72.5% (95% CI 62% to 81%) | 422 (61% of mean week) | 120.6 |
| Sensitivity only: shared shock, rho=0.3 | 71.0% | 62.5% (95% CI 52% to 72%) | 406 (59% of mean week) | 142.1 |
| Sensitivity only: shared shock, rho=0.9 | 71.0% | 62.5% (95% CI 52% to 72%) | 421 (61% of mean week) | 141.8 |
| Post-hoc diagnostic: one pooled KM for all customers | 82.0% | 76.2% (95% CI 66% to 84%) | 446 (64% of mean week) | 113.3 |
| cashcast (TabPFN), as published | 77.1% | 67.5% | not published | not published |
<!-- /TABLE -->

Rows 1–2 are the headline pair (a vs b). The baselines are "point forecast plus the training set's empirical
residuals, drawn independently", since a bare point forecast has no band; the same truncation (delay must exceed
the invoice's age) is applied. cashcast's per-invoice 77.1% is its published replay figure over the same 905
open-invoice rows.

Counts of weeks outside the band (below / above) are in the JSON: ours, independent 14 / 17; ours, shared 13 / 17;
the due-date baseline 7 / 11. Our misses are both-sided, so the band is too narrow rather than biased.

## Method

- **Data:** IBM Watson sample "Accounts Receivable", 2,466 invoices, 100 customers, 2012–13, every invoice 30-day terms and eventually settled.
- **Our model:** `engine.arrival` unchanged: a Kaplan–Meier delay curve per customer, conditional on the
  invoice's age, with open invoices counted as censored. Customers with fewer than 5 settled invoices would fall
  back to a pooled curve (never triggered). Invoices are drawn by inverse CDF (`sample_delay`).
- **Shared shock (b):** the engine's own mechanism (`engine.simulate.RHO` = 0.6, `_phi`): each path draws one
  normal per customer, mixed into every invoice's normal as `rho*shock + sqrt(1-rho²)*own`, then mapped to a
  uniform. (a) is the same draws with rho = 0, so (a) and (b) differ only by the shock. RHO = 0.6 is the value
  the engine already had; it was not fitted to IBM. Rows at rho 0.3 and 0.9 are sensitivity checks, not
  selections.
- **Per-invoice interval:** the P10 and P90 of that invoice's conditional delay; hit = actual payment day inside.
- **What was fixed before the first run and never changed after:** RHO, the 5-invoice pooling rule, 2,000
  paths, the seed, the origins. Nothing was tuned on the test period. The pooled-curve row was added after the
  headline and is labelled as such.
- **Self-check:** the script asserts it reproduces cashcast's replay counts (905 open rows, 784 not yet due, 80
  weeks, mean weekly cash 693.5), tests the KM sampler on a known sample, and asserts the shock widens the band.

## Protocol differences from cashcast

Matched exactly: the 10 origins (1st of each month, 2013-02-01 to 2013-11-01); open set (issued before the
origin, not settled before it); 8-week horizon in 7-day weeks from the origin; "weekly cash" = amount of those
open invoices actually settled that week, new invoices ignored; band = P10 to P90 of 2,000 simulated schedules;
coverage over 80 weeks. Unmatched or different:

1. **No train/test split in the usual sense.** Like cashcast's replay, each origin uses only information from
   before it, so no future leakage; but their *backtest* (monthly, 1,075 invoices, 79.1% hit) is a different
   exercise. The 67.5% comes from their demo replay, which is what we copy.
2. **Training data.** cashcast trains on invoices settled before the origin (at most the last 1,000 rows) with
   14 features. We use a per-customer curve from all invoices issued before the origin, with unsettled ones as
   censored information (they are known unsettled at the origin). No features, no amounts.
3. **Origin-day edge.** We treat an invoice settled *on* the origin date as still open (their rule); our engine
   clock is the day before. Open counts match theirs exactly.
4. **Different models, same data.** We could not rerun cashcast (TabPFN weights); 67.5% and 77.1% are their
   published numbers, not a re-measurement. Their per-invoice and weekly figures are from one run.
5. **Dependency.** Within one origin, the 8 weeks share the same invoices, and the 10 origins overlap, so the 80
   weeks are not independent. The ±10 point interval in the table is the naive binomial one and is, if anything,
   optimistic. By-origin coverage is in the JSON (April's origin is bad for every method).

## Limitations

- **The dataset is an IBM sample that may itself be synthetic.** We call it "an external public dataset we didn't
  generate", not real data. Licence not stated.
- **It tests prediction plus simulation only.** There is no GST, no overdraft or drawing power, no payment
  obligations and no TDS; nothing here says anything about the shortfall probabilities or the recommendations.
- **One dataset.** Large corporate customers on identical 30-day terms, all invoices eventually paid (no
  never-paid invoices, which flatters every model). A small Indian
  manufacturer's buyers (a PSU past 180 days, quarter-end slips) are exactly what this does not contain.
- **The shared buyer shock is not validated.** This dataset has almost no shared delay, so the test is nearly
  blind to it; what we can say is that it did no harm (coverage +1 week in 80, band +1.5%). The 0.08 correlation
  is a descriptive check on all the data, not a forecast.
- **80 weeks is a small sample** (see item 5 above).
- **Our per-customer curves are too narrow here**, and we are not fixing that on the test period. A pooled or
  shrunk-toward-pooled curve for customers with few invoices is the obvious change; it would need its own
  fresh validation on data we haven't looked at.

## The sentence the pitch can quote

> "On an external public dataset we didn't generate (IBM's 2,466-invoice sample), our model's weekly cash band
> held the actual cash in about 62% of 80 weeks against a published 67.5% for the cashcast prototype: not
> better, and not the 80% we aim for. The shared-buyer-shock idea made no measurable difference there because
> that data has almost no shared delay, so we haven't validated it; we've only shown it does no harm."
