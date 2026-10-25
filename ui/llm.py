"""Groq for the ask box: transcribe speech, parse a question into a Scenario, explain an engine result.

The LLM never computes numbers. parse() only fills the typed Scenario, which the owner confirms before
anything runs. explain() writes prose from the engine's own numbers; any sentence with a number that isn't
one of them is dropped, and a template sentence stands in if the answer itself fails.
"""
import base64, json, os, re, sys, urllib.error, urllib.request, uuid
from datetime import date, timedelta
from pathlib import Path

MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
FALLBACK = "openai/gpt-oss-20b"   # separate free-tier rate limit; used when MODEL answers 429
URL = "https://api.groq.com/openai/v1/chat/completions"
BUYERS = ["Buyer A", "Buyer B", "CPSE", "Small customers"]
TYPES = ["status", "new_order", "delay_payment", "expense_shock", "sales_drop", "supplier_terms",
         "schedule_change", "payment_received", "add_invoice", "add_obligation"]
KINDS = ["wages", "emi", "gst", "rent", "power", "advance_tax", "bonus", "supplier"]   # engine.ledger.KINDS
LANGS = {"en": "English", "mr": "Marathi (Devanagari)", "hi": "Hindi (Devanagari)"}
try:
    from engine.ledger import GST_RATE, TODAY
except ImportError:
    GST_RATE, TODAY = 0.18, date.today()


def _key(*names):
    names = names or ("GROQ_KEY", "GROQ_API_KEY")
    k = next((os.environ[n] for n in names if os.environ.get(n)), None)
    if k:
        return k
    for d in Path(__file__).resolve().parents:  # repo root .env (gitignored); worktrees look further up
        f = d / ".env"
        if f.exists():
            for line in f.read_text().splitlines():
                name, _, v = line.partition("=")
                if name.strip() in names and v.strip():
                    return v.strip().strip("'\"")
    raise RuntimeError(f"No {names[0]} in the environment or .env")


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


# ---------- speech to text ----------
STT_MODEL, STT_FALLBACK = "whisper-large-v3", "whisper-large-v3-turbo"   # full model is better on Marathi
STT_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
# Biases Whisper towards the words owners use; no language set, so Marathi, Hindi and English all work.
STT_HEAD, STT_TAIL = "ऑर्डर, लाख, दिवस, पगार, बजाज, टाटा", "wages, GST, overdraft, advance."
STT_PROMPT = f"{STT_HEAD}, बायर ए, बायर बी, Buyer A, Buyer B, CPSE, {STT_TAIL}"


OR_STT_MODEL = os.environ.get("STT_MODEL", "elevenlabs/scribe-v2")
OR_STT_URL = "https://openrouter.ai/api/v1/audio/transcriptions"


def transcribe(audio, mime="audio/webm", hint=None):
    """OpenRouter Voxtral first; any failure falls back to Groq Whisper. hint = the tenant's buyer names, biasing Whisper."""
    try:
        fmt = {"mpeg": "mp3", "mp4": "m4a", "x-wav": "wav"}.get(mime.split(";")[0].split("/")[-1], mime.split(";")[0].split("/")[-1])
        body = json.dumps({"model": OR_STT_MODEL, "input_audio": {"data": base64.b64encode(audio).decode(), "format": fmt}}).encode()
        req = urllib.request.Request(OR_STT_URL, body, {"Authorization": f"Bearer {_key('OPENROUTER_KEY')}",
                                                        "Content-Type": "application/json", "User-Agent": "kabtak-ui"})
        with urllib.request.urlopen(req, timeout=60) as r:
            text = json.load(r)["text"].strip()
        if text:
            return text
    except Exception as e:
        print("transcribe: OpenRouter failed, falling back to Groq Whisper:", e, file=sys.stderr)
    return _whisper(audio, mime, hint=hint)


