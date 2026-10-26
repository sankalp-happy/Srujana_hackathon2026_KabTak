"""Kab Tak? WhatsApp bot on Evolution API (Baileys mode = UNOFFICIAL WhatsApp Web protocol; use a spare test SIM).

Run:   uvicorn whatsapp.evolution_bot:app --port 8001      (from repo root)
Check: python3 -m whatsapp.evolution_bot                   (offline, send_text mocked)
Env:   EVOLUTION_URL, EVOLUTION_INSTANCE, AUTHENTICATION_API_KEY  (see whatsapp/evolution/.env.example), ONBOARD_URL
Every sender is answered from their own business (engine.tenants); unknown numbers get the onboarding link.
"""
import base64
import re
import os
import threading

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request

from engine import ledger, tenants
from engine.answer import answer as engine_answer, undo as engine_undo, reset as engine_reset

app = FastAPI()
env = os.environ.get
lock = threading.Lock()  # ponytail: one message at a time (a "yes" must not overtake its question); per-sender locks if throughput matters

# Parser and STT live in ui/llm.py (Groq parse, OpenRouter scribe-v2 -> Whisper); keys come from the env or a git-ignored .env.
# The LLM only fills the Scenario; the engine does all the numbers.
try:
    from ui.llm import parse as parse_scenario, transcribe as _stt
    transcribe = lambda audio, hint=None: _stt(audio, "audio/ogg", hint)  # WhatsApp voice notes are OGG/Opus
except ImportError:
    def parse_scenario(text: str, buyers=None, today=None) -> dict:  # offline placeholder
        return {"type": "status", "party": None, "amount_inr": None, "days": None, "pct": None,
                "date": None, "obligation": None, "transcript": text,
                "needs_clarification": False, "question": None}
    transcribe = None
from whatsapp.reply import bill_list, entry_text, format_reply, invoice_list, readback

try:
    from engine.answer import SUPPORTED as supported
except ImportError:
    supported = None
YES = {"हो", "होय", "हां", "हाँ", "ठीक", "yes", "y", "ok", "okay", "haan", "ha", "han", "ho", "hoy", "ji", "theek"}
NO = {"नाही", "नको", "नहीं", "नही", "no", "n", "nahi", "nahin", "nai"}
RISK = {"risk", "risky", "safe", "check", "रिस्क", "जोखिम", "धोका"}  # "no, tell me the risk": the owner wants the what-if answered
WORD = re.compile(r"[\wऀ-ॣ]+")  # \w alone splits Devanagari at vowel signs: "हाँ" -> "ह"
JOIN = re.compile(r"\bjoin\b\W*((?:\d\s?){6})(?!\d)", re.I)  # "JOIN 123456", "join 123 456", "Join 1 2 3 4 5 6." (voice)
asked: dict[str, tuple[str, str, dict]] = {}  # sender -> (original text, our clarification question, what we parsed so far)
last_result: dict[str, dict] = {}  # sender -> engine result, charted after the reply
pending: dict[str, dict] = {}  # sender -> scenario awaiting yes/no (demo only)


START = ("Tell me what money is coming in and going out, and I'll forecast from there:\n"
         "• Add invoice: Sharma Traders, 50 thousand, dated today\n• I have a 30 thousand rent bill due 1 Nov, add it")


def no_data(tid: str) -> bool:
    """Signed up on the website without a spreadsheet and nothing added yet: a forecast would be empty."""
    inv, obl, _ = ledger.load(tid)
    return inv.empty and obl.empty


def join(sender: str, code: str) -> str:
    tid = tenants.claim(code, sender)
    if not tid:
        return ("That code isn't valid, was already used, or was made for a different number. Send *JOIN <6-digit code>* "
                "from the WhatsApp number you gave on the sign-up page.")
    for d in (asked, pending, last_result):  # a number that moves business starts clean
        d.pop(sender, None)
    prof = ledger.profile(tid)
    if no_data(tid):
        return f"Welcome, *{prof['business_name']}*! This number is now linked.\n\n{START}"
    b = prof["buyers"] or ["your buyer"]
    demo = "\n\n_Demo data is synthetic._" if prof.get("synthetic") else ""
    return (f"Welcome, *{prof['business_name']}*! This number is now linked. Try:\n"
            f"• What if {b[0]} pays 30 days late?\n• Can I take a 5 lakh order from {b[-1]} on 60-day terms?\n"
            f"Type or send a voice note.{demo}")


