"""Tiny HTTP server that serves the live explorer and persists state changes
to .informalizer/knowledge.json. Stdlib only — no extra dependencies.

Endpoints:
  GET  /                — re-renders the explorer HTML (so reloads pick up
                          state changes made via the API or the CLI).
  POST /api/state       — body: {"name": "<obj name>", "state": "known|learning|unknown"}.
                          Resolves the uid against the served source file and
                          calls KnowledgeStore.set_state, which writes through
                          to .informalizer/knowledge.json on each change.
"""

import json
import sqlite3
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable

from .html_renderer import render_explorer_html
from .knowledge_store import KnowledgeStore, VALID_STATES, make_uid


class _Handler(BaseHTTPRequestHandler):
    # Injected by partial() in serve_explorer.
    render_html: Callable[[], str]
    source_file: Path
    store: KnowledgeStore
    valid_names: frozenset

    def log_message(self, format, *args):  # quiet stdlib noise
        return

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            try:
                body = self.render_html().encode("utf-8")
            except Exception as exc:
                self._send(500, str(exc).encode("utf-8"), "text/plain; charset=utf-8")
                return
            self._send(200, body, "text/html; charset=utf-8")
            return
        self.send_error(404)

    def do_POST(self):
        if self.path != "/api/state":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length") or "0")
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            name = payload["name"]
            state = payload["state"]
        except Exception:
            self.send_error(400, "Bad JSON payload")
            return

        if state not in VALID_STATES:
            self.send_error(400, f"Invalid state: {state!r}")
            return
        if name not in self.valid_names:
            self.send_error(404, f"Unknown object: {name!r}")
            return

        uid = make_uid(self.source_file, name)
        self.store.set_state(uid, state)
        self._send(200, b'{"ok":true}', "application/json")


def serve_explorer(
    conn: sqlite3.Connection,
    source_file: Path,
    similar_k: int = 3,
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = True,
) -> None:
    src_path = Path(source_file).resolve()
    store = KnowledgeStore()

    # Validate up front using the caller's connection (main thread).
    from .corpus import get_objects_for_file, open_corpus
    records = get_objects_for_file(conn, src_path)
    if not records:
        raise ValueError(
            f"{src_path} has no objects in the corpus. Run "
            f"`informalizer corpus add {source_file}` first."
        )
    valid_names = frozenset(r.name for r in records)

    # SQLite connections are bound to the thread that created them, but
    # ThreadingHTTPServer dispatches each request to a worker thread. Open
    # a fresh connection per render call.
    def render() -> str:
        req_conn = open_corpus()
        try:
            return render_explorer_html(
                req_conn, src_path,
                knowledge_store=KnowledgeStore(),  # re-read from disk each request
                similar_k=similar_k,
                server_mode=True,
            )
        finally:
            req_conn.close()

    # Stash dependencies on the class — BaseHTTPRequestHandler.__init__ runs
    # the request synchronously, so we can't pass them through __init__ kwargs.
    # staticmethod prevents Python from binding `render` to `self`.
    _Handler.render_html = staticmethod(render)
    _Handler.source_file = src_path
    _Handler.store = store
    _Handler.valid_names = valid_names

    httpd = ThreadingHTTPServer((host, port), _Handler)
    url = f"http://{host}:{port}/"
    print(f"informalizer serve: {url}")
    print(f"  source:   {src_path}")
    print(f"  store:    {store.path}")
    print("  Click states are written through to knowledge.json.")
    print("  Re-run `informalizer wiki` to refresh the wiki.")
    print("  Ctrl+C to stop.")

    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopping.")
    finally:
        httpd.server_close()
