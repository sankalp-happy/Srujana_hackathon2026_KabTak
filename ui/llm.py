"""Groq LLM for the free-text box: parse a question into a Scenario, and explain an engine result.

The LLM never produces numbers. parse() only fills the typed Scenario, which the owner confirms before
anything runs. explain() writes prose with {placeholders}; code fills them from the engine result, and a
reply that writes any number of its own is thrown away for a template sentence.
"""
import json, os, re, sys, urllib.error, urllib.request
from datetime import date, timedelta
from pathlib import Path

MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
FALLBACK = "openai/gpt-oss-20b"   # separate free-tier rate limit; used when MODEL answers 429
URL = "https://api.groq.com/openai/v1/chat/completions"
BUYERS = ["Buyer A", "Buyer B", "CPSE", "Small customers"]
TYPES = ["status", "new_order", "delay_payment", "expense_shock", "sales_drop", "supplier_terms",
         "schedule_change", "payment_received"]
LANGS = {"en": "English", "mr": "Marathi (Devanagari)", "hi": "Hindi (Devanagari)"}
try:
    from engine.ledger import TODAY
except ImportError:
    TODAY = date.today()


def _key():
    k = os.environ.get("GROQ_KEY") or os.environ.get("GROQ_API_KEY")
    if k:
        return k
    for d in Path(__file__).resolve().parents:  # repo root .env (gitignored); worktrees look further up
        f = d / ".env"
        if f.exists():
            for line in f.read_text().splitlines():
                name, _, v = line.partition("=")
                if name.strip() in ("GROQ_KEY", "GROQ_API_KEY") and v.strip():
                    return v.strip().strip("'\"")
    raise RuntimeError("No GROQ_KEY in the environment or .env")


