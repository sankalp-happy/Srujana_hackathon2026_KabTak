"""WhatsApp webhook with swappable providers (Twilio Sandbox or Meta Cloud API).

Run:  uvicorn app:app --port 8000        (from this folder)
Pick: PROVIDER=twilio | meta   (see .env.example)
Check: python app.py            (offline self-check, no network)
"""
import base64
import hashlib
import hmac
import json
import os
from dataclasses import dataclass

import httpx
from fastapi import FastAPI, HTTPException, Request, Response

app = FastAPI()
env = os.environ.get


@dataclass
class Msg:
    sender: str  # E.164 digits, no "whatsapp:" prefix
    text: str = ""
    audio_url: str = ""  # voice note; fetch with fetch_audio()


def handle(m: Msg) -> str:
    """Plug the Kab Tak pipeline in here: voice -> STT -> scenario -> simulator -> reply text."""
    if m.audio_url:
        return "Voice note received (STT not wired yet)."
    return f"You said: {m.text}"


# ---------- providers ----------
def send_message(to: str, text: str) -> None:
    if env("PROVIDER", "twilio") == "meta":
        r = httpx.post(
            f"https://graph.facebook.com/v21.0/{env('META_PHONE_NUMBER_ID')}/messages",
            headers={"Authorization": f"Bearer {env('META_TOKEN')}"},
            json={"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text}},
        )
    else:
        sid = env("TWILIO_SID")
        r = httpx.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
            auth=(sid, env("TWILIO_TOKEN")),
            data={"From": env("TWILIO_FROM", "whatsapp:+14155238886"), "To": f"whatsapp:+{to}", "Body": text},
        )
    r.raise_for_status()


def fetch_audio(m: Msg) -> bytes:
    """Download a voice note. Meta gives a media id (resolve to URL first); Twilio gives a URL (basic auth)."""
    if env("PROVIDER", "twilio") == "meta":
        h = {"Authorization": f"Bearer {env('META_TOKEN')}"}
        url = httpx.get(f"https://graph.facebook.com/v21.0/{m.audio_url}", headers=h).json()["url"]
        return httpx.get(url, headers=h).content
    return httpx.get(m.audio_url, auth=(env("TWILIO_SID"), env("TWILIO_TOKEN")), follow_redirects=True).content


def parse_meta(body: dict) -> list[Msg]:
    out = []
    for e in body.get("entry", []):
        for c in e.get("changes", []):
            for x in c.get("value", {}).get("messages", []):
                if x["type"] == "text":
                    out.append(Msg(x["from"], text=x["text"]["body"]))
                elif x["type"] == "audio":
                    out.append(Msg(x["from"], audio_url=x["audio"]["id"]))
    return out


def twilio_sig(token: str, url: str, params: dict) -> str:
    s = url + "".join(k + params[k] for k in sorted(params))
    return base64.b64encode(hmac.new(token.encode(), s.encode(), hashlib.sha1).digest()).decode()


# ---------- routes ----------
@app.get("/webhook/meta")
def meta_verify(request: Request):
    q = request.query_params
    if q.get("hub.mode") == "subscribe" and q.get("hub.verify_token") == env("META_VERIFY_TOKEN"):
        return Response(q.get("hub.challenge"), media_type="text/plain")
    raise HTTPException(403)


@app.post("/webhook/meta")
async def meta_in(request: Request):
    raw = await request.body()
    if secret := env("META_APP_SECRET"):
        want = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(want, request.headers.get("X-Hub-Signature-256", "")):
            raise HTTPException(403)
    for m in parse_meta(json.loads(raw)):
        send_message(m.sender, handle(m))
    return {"ok": True}  # Meta retries on non-200, so always ack


@app.post("/webhook/twilio")
async def twilio_in(request: Request):
    p = {k: str(v) for k, v in (await request.form()).items()}
    if token := env("TWILIO_TOKEN"):
        url = env("PUBLIC_BASE_URL", "").rstrip("/") + "/webhook/twilio"
        if not hmac.compare_digest(twilio_sig(token, url, p), request.headers.get("X-Twilio-Signature", "")):
            raise HTTPException(403)
    audio = p.get("MediaUrl0", "") if p.get("MediaContentType0", "").startswith("audio") else ""
    m = Msg(p["From"].removeprefix("whatsapp:+"), text=p.get("Body", ""), audio_url=audio)
    send_message(m.sender, handle(m))
    return Response("<Response/>", media_type="application/xml")  # reply sent via REST above


if __name__ == "__main__":
    meta = {"entry": [{"changes": [{"value": {"messages": [
        {"from": "919999999999", "type": "text", "text": {"body": "hi"}},
        {"from": "919999999999", "type": "audio", "audio": {"id": "MID"}}]}}]}]}
    a, b = parse_meta(meta)
    assert a == Msg("919999999999", text="hi") and b.audio_url == "MID"
    # Twilio's documented test vector shape: signature must change if any param changes
    assert twilio_sig("t", "https://x/y", {"A": "1"}) != twilio_sig("t", "https://x/y", {"A": "2"})
    assert handle(a) == "You said: hi"
    print("ok")
