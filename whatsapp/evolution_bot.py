"""Kab Tak? WhatsApp bot on Evolution API (Baileys mode = UNOFFICIAL WhatsApp Web protocol; use a spare test SIM).

Run:   uvicorn whatsapp.evolution_bot:app --port 8001      (from repo root)
Check: python3 -m whatsapp.evolution_bot                   (offline, send_text mocked)
Env:   EVOLUTION_URL, EVOLUTION_INSTANCE, AUTHENTICATION_API_KEY  (see whatsapp/evolution/.env.example)
"""
import base64
import json
import os
from pathlib import Path

import httpx
from fastapi import FastAPI, Request

app = FastAPI()
env = os.environ.get
FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "engine_result.json"

try:
    from engine.answer import answer as engine_answer
except ImportError:  # engine not merged yet
    engine_answer = lambda s: json.loads(FIXTURE.read_text())

# Parser and STT live in ui/llm.py (Groq parse, OpenRouter scribe-v2 -> Whisper); keys come from the env or a git-ignored .env.
# The LLM only fills the Scenario; the engine does all the numbers.
try:
    from ui.llm import parse as parse_scenario, transcribe as _stt
    transcribe = lambda audio: _stt(audio, "audio/ogg")  # WhatsApp voice notes are OGG/Opus
except ImportError:
    def parse_scenario(text: str) -> dict:  # offline placeholder
        return {"type": "status", "party": None, "amount_inr": None, "days": None, "pct": None,
                "date": None, "obligation": None, "transcript": text,
                "needs_clarification": False, "question": None}
    transcribe = None
from whatsapp.reply import format_reply, readback

YES = {"हो", "होय", "हां", "हाँ", "yes", "y", "ok", "okay"}
NO = {"नाही", "नको", "no", "n"}
asked: dict[str, tuple[str, str]] = {}  # sender -> (original text, our clarification question)
pending: dict[str, dict] = {}  # sender -> scenario awaiting yes/no (demo only)


def reply_for(sender: str, text: str) -> str:
    t = text.strip().lower()
    if sender in pending and t in YES:
        try:
            return format_reply(engine_answer(pending.pop(sender)))
        except ValueError as e:
            return str(e)
    if sender in pending and t in NO:
        pending.pop(sender)
        return "OK, please say it again."
    if sender in asked:  # the reply answers our question: parse the last exchange together, not the whole chat
        orig, q = asked.pop(sender)
        text = f"{orig}\nQuestion asked: {q}\nOwner's answer: {text}"
    try:
        s = parse_scenario(text)
    except Exception:  # LLM down / key missing
        return "Sorry, I couldn't understand that. Please rephrase."
    if s.get("needs_clarification"):
        asked[sender] = (text, s["question"])
        return s["question"]
    if s["type"] == "status":  # no fields to misread, so nothing to confirm
        return format_reply(engine_answer(s))
    pending[sender] = s
    return readback(s)


def _evo(path: str, body: dict) -> httpx.Response:
    r = httpx.post(f"{env('EVOLUTION_URL', 'http://localhost:8080')}{path}/{env('EVOLUTION_INSTANCE')}",
                   headers={"apikey": env("AUTHENTICATION_API_KEY", "")}, json=body, timeout=30)
    r.raise_for_status()
    return r


def send_text(number: str, text: str) -> None:
    _evo("/message/sendText", {"number": number, "text": text})


def audio_bytes(data: dict) -> bytes:
    # base64 is inlined only if the instance webhook was set with base64 enabled; else ask Evolution for it.
    b64 = data["message"].get("base64")
    if not b64:  # UNVERIFIED against a live server
        b64 = _evo("/chat/getBase64FromMediaMessage", {"message": {"key": data["key"]}}).json()["base64"]
    return base64.b64decode(b64)


