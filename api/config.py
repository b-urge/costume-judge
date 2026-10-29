from http.server import BaseHTTPRequestHandler

try:
    from .common import process_config
except ImportError:
    from common import process_config


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        status, content_type, payload = process_config()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        self.send_error(405)
