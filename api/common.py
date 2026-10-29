import base64
import json
import os
import time
import urllib.error
import urllib.request
from email.parser import BytesParser
from email.policy import default as default_policy


def _header_value(headers, name):
    if headers is None:
        return None
    if hasattr(headers, 'get'):
        value = headers.get(name)
        if value is not None:
            return value
        return headers.get(name.lower())
    lowered = name.lower()
    for key, value in headers.items():
        if str(key).lower() == lowered:
            return value
    return None


def _json_response(status, payload):
    return status, 'application/json', json.dumps(payload).encode('utf-8')


def _event_code_error(headers):
    expected = (os.environ.get('EVENT_CODE') or '').strip()
    if not expected:
        return None
    provided = (_header_value(headers, 'x-event-code') or '').strip()
    if not provided:
        return _json_response(401, {'error': 'Event code required'})
    if provided != expected:
        return _json_response(403, {'error': 'Invalid event code'})
    return None


def config_payload():
    return {
        'event_code_required': bool((os.environ.get('EVENT_CODE') or '').strip())
    }


def process_config():
    return _json_response(200, config_payload())


def parse_photo_from_multipart(headers, body):
    content_type = _header_value(headers, 'Content-Type')
    if not content_type or 'multipart/form-data' not in content_type:
        raise ValueError('Expected multipart/form-data')
    message = BytesParser(policy=default_policy).parsebytes(
        b'Content-Type: ' + content_type.encode() + b'\r\n\r\n' + body
    )
    for part in message.iter_attachments():
        name = part.get_param('name', header='content-disposition')
        filename = part.get_filename()
        if name == 'photo' and filename:
            return part.get_content()
    raise ValueError('No photo field')


def process_judge(headers, body):
    blocked = _event_code_error(headers)
    if blocked:
        return blocked

    api_key = (os.environ.get('GEMINI_API_KEY') or '').strip()
    if not api_key:
        return _json_response(400, {'error': 'GEMINI_API_KEY is not set'})

    try:
        photo_bytes = parse_photo_from_multipart(headers, body)
        result = call_gemini(photo_bytes, api_key, (os.environ.get('GEMINI_MODEL') or 'gemini-2.5-flash').strip())
        return _json_response(200, result)
    except Exception:
        return _json_response(200, {'message': 'The spirits are busy, try again in a moment'})


def process_speak(headers, body):
    blocked = _event_code_error(headers)
    if blocked:
        return blocked

    api_key = (os.environ.get('ELEVENLABS_API_KEY') or '').strip()
    if not api_key:
        return _json_response(400, {'error': 'No ELEVENLABS_API_KEY set'})

    try:
        data = json.loads(body.decode('utf-8'))
        text = data.get('text', '')
        mp3 = elevenlabs_speak(text, api_key)
        return 200, 'audio/mpeg', mp3
    except Exception as error:
        return _json_response(400, {'error': str(error)})


def elevenlabs_speak(text, api_key):
    text = str(text or '').strip()
    if not text:
        raise ValueError('No text to speak')

    voice_id = 'CwhRBWXzGAHq8TQ4Fs17'
    url = f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}'
    payload = json.dumps({
        'text': text,
        'model_id': 'eleven_multilingual_v2',
        'voice_settings': {'stability': 0.46, 'similarity_boost': 0.45},
    }).encode('utf-8')
    request = urllib.request.Request(
        url,
        data=payload,
        method='POST',
        headers={
            'xi-api-key': api_key,
            'Content-Type': 'application/json',
            'Accept': 'audio/mpeg',
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            if response.status != 200:
                raise RuntimeError(f'ElevenLabs error HTTP {response.status}')
            return response.read()
    except urllib.error.HTTPError as error:
        detail = error.read().decode('utf-8', errors='replace').strip()
        try:
            parsed = json.loads(detail)
            detail = parsed.get('detail', detail)
            if isinstance(detail, dict):
                detail = detail.get('message', json.dumps(detail))
        except Exception:
            pass
        raise RuntimeError(f'ElevenLabs error HTTP {error.code}: {detail}') from error


def call_gemini(image_bytes, api_key, model_name):
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
                {'inline_data': {'mime_type': 'image/jpeg', 'data': base64.b64encode(image_bytes).decode('ascii')}},
            ]
        }],
        'generationConfig': {'responseMimeType': 'application/json', 'responseSchema': score_schema},
    }

    def fetch(name):
        url = 'https://generativelanguage.googleapis.com/v1beta/models/' + name + ':generateContent'
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'x-goog-api-key': api_key},
            method='POST',
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode('utf-8'))

    last_error = None
    for retries, name in ((3, model_name), (1, 'gemini-3.8-flash')):
        for attempt in range(retries):
            try:
                body = fetch(name)
                model_text = body['candidates'][0]['content']['parts'][0]['text']
                parsed = json.loads(model_text)
                required = {'costume', 'spookiness', 'creativity', 'effort', 'overall', 'roast'}
                if not isinstance(parsed, dict) or set(parsed.keys()) != required:
                    raise ValueError('Gemini returned an invalid scorecard shape')
                return {
                    'costume': str(parsed['costume']).strip(),
                    'spookiness': int(parsed['spookiness']),
                    'creativity': int(parsed['creativity']),
                    'effort': int(parsed['effort']),
                    'overall': int(parsed['overall']),
                    'roast': str(parsed['roast']).strip(),
                }
            except urllib.error.HTTPError as error:
                detail = error.read().decode('utf-8', errors='replace')
                last_error = RuntimeError(f'Gemini API request failed with HTTP {error.code}: {detail}')
                if error.code not in (429, 503) or attempt >= retries - 1:
                    break
                time.sleep(2)
            except Exception as error:
                last_error = error
                break
    raise last_error or RuntimeError('Gemini request failed')
