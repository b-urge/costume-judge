# Costume Judge

Costume Judge is a local web app for playful Halloween costume judging. It captures a photo from the browser camera—or accepts an uploaded image—and sends the image to Google Gemini for a structured scorecard covering:

- Costume description
- Spookiness
- Creativity
- Effort
- Overall score
- A sharp, theatrical roast of the outfit

When ElevenLabs is configured, the roast is also spoken aloud using the premade Roger voice. If ElevenLabs is unavailable, the browser falls back to its built-in speech synthesis.

## How it works

The application is intentionally lightweight:

- `server.py` runs a Python standard-library HTTP server.
- The browser UI lives in `templates/` and `static/`.
- Gemini analyzes the submitted image and returns JSON matching the scorecard schema.
- ElevenLabs converts the roast into MP3 audio through the `/speak` endpoint.
- No frontend framework, package manager, or build step is required.

## Requirements

- Python 3
- A Google Gemini API key with access to a vision-capable Gemini model
- An ElevenLabs API key for spoken roasts (optional; browser speech is used without it)
- A browser with camera access, or an image file to upload

## Configuration

Copy the example environment file:

```sh
cp .env.example .env
```

Then edit `.env` and set your keys:

```dotenv
GEMINI_API_KEY=your-gemini-api-key
ELEVENLABS_API_KEY=your-elevenlabs-api-key
```

The Gemini model settings are optional. See `.env.example` for the supported overrides. Keep `.env` local: it is listed in `.gitignore` and must never be committed or pushed.

## Run locally

From the project directory, start the server:

```sh
python3 server.py
```

Open [http://localhost:8000](http://localhost:8000) in a browser. Allow camera access, or choose an image file, then select **Judge my costume**.

To verify the ElevenLabs configuration independently:

```sh
python3 test_elevenlabs.py
```

A successful configuration prints `HTTP status: 200`.

## Why Mel was used

Mel is an AI coding assistant that runs in the terminal alongside the project files. I used it to inspect the existing application, implement and refine the Gemini and ElevenLabs integration, make the interface changes, and verify the result with local commands. That made it possible to iterate quickly while keeping the project as a small, readable Python application rather than introducing a larger framework or toolchain.

## Hackathon

Costume Judge was made for the [Trick or Build hackathon](https://luma.com/wp7gehbn), a Halloween-themed building event. The project combines a quick camera-first experience with generative scoring and theatrical audio for a deliberately playful result.

## Security and privacy notes

- Do not commit `.env` or paste API keys into source files.
- The server sends submitted photos to Gemini for analysis.
- Roasts are sent to ElevenLabs when spoken audio is enabled.
- Run the app locally unless you have deliberately configured authentication and a suitable deployment environment.

## License

No license has been specified yet.
