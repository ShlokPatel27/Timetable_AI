import json
import sys
import os
from http.server import BaseHTTPRequestHandler

# Add current directory to path so we can import modules in project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from timetable_ga import run_ga_api

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        config = json.loads(post_data.decode('utf-8'))
        
        # Suppress any print() in GA logic that might fail in serverless env
        old_stdout = sys.stdout
        sys.stdout = open(os.devnull, "w")
        
        try:
            result = run_ga_api(config)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        finally:
            sys.stdout.close()
            sys.stdout = old_stdout

    def do_GET(self):
        # Allow GET briefly for testing or health check
        if self.path == "/api/run":
            result = run_ga_api({})
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
