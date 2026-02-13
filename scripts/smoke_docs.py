from __future__ import annotations

import http.server
import os
import socketserver
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "docs"
REQUIRED_PATHS = [
    "/index.html",
    "/styles.css",
    "/app.js",
    "/py/playground.py",
    "/js/schemas.js",
    "/js/runtime.js",
    "/js/runtime.worker.js",
    "/js/consent.js",
    "/js/onboarding.js",
]


def main() -> int:
    os.chdir(ROOT)

    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, fmt: str, *args) -> None:
            return

    with socketserver.TCPServer(("127.0.0.1", 0), QuietHandler) as httpd:
        port = httpd.server_address[1]
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        time.sleep(0.15)

        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            fetched = {}
            for path in REQUIRED_PATHS:
                with opener.open(f"http://127.0.0.1:{port}{path}", timeout=5) as resp:
                    assert resp.status == 200, f"Expected 200 for {path}, got {resp.status}"
                    fetched[path] = resp.read().decode("utf-8", errors="replace")

            html = fetched["/index.html"]
            js = fetched["/app.js"]
            assert 'id="runBtn"' in html
            assert 'id="runFactsOutput"' in html
            assert 'id="validationErrors"' in html
            assert 'id="publicationExportBtn"' in html
            assert 'id="cookieBanner"' in html
            assert 'id="tourModal"' in html
            assert 'data-results-tab="overview"' in html
            assert "Quick Start Presets" in html
            assert 'type="module" src="app.js"' in html
            assert "PlaygroundRuntime" in js
            assert "buildConfigV2" in js
            assert "buildRunResultV2" in js
            assert "initConsentAndOnboarding" in js
            print("docs smoke test: PASS")
            return 0
        finally:
            httpd.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
