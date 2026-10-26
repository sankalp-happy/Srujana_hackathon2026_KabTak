# Demo: sign up, link a number, ask on WhatsApp (about 2 minutes)

One bot, one engine, one site; each business sees only its own ledger. Live at **https://172-198-161-228.sslip.io**, bot number **+91 6205 559 096**. All demo data is synthetic and says so.

## The flow

1. **Landing page** (`/`): the owner taps *Sign up*.
2. **`/onboard`, step 1:** name, business name, their WhatsApp number (10 digits), optional bank balance.
3. **Step 2, two options:**
   - **Upload the Kab Tak? Excel** (`invoices`, `obligations`, `position` sheets). The page offers a blank template and a demo workbook of a made-up Pune CNC shop (`ui/kabtak-demo.xlsx`). The page shows what loaded and the first forecast. **Upload before opening WhatsApp:** once the number is linked, the page can no longer upload.
   - **Skip the upload:** a yellow disclaimer says forecasts rest on standard assumptions until there is data; tick it and the Terms to enable *Open WhatsApp*.
4. **Open WhatsApp.** The button opens the bot with "What is the status of my current cash flow?" ready to send. The first message from the number given at sign-up **links that number** to the business; the bot replies "Welcome, *<business>*! This number is now linked" and answers the question. (Fallback: `JOIN <6-digit code>`.)
5. **Ask.** Text or voice note; the bot reads back what it understood, the owner says yes or no, then it answers with the riskiest week and a chart. "What is my status?" is answered at once; everything else asks for the yes first.
6. **An unknown number** that messages the bot gets the sign-up link and no data.

## Setup before the room fills

- Open the site once on the demo laptop and on the phone, so the first load is warm.
- Phone 1 (the "owner"): a number nobody has signed up with. Phone 2: a number you will link by hand to `mahesh-cnc`. Phone 3: a stranger (any other number).
- Link a phone by hand on the VM (digits only, with country code):

```bash
cd deploy && docker compose exec bot python -m engine.tenants link 919999999999 mahesh-cnc
```

- Have `ui/kabtak-demo.xlsx` in Downloads (also on the `/onboard` page). The other demo businesses, `shree-textiles` (no overdraft, 5 buyers) and `sai-snacks` (3 months old, few paid invoices) are linked the same way if you want a different shape.
- Plan B if the upload fails live: sign up and skip the upload with the disclaimer; or link Phone 1 by hand to `shree-textiles` with the command above and ask the same question.
- Rehearse once with a throwaway sign-up so the demo number's first message is a real first message.

## Script

| Time | Do | Say |
|---|---|---|
| 0:00 | Phone 3 sends "hi" to the bot. | "A stranger messages the bot. It never answers from anyone's data. It sends the sign-up link." |
| 0:10 | On the laptop, open `/onboard`, fill step 1 with Phone 1's number, continue. Upload `kabtak-demo.xlsx`. | "The owner's invoices and bills as an Excel file. Parsing and GST maths are plain code; bad rows are skipped and listed, never guessed. The page shows the first forecast." |
| 0:40 | Tap *Open WhatsApp* on Phone 1 and send the prefilled message. | "The first message from this number links it to this business. No code to type." |
| 0:55 | Phone 1: "What if Buyer A pays 30 days late?" Say yes at the read-back. | "It reads back what it understood before running anything. Then the riskiest week and how many days late Buyer A can be." |
| 1:20 | Phone 2 (linked to `mahesh-cnc`): the same words. | "Same question, same bot, a different business." |
| 1:40 | Both screens side by side. | "Each answer is computed by the simulator from that business's own ledger. The language model only parses and phrases." |

## What the judges should notice

- **Different answers to the same question**, because the ledgers differ.
- **Isolation.** Phone 3 got a link, not data.
- **Honesty about thin data.** With no upload, the page says forecasts rest on standard assumptions, and replies for a thin ledger say forecasts sharpen as invoices are added.
- **Nothing is hard-wired.** No overdraft, 1 to about 20 buyers, other GST rates all go through the same engine.
- **What is not there yet:** fix suggestions (the product shows the risk, the riskiest week and how late each buyer can pay, not how to fix it), replies in Hindi or Marathi (English only), a Tally import.

## Demo businesses

| Business | Shape |
|---|---|
| `mahesh-cnc` | CNC shop, Pune. ₹42 L overdraft, 4 buyers, quarter-end slips. "Today" is pinned to 25 Oct 2026, so its numbers stay put. |
| `shree-textiles` | Power-loom fabric trader, Ichalkaranji. No overdraft, bank ₹11 L, 5 buyers: one pays at about 75 days, one the next day. Sales peak Nov–Feb. |
| `sai-snacks` | Snack maker, Pune, 3 months old. 3 buyers, 8 paid invoices, bank ₹2 L. Every buyer uses the default payment curve (too little history). |

Numbers in the answers come from the engine on the day. If a number written anywhere disagrees with the engine, the engine wins. A business made by uploading `kabtak-demo.xlsx` is dated by the real date, not 25 Oct, so its open invoices look a day older for every day after the 25th and its numbers differ slightly from `mahesh-cnc` (status risk is still 2%, but the riskiest week starts 10 Nov, not 9 Nov, and buyers owe ₹49.7 L, not ₹47.1 L). The engine labels it "ledger uploaded by the owner" because it cannot tell a demo file from a real one, so say it is the demo workbook.
