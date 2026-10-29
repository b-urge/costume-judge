from http.server import BaseHTTPRequestHandler

try:
    from .common import process_judge
except ImportError:
    from common import process_judge


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        status, content_type, payload = process_judge(self.headers, body)
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        self.send_error(405)
