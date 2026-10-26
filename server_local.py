"""
Lightweight HTTP server for the Timetable GA web interface.
Uses only the Python standard library -- no extra dependencies.

Start:  python server.py
Open :  http://localhost:8080
"""

import json
import os
import sys
import io
import re
from http.server import HTTPServer, SimpleHTTPRequestHandler

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False

# Import the GA runner
from timetable_ga import run_ga_api


PORT = 8080
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public")


class GAHandler(SimpleHTTPRequestHandler):
    """Serves static files from /static and exposes /api/run."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    # -- API endpoint ------------------------------------------------------
    def do_GET(self):
        if self.path == "/api/run":
            self._handle_run()
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == "/api/run":
            content_length = int(self.headers.get('Content-Length', 0))
            config = {}
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                try:
                    config = json.loads(post_data.decode('utf-8'))
                except Exception as e:
                    print(f"Error parsing JSON: {e}", file=sys.__stderr__)
            self._handle_run(config)
        elif self.path == "/api/export_google_sheets":
            self._handle_export_sheets()
        else:
            self.send_error(404, "Endpoint not found")

    def _handle_run(self, config_dict=None):
        old_stdout = sys.stdout
        try:
            # Redirect stdout to suppress GA print() calls that may contain
            # characters unsupported by the Windows cp1252 console codec.
            sys.stdout = open(os.devnull, "w", encoding="utf-8", errors="replace")

            result = run_ga_api(config_dict)

            payload = json.dumps(result)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
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
            # Always restore stdout
            try:
                sys.stdout.close()
            except Exception:
                pass
            sys.stdout = old_stdout

    def _extract_id(self, value):
        """Extract a Google ID from a URL or raw ID string."""
        if not value:
            return None
        value = value.strip()
        if not value:
            return None
        # Spreadsheet URL: https://docs.google.com/spreadsheets/d/ID/edit
        m = re.search(r'/d/([a-zA-Z0-9_-]+)', value)
        if m:
            return m.group(1)
        # Folder URL: https://drive.google.com/drive/folders/ID
        m = re.search(r'/folders/([a-zA-Z0-9_-]+)', value)
        if m:
            return m.group(1)
        # If it looks like a clean ID already (alphanumeric + dashes/underscores, reasonable length)
        if re.match(r'^[a-zA-Z0-9_-]{10,}$', value):
            return value
        # Otherwise return as-is (the API will validate it)
        return value

    def _handle_export_sheets(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self.send_error(400, "Empty payload")
            return

        try:
            post_data = self.rfile.read(content_length)
            payload = json.loads(post_data.decode('utf-8'))
            
            # Diagnostic print (wrapped to avoid OSError on Windows)
            try:
                print(f"DEBUG: Received payload keys: {list(payload.keys())}", file=sys.__stderr__)
            except OSError:
                pass
            
            csv_rows = payload.get("rows", [])
            raw_folder = payload.get("folder_id")
            raw_spreadsheet = payload.get("spreadsheet_id")
            
            # Extract clean IDs from URLs (safety net in case frontend sends raw URLs)
            folder_id = self._extract_id(raw_folder)
            spreadsheet_id = self._extract_id(raw_spreadsheet)
            
            # Debug log
            with open("export_error.log", "a", encoding="utf-8") as f:
                f.write(f"\n--- Request at {self.log_date_time_string()} ---\n")
                f.write(f"Raw Folder: {raw_folder}\n")
                f.write(f"Raw Spreadsheet: {raw_spreadsheet}\n")
                f.write(f"Extracted Folder ID: {folder_id}\n")
                f.write(f"Extracted Spreadsheet ID: {spreadsheet_id}\n")
            
            if not GSPREAD_AVAILABLE:
                raise Exception("gspread library is not installed on the server.")
                
            if not os.path.exists("credentials.json"):
                raise Exception("Missing credentials.json for Google Sheets API authentication. "
                                "Please refer to GOOGLE_SHEETS_SETUP.md in the project root for instructions on how to get it.")
            
            # Authenticate
            scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
            credentials = Credentials.from_service_account_file('credentials.json', scopes=scopes)
            gc = gspread.authorize(credentials)
            
            # Get the spreadsheet
            if spreadsheet_id:
                # Open existing spreadsheet
                try:
                    sh = gc.open_by_key(spreadsheet_id)
                except gspread.exceptions.APIError as e:
                    body = str(e).lower()
                    if "invalid" in body and "argument" in body:
                        raise Exception(f"The ID you provided ('{spreadsheet_id}') is not a valid Spreadsheet ID. "
                                        "If this is a Folder ID, please move it to the 'Target Folder ID' field. "
                                        "Otherwise, make sure you copied the correct part of the URL.")
                    raise e
            else:
                # Create a new spreadsheet
                try:
                    sh = gc.create("University Timetable (Generated by GA)", folder_id=folder_id)
                except gspread.exceptions.APIError as e:
                    if "quota" in str(e).lower():
                        raise Exception("Google Drive storage quota exceeded. "
                                        "Service accounts have 0GB storage. To fix this: "
                                        "1) Create a Google Sheet manually in your Drive. "
                                        "2) Share it as Editor with: timetable@eloquent-clover-435616-m1.iam.gserviceaccount.com "
                                        "3) Paste the sheet URL into the 'Spreadsheet URL' field in the sidebar.")
                    raise e
            
            # Share it so anyone with link can view (only if it's a new one or we want to ensure access)
            if not spreadsheet_id:
                sh.share(None, role='reader', type='anyone')
            
            # Get the first sheet
            worksheet = sh.get_worksheet(0)
            
            # Update the sheet with the 2D array data
            if csv_rows:
                # For safety, let's clear it first if updating an existing one
                if spreadsheet_id:
                    worksheet.clear()
                worksheet.update(values=csv_rows, range_name=f'A1')
                
            # Formatting (Make headers bold)
            # Use columns up to Z for safety
            worksheet.format("A1:Z6", {
                "textFormat": {
                    "bold": True
                }
            })

            # Respond with the URL
            response_data = {"url": sh.url}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode("utf-8"))
            
        except Exception as e:
            import traceback
            with open("export_error.log", "a", encoding="utf-8") as f:
                traceback.print_exc(file=f)
            try:
                print(f"Google Sheets Export Error: {e}", file=sys.__stderr__)
            except OSError:
                pass
            try:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            except Exception:
                pass


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
