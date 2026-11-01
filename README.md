# Moodwave | Emotion-Based Music Player

Moodwave pairs a real-time mood check-in with a YouTube Music playlist. The migrated app uses a React, Vite, TypeScript, and Tailwind frontend with a FastAPI backend. The previous Streamlit implementation remains in the repository as a legacy version.

## Features

- Browser webcam mood scans, with JPEG frames sent to the local API every 1.5 seconds for five seconds
- DeepFace emotion detection and majority voting across the scan
- Twelve shuffled, deduplicated mood-based YouTube Music suggestions, sourced from playlists and keyword searches in the selected language
- User-initiated YouTube IFrame playback with progress seeking, previous, next, shuffle, auto-next, and automatic skip for embed errors
- Recharts mood history saved in browser local storage
- Mood-reactive gradients, glass panels, animated scan UI, and dark/light themes
- Responsive layout; camera frames are processed by the local backend and are not saved

## Project structure

```text
.
├── backend/
│   ├── main.py                 # FastAPI API: /detect, /songs, /health
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.tsx             # React app and player
│   │   ├── api.ts              # FastAPI client
│   │   ├── moods.ts            # Mood palette and labels
│   │   ├── types.ts
│   │   └── index.css           # Tailwind and Moodwave styles
│   ├── package.json
│   └── .env.example
├── app.py                      # Legacy Streamlit app
├── detection.py                # Legacy Streamlit camera detection
└── music.py                    # Legacy Streamlit song/player helpers
```

## Requirements

- Python 3.11 or 3.12 recommended for DeepFace and its TensorFlow dependencies
- Node.js 20.19+ (Node.js 22+ recommended)
- A YouTube Data API v3 key is optional; it enables embeddable-video search as a fallback if YouTube Music search is unavailable

Moodwave uses `ytmusicapi` for its primary search. If that search fails or returns no tracks, it can use the YouTube Data API v3 with `videoEmbeddable=true`; set `YOUTUBE_API_KEY` to enable that fallback.

## Run locally (Windows PowerShell)

From the repository root, create a Python environment and install the backend packages:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
```

Optionally set a YouTube Data API key to enable fallback search, then start FastAPI:

```powershell
$env:YOUTUBE_API_KEY = "your-youtube-data-api-v3-key"
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

In another terminal, install and start the frontend:

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```

Open [http://localhost:5173](http://localhost:5173). Vite proxies `/api` requests to FastAPI on port `8000`. The FastAPI CORS allowlist defaults to `localhost:5173` and `127.0.0.1:5173`; customize it with the comma-separated `CORS_ORIGINS` environment variable if the frontend uses a different origin.

The frontend reads `VITE_API_BASE_URL` from `frontend/.env` when set. For the default local Vite proxy, copy `frontend/.env.example` to `frontend/.env` or leave the variable unset.

## API

### `POST /detect`

Request JSON:

```json
{
  "frame": "data:image/jpeg;base64,/9j/..."
}
```

Response:

```json
{
  "emotion": "happy",
  "emoji": "😊"
}
```

### `GET /songs?emotion=happy&lang=en&genre=all`

Searches mood playlists first, loads tracks from the top two, then searches three mood keywords in the selected language. Results are deduplicated by video ID, shuffled, and capped at 12. Suggestion results are not cached.

```json
[
  {
    "videoId": "youtube-video-id",
    "title": "Song title",
    "artist": "Artist name",
    "duration": "3:45",
    "thumbnail": "https://..."
  }
]
```

Supported emotion values are `happy`, `sad`, `angry`, `surprise`, `fear`, `disgust`, and `neutral`.
Supported `lang` values are `en`, `es`, `hi`, `fr`, `de`, `pt`, `ja`, and `ko`. `genre` accepts `all`, `pop`, `rock`, `hip-hop`, `r-and-b`, `electronic`, `indie`, `classical`, `jazz`, `lofi`, or `country`.

## Checks

```powershell
cd frontend
npm run build
npm run lint
cd ..
python -m compileall backend\main.py
```
