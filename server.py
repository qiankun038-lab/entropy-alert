#!/usr/bin/env python3
"""
ENTROPY SURVIVOR - Development Server
Serves the website with data directory access
"""

import http.server
import socketserver
import os
from pathlib import Path
import json

BASE_DIR = Path(__file__).parent
WEBSITE_DIR = BASE_DIR / "website"
DATA_DIR = BASE_DIR / "data"
PORT = 8080

class EntropySurvivorHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEBSITE_DIR), **kwargs)
    
    def do_GET(self):
        # Route /data/* to data directory
        if self.path.startswith('/data/'):
            file_path = DATA_DIR / self.path[6:]  # Remove '/data/'
            if file_path.exists() and file_path.is_file():
                self.send_response(200)
                if file_path.suffix == '.json':
                    self.send_header('Content-type', 'application/json')
                elif file_path.suffix == '.jsonl':
                    self.send_header('Content-type', 'application/x-ndjson')
                else:
                    self.send_header('Content-type', 'text/plain')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                with open(file_path, 'rb') as f:
                    self.wfile.write(f.read())
                return
            else:
                self.send_error(404, f"File not found: {self.path}")
                return
        
        # Default handler for website files
        super().do_GET()
    
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

def run_server():
    with socketserver.TCPServer(("", PORT), EntropySurvivorHandler) as httpd:
        print(f"\n{'='*60}")
        print(f"  ENTROPY SURVIVOR - Web Server")
        print(f"  Running at: http://localhost:{PORT}")
        print(f"  Website: {WEBSITE_DIR}")
        print(f"  Data: {DATA_DIR}")
        print(f"{'='*60}\n")
        print("Press Ctrl+C to stop...")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down...")

if __name__ == "__main__":
    run_server()
