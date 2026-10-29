#!/usr/bin/env python3
"""Probe the configured ElevenLabs voice without printing the API key."""

import json
import os
import urllib.error
import urllib.request


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VOICE_ID = 'CwhRBWXzGAHq8TQ4Fs17'  # ElevenLabs premade "Roger"


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
        pass
    return values


def main():
    api_key = load_env(os.path.join(BASE_DIR, '.env')).get('ELEVENLABS_API_KEY')
    if not api_key:
        print('HTTP status: not sent')
        print('ElevenLabs error: ELEVENLABS_API_KEY is missing from .env')
        return 1

    request = urllib.request.Request(
        'https://api.elevenlabs.io/v1/text-to-speech/' + VOICE_ID,
        data=json.dumps({
            'text': 'Happy Halloween',
            'model_id': 'eleven_multilingual_v2',
            'voice_settings': {'stability': 0.46, 'similarity_boost': 0.45},
        }).encode('utf-8'),
        headers={
            'xi-api-key': api_key,
            'Content-Type': 'application/json',
            'Accept': 'audio/mpeg',
        },
        method='POST',
    )

    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            print('HTTP status:', response.status)
            print('ElevenLabs error: none')
            return 0
    except urllib.error.HTTPError as error:
        print('HTTP status:', error.code)
        print('ElevenLabs error:', error.read().decode('utf-8', errors='replace'))
        return 1
    except urllib.error.URLError as error:
        print('HTTP status: unavailable')
        print('ElevenLabs error:', error.reason)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
