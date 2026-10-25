# Kab Tak? Pitch script (about 2.5 minutes)

Read aloud. Plain words. Every number comes from the program.

## 1. The problem (20 seconds)
Imagine a shop owner whose books show a profit. He wants to buy a new ₹10 lakh machine and grow. He asks one question: can I afford it? But profit on paper is not cash in the bank. His money is stuck in unpaid invoices while wages and bills fall due. Today he guesses, or asks his CA.

## 2. What owners use today (25 seconds)
Tally and Zoho are good at recording what already happened. TallyPrime can show expected cash for each month. You can type in a bank limit and enter the machine as a memo entry. It takes the due dates from your books and assumes each customer pays on the due date. Zoho Books can forecast from recurring bills and invoices, plus assumptions you type in. You enter the expected payment date on each invoice yourself. On the pages we read, neither one works out how late each buyer really pays.

## 3. What we add (45 seconds)
One. We predict how late each buyer pays, using that buyer's own payment history, including invoices that are still open.

Two. We give a chance, not one number. We play out 1,000 possible futures and tell you the chance of missing a payment in each week. A buyer who is late stays late on all their invoices.

Three. Our bank limit moves. It shrinks when invoices get older than 90 days. TallyPrime takes a fixed limit that you type in.

Four. We answer the decision. We tell you the largest purchase you can pay for on each date, and how many days late each buyer can be before the risk is too high.

## 4. How it works (35 seconds)
First, we learn how late each buyer pays. We use a standard method called Kaplan-Meier. It looks at every past invoice, and it counts the unpaid ones as "still waiting", not as paid.

Second, we play out the next 90 days a thousand times. In each run, we pick a payment day for every invoice from that buyer's history. Then we go day by day: payments come in, then wages, loan instalments, GST and material bills go out. If a run cannot pay a bill, even using the bank limit, that run failed. The chance of missing a payment is the share of runs that failed.

Third, to find the safe answer, we try a value, halve the range, and repeat. That gives us how many days late a buyer can be and the largest purchase we can afford on each date.

It is built in Python with numpy and pandas, about 900 lines, and it runs with one Docker command. A language model only reads the question and writes the answer. It never does the maths, and any number it writes that the program did not produce is deleted.

## 5. The result (20 seconds)
If he buys the machine in 15 days, the chance of missing a payment is 99.8%. Today, without the machine, it is 3.4%. We then tell him when it is safe. A ₹10 lakh machine becomes safe on 17 January. Before that, the most he can pay for is under ₹1 lakh in November, ₹5.2 lakh by Christmas, and ₹7.5 lakh by 8 January.

## 6. What we do not have (15 seconds)
Our data is made up, and the ₹10 lakh is an example. We treat the machine as one payment from cash and the bank limit, with no loan. We have not tested on real businesses. We do not read Tally or Zoho files. We do not yet suggest fixes, so that is what we build next.

## Close
Tally and Zoho tell you what happened. Kab Tak? tells you what is likely to happen, and when you can afford the purchase.

---

## Facts behind each claim (for questions)
- TallyPrime Cash Flow Projection: shows receivables and payables by period, lets you set a bank overdraft limit, excludes overdue bills unless you turn that on, supports scenarios through memorandum vouchers. It describes no late-payment model. Source: https://help.tallysolutions.com/tally-prime/accounting-financial-reports/cash-flow-and-projection-report-tally/
- Zoho Books: Cash Flow Forecasting report from recurring items and assumptions; expected payment date is typed in by the user; Zia flags invoices later than your usual. We found no automatic prediction of a customer's payment date. Sources: https://www.zoho.com/us/books/kb/reminders/rem-epd.html and https://www.zoho.com/in/books/help/ai-features/ai-features.html
- Other products do predict payment timing. Float, an add-on for Xero, says it applies each customer's past payment behaviour automatically. So "predicting payment timing" is not new in the market. It is new against Tally and Zoho as we read them. Source: https://apps.xero.com/us/app/float-cashflow-forecasting
- Tech stack: Python 3.12, numpy 1.26, pandas 2.2, Python's built-in web server, plain HTML/CSS/JavaScript, Docker. The engine has no machine-learning library. Model calls: Groq gpt-oss-120b for words, OpenRouter scribe-v2 for speech with Groq Whisper as backup.
- Methods: Kaplan-Meier per buyer; payment days drawn from the curve (only the part after the invoice's age); one shared random draw per buyer with a link of 0.6 (assumption); a 30% chance per run that quarter-end payments slip a week (assumption); a day-by-day cash loop over 1,000 runs; bank limit recomputed every Monday from stock and invoices under 90 days; search by halving the range on fixed random numbers.
- We have not used Tally or Zoho. Check their live product before the jury.
- Our own numbers are from running the engine on synthetic data: 3.4% today, 99.8% for a ₹10 lakh payment on day 15 (998 of 1,000 runs), first safe date 17 Jan 2027 (day 84), largest safe payment about ₹0.4 L on day 15, ₹0.7 L on days 30 and 45, ₹5.2 L on day 60, ₹7.5 L on day 75, ₹10.8 L on day 85. Each is found by trying prices and halving the range.
- The machine is modelled as a one-time expense (the engine's expense scenario). Loans, instalments and part payments are not in the answer.
