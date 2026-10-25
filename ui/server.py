"""Kab Tak? UI server: serves ui/index.html and answers scenarios.

Run from the repo root:  python3 ui/server.py   (then open http://localhost:8000)
"""
import base64, binascii, json, os, sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
RESULT = os.environ.get("KABTAK_RESULT", "fixtures/engine_result.json")

UI = Path(__file__).resolve().parent
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
        from engine import ledger
        if not hasattr(ledger, "profile"):  # ponytail: drop once the engine's tenant API is on main
            self.send_json(501, {"error": "This engine build has no multi-tenant support yet."})
            return False, None
        return True, tid

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/onboard":
            self.path = "/onboard.html"
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
        """POST /api/onboard/preview and /commit: JSON in, JSON out."""
        n = int(self.headers.get("Content-Length", 0))
        if not 0 < n <= 7_000_000:  # 5 MB file as base64
            return self.send_json(413, {"error": "Send a file of 5 MB or less."})
        try:
            body = json.loads(self.rfile.read(n))
            import ingest
            if not body.get("consent"):
                return self.send_json(400, {"error": "Please tick the consent box first."})
            up = body if self.path.endswith("preview") else body.get("upload")
            if up:
                raw = base64.b64decode(up["content_b64"], validate=True)
                if len(raw) > 5_000_000:
                    return self.send_json(413, {"error": "Send a file of 5 MB or less."})
                headers, rows = ingest.read_table(up["filename"], raw)
                if self.path.endswith("preview"):
                    mapping = body.get("mapping") or ingest.map_columns(headers, rows)  # given = the owner edited it: no LLM call
                    return self.send_json(200, {"headers": headers, "mapping": mapping, "total_rows": len(rows),
                                                **ingest.parse_invoices(headers, rows, mapping)})
                good = [r for r in ingest.parse_invoices(headers, rows, up["mapping"])["rows"] if not r["errors"]]
            else:
                good = []
            from engine import tenants
            tid = ingest.write_tenant(body.get("name"), body.get("position") or {}, body.get("recurring") or [], good)
            return self.send_json(200, {"tenant_id": tid, "join_code": tenants.new_join_code(tid),
                                        "bot_number": os.environ.get("BOT_NUMBER", ""), "invoices_loaded": len(good)})
        except (ValueError, KeyError, TypeError, AttributeError, binascii.Error) as e:  # bad input, not a server bug
            return self.send_json(422, {"error": f"Couldn't use that: {e}"})

    def do_POST(self):
        if self.path in ("/api/onboard/preview", "/api/onboard/commit"):
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
    HTTPServer((os.environ.get("HOST", "127.0.0.1"), port), Handler).serve_forever()