def reply_for(sender: str, text: str) -> str:
    if m := JOIN.search(text):
        return join(sender, re.sub(r"\D", "", m.group(1)))
    if tid := tenants.claim_phone(sender):  # first message from the number given at sign-up: link it (even if it was linked to another business), then answer
        for d in (asked, pending, last_result):
            d.pop(sender, None)
        return f"Welcome, *{ledger.profile(tid)['business_name']}*! This number is now linked.\n\n{answer_for(sender, tid, text)}"
    if tid := tenants.tenant_for(sender):
        return answer_for(sender, tid, text)
    # never answer a stranger from anyone's data
    return (f"Hi! I don't know this number yet. Set up your business at {env('ONBOARD_URL', 'http://localhost:8000/onboard')} "
            "and then message us from the WhatsApp number you signed up with.")


def run(sender: str, tid: str, s: dict) -> str:
    try:
        r = engine_answer(s, tenant=tid)
    except ValueError as e:
        return str(e)
    last_result[sender] = r
    return format_reply(r)


def answer_for(sender: str, tid: str, text: str) -> str:
    prof = ledger.profile(tid)
    words = WORD.findall(text.lower())  # voice transcripts come with punctuation ("Yes.")
    t = words[0] if words else ""
    if t == "undo":  # owner entries: undo the last one, or reset to the base data (confirmed first)
        e = engine_undo(tenant=tid)
        return f"Removed. {entry_text(e)}" if e else "Nothing to undo."
    if t == "reset":
        pending[sender] = {"type": "reset"}
        return "Remove *all* invoices and bills you added and go back to the base data?\n\nReply *yes* or *no*."
    if sender in pending and pending[sender]["type"] not in ("reset", "add_invoice") and (RISK & set(words) or "what if" in text.lower()):
        s = pending.pop(sender)  # a what-if never saves; a bill they were asked to save becomes "what if I pay it"
        return run(sender, tid, {**s, "type": "expense_shock"} if s["type"] == "add_obligation" else s)
    if sender in pending and t in YES:
        if pending[sender]["type"] == "reset":
            pending.pop(sender)
            return f"Back to the base data: removed {engine_reset(tenant=tid)} added entries."
        return run(sender, tid, pending.pop(sender))
    if sender in pending and t in NO:
        s = pending.pop(sender)
        if s["type"] == "add_obligation":  # "don't save it" almost always means "but can I pay it?": show that instead
            return f"Not saved. Here is the risk if you pay it:\n\n{run(sender, tid, {**s, 'type': 'expense_shock'})}"
        return "OK, please say it again."
    try:
        s = None
        if sender in asked:  # the reply may answer our question, or be a whole new question that stands on its own
            orig, q, prev = asked.pop(sender)
            if prev.get("amount_inr") and prev.get("date") and (RISK & set(words) or "what if" in text.lower() or t in NO):
                # "save it or what-if?" answered "no / what if / tell me the risk": run that what-if, no second guess
                return run(sender, tid, {**prev, "type": "expense_shock", "needs_clarification": False, "question": None})
            alone = parse_scenario(text, buyers=prof["buyers"], today=prof["today"])
            if not alone.get("needs_clarification") and (alone.get("amount_inr") or alone.get("party") or alone["type"].startswith("list_")):
                s = alone
            else:  # a short answer ("Buyer A", "what if"): read it with the question it answers, not the whole chat
                text = f"{orig}\nQuestion asked: {q}\nOwner's answer: {text}"
        s = s or parse_scenario(text, buyers=prof["buyers"], today=prof["today"])
    except Exception:  # LLM down / key missing / timed out: not the owner's fault
        return "I'm a bit busy right now, please send that again in a minute."
    if s.get("needs_clarification"):
        asked[sender] = (text, s["question"], s)
        return s["question"]
    if not s["type"].startswith("add_") and no_data(tid):  # a what-if on an empty ledger would say "0% risk"
        return f"I don't have any of your numbers yet. {START}"
    if s["type"] in ("list_invoices", "list_obligations"):  # reads the ledger, saves nothing: answer at once
        inv, obl, _ = ledger.load(tid)
        if s["type"] == "list_obligations":
            return bill_list(obl, prof["today"])
        return invoice_list(inv, prof["today"], s.get("party") if s.get("party") in prof["buyers"] else None)
    if supported is not None and s["type"] not in supported:  # don't ask to confirm what the engine will refuse
        return ("I can't model that yet.\nI can answer: *status*, *new order*, *buyer pays late*, *one-off expense*, "
                "*payment from a buyer*, save an *invoice* / *bill* you tell me about, or *list* your invoices or bills.\n"
                f"Buyers I know: {', '.join(prof['buyers'])}.")
    if s["type"] == "status":  # saves nothing: answer at once
        return run(sender, tid, s)
    pending[sender] = s
    return readback(s, prof["params"].get("gst_rate", 0.18))


