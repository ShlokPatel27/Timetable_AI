"""
Lightweight HTTP server for the Timetable GA web interface.
Uses only the Python standard library -- no extra dependencies.

Start:  python server_local.py
Open :  http://localhost:8080
"""

import json
import os
import sys
import io
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Import the GA runner
from timetable_ga import run_ga_api, run_ga_edit


PORT = 8080
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public")


class GAHandler(SimpleHTTPRequestHandler):
    """Serves static files from /public and exposes /api/run."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def do_GET(self):
        if self.path == "/api/run":
            self._handle_run()
        else:
            super().do_GET()

    def do_POST(self):
        if self.path in ("/api/run", "/api/edit"):
            content_length = int(self.headers.get('Content-Length', 0))
            payload = {}
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                try:
                    payload = json.loads(post_data.decode('utf-8'))
                except Exception as e:
                    print(f"Error parsing JSON: {e}", file=sys.__stderr__)
            if self.path == "/api/run":
                self._handle_run(payload)
            else:
                self._handle_edit(payload)
        else:
            self.send_error(404, "Endpoint not found")

    def _handle_edit(self, body=None):
        if body is None:
            body = {}
        old_stdout = sys.stdout
        try:
            sys.stdout = open(os.devnull, "w", encoding="utf-8", errors="replace")
            csv_text = body.get("csv_content", "")
            edit_instruction = body.get("edit_instruction", "")
            config = body.get("config", {})

            result = run_ga_edit(csv_text, edit_instruction, config)

            payload = json.dumps(result, ensure_ascii=False)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(payload.encode("utf-8"))
        except Exception as e:
            import traceback
            traceback.print_exc(file=sys.__stderr__)
            try:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            except Exception:
                pass
        finally:
            try:
                sys.stdout.close()
            except Exception:
                pass
            sys.stdout = old_stdout

    def _handle_run(self, config_dict=None):
        old_stdout = sys.stdout
        try:
            # Redirect stdout to suppress GA print() calls that may contain
            # characters unsupported by the Windows cp1252 console codec.
            sys.stdout = open(os.devnull, "w", encoding="utf-8", errors="replace")

            result = run_ga_api(config_dict)

            payload = json.dumps(result, ensure_ascii=False)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(payload.encode("utf-8"))
        except Exception as e:
            import traceback
            with open("server_error.log", "w", encoding="utf-8") as f:
                traceback.print_exc(file=f)
            traceback.print_exc(file=sys.__stderr__)
            try:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            except Exception:
                pass
        finally:
            try:
                sys.stdout.close()
            except Exception:
                pass
            sys.stdout = old_stdout

    def log_message(self, format, *args):
        try:
            super().log_message(format, *args)
        except OSError:
            pass


if __name__ == "__main__":
    server = HTTPServer(("", PORT), GAHandler)
    print(f"  Timetable GA server running at  http://localhost:{PORT}")
    print("  Press Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")
        server.server_close()
