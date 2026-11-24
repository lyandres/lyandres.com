#!/usr/bin/env python3
"""Local preview server: python3 tools/serve.py [port]

Same as `python3 -m http.server`, but tells the browser never to cache, so a
rebuilt page always shows on a normal reload.
"""
import functools
import http.server
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Expires", "0")
        super().end_headers()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    http.server.ThreadingHTTPServer(("", port), functools.partial(Handler, directory=ROOT)).serve_forever()