def _evo(path: str, body: dict) -> httpx.Response:
    r = httpx.post(f"{env('EVOLUTION_URL', 'http://localhost:8080')}{path}/{env('EVOLUTION_INSTANCE')}",
                   headers={"apikey": env("AUTHENTICATION_API_KEY", "")}, json=body, timeout=30)
    r.raise_for_status()
    return r


def send_text(number: str, text: str) -> None:
    _evo("/message/sendText", {"number": number, "text": text})


def send_chart(number: str, r: dict) -> None:
    from whatsapp.chart import chart_png
    _evo("/message/sendMedia", {"number": number, "mediatype": "image", "mimetype": "image/png",
                                "fileName": "kabtak.png", "media": base64.b64encode(chart_png(r)).decode()})


def audio_bytes(data: dict) -> bytes:
    # base64 is inlined only if the instance webhook was set with base64 enabled; else ask Evolution for it.
    b64 = data["message"].get("base64")
    if not b64:  # UNVERIFIED against a live server
        b64 = _evo("/chat/getBase64FromMediaMessage", {"message": {"key": data["key"]}}).json()["base64"]
    return base64.b64decode(b64)


def handle(d: dict, sender: str) -> None:
    """Parse, run the engine and reply. Runs after the webhook has been acked."""
    msg = d.get("message") or {}
    text = msg.get("conversation") or (msg.get("extendedTextMessage") or {}).get("text") or ""
    heard = "audioMessage" in msg
    doc = "documentMessage" in msg or "documentWithCaptionMessage" in msg
    with lock:
        try:
            if heard:
                if transcribe is None:
                    text, out = "", "Voice notes aren't wired yet (STT pending). Please type your question."
                else:
                    try:  # the tenant's buyer names bias speech-to-text
                        tid = tenants.tenant_for(sender)
                        text = transcribe(audio_bytes(d), ", ".join(ledger.profile(tid)["buyers"]) if tid else None)
                    except Exception:
                        text, out = "", "Couldn't read the voice note. Please type your question."
            if text:
                out = reply_for(sender, text)
                if heard:
                    out = f'_Heard: "{text}"_\n\n{out}'
            elif doc:
                out = (f"I can't open files here. Excel files are uploaded on the sign-up page, before you link this number: "
                       f"{env('ONBOARD_URL', 'http://localhost:8000/onboard')}\nHere you can type or send a voice note.")
            elif not heard:
                return
            send_text(sender, out)
            if sender in last_result:
                try:
                    send_chart(sender, last_result.pop(sender))
                except Exception as e:  # chart is a bonus; the text reply already went out
                    print("chart failed:", e)
        except Exception as e:  # nobody retries a background task; don't leave a half-handled message
            print("handle failed:", e)


@app.post("/webhook")
@app.post("/webhook/{event:path}")  # also accepts webhook-by-events URLs, e.g. /webhook/messages-upsert
async def webhook(request: Request, tasks: BackgroundTasks, event: str = ""):
    try:
        body = await request.json()
    except ValueError:
        raise HTTPException(400, "Body must be JSON")
    if not isinstance(body, dict):
        raise HTTPException(400, "Body must be a JSON object")
    if str(body.get("event", "")).lower().replace("_", ".") != "messages.upsert":
        return {"ok": True}
    d = body["data"]
    k = d["key"]
    if k.get("fromMe"):  # ignore our own echoes
        return {"ok": True}
    if not tenants.first_time(k["id"]):  # Evolution retries slow webhooks; a retry must never run (or save) twice
        return {"ok": True, "duplicate": True}
    # newer WhatsApp sends @lid ids; the real number is in remoteJidAlt
    sender = (k.get("remoteJidAlt") if k["remoteJid"].endswith("@lid") and k.get("remoteJidAlt") else k["remoteJid"]).split("@")[0]
    tasks.add_task(handle, d, sender)
    return {"ok": True}  # ack at once; the LLM and engine run in the background