def _chat(messages, schema=None, model=MODEL, temperature=0):
    body = {"model": model, "messages": messages, "temperature": temperature}
    if schema:
        body["response_format"] = {"type": "json_schema", "json_schema": {"name": "out", "strict": True, "schema": schema}}
    req = urllib.request.Request(URL, json.dumps(body).encode(), {
        "Authorization": f"Bearer {_key()}", "Content-Type": "application/json", "User-Agent": "kabtak-ui"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            text = json.load(r)["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        if e.code == 429 and model != FALLBACK:
            return _chat(messages, schema, FALLBACK, temperature)
        raise
    return json.loads(text) if schema else text.strip()


# ---------- parse ----------
_n = lambda t: {"type": [t, "null"]}
SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["type", "party", "amount_inr", "days", "pct", "date", "obligation", "needs_clarification",
                 "question", "lang"],
    "properties": {
        "type": {"type": "string", "enum": TYPES}, "party": _n("string"), "amount_inr": _n("integer"),
        "days": _n("integer"), "pct": _n("integer"), "date": _n("string"),
        "obligation": {"type": ["string", "null"], "enum": ["wages", "emi", "gst", "rent", None]},
        "needs_clarification": {"type": "boolean"}, "question": _n("string"),
        "lang": {"type": "string", "enum": list(LANGS)},
    },
}
PARSE_PROMPT = f"""You turn a small-factory owner's question about cash flow into one typed scenario. Today is {TODAY:%Y-%m-%d} ({TODAY:%A}).
Copy values only from what the owner said; never guess an amount, a number of days or a date.

type, its required fields, and what days means:
- status: none. "Can I pay wages on the 7th?", "how are we doing?"
- new_order: party, amount_inr, days = payment terms offered. "Should I take Bajaj's 12 lakh order on 90-day terms?"
- delay_payment: party, days = extra days late. "What if Buyer A pays a month late?"
- expense_shock: amount_inr, date. "The spindle motor needs 2 lakh next week"
- sales_drop: pct, days = how long. supplier_terms: party, days = new terms. schedule_change: obligation, date.
- payment_received: party, amount_inr, date.

Rules:
- Known buyers: {", ".join(BUYERS)}. For delay_payment the party must be one of these, written exactly so; if the owner names someone else, ask which buyer they mean. For new_order use the name as said (e.g. "Bajaj"), or "New buyer" if unnamed.
- amount_inr is whole rupees: 1 lakh = 100000, 1 crore = 10000000, 1 hazaar = 1000. "12 L" = 1200000. Read Devanagari digits (०-९) and Marathi/Hindi number words.
- "a month" = 30 days, "two months" = 60, "a week" = 7. Dates are YYYY-MM-DD, resolved from today; "next week" = {TODAY + timedelta(days=7):%Y-%m-%d}.
- If a required field is missing or the question is unclear, set needs_clarification true and put exactly ONE short follow-up question in question, in the owner's language. Otherwise question is null.
- Fields a type doesn't use are null. lang is the language of the question: en, mr (Marathi) or hi (Hindi)."""


def parse(text):
    s = _chat([{"role": "system", "content": PARSE_PROMPT}, {"role": "user", "content": text}], SCHEMA)
    s["transcript"] = text
    return s


# ---------- explain ----------
MONTHS = {
    "en": "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(),
    "mr": "जाने फेब्रु मार्च एप्रि मे जून जुलै ऑग सप्टें ऑक्टो नोव्हें डिसें".split(),
    "hi": "जन फ़र मार्च अप्रै मई जून जुला अग सितं अक्टू नवं दिसं".split(),
}
DAYS = {"en": "days", "mr": "दिवस", "hi": "दिन"}


def _inr(n):
    a = abs(n)
    if a >= 1e5:
        return f"₹{a / 1e5:.{0 if a >= 1e6 else 1}f} L".replace(".0 L", " L")
    return f"₹{a:,.0f}"


def facts(r, lang):
    """Formatted numbers the LLM may cite by name. All values come straight from the engine result."""
    pc = lambda p: f"{round(p * 100)}%"
    dt = lambda iso: f"{date.fromisoformat(iso).day} {MONTHS[lang][date.fromisoformat(iso).month - 1]}"
    w, t = r["worst_week"], r["today"]
    f = {"worst_week": dt(w["week_start"]), "worst_week_risk": pc(w["p_shortfall"]),
         "worst_week_payments": w["obligation"] or "-", "risk_limit": pc(r["risk_target"]),
         "bank": _inr(t["bank_inr"]), "overdraft_headroom": _inr(t["headroom_inr"]),
         "owed_to_you": _inr(t["receivable_inr"]), "owed_over_45_days": _inr(t["overdue_45_inr"])}
    if r.get("baseline"):
        f["worst_week_risk_before"] = pc(r["baseline"]["worst_week"]["p_shortfall"])
    s = r["scenario"]
    for k in r.get("kab_tak") or []:  # only buyers the question is about, so the LLM can't mix them up
        if s["type"] == "status" or s.get("party") == k["buyer"]:
            f[k["buyer"].lower().replace(" ", "_") + "_can_pay_late_by"] = f"{k['max_delay_days']} {DAYS[lang]}"
    if o := r.get("order"):
        f.update(order_amount=_inr(o["amount_inr"]), order_terms=f"{o['terms_days']} {DAYS[lang]}",
                 order_safe_terms=f"{o['max_safe_terms_days']} {DAYS[lang]}", order_min_advance=f"{o['min_advance_pct']}%",
                 order_margin=_inr(o["margin_inr"]))
    if s.get("amount_inr"):
        f["asked_amount"] = _inr(s["amount_inr"])
    if s.get("days") is not None:
        f["asked_days"] = f"{s['days']} {DAYS[lang]}"
    return f


# ponytail: catches digits and scale/percent words, not every spelled-out number (e.g. "thirty", "तीस").
# Prompt forbids those too; extend the word list if the golden set shows leaks.
NUMBERISH = re.compile(r"[0-9०-९]|%|₹|\b(lakh|lac|crore|thousand|hundred|percent)\b|लाख|कोटी|करोड|हजार|हज़ार|शंभर|सौ|टक्के|प्रतिशत",
                       re.I)

EXPLAIN_PROMPT = """You explain a cash-flow forecast to a small-factory owner who is not an accountant.
Write {lang}, 3 or 4 short sentences, plain everyday words. Answer the owner's question first, consistent with "verdict", then the most important risk, then what they could do (only what the facts support).
You must NOT write any number, digit, percentage, amount or date yourself. Refer to numbers only by writing a placeholder name from the facts in curly braces, e.g. {{worst_week_risk}}. Use only the placeholder names listed in "facts" (that list is complete; never make one up). If something you want to mention has no placeholder, say it in words ("that date", "the wages") without the number. This includes numbers from the owner's own question: write {{asked_amount}} or {{asked_days}}, never the number itself. Placeholders already include their unit (days, %, ₹), so don't repeat the unit.
Facts: worst_week = start of the riskiest week; worst_week_risk = chance of not being able to make a payment that week; <buyer>_can_pay_late_by = how many extra days that buyer can be late before the owner runs short; order_safe_terms = longest payment terms that stay safe; order_min_advance = smallest advance that makes the order safe; overdraft_headroom = overdraft still available.
Never say "guaranteed". Don't use jargon such as "P(shortfall)", "Monte Carlo" or "drawing power"; say "the overdraft you can still use"."""


def _safe(text, f):
    """Keep the sentences that cite only known placeholders and write no number of their own.
    None if the first sentence (the answer to the question) fails: dropping it could flip the meaning."""
    parts = [x.strip() for x in re.split(r"(?<=[.?!।])\s+|\n+", text) if x.strip()]
    kept = [_fill(x, f) for x in parts]
    return " ".join(k for k in kept if k) if kept and kept[0] else None


def _fill(text, f):
    names = re.findall(r"\{(\w+)\}", text)
    if any(n not in f for n in names) or NUMBERISH.search(re.sub(r"\{\w+\}", "", text)):
        return None
    return re.sub(r"\{(\w+)\}", lambda m: f[m.group(1)], text)


TEMPLATE = {
    "en": "The hardest week starts {worst_week}: a {worst_week_risk} chance of running short (limit {risk_limit}).",
    "mr": "सर्वात कठीण आठवडा {worst_week} पासून: पैसे कमी पडण्याची शक्यता {worst_week_risk} (मर्यादा {risk_limit}).",
    "hi": "सबसे मुश्किल हफ़्ता {worst_week} से: पैसे कम पड़ने की संभावना {worst_week_risk} (सीमा {risk_limit}).",
}


def explain(question, result, lang="en"):
    """-> {"text", "source": "llm" | "template"}. Every number in text comes from facts(result)."""
    lang = lang if lang in LANGS else "en"
    f = facts(result, lang)
    question = re.sub(r"[0-9०-९][0-9०-९,.]*", "…", question or "")  # its numbers are in facts as asked_*
    msg = json.dumps({"question": question, "scenario": {k: v for k, v in result["scenario"].items() if v is not None},
                      "facts": f, "verdict": _verdict(result), "order_verdict": _order_verdict(result.get("order"))}, ensure_ascii=False)
    text = None
    for temp in (0, 0.5):  # one retry, warmer so it isn't the same reply; a leak is rejected, not repaired
        try:
            raw = _chat([{"role": "system", "content": EXPLAIN_PROMPT.format(lang=LANGS[lang])},
                         {"role": "user", "content": msg}], temperature=temp)
            text = _safe(raw, f)
            if not text:
                print("explain: rejected, first sentence cites an unknown placeholder or writes a number:", raw, file=sys.stderr)
        except Exception as e:
            print("explain: LLM call failed:", e, file=sys.stderr)
            break
        if text:
            break
    return {"text": text, "source": "llm"} if text else {"text": _fill(TEMPLATE[lang], f), "source": "template"}


def _verdict(r):
    p = r["worst_week"]["p_shortfall"]   # same three levels as the UI stamp (app.js level())
    return "safe" if p <= r["risk_target"] else "at risk" if p < 0.5 else "likely to fall short"


def _order_verdict(o):
    if not o:
        return None
    if o["max_safe_terms_days"] >= o["terms_days"]:
        return "safe on the requested terms"
    return "not safe on the requested terms; shorter terms or an advance needed" if o["max_safe_terms_days"] \
        else "terms alone can't make it safe; an advance is needed"


if __name__ == "__main__":
    f = {"worst_week": "28 Dec", "worst_week_risk": "38%", "risk_limit": "5%"}
    assert _fill("Week of {worst_week}: {worst_week_risk} risk.", f) == "Week of 28 Dec: 38% risk."
    for bad in ("Risk is 38% in {worst_week}.", "Ask for a ३० टक्के advance.", "Use {nope}.", "Borrow 2 lakh."):
        assert _fill(bad, f) is None, bad
    assert _fill(TEMPLATE["mr"], f)
    assert _safe("Week of {worst_week} is risky. Pay on the 7th. Risk is {worst_week_risk}.", f) == "Week of 28 Dec is risky. Risk is 38%."
    assert _safe("Pay on the 7th. Week of {worst_week} is risky.", f) is None
    print("ok")
