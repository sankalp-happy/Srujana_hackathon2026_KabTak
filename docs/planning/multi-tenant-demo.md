# Multi-tenant demo: two phones, 90 seconds

One bot, one engine, one page, and each business sees only its own ledger. All data is synthetic and says so.

## Setup (before the room fills)

```bash
python3 data/make_demo_tenants.py                      # rebuilds shree-textiles, sai-snacks and the sample file (~2 s)
python3 -m engine.tenants link <PHONE2> mahesh-cnc     # phone 2 = Mahesh's CNC shop (digits only, e.g. 919999999999)
python3 -m engine.tenants link <PHONE4> sai-snacks     # optional: the 3-month-old business, for Q&A
uvicorn whatsapp.evolution_bot:app --port 8001         # the bot
python3 ui/server.py                                   # onboarding page at http://localhost:8000/onboard
```

- Phone 1 is **not** linked to anything. Phone 3 is a number nobody has linked. Keep the sample file open in a Finder window: `data/samples/kolhapur_auto_spares_sales_register.xlsx`.
- Check once: `python3 -m engine.tenants` lists the links. Rehearse the commit step so the join code comes from a fresh onboarding, not a rehearsal one.
- Suggested recurring bills to type on the page: wages ₹1,20,000 on the 7th, EMI ₹40,000 on the 5th, rent ₹30,000 on the 1st; bank ₹2,50,000.
- Plan B if the upload fails live: `python3 -m engine.tenants link <PHONE1> shree-textiles`, then ask the same question in Marathi. Shree has no overdraft, and its tightest week is early-mid November (about ₹2 L short on a point estimate).

## Script

| Time | Do | Say |
|---|---|---|
| 0:00 | Phone 3 (unknown number) sends "hi". | "A stranger messages the bot. It never answers from anyone's data. It sends the onboarding link." |
| 0:10 | Open `/onboard`, drop the Tally file (a messy export of a fictional business: Kolhapur Auto Spares). Show the preview: the 5 bad rows flagged, 95 invoices, 5 buyers. Type the three recurring bills. Commit. | "A real Tally register, with a blank row, a credit note, a duplicate, a bad date and a total row. The model only maps column names. Parsing and GST maths are plain code." |
| 0:40 | Phone 1 sends `JOIN <code>`. The bot replies with a welcome that names the business. | "One code, and this number now belongs to Kolhapur Auto Spares." |
| 0:50 | Phone 1: "Can I pay wages next week?" | "Its own invoices, its own bills, its own payment history." |
| 1:05 | Phone 2 (linked to `mahesh-cnc`): the same words. | "Same question, same bot, a different business." |
| 1:20 | Put both screens side by side. | "Two businesses, two answers. Each one is computed by the simulator from that tenant's ledger. The LLM only parses and phrases." |

## What the judges should notice

- **Different answers to the same question.** Mahesh has an overdraft with headroom. The new business has none, so a shortfall can't be covered.
- **Isolation.** Phone 3 got a link, not data. Phone 1 can't see Mahesh's buyers (ask it about "Buyer A": it doesn't know the name).
- **Honesty about thin data.** A new business with a few paid invoices gets a pooled or default payment curve, and the answer says so in its assumptions. Show `sai-snacks` here if asked: 8 paid invoices in 3 months.
- **Nothing is hard-wired.** No overdraft, 2 to 5 buyers, a different season and a different GST rate all go through the same engine.
- **Messy input, not clean fixtures.** The file is the kind a CA exports, and the preview says exactly which rows it refused.

## Demo tenants

| Tenant | Shape |
|---|---|
| `mahesh-cnc` | CNC shop, Pune. ₹42 L overdraft, 4 buyers, quarter-end slips. |
| `shree-textiles` | Power-loom fabric trader, Ichalkaranji (Marathi owner). No overdraft, bank ₹11 L, 5 buyers: Mehta Wholesale pays at ~75 days, Counter sales pays the next day. Sales peak Nov–Feb; the engine puts a ~23% shortfall risk on the week of 14 Dec (Mahesh: 2%). |
| `sai-snacks` | Snack maker, Pune, 3 months old. 3 buyers, 8 paid invoices, bank ₹2 L. Every buyer uses the default payment curve (too little history); ~17% risk in January. |

Numbers in the answers come from the engine on the day. Rehearse once, and if a number here disagrees with the engine, the engine wins.
