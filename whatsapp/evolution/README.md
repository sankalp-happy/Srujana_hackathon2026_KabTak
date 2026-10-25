# Kab Tak? on Evolution API

> **Warning:** Evolution API in Baileys mode uses the **unofficial WhatsApp Web protocol**. The number can be banned. Use a **spare test SIM, never the owner's real number**. Evolution's official Cloud API mode is the safer choice for production.

Run everything from the repo root unless noted.

## 1. Start Evolution
```bash
cd whatsapp/evolution && cp .env.example .env
```
Fill in `.env` (values are yours; never commit it). Suggested: `SERVER_URL=http://localhost:8080`, `DATABASE_PROVIDER=postgresql`, `DATABASE_CONNECTION_URI=postgresql://<user>:<pass>@postgres:5432/<db>?schema=evolution_api` (matching the `POSTGRES_*` values), `CACHE_REDIS_ENABLED=true`, `CACHE_REDIS_URI=redis://redis:6379/6`, `AUTHENTICATION_API_KEY=<long random string>`, `EVOLUTION_URL=http://localhost:8080`, `EVOLUTION_INSTANCE=kabtak`.
```bash
docker compose up
```

## 2. Create an instance and scan the QR
```bash
curl -X POST localhost:8080/instance/create -H "apikey: $AUTHENTICATION_API_KEY" -H "Content-Type: application/json" \
  -d '{"instanceName":"kabtak","integration":"WHATSAPP-BAILEYS","qrcode":true}'
```
Open `http://localhost:8080/manager` (log in with the API key) to see the QR, or `GET /instance/connect/kabtak`. On the test SIM's phone: WhatsApp → Linked devices → Link a device → scan.

## 3. Run the adapter and expose it
```bash
export $(grep -v '^#' whatsapp/evolution/.env | xargs)   # adapter reads EVOLUTION_*, AUTHENTICATION_API_KEY
uvicorn whatsapp.evolution_bot:app --port 8001
ngrok http 8001      # or: cloudflared tunnel --url http://localhost:8001
```
Point the webhook at it. Evolution runs in Docker, so if you skip the tunnel use `http://host.docker.internal:8001/webhook`:
```bash
curl -X POST localhost:8080/webhook/set/kabtak -H "apikey: $AUTHENTICATION_API_KEY" -H "Content-Type: application/json" \
  -d '{"webhook":{"enabled":true,"url":"https://<tunnel>/webhook","events":["MESSAGES_UPSERT"],"base64":true}}'
```
`base64: true` inlines voice notes in the payload; otherwise the adapter fetches them via `/chat/getBase64FromMediaMessage`. Message the test number from another phone.

## 4. Self-check (offline, no Docker)
```bash
python3 -m whatsapp.evolution_bot    # prints "ok"
```

## Status
- Parser, Marathi read-back and reply are placeholders until Person A's `whatsapp/scenario.py`, `whatsapp/reply.py` and `transcribe` exist; the adapter imports them automatically when present. Without `transcribe`, voice notes get a "please type" reply.
- Endpoint paths and payload shapes were taken from Evolution's source and docs sites. **Not verified against a live server:** the QR scan, the exact webhook `set` body for your version, and `getBase64FromMediaMessage`.
