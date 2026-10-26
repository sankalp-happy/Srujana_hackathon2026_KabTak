"""Kab Tak? server: landing page at /, sign-up at /onboard, dashboard at /dashboard; answers scenarios.

Run from the repo root:  python3 ui/server.py   (then open http://localhost:8000)
"""
import base64, binascii, json, os, re, sys
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
RESULT = os.environ.get("KABTAK_RESULT", "fixtures/engine_result.json")

UI = Path(__file__).resolve().parent
LANDING = UI.parent / "landing-page" / "index.html"
BOT_NUMBER = os.environ.get("BOT_NUMBER", "916205559096")   # the Kab Tak? WhatsApp bot; set BOT_NUMBER to use another
TERMS_VERSION = "2026-10-25"   # bump when ui/terms.html changes
STATUS = {"type": "status", "party": None, "amount_inr": None, "days": None, "pct": None, "date": None,
          "obligation": None, "transcript": None, "needs_clarification": False, "question": None}


def tenant_name(tid):
    """(business_name, synthetic) from the tenant's profile.json, or (None, None) if there isn't one."""
    try:
        from engine import tenants
        p = json.loads((tenants.tenant_dir(tid) / "profile.json").read_text(encoding="utf-8"))
        return p.get("business_name"), p.get("synthetic")
    except (OSError, ValueError, ImportError):
        return None, None


def signup(body):
    """Step 1 of sign-up: name, business, WhatsApp number (+ optional bank balance) -> an empty business and a
    join code that only that number can use. -> {tenant_id, join_code, bot_number}. Bad input raises ValueError."""
    import ingest
    from engine import tenants
    owner = re.sub(r"\s+", " ", str(body.get("owner_name") or "")).strip()
    if not 0 < len(owner) <= 80:
        raise ValueError("Please enter your name.")
    digits = re.sub(r"\D", "", str(body.get("phone") or ""))
    phone = "91" + digits if len(digits) == 10 else digits   # 10 digits = an Indian mobile without +91
    if not re.fullmatch(r"91[6-9]\d{9}", phone):
        raise ValueError("Enter your 10-digit WhatsApp number.")
    bank = body.get("bank_inr")
    tid = ingest.write_tenant(body.get("business_name"), {"bank_inr": 0 if bank in (None, "") else bank},
                              owner_name=owner, phone=phone)
    return {"tenant_id": tid, "join_code": tenants.new_join_code(tid, phone), "bot_number": BOT_NUMBER}


def _signed(body):
    """The sign-up page's own business: its id plus its still-unused join code. -> tenant id, else PermissionError."""
    from engine import tenants
    tid = str(body.get("tenant_id") or "")
    if not (tenants.exists(tid) and tenants.unclaimed(body.get("join_code", ""), tid)):
        raise PermissionError("This sign-up page has expired. Send your invoices on WhatsApp instead.")
    return tid