@app.post("/webhook")
@app.post("/webhook/{event:path}")  # also accepts webhook-by-events URLs, e.g. /webhook/messages-upsert
async def webhook(request: Request, event: str = ""):
    body = await request.json()
    if str(body.get("event", "")).lower().replace("_", ".") != "messages.upsert":
        return {"ok": True}
    d = body["data"]
    if d["key"].get("fromMe"):  # ignore our own echoes
        return {"ok": True}
    k = d["key"]  # newer WhatsApp sends @lid ids; the real number is in remoteJidAlt
    sender = (k.get("remoteJidAlt") if k["remoteJid"].endswith("@lid") and k.get("remoteJidAlt") else k["remoteJid"]).split("@")[0]
    msg = d.get("message") or {}
    text = msg.get("conversation") or (msg.get("extendedTextMessage") or {}).get("text") or ""
    if "audioMessage" in msg:
        if transcribe is None:
            text = ""
            out = "Voice notes aren't wired yet (STT pending). Please type your question."
        else:
            try:
                text = transcribe(audio_bytes(d))
            except Exception:
                text, out = "", "Couldn't read the voice note. Please type your question."
    if text:
        out = reply_for(sender, text)
    elif "audioMessage" not in msg:
        return {"ok": True}
    send_text(sender, out)
    return {"ok": True}  # always ack so Evolution doesn't retry


if __name__ == "__main__":
    from unittest import mock

    from fastapi.testclient import TestClient

    def payload(msg):
        return {"event": "messages.upsert", "instance": "kabtak", "data": {
            "key": {"remoteJid": "919999999999@s.whatsapp.net", "fromMe": False, "id": "A1"},
            "pushName": "Owner", "message": msg, "messageType": "conversation"}}

    order = {"type": "new_order", "party": "Bajaj", "amount_inr": 1200000, "days": 90, "pct": None, "date": None,
             "obligation": None, "transcript": "x", "needs_clarification": False, "question": None}
    c = TestClient(app)
    with mock.patch(f"{__name__}.send_text") as st, mock.patch(f"{__name__}.parse_scenario", return_value=order):
        assert c.post("/webhook", json=payload({"conversation": "Bajaj 12 lakh order, 90 days?"})).status_code == 200
        assert "Correct?" in st.call_args[0][1]
        c.post("/webhook/messages-upsert", json=payload({"conversation": "yes"}))  # real engine
        assert st.call_args[0][0] == "919999999999"
        assert "%" in st.call_args[0][1] and "Week of" in st.call_args[0][1]
        with mock.patch(f"{__name__}.parse_scenario", return_value=dict(order, needs_clarification=True, question="Which buyer?")) as ps:
            c.post("/webhook", json=payload({"conversation": "what if he pays late?"}))
            assert st.call_args[0][1] == "Which buyer?"
        with mock.patch(f"{__name__}.parse_scenario", return_value=order) as ps:
            c.post("/webhook", json=payload({"conversation": "Buyer A"}))
            assert "Which buyer?" in ps.call_args[0][0] and "what if he pays late?" in ps.call_args[0][0]
        pending.clear()
        n = st.call_count
        with mock.patch(f"{__name__}.parse_scenario", return_value=dict(order, type="status", party=None, amount_inr=None, days=None)):
            c.post("/webhook", json=payload({"conversation": "what is the status"}))
        assert st.call_count == n + 1 and "Correct?" not in st.call_args[0][1]  # answered directly
        bad = dict(order, type="delay_payment", party="Nobody", days=30)
        with mock.patch(f"{__name__}.parse_scenario", return_value=bad):
            c.post("/webhook", json=payload({"conversation": "x"}))
            c.post("/webhook", json=payload({"conversation": "yes"}))
        assert "Unknown party" in st.call_args[0][1]  # engine ValueError message
        lid = payload({"conversation": "hi"})
        lid["data"]["key"].update(remoteJid="123@lid", remoteJidAlt="918888888888@s.whatsapp.net")
        c.post("/webhook", json=lid)
        assert st.call_args[0][0] == "918888888888"
        n = st.call_count
        c.post("/webhook", json=payload({"audioMessage": {}}))
        assert st.call_count == n + 1
    print("ok")
