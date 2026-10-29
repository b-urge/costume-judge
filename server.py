#!/usr/bin/env python3
"""
Minimal HTTP server for Costume Judge.
Serves index at / and accepts POST /upload with a multipart/form-data image file named "photo".
Reads GEMINI_API_KEY from .env in the working directory.
Uses only Python standard library.
"""

import base64
import http.server
import socketserver
import urllib.error
import urllib.request
import json
import os
from http import HTTPStatus
from email.parser import BytesParser
from email.policy import default as default_policy

PORT = 8000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')


def load_env(path='.env'):
    env = {}
    try:
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    k, v = line.split('=', 1)
                    env[k.strip()] = v.strip()
    except FileNotFoundError:
        pass
    return env

ENV = load_env(os.path.join(BASE_DIR, '.env'))
GEMINI_API_KEY = ENV.get('GEMINI_API_KEY')

# Default model: a stable, older Flash image-capable model to reduce 503/429 incidents.
# Override with GEMINI_MODEL if you want.
GEMINI_MODEL_DEFAULT = ENV.get('GEMINI_MODEL_DEFAULT', 'gemini-2.5-flash')
# Fallback model for when the default is unavailable.
GEMINI_MODEL_FALLBACK = ENV.get('GEMINI_MODEL_FALLBACK', 'gemini-3.8-flash')

# Backwards-compatible override: if GEMINI_MODEL is set, it becomes the primary model.
GEMINI_MODEL = ENV.get('GEMINI_MODEL', GEMINI_MODEL_DEFAULT)


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.path = '/templates/index.html'
            return http.server.SimpleHTTPRequestHandler.do_GET(self)
        # serve static and template files
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        if self.path == '/upload':
            content_type = self.headers.get('Content-Type')
            if not content_type or 'multipart/form-data' not in content_type:
                self.send_error(HTTPStatus.BAD_REQUEST, 'Expected multipart/form-data')
                return
            boundary = content_type.split('boundary=')[-1].encode()
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            # parse multipart
            msg = BytesParser(policy=default_policy).parsebytes(b'Content-Type: ' + content_type.encode() + b'\r\n\r\n' + body)
            photo_bytes = None
            for part in msg.iter_attachments():
                name = part.get_param('name', header='content-disposition')
                filename = part.get_filename()
                if name == 'photo' and filename:
                    photo_bytes = part.get_content()
                    break
            if not photo_bytes:
                self.send_error(HTTPStatus.BAD_REQUEST, 'No photo field')
                return
            # call Gemini
            try:
                result = call_gemini(photo_bytes)
            except Exception as e:
                # Friendly failure for the UI (no raw error details), but log the real error server-side.
                # Never log secrets; this should only contain status/message returned by Gemini.
                print('Gemini error:', str(e))
                self.send_response(HTTPStatus.OK)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'message': 'The spirits are busy, try again in a moment'
                }).encode())
                return

            self.send_response(HTTPStatus.OK)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
            return
        elif self.path == '/speak':
            # ElevenLabs TTS: expects JSON {"text": "..."}, returns MP3 or error.
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body)
                text = data.get('text')
            except Exception:
                self.send_error(HTTPStatus.BAD_REQUEST, 'Invalid JSON')
                return
            ELEVEN_KEY = ENV.get('ELEVENLABS_API_KEY')
            if not ELEVEN_KEY:
                self.send_response(HTTPStatus.BAD_REQUEST)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'No ELEVENLABS_API_KEY set'}).encode())
                return
            try:
                mp3bytes = elevenlabs_speak(text, ELEVEN_KEY)
                self.send_response(HTTPStatus.OK)
                self.send_header('Content-Type', 'audio/mpeg')
                self.end_headers()
                self.wfile.write(mp3bytes)
            except Exception as e:
                # Never print/log keys!
                self.send_response(HTTPStatus.BAD_REQUEST)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
            return
        self.send_error(HTTPStatus.NOT_FOUND)

def elevenlabs_speak(text, api_key):
    text = text.strip()
    if not text:
        raise ValueError('No text to speak')
    import urllib.request
    voice_id = 'CwhRBWXzGAHq8TQ4Fs17'  # ElevenLabs premade "Roger" -- dramatic, clear
    url = f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}'
    data = json.dumps({
        'text': text,
        'model_id': 'eleven_multilingual_v2',
        'voice_settings': {'stability': 0.46, 'similarity_boost': 0.45}
    }).encode('utf-8')
    req = urllib.request.Request(url, data=data, method='POST', headers={
        'xi-api-key': api_key,
        'Content-Type': 'application/json',
        'Accept': 'audio/mpeg'
    })
    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            if resp.status != 200:
                raise RuntimeError(f'ElevenLabs error HTTP {resp.status}')
            return resp.read()
    except urllib.error.HTTPError as error:
        detail = error.read().decode('utf-8', errors='replace').strip()
        try:
            detail = json.loads(detail).get('detail', detail)
            if isinstance(detail, dict):
                detail = detail.get('message', json.dumps(detail))
        except (TypeError, ValueError):
            pass
        raise RuntimeError(f'ElevenLabs error HTTP {error.code}: {detail}') from error