def terms(body):
    """Record that the owner ticked the Terms of Service (and the less-data warning) on the sign-up page."""
    from datetime import datetime, timezone
    from engine import tenants
    tid = _signed(body)
    f = tenants.tenant_dir(tid) / "profile.json"
    prof = json.loads(f.read_text())
    prof.update(terms_version=TERMS_VERSION, terms_accepted_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    f.write_text(json.dumps(prof, indent=2, ensure_ascii=False))
    return {"ok": True}


def excel(body):
    """Step 2, option 1: the owner's Kab Tak? workbook becomes the business's ledger. Allowed while the sign-up's join
    code is unused (only that page has it). -> what was loaded, and the first forecast."""
    import ingest
    from engine.answer import answer, reload
    tid = _signed(body)
    raw = base64.b64decode(body["content_b64"], validate=True)
    if len(raw) > 5_000_000:
        raise ValueError("Send a file of 5 MB or less.")
    inv, obl, pos, errors = ingest.read_workbook(raw)
    buyers = ingest.fill_tenant(tid, inv, obl, pos)
    reload(tid)
    r = answer(STATUS, tenant=tid)
    return {"invoices": len(inv), "open_invoices": sum(not x["paid_date"] for x in inv), "bills": len(obl),
            "buyers": buyers, "position_loaded": pos is not None, "skipped": len(errors),
            "errors": errors[:ingest.MAX_ERRORS], "worst_week": r["worst_week"]}


def fixture():
    with open(RESULT, encoding="utf-8") as f:
        return json.load(f)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(UI), **kw)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")  # demo edits show on reload
        super().end_headers()

    def send_json(self, status, body):
        data = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def tenant(self, tid):
        """Validate a tenant id from the request. -> (ok, tid); tid None = the demo tenant. Sends the error itself."""
        if not tid:
            return True, None
        from engine import tenants
        try:
            known = tenants.exists(tid)
        except ValueError:
            known = False
        if not known:
            self.send_json(404, {"error": f"Unknown business {tid!r}."})
            return False, None
        return True, tid

    def send_page(self, f):
        data = f.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/" and LANDING.exists():   # no landing page checked out: / stays the dashboard
            return self.send_page(LANDING)
        if url.path in ("/onboard", "/dashboard", "/terms"):
            self.path = {"/onboard": "/onboard.html", "/dashboard": "/index.html", "/terms": "/terms.html"}[url.path]
        if url.path == "/api/result":  # first screen: live status check, fixture if KABTAK_RESULT is set or no engine
            ok, tid = self.tenant(parse_qs(url.query).get("tenant", [None])[0])
            if not ok:
                return
            name, synthetic = tenant_name(tid or "mahesh-cnc")
            who = {"business_name": name, "synthetic": synthetic}
            if "KABTAK_RESULT" not in os.environ:
                try:
                    from engine.answer import answer
                    return self.send_json(200, {"source": "engine", **who, "result": answer(STATUS, **({"tenant": tid} if tid else {}))})
                except ImportError:
                    pass
            if tid:
                return self.send_json(503, {"error": "No engine here, so there is no forecast for this business."})
            return self.send_json(200, {"source": f"fixture: {RESULT}", **who, "result": fixture()})
        return super().do_GET()

    def onboard(self):
        """POST /api/signup, /api/onboard/excel and /api/onboard/terms: JSON in, JSON out."""
        n = int(self.headers.get("Content-Length", 0))
        if not 0 < n <= 7_000_000:  # 5 MB file as base64
            return self.send_json(413, {"error": "Send a file of 5 MB or less."})
        try:
            body = json.loads(self.rfile.read(n))
            return self.send_json(200, {"/api/signup": signup, "/api/onboard/excel": excel, "/api/onboard/terms": terms}[self.path](body))
        except PermissionError as e:
            return self.send_json(403, {"error": str(e)})
        except (ValueError, KeyError, TypeError, AttributeError, binascii.Error) as e:  # bad input, not a server bug
            return self.send_json(422, {"error": f"Couldn't use that: {e}"})

    def do_POST(self):
        if self.path in ("/api/signup", "/api/onboard/excel", "/api/onboard/terms"):
            return self.onboard()
        if self.path not in ("/api/answer", "/api/parse", "/api/explain", "/api/transcribe"):
            return self.send_json(404, {"error": "not found"})
        if self.path == "/api/transcribe":  # body is the raw recording from the mic button
            n = int(self.headers.get("Content-Length", 0))
            if not 0 < n <= 25_000_000:  # Groq's upload limit
                return self.send_json(400, {"error": "Recording is empty or too long."})
            import llm
            try:
                return self.send_json(200, {"text": llm.transcribe(self.rfile.read(n), self.headers.get("Content-Type", "audio/webm"))})
            except Exception as e:
                return self.send_json(502, {"error": f"Speech-to-text unavailable ({e}). Type the question instead."})
        try:
            scenario = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        except ValueError:
            return self.send_json(400, {"error": "Scenario is not valid JSON."})
        ok, tid = self.tenant(scenario.pop("tenant", None) if isinstance(scenario, dict) else None)
        if not ok:
            return
        if self.path != "/api/answer":  # free-text box: LLM parses the question / explains the result
            import llm
            try:
                if self.path == "/api/parse":
                    if tid:
                        from engine import ledger
                        prof = ledger.profile(tid)
                        return self.send_json(200, {"scenario": llm.parse(scenario["text"], buyers=prof["buyers"], today=prof["today"])})
                    return self.send_json(200, {"scenario": llm.parse(scenario["text"])})
                return self.send_json(200, llm.explain(scenario["question"], scenario["result"], scenario.get("lang")))
            except Exception as e:
                return self.send_json(502, {"error": f"Language model unavailable ({e}). Use the form instead."})
        try:
            from engine.answer import answer
        except ImportError:
            if tid:
                return self.send_json(503, {"error": "No engine here, so there is no forecast for this business."})
            return self.send_json(200, {"source": f"fixture: {RESULT} (engine not available)", "result": fixture()})
        try:
            return self.send_json(200, {"source": "engine", "result": answer(scenario, **({"tenant": tid} if tid else {}))})
        except ValueError as e:
            return self.send_json(422, {"error": str(e)})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Kab Tak? UI on http://localhost:{port}  (result file: {RESULT})")
    ThreadingHTTPServer((os.environ.get("HOST", "127.0.0.1"), port), Handler).serve_forever()
