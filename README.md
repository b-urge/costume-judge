Costume Judge

A minimal local web app that captures a webcam photo and sends it to a Gemini model for a playful Halloween judging JSON response.

Usage

1. Copy .env.example to .env and set GEMINI_API_KEY.
2. Start the server: python3 server.py
3. Open http://localhost:8000 in a browser.
4. Click "Judge my costume" to capture a photo and get a Halloween-themed scorecard.

Notes

- The server uses only Python's standard library.
- The Gemini API endpoint in server.py is a placeholder; replace it with the correct Flash-capable model endpoint if you have one.
- The server will raise an error if GEMINI_API_KEY is not set in .env.