def call_gemini(image_bytes):
    """Send an image to Gemini and return its scorecard JSON."""
    if not GEMINI_API_KEY:
        raise RuntimeError('GEMINI_API_KEY not set in .env')

    prompt = (
        'You are a Halloween costume judge with the regal, withering glamour of a Dynasty-era diva, '
        'the deadpan observational timing of a great stand-up, and the brutal-but-loving delivery of a '
        'Vegas comedy legend. Funny and sharp, never cruel. Roast only the clothes, props, and effort—'
        'never anyone\'s body, face, age, weight, race, gender, or anything they can\'t change.\n\n'
        'TASK:\n'
        '1) Describe exactly what the person is wearing in a short, concrete costume description (what it looks like).\n'
        '2) Then write a 1–2 sentence roast of the outfit.\n\n'
        'If it isn\'t a Halloween costume (e.g., regular street clothes), clock it bluntly, score it low, '
        'and dare them to try harder.\n\n'
        'Return ONLY JSON matching the provided response schema.'
    )
    score_schema = {
        'type': 'OBJECT',
        'properties': {
            'costume': {'type': 'STRING'},
            'spookiness': {'type': 'INTEGER', 'minimum': 1, 'maximum': 10},
            'creativity': {'type': 'INTEGER', 'minimum': 1, 'maximum': 10},
            'effort': {'type': 'INTEGER', 'minimum': 1, 'maximum': 10},
            'overall': {'type': 'INTEGER', 'minimum': 1, 'maximum': 10},
            'roast': {'type': 'STRING'},
        },
        'required': ['costume', 'spookiness', 'creativity', 'effort', 'overall', 'roast'],
        'propertyOrdering': ['costume', 'spookiness', 'creativity', 'effort', 'overall', 'roast'],
    }
    payload = {
        'contents': [{
            'parts': [
                {'text': prompt},
                {'inline_data': {
                    'mime_type': 'image/jpeg',
                    'data': base64.b64encode(image_bytes).decode('ascii'),
                }},
            ]
        }],
        'generationConfig': {
            'responseMimeType': 'application/json',
            'responseSchema': score_schema,
        },
    }

    def fetch_with_model(model_name):
        url = (
            'https://generativelanguage.googleapis.com/v1beta/models/'
            + model_name
            + ':generateContent'
        )
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'x-goog-api-key': GEMINI_API_KEY,
            },
            method='POST',
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode('utf-8'))

    def parse_scorecard(response_body):
        model_text = response_body['candidates'][0]['content']['parts'][0]['text']
        parsed = json.loads(model_text)
        if not isinstance(parsed, dict):
            raise ValueError('Gemini returned an invalid scorecard shape')
        required_keys = {'costume', 'spookiness', 'creativity', 'effort', 'overall', 'roast'}
        if set(parsed) != required_keys:
            raise ValueError('Gemini returned an invalid scorecard shape')
        if not isinstance(parsed['costume'], str) or not parsed['costume'].strip():
            raise ValueError('Gemini returned an invalid costume description')
        for key in ('spookiness', 'creativity', 'effort', 'overall'):
            if isinstance(parsed[key], bool) or not isinstance(parsed[key], (int, float)) or not 1 <= parsed[key] <= 10:
                raise ValueError('Gemini returned an invalid score')
        if not isinstance(parsed['roast'], str) or not parsed['roast'].strip():
            raise ValueError('Gemini returned an invalid roast')
        return {
            'costume': parsed['costume'].strip(),
            'spookiness': int(parsed['spookiness']),
            'creativity': int(parsed['creativity']),
            'effort': int(parsed['effort']),
            'overall': int(parsed['overall']),
            'roast': parsed['roast'].strip(),
        }

    primary_model = GEMINI_MODEL
    fallback_model = GEMINI_MODEL_FALLBACK

    # Retry transient quota/service issues for the primary model.
    retryable_statuses = {429, 503}
    last_error_text = None

    for model_name, max_retries in [(primary_model, 3), (fallback_model, 1)]:
        attempts = 0
        while attempts < max_retries:
            try:
                response_body = fetch_with_model(model_name)
                return parse_scorecard(response_body)
            except urllib.error.HTTPError as error:
                error_body = error.read().decode('utf-8', errors='replace')
                last_error_text = 'Gemini API request failed with HTTP ' + str(error.code) + ': ' + error_body
                if error.code not in retryable_statuses or attempts >= max_retries - 1:
                    break
                # short wait before retry
                import time
                time.sleep(2)
                attempts += 1
            except Exception as error:
                last_error_text = str(error)
                break

    raise RuntimeError(last_error_text or 'Gemini request failed')


if __name__ == '__main__':
    os.chdir(BASE_DIR)
    Handler.extensions_map.update({
        '.js': 'application/javascript',
        '.css': 'text/css',
        '.html': 'text/html',
    })
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(('', PORT), Handler) as httpd:
        print(f'Serving at http://localhost:{PORT}')
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\nShutting down')
            httpd.server_close()