if __name__ == "__main__":
    import itertools
    import json
    import tempfile
    from datetime import date
    from pathlib import Path
    from unittest import mock

    from fastapi.testclient import TestClient

    ids = itertools.count(1)

    def payload(msg, sender="919999999999", mid=None):
        return {"event": "messages.upsert", "instance": "kabtak", "data": {
            "key": {"remoteJid": f"{sender}@s.whatsapp.net", "fromMe": False, "id": mid or f"M{next(ids)}"},
            "pushName": "Owner", "message": msg, "messageType": "conversation"}}

    order = {"type": "new_order", "party": "Bajaj", "amount_inr": 1200000, "days": 90, "pct": None, "date": None,
             "obligation": None, "transcript": "x", "needs_clarification": False, "question": None}
    result = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "engine_result.json").read_text())
    profiles = {  # two businesses, mocked: the engine is workstream A's
        "biz-a": {"business_name": "Mahesh Precision Components", "buyers": ["Buyer A", "Buyer B", "CPSE"], "today": date(2026, 10, 25),
                  "synthetic": True, "params": {}},
        "biz-b": {"business_name": "Om Textiles", "buyers": ["Ravi Mills", "Sai Traders"], "today": date(2026, 11, 1),
                  "synthetic": False, "params": {"gst_rate": 0.05}}}
    A, B, X = "919000000001", "919000000002", "919000000003"   # owner of biz-a, owner of biz-b, stranger
    onboard = "http://localhost:8000/onboard"

    def late(text, buyers=None, today=None):  # what the parser would return for "<first buyer> pays late"
        return dict(order, type="delay_payment", party=buyers[0], amount_inr=None, days=30)

    c = TestClient(app)
    with tempfile.TemporaryDirectory() as tmp, mock.patch.object(tenants, "DATA_ROOT", Path(tmp)), \
            mock.patch.object(ledger, "profile", side_effect=lambda t: profiles[t], create=True), \
            mock.patch(f"{__name__}.send_text") as st, mock.patch(f"{__name__}.send_chart") as sc, \
            mock.patch(f"{__name__}.engine_answer", return_value=result) as ea, \
            mock.patch(f"{__name__}.engine_undo") as eu, mock.patch(f"{__name__}.engine_reset", return_value=2) as er, \
            mock.patch(f"{__name__}.parse_scenario", side_effect=late) as ps, \
            mock.patch(f"{__name__}.no_data", return_value=False) as nd:
        def say(text, sender, mid=None):
            assert c.post("/webhook", json=payload({"conversation": text}, sender, mid)).status_code == 200
            assert st.call_args[0][0] == sender
            return st.call_args[0][1]

        # (a) a stranger gets the onboarding link; no engine, no parser, no demo-tenant fallback
        for t in ("what is my status?", "reset", "undo", "yes", "JOIN 12345"):
            r = say(t, X)
            assert onboard in r and "signed up with" in r, r
        with mock.patch.dict(os.environ, {"ONBOARD_URL": "https://kabtak.example/onboard"}):
            assert "https://kabtak.example/onboard" in say("hi", X)
        assert not (ps.called or ea.called or eu.called or er.called) and tenants.tenant_for(X) is None

        # (b) JOIN links the number; a wrong code is refused; a code works once
        ca, cb = tenants.new_join_code("biz-a"), tenants.new_join_code("biz-b")
        wrong = next(f"{n:06d}" for n in itertools.count() if f"{n:06d}" not in (ca, cb))
        assert "isn't valid" in say(f"JOIN {wrong}", X) and tenants.tenant_for(X) is None
        r = say(f"join {ca[:3]} {ca[3:]}", A)  # case and spaces are fine
        assert tenants.tenant_for(A) == "biz-a" and "Mahesh Precision Components" in r and "Buyer A pays 30 days late" in r and "synthetic" in r
        assert "isn't valid" in say(f"JOIN {ca}", X) and tenants.tenant_for(X) is None  # already used
        with mock.patch(f"{__name__}.transcribe", return_value=f"Join {' '.join(cb)}.") as tr, \
                mock.patch(f"{__name__}.audio_bytes", return_value=b"ogg"):  # JOIN inside a voice note
            assert c.post("/webhook", json=payload({"audioMessage": {}}, B)).status_code == 200
            assert tr.call_args[0][1] is None  # a stranger has no buyers to hint
        assert tenants.tenant_for(B) == "biz-b" and "Om Textiles" in st.call_args[0][1] and "Ravi Mills" in st.call_args[0][1]
        assert not (ps.called or ea.called)

        # (b2) signed up on the website with a number: its first message links it, no code typed; others can't use it
        P = "917000000000"
        tenants.new_join_code("biz-b", "+91 70000 00000")
        assert "don't know this number" in say("What is the status of my current cash flow?", X) and tenants.tenant_for(X) is None
        r = say("What is the status of my current cash flow?", P)
        assert r.startswith("Welcome, *Om Textiles") and "now linked" in r and tenants.tenant_for(P) == "biz-b", r
        assert "Welcome" not in say("What is the status of my current cash flow?", P)   # only the first message says hello
        pending.pop(P, None)
        asked.pop(P, None)
        ps.reset_mock()

        # (c) each sender hits the engine with their own tenant and the parser with their own buyers, even interleaved
        say("Buyer A pays late?", A)
        assert ps.call_args.kwargs == {"buyers": profiles["biz-a"]["buyers"], "today": date(2026, 10, 25)}
        r = say("Ravi Mills pays late?", B)
        assert ps.call_args.kwargs == {"buyers": profiles["biz-b"]["buyers"], "today": date(2026, 11, 1)} and "Ravi Mills" in r
        assert not ea.called  # (e) nothing runs before the yes
        say("Yes.", A)
        assert ea.call_args.args[0]["party"] == "Buyer A" and ea.call_args.kwargs == {"tenant": "biz-a"}
        say("yes", B)
        assert ea.call_args.args[0]["party"] == "Ravi Mills" and ea.call_args.kwargs == {"tenant": "biz-b"} and ea.call_count == 2
        assert [x[0][0] for x in sc.call_args_list] == [A, B]  # each gets their own chart
        eu.return_value = {"table": "obligations", "row": {"label": "Repair", "amount_inr": 200000, "date": "2026-11-10"}}
        assert "Removed" in say("Undo", B) and eu.call_args.kwargs == {"tenant": "biz-b"}
        say("reset", B)
        assert not er.called  # reset waits for yes
        assert "removed 2" in say("yes", B) and er.call_args.kwargs == {"tenant": "biz-b"}
        inv = dict(order, type="add_invoice", party="Sai Traders", amount_inr=200000, days=None, date="2026-11-02")
        with mock.patch(f"{__name__}.parse_scenario", return_value=inv):
            assert "+ 5% GST" in say("add invoice Sai Traders 2 lakh", B)  # the tenant's own GST rate
        pending.pop(B)
        with mock.patch(f"{__name__}.parse_scenario", return_value=dict(order, type="sales_drop", party=None, pct=20, days=30)):
            r = say("what if sales drop 20% for a month", B)
        assert "can't model" in r and "Ravi Mills, Sai Traders" in r and "Buyer A" not in r  # help names this tenant's buyers

        # (d) the same message id twice is processed once, so a retried "yes" never saves an invoice twice
        n = (ps.call_count, st.call_count)
        say("Buyer A pays late?", A, "RETRY1")
        say("Buyer A pays late?", A, "RETRY1")
        assert (ps.call_count, st.call_count) == (n[0] + 1, n[1] + 1)
        n = ea.call_count
        say("yes", A, "RETRY2")
        say("yes", A, "RETRY2")
        assert ea.call_count == n + 1

        # (e) clarification, @lid, voice, engine errors
        with mock.patch(f"{__name__}.parse_scenario", return_value=dict(order, needs_clarification=True, question="Which buyer?")):
            assert say("what if he pays late?", A) == "Which buyer?"
        unclear = dict(order, needs_clarification=True, question="Which buyer?")
        with mock.patch(f"{__name__}.parse_scenario", side_effect=[unclear, order]) as p2:   # "Buyer B" alone is unclear
            say("Buyer B", A)
            assert "Which buyer?" in p2.call_args[0][0] and "what if he pays late?" in p2.call_args[0][0]
        pending.clear()
        # a whole new question while we wait on ours stands on its own (it used to be glued to the old question)
        spend = dict(order, type="expense_shock", party=None, amount_inr=2_000_000, days=None, date="2026-11-15")
        with mock.patch(f"{__name__}.parse_scenario", return_value=dict(order, type="add_obligation", needs_clarification=True,
                                                                          question="Which kind of bill?")):
            say("Then pay 20 lakh on 15 Nov", A)
        with mock.patch(f"{__name__}.parse_scenario", return_value=spend) as p3:
            r = say("क्या हम 20 लाख का payment 15 नवंबर को कर सकते हैं?", A)
            assert p3.call_count == 1 and "Question asked" not in p3.call_args[0][0] and "One-off expense" in r, r
        pending.clear()
        # "no" to saving a bill shows the risk of paying it instead of a dead end
        bill = dict(order, type="add_obligation", party="Machine repair", obligation="supplier", amount_inr=300_000, days=None,
                    date="2026-11-02")
        with mock.patch(f"{__name__}.parse_scenario", return_value=bill):
            assert "Save this?" in say("I have to pay a 3 lakh repair bill on 2 Nov", A)
        n = ea.call_count
        r = say("No", A)
        assert r.startswith("Not saved. Here is the risk if you pay it") and ea.call_args[0][0]["type"] == "expense_shock" and ea.call_count == n + 1
        assert ea.call_args[0][0]["amount_inr"] == 300_000 and ea.call_args[0][0]["date"] == "2026-11-02" and A not in pending
        last_result.clear()
        save_or_whatif = dict(spend, type="add_obligation", needs_clarification=True,
                              question="Should I save this as a real bill, or is it a what-if?")
        for reply in ("no , tell me the risk", "What if", "नहीं"):   # the live case: answered without asking the model again
            with mock.patch(f"{__name__}.parse_scenario", return_value=save_or_whatif):
                say("Then pay 20 lakh on 15th of November", A)
            n = ea.call_count
            with mock.patch(f"{__name__}.parse_scenario", side_effect=AssertionError("no second parse")):
                assert "Riskiest week" in say(reply, A), reply
            assert ea.call_count == n + 1 and ea.call_args[0][0]["type"] == "expense_shock" and A not in asked
            assert (ea.call_args[0][0]["amount_inr"], ea.call_args[0][0]["date"]) == (2_000_000, "2026-11-15")
        last_result.clear()
        with mock.patch(f"{__name__}.parse_scenario", return_value=spend):   # "no, tell me the risk" at a read-back answers it
            say("pay 20 lakh on 15 Nov", A)
        n = ea.call_count
        assert "Riskiest week" in say("no , tell me the risk", A) and ea.call_count == n + 1 and A not in pending
        with mock.patch(f"{__name__}.parse_scenario", return_value=bill):
            say("3 lakh repair bill on 2 Nov, add it", A)
        n = ea.call_count
        say("what if I just pay it?", A)   # answered as a what-if: the bill is not saved
        assert ea.call_count == n + 1 and ea.call_args[0][0]["type"] == "expense_shock" and A not in pending
        last_result.clear()
        pay = dict(order, type="payment_received", party="Buyer A", amount_inr=2000000, days=None, date="2026-11-03")
        with mock.patch(f"{__name__}.parse_scenario", return_value=pay):
            assert "Incoming payment" in say("Buyer A pays 20L on 3 Nov", A)
            ea.return_value = dict(result, scenario={**result["scenario"], "type": "payment_received"},
                                   baseline={"worst_week": {"p_shortfall": 0.02}})
            assert "vs current forecast" in say("yes", A)
        with mock.patch(f"{__name__}.parse_scenario", return_value=dict(order, type="status", party=None, amount_inr=None, days=None)):
            n = ea.call_count
            assert "Riskiest week" in say("what is the status", A) and ea.call_count == n + 1 and A not in pending  # status saves nothing: no confirm step
        pending.clear()
        ea.side_effect = ValueError("Unknown party: Nobody")
        with mock.patch(f"{__name__}.parse_scenario", return_value=dict(order, type="delay_payment", party="Nobody", days=30)):
            say("x", A)
            assert "Unknown party" in say("yes", A)
        ea.side_effect = None
        lid = payload({"conversation": "hi"}, "123")
        lid["data"]["key"].update(remoteJid="123@lid", remoteJidAlt=f"{B}@s.whatsapp.net")
        assert c.post("/webhook", json=lid).status_code == 200 and st.call_args[0][0] == B and ps.call_args.kwargs["buyers"][0] == "Ravi Mills"
        with mock.patch(f"{__name__}.transcribe", return_value="Ravi Mills pays late") as tr, mock.patch(f"{__name__}.audio_bytes", return_value=b"ogg"):
            c.post("/webhook", json=payload({"audioMessage": {}}, B))
            assert tr.call_args[0][1] == "Ravi Mills, Sai Traders"  # the tenant's buyers bias speech-to-text
            assert st.call_args[0][1].startswith('_Heard: "Ravi Mills pays late"_') and "Please confirm" in st.call_args[0][1]
        n = st.call_count
        with mock.patch(f"{__name__}.audio_bytes", side_effect=RuntimeError):
            c.post("/webhook", json=payload({"audioMessage": {}}, A))
        assert st.call_count == n + 1 and "Couldn't read" in st.call_args[0][1]
        n = st.call_count
        c.post("/webhook", json=payload({"stickerMessage": {}}, A))  # nothing to answer
        assert st.call_count == n
        # (f) yes/no in Devanagari and romanised Hindi/Marathi: whole words survive tokenising
        assert [WORD.findall(w.lower())[0] for w in ("हाँ", "होय", "नाही", "Haan.", "नहीं")] == ["हाँ", "होय", "नाही", "haan", "नहीं"]
        for yes, no in (("हाँ", "नाही"), ("होय", "नको"), ("Haan.", "nahi"), ("ji", "Nahin!"), ("हां।", "नहीं")):
            say("Buyer A pays late?", A)
            n = ea.call_count
            say(yes, A)
            assert ea.call_count == n + 1 and A not in pending, yes
            say("Buyer A pays late?", A)
            assert "say it again" in say(no, A) and ea.call_count == n + 1 and A not in pending, no
        # (g) a phone already linked to one business that signs up again moves to the new one
        tenants.new_join_code("biz-b", f"+{A}")
        r = say("hi", A)
        assert tenants.tenant_for(A) == "biz-b" and r.startswith("Welcome, *Om Textiles"), r
        tenants.link(A, "biz-a")
        pending.clear()
        # (h) a slow or dead LLM is not the owner's fault; a file gets the sign-up page; a non-JSON body is a 400
        with mock.patch(f"{__name__}.parse_scenario", side_effect=TimeoutError):
            assert "a bit busy" in say("Buyer A pays late?", A)
        n = st.call_count
        c.post("/webhook", json=payload({"documentMessage": {"fileName": "books.xlsx"}}, A))
        assert st.call_count == n + 1 and onboard in st.call_args[0][1] and "Excel" in st.call_args[0][1]
        assert c.post("/webhook", content=b"not json").status_code == 400 and c.post("/webhook", json=[1]).status_code == 400
        # (i) list invoices / bills: read straight from the ledger, no engine run, no confirm step
        import pandas as pd
        inv_df = pd.DataFrame([{"invoice_no": "INV-1", "buyer": "Buyer A", "invoice_date": date(2026, 9, 1), "gross_inr": 236000,
                                "paid_date": None, "disputed": 0, "source": "owner"}])
        obl_df = pd.DataFrame([{"date": date(2026, 11, 7), "label": "Wages", "kind": "wages", "amount_inr": 340000}])
        pending.pop(A, None)
        n = ea.call_count
        with mock.patch.object(ledger, "load", return_value=(inv_df, obl_df, {})) as ld:
            with mock.patch(f"{__name__}.parse_scenario", return_value=dict(order, type="list_invoices", party=None)):
                r = say("show my invoices", A)
            assert "Unpaid invoices: 1" in r and "INV-1" in r and "added by you" in r and ld.call_args[0][0] == "biz-a", r
            with mock.patch(f"{__name__}.parse_scenario", return_value=dict(order, type="list_obligations", party=None)):
                assert "*Wages*" in say("list my bills", A)
        assert ea.call_count == n and A not in pending

        nd.return_value = True  # signed up on the website with no spreadsheet: ask for numbers, don't forecast nothing
        with mock.patch(f"{__name__}.parse_scenario", return_value=dict(order, type="status", party=None, amount_inr=None, days=None)):
            c.post("/webhook", json=payload({"conversation": "how are we doing?"}, A))
        assert "don't have any of your numbers" in st.call_args[0][1] and "Add invoice" in st.call_args[0][1]
        with mock.patch(f"{__name__}.parse_scenario", return_value=inv):
            c.post("/webhook", json=payload({"conversation": "add an invoice"}, A))
        assert "Save this?" in st.call_args[0][1]  # adding data still works
    print("ok")
