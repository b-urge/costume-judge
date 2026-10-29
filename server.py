#!/usr/bin/env python3
"""Local server for Costume Judge, compatible with Vercel API handlers."""

import os
import json
import http.server
import socketserver
from urllib.parse import urlparse

from api.common import process_config, process_judge, process_speak


PORT = int(os.environ.get('PORT', '8000'))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(BASE_DIR, 'public')


def load_env(path):
    values = {}
    try:
        with open(path, 'r') as env_file:
            for line in env_file:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    values[key.strip()] = value.strip()
    except FileNotFoundError:
        return values
    return values


for key, value in load_env(os.path.join(BASE_DIR, '.env')).items():
    if key not in os.environ:
        os.environ[key] = value


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC_DIR, **kwargs)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/api/config':
            status, content_type, payload = process_config()
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.end_headers()
            self.wfile.write(payload)
            return
        if path == '/':
            self.path = '/index.html'
        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)

        if path == '/api/judge':
            status, content_type, payload = process_judge(self.headers, body)
        elif path == '/api/speak':
            status, content_type, payload = process_speak(self.headers, body)
        else:
            self.send_error(404)
            return

        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.end_headers()
        self.wfile.write(payload)


if __name__ == '__main__':
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(('', PORT), Handler) as httpd:
        print(f'Serving at http://localhost:{PORT}')
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\nShutting down')
            httpd.server_close()