def _whisper(audio, mime="audio/webm", model=STT_MODEL, hint=None):
    ext = {"webm": "webm", "ogg": "ogg", "mp4": "m4a", "mpeg": "mp3", "wav": "wav", "x-wav": "wav", "aiff": "aiff"}.get(
        mime.split(";")[0].split("/")[-1], "webm")
    b = uuid.uuid4().hex
    field = lambda k, v: f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    body = (field("model", model) + field("response_format", "json") + field("prompt", f"{STT_HEAD}, {hint}, {STT_TAIL}" if hint else STT_PROMPT) +
            f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="q.{ext}"\r\n'
            f"Content-Type: {mime.split(';')[0]}\r\n\r\n".encode() + audio + f"\r\n--{b}--\r\n".encode())
    req = urllib.request.Request(STT_URL, body, {"Authorization": f"Bearer {_key()}", "User-Agent": "kabtak-ui",
                                                 "Content-Type": f"multipart/form-data; boundary={b}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)["text"].strip()
    except urllib.error.HTTPError as e:
        if e.code == 429 and model != STT_FALLBACK:
            return _whisper(audio, mime, STT_FALLBACK, hint)
        raise


# ---------- parse ----------
_n = lambda t: {"type": [t, "null"]}
SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["type", "party", "amount_inr", "days", "pct", "date", "obligation", "needs_clarification",
                 "question", "lang"],
    "properties": {
        "type": {"type": "string", "enum": TYPES}, "party": _n("string"), "amount_inr": _n("integer"),
        "days": _n("integer"), "pct": _n("integer"), "date": _n("string"),
        "obligation": {"type": ["string", "null"], "enum": [*KINDS, None]},
        "needs_clarification": {"type": "boolean"}, "question": _n("string"),
        "lang": {"type": "string", "enum": list(LANGS)},
    },
}
def _parse_prompt(buyers, today):
    a, b = (buyers + ["your buyer", "another buyer"])[:2] if len(buyers) < 2 else buyers[:2]   # example names come from the tenant
    return f"""You turn a small-factory owner's question about cash flow into one typed scenario. Today is {today:%Y-%m-%d} ({today:%A}).
Copy values only from what the owner said; never guess an amount, a number of days or a date.

type, its required fields, and what days means:
- status: none. "Can I pay wages on the 7th?", "how are we doing?"
- new_order: party, amount_inr, days = payment terms offered. "Should I take Bajaj's 12 lakh order on 90-day terms?"
- delay_payment: party, days = extra days late. "What if {a} pays a month late?"
- expense_shock: amount_inr, date. Any one-off money going out: a repair, a purchase, a cash withdrawal, the owner taking money out, a loan repayment. "The spindle motor needs 2 lakh next week", "Can I withdraw 12 L after 5 days?". The purpose doesn't matter; never ask for it.
- sales_drop: pct, days = how long. supplier_terms: party, days = new terms. schedule_change: obligation, date.
- payment_received: party, amount_inr = the cash the buyer pays, date = when (after today). A what-if that saves nothing: "{a} is paying 20 L on 3 Nov", "what if {b} clears 5 lakh next week?".
- add_invoice: party, amount_inr = value before GST, date = invoice date (may be past). The owner tells you to record a real invoice they raised: "Add invoice: {a}, 2 lakh plus GST, dated today", "I billed {b} 3 lakh on 20 Oct, note it".
- add_obligation: amount_inr, date = due date, obligation = the closest kind ({", ".join(KINDS)}; bills from suppliers, repairs and other vendors are supplier), party = a short label for the bill in the owner's words (e.g. "Machine repair", "Tata Steel"). The owner tells you to record a real bill they must pay: "I have a 2 lakh machine repair bill due 10 Nov, add it".
- add_* SAVE data; every other type is a what-if that saves nothing. Use add_* only when the owner states a real invoice or bill and asks to add, record, note, save or enter it. "Can I spend / what if / should I" is a what-if (expense_shock, new_order). A bare amount and date with no ask ("Machine repair 2 lakh on 10 Nov") is unclear: set needs_clarification and ask "Should I save this as a real bill, or is it a what-if?" (or "real invoice").

Rules:
- Known buyers: {", ".join(buyers) or "none yet"}. For delay_payment, payment_received and add_invoice the party must be one of these, written exactly so; if the owner names someone else, ask which of these buyers they mean, listing them all. For new_order use the name as said (e.g. "Bajaj"), or "New buyer" if unnamed.
- amount_inr is whole rupees: 1 lakh = 100000, 1 crore = 10000000, 1 hazaar = 1000. "12 L" = 1200000. Read Devanagari digits (०-९) and Marathi/Hindi number words.
- "a month" = 30 days, "two months" = 60, "a week" = 7. Dates are YYYY-MM-DD, resolved from today; "next week" = {today + timedelta(days=7):%Y-%m-%d}.
- If a required field is missing or the question is unclear, set needs_clarification true and put exactly ONE short follow-up question in question, in the owner's language. Otherwise question is null.
- Fields a type doesn't use are null. lang is the language of the question: en, mr (Marathi) or hi (Hindi)."""


def parse(text, buyers=None, today=None):
    """buyers/today come from the tenant's profile (engine.ledger.profile); None = the demo tenant's."""
    s = _chat([{"role": "system", "content": _parse_prompt(BUYERS if buyers is None else buyers, today or TODAY)}, {"role": "user", "content": text}], SCHEMA)
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


_slug = lambda name: re.sub(r"\W+", "_", name.lower()).strip("_")


def facts(r, lang):
    """The numbers the LLM may quote, already formatted, scoped to the question so it can't mix them up.
    Names say what each number means. Values come from the engine result; the one sum (advance in rupees)
    is done here so the LLM never has to calculate."""
    pc = lambda p: f"{round(p * 100)}%"
    dt = lambda iso: f"{date.fromisoformat(iso).day} {MONTHS[lang][date.fromisoformat(iso).month - 1]}"
    d = lambda n: f"{n} {DAYS[lang]}"
    s, w, t = r["scenario"], r["worst_week"], r["today"]
    f = {"riskiest_week_starts": dt(w["week_start"]),
         "chance_of_running_short_in_riskiest_week": pc(w["p_shortfall"]),
         "acceptable_risk_limit": pc(r["risk_target"]),
         "bills_you_must_pay_in_riskiest_week": w["obligation"] or "-",
         "chance_all_bills_get_paid": pc(1 - w["p_shortfall"]),
         "overdraft_left_already_used_in_this_forecast": _inr(t["headroom_inr"])}
    if r.get("baseline"):
        f["chance_of_running_short_before_this_change"] = pc(r["baseline"]["worst_week"]["p_shortfall"])
    if s["type"] == "status":
        f.update(bank_balance=_inr(t["bank_inr"]), money_buyers_owe_you=_inr(t["receivable_inr"]),
                 money_owed_for_over_45_days=_inr(t["overdue_45_inr"]))
    for k in r.get("kab_tak") or []:
        if s["type"] == "status" or s.get("party") == k["buyer"]:
            f[f"days_{_slug(k['buyer'])}_can_pay_late_before_you_run_short"] = d(k["max_delay_days"])
    if s["type"] == "delay_payment":
        f[f"days_late_asked_about_for_{_slug(s['party'])}"] = d(s["days"])
    if s["type"] == "expense_shock":
        f.update(expense_amount=_inr(s["amount_inr"]), expense_date=dt(s["date"]))
    if o := r.get("order"):
        f.update(order_value=_inr(o["amount_inr"]), payment_terms_asked=d(o["terms_days"]),
                 longest_safe_payment_terms=d(o["max_safe_terms_days"]),
                 smallest_safe_advance_pct=f"{o['min_advance_pct']}%",
                 smallest_safe_advance_rupees=_inr(o["amount_inr"] * (1 + GST_RATE) * o["min_advance_pct"] / 100),
                 profit_margin_on_order=_inr(o["margin_inr"]))
    return f


EXPLAIN_PROMPT = """You explain a cash-flow forecast to a small-factory owner who is not an accountant.
Write {lang}, 3 or 4 short sentences, plain everyday words. Answer the owner's question first, then the most important risk, then what they could do (only what the facts support).
TONE: "verdict" decides how the first sentence answers. Follow it exactly. A risk that is only above the acceptable limit is "yes, but it's tight", never "no". Only say no, or that they can't or shouldn't, when verdict starts with "no". The owner decides; you describe the odds and the options.
The forecast already assumes the owner uses all the overdraft left, so never suggest the overdraft as a way to cover or fix anything. If the facts give no fix, don't invent one.
Each fact's name says exactly what it means; don't use a number for anything else. Bills are money going out, never coming in.
NUMBERS, strict rules:
- Every number you write must be copied from the values in "facts" (Devanagari digits are fine), or from the owner's question.
- Never calculate anything: no sums, differences, products, percentages of amounts or averages.
- Never convert units (no days to weeks or months, no lakh to million) and never round.
- Don't write numbers as words (e.g. "thirty", "तीस").
- If a number you'd like to mention isn't in the facts, describe it in words without a number.
- Never write a fact's name itself; write what it means.
Never say "guaranteed". No jargon ("P(shortfall)", "Monte Carlo", "drawing power", "headroom")."""

_DEV = str.maketrans("०१२३४५६७८९", "0123456789")
_NUM = re.compile(r"\d+(?:[.,]\d+)*")


def _nums(text):
    return {n.replace(",", "") for n in _NUM.findall(text.translate(_DEV))}


# ponytail: checks digits only; numbers spelled as words ("thirty") and a real number used for the wrong
# thing get through. The prompt and the scoped, self-describing fact names are what guard those.
def _safe(text, f, question=""):
    """Keep sentences whose every number is a fact value (or from the question) and that leak no fact name.
    None if the first sentence (the answer to the question) fails: dropping it could flip the meaning."""
    allowed = _nums(" ".join([*f, *f.values(), question]))   # names carry fixed numbers too ("over_45_days")
    ok = lambda x: _nums(x) <= allowed and not re.search(r"\b[a-z]+_[a-z_]+\b", x)
    parts = [x.strip() for x in re.split(r"(?<=[.?!।])\s+|\n+", text) if x.strip()]
    return " ".join(x for x in parts if ok(x)) if parts and ok(parts[0]) else None


TEMPLATE = {
    "en": "The riskiest week starts {riskiest_week_starts}: a {chance_of_running_short_in_riskiest_week} chance of running short (limit {acceptable_risk_limit}).",
    "mr": "सर्वात कठीण आठवडा {riskiest_week_starts} पासून: पैसे कमी पडण्याची शक्यता {chance_of_running_short_in_riskiest_week} (मर्यादा {acceptable_risk_limit}).",
    "hi": "सबसे मुश्किल हफ़्ता {riskiest_week_starts} से: पैसे कम पड़ने की संभावना {chance_of_running_short_in_riskiest_week} (सीमा {acceptable_risk_limit}).",
}


def explain(question, result, lang="en"):
    """-> {"text", "source": "llm" | "template"}. Every number in text is a value from facts(result) or the question."""
    lang = lang if lang in LANGS else "en"
    question = question or ""
    f = facts(result, lang)
    msg = json.dumps({"question": question, "facts": f, "verdict": _verdict(result),
                      "order_verdict": _order_verdict(result.get("order"))}, ensure_ascii=False)
    text = None
    for temp in (0, 0.5):  # one retry, warmer so it isn't the same reply; a bad sentence is dropped, not repaired
        try:
            raw = _chat([{"role": "system", "content": EXPLAIN_PROMPT.format(lang=LANGS[lang])},
                         {"role": "user", "content": msg}], temperature=temp)
            text = _safe(raw, f, question)
            if not text:
                print("explain: rejected, first sentence has a number not in the facts:", raw, file=sys.stderr)
        except Exception as e:
            print("explain: LLM call failed:", e, file=sys.stderr)
            break
        if text:
            break
    return {"text": text, "source": "llm"} if text else {"text": TEMPLATE[lang].format_map(f), "source": "template"}


def _verdict(r):
    """How to answer, graded by the riskiest week's chance of a missed payment."""
    p = r["worst_week"]["p_shortfall"]
    if p <= r["risk_target"]:
        return "yes: safe, within the acceptable limit"
    if p < 0.25:
        return "yes, most likely fine, but tighter than the acceptable limit: say 'yes, but', never 'no'"
    if p < 0.5:
        return "risky: a real chance of missing a payment; don't give a flat yes or no, say what would make it safer"
    return "no, not as things stand: missing a payment is more likely than not"


def _order_verdict(o):
    if not o:
        return None
    if o["max_safe_terms_days"] >= o["terms_days"]:
        return "safe on the requested terms"
    return "not safe on the requested terms; shorter terms or an advance needed" if o["max_safe_terms_days"] \
        else "terms alone can't make it safe; an advance is needed"


if __name__ == "__main__":
    f = {"riskiest_week_starts": "28 Dec", "chance_of_running_short_in_riskiest_week": "38%",
         "acceptable_risk_limit": "5%", "smallest_safe_advance_rupees": "₹4.2 L"}
    assert _safe("Week of 28 Dec is risky. Ask for ₹४.२ L upfront.", f) == "Week of 28 Dec is risky. Ask for ₹४.२ L upfront."
    assert _safe("Week of 28 Dec is risky. That is ₹3.6 L. Risk is 38%.", f) == "Week of 28 Dec is risky. Risk is 38%."
    assert _safe("Risk is 38%. See acceptable_risk_limit.", f) == "Risk is 38%."
    assert _safe("Pay 12 lakh on the 7th.", f) is None and _safe("Pay 12 lakh on the 7th.", f, "withdraw 12L by the 7th") 
    assert _safe("Risk 1.5 months. Week of 28 Dec.", f) is None
    assert "28 Dec" in TEMPLATE["mr"].format_map(f)
    q = _parse_prompt(["Om Traders", "Bajrang Mills"], TODAY)   # examples use the tenant's buyers, not Mahesh's
    assert "Buyer A" not in _parse_prompt([], TODAY) and "none yet" in _parse_prompt([], TODAY)   # a new business never sees Mahesh's buyers
    assert "Om Traders pays a month late" in q and "Bajrang Mills clears" in q and "Buyer A" not in q and "CPSE" not in q
    assert _safe("₹26 L is over 45 days old.", {**f, "money_owed_for_over_45_days": "₹26 L"})
    print("ok")
