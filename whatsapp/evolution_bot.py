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

# Person A's pipeline, if merged on this branch; otherwise the placeholders below.
try:
    from whatsapp.scenario import parse_scenario
except ImportError:
    def parse_scenario(text: str) -> dict:  # TODO(Person A): replace with the real LLM parser
        return {"type": "status", "party": None, "amount_inr": None, "days": None, "pct": None,
                "date": None, "obligation": None, "transcript": text,
                "needs_clarification": False, "question": None}
try:
    from whatsapp.reply import format_reply
except ImportError:
    def format_reply(result: dict) -> str:  # TODO(Person A): 2-line Marathi reply
        w = result["worst_week"]
        return f"Week of {w['week_start']}: {round(w['p_shortfall'] * 100)}% chance of running short ({w['obligation']})."
try:
    from whatsapp.app import transcribe  # Sarvam STT (A4), if it exists
except ImportError:
    transcribe = None

YES = {"हो", "होय", "हां", "हाँ", "yes", "y", "ok", "okay"}
NO = {"नाही", "नको", "no", "n"}
pending: dict[str, dict] = {}  # sender -> scenario awaiting yes/no (demo only)


def readback(s: dict) -> str:  # TODO(Person A): Marathi read-back
    parts = [s["type"]] + [f"{k}={s[k]}" for k in ("party", "amount_inr", "days", "pct", "date", "obligation") if s.get(k) is not None]
    return f"{', '.join(parts)}. Correct? (हो / नाही)"


def reply_for(sender: str, text: str) -> str:
    t = text.strip().lower()
    if sender in pending and t in YES:
        try:
            return format_reply(engine_answer(pending.pop(sender)))
        except ValueError as e:
            return str(e)
    if sender in pending and t in NO:
        pending.pop(sender)
        return "ठीक आहे, पुन्हा सांगा."
    s = parse_scenario(text)
    if s.get("needs_clarification"):
        return s["question"]
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
    sender = d["key"]["remoteJid"].split("@")[0]  # ponytail: @lid JIDs aren't phone numbers; Evolution swaps in remoteJidAlt when it can
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

    c = TestClient(app)
    with mock.patch(f"{__name__}.send_text") as st:
        assert c.post("/webhook", json=payload({"conversation": "Can I pay wages on the 7th?"})).status_code == 200
        assert "Correct?" in st.call_args[0][1]
        c.post("/webhook/messages-upsert", json=payload({"conversation": "हो"}))
        assert st.call_args[0][0] == "919999999999"
        assert "%" in st.call_args[0][1]
        n = st.call_count
        c.post("/webhook", json=payload({"audioMessage": {}}))
        assert st.call_count == n + 1
    print("ok")
