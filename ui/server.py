"""Kab Tak? UI server: serves ui/index.html and answers scenarios.

Run from the repo root:  python3 ui/server.py   (then open http://localhost:8000)
"""
import json, os, sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
RESULT = os.environ.get("KABTAK_RESULT", "fixtures/engine_result.json")

UI = Path(__file__).resolve().parent
STATUS = {"type": "status", "party": None, "amount_inr": None, "days": None, "pct": None, "date": None,
          "obligation": None, "transcript": None, "needs_clarification": False, "question": None}


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

    def do_GET(self):
        if self.path == "/api/result":  # first screen: live status check, fixture if KABTAK_RESULT is set or no engine
            if "KABTAK_RESULT" not in os.environ:
                try:
                    from engine.answer import answer
                    return self.send_json(200, {"source": "engine", "result": answer(STATUS)})
                except ImportError:
                    pass
            return self.send_json(200, {"source": f"fixture: {RESULT}", "result": fixture()})
        return super().do_GET()

    def do_POST(self):
        if self.path not in ("/api/answer", "/api/parse", "/api/explain"):
            return self.send_json(404, {"error": "not found"})
        try:
            scenario = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        except ValueError:
            return self.send_json(400, {"error": "Scenario is not valid JSON."})
        if self.path != "/api/answer":  # free-text box: LLM parses the question / explains the result
            import llm
            try:
                if self.path == "/api/parse":
                    return self.send_json(200, {"scenario": llm.parse(scenario["text"])})
                return self.send_json(200, llm.explain(scenario["question"], scenario["result"], scenario.get("lang")))
            except Exception as e:
                return self.send_json(502, {"error": f"Language model unavailable ({e}). Use the form instead."})
        try:
            from engine.answer import answer
        except ImportError:
            return self.send_json(200, {"source": f"fixture: {RESULT} (engine not available)", "result": fixture()})
        try:
            return self.send_json(200, {"source": "engine", "result": answer(scenario)})
        except ValueError as e:
            return self.send_json(422, {"error": str(e)})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Kab Tak? UI on http://localhost:{port}  (result file: {RESULT})")
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()
