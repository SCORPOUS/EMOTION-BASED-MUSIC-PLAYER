import base64
import binascii
import logging
import os
import random
from functools import lru_cache
from io import BytesIO
from typing import Literal, TypeGuard

import httpx
import numpy as np
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field
from ytmusicapi import YTMusic
from mood_queries import build_mood_queries


logger = logging.getLogger("moodwave.api")

Emotion = Literal["happy", "sad", "angry", "surprise", "fear", "disgust", "neutral"]
Language = Literal["en", "es", "hi", "fr", "de", "pt", "ja", "ko"]
Genre = Literal[
    "all",
    "pop",
    "rock",
    "hip-hop",
    "r-and-b",
    "electronic",
    "indie",
    "classical",
    "jazz",
    "lofi",
    "country",
]
EMOTION_EMOJI = {
    "happy": "😊",
    "sad": "😢",
    "angry": "😠",
    "surprise": "😲",
    "fear": "😰",
    "disgust": "🤢",
    "neutral": "😐",
}
LANGUAGE_NAMES = {
    "en": "English",
    "es": "Spanish",
    "hi": "Hindi",
    "fr": "French",
    "de": "German",
    "pt": "Portuguese",
    "ja": "Japanese",
    "ko": "Korean",
}
GENRE_NAMES = {
    "all": "",
    "pop": "pop",
    "rock": "rock",
    "hip-hop": "hip hop",
    "r-and-b": "R&B",
    "electronic": "electronic",
    "indie": "indie",
    "classical": "classical",
    "jazz": "jazz",
    "lofi": "lofi",
    "country": "country",
}
MAX_FRAME_BYTES = 8 * 1024 * 1024
MAX_FRAME_PIXELS = 5_000_000
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"


def is_emotion(value: str) -> TypeGuard[Emotion]:
    return value in EMOTION_EMOJI


class FrameRequest(BaseModel):
    frame: str = Field(min_length=1, max_length=MAX_FRAME_BYTES * 2)


class EmotionResponse(BaseModel):
    emotion: Emotion
    emoji: str


class SongResponse(BaseModel):
    videoId: str
    title: str
    artist: str
    duration: str
    thumbnail: str


app = FastAPI(title="Moodwave API", version="1.0.0")
allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@lru_cache(maxsize=1)
def get_ytmusic() -> YTMusic:
    return YTMusic()


def decode_frame(encoded_frame: str) -> np.ndarray:
    if encoded_frame.startswith("data:"):
        try:
            header, encoded_frame = encoded_frame.split(",", maxsplit=1)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid image data URL.") from exc
        if ";base64" not in header:
            raise HTTPException(status_code=400, detail="Image data must be base64 encoded.")

    try:
        image_bytes = base64.b64decode(encoded_frame, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Frame is not valid base64.") from exc

    if not image_bytes or len(image_bytes) > MAX_FRAME_BYTES:
        raise HTTPException(status_code=413, detail="Frame must be under 8 MB.")

    try:
        with Image.open(BytesIO(image_bytes)) as image:
            if image.width * image.height > MAX_FRAME_PIXELS:
                raise HTTPException(status_code=413, detail="Frame dimensions are too large.")
            rgb_image = image.convert("RGB")
            return np.asarray(rgb_image)
    except UnidentifiedImageError as exc:
        raise HTTPException(status_code=400, detail="Frame must be a valid image.") from exc


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/detect", response_model=EmotionResponse)
def detect_emotion(payload: FrameRequest) -> EmotionResponse:
    frame = decode_frame(payload.frame)
    try:
        from deepface import DeepFace

        result = DeepFace.analyze(
            frame,
            actions=["emotion"],
            enforce_detection=False,
        )
    except Exception as exc:
        logger.exception("DeepFace failed to analyze a camera frame.")
        raise HTTPException(
            status_code=503,
            detail="Emotion analysis is unavailable. Check the DeepFace model setup and retry.",
        ) from exc

    analysis = result[0] if isinstance(result, list) else result
    emotion = str(analysis.get("dominant_emotion", "")).lower()
    if not is_emotion(emotion):
        logger.error("DeepFace returned an unsupported emotion: %s", emotion)
        raise HTTPException(status_code=502, detail="Emotion analysis returned an unknown mood.")
    return EmotionResponse(emotion=emotion, emoji=EMOTION_EMOJI[emotion])


def _thumbnail(result: dict) -> str:
    thumbnails = result.get("thumbnails") or []
    return thumbnails[-1].get("url", "") if thumbnails else ""


def _song_from_ytmusic_result(result: dict) -> SongResponse | None:
    video_id = result.get("videoId")
    if not video_id:
        return None
    artists = result.get("artists") or []
    return SongResponse(
        videoId=video_id,
        title=result.get("title") or "Unknown title",
        artist=", ".join(
            artist.get("name", "") for artist in artists if artist.get("name")
        )
        or "Unknown artist",
        duration=result.get("duration") or "",
        thumbnail=_thumbnail(result),
    )


def get_songs(emotion: Emotion, lang: Language, genre: Genre = "all") -> list[SongResponse]:
    queries = build_mood_queries(emotion, lang)
    if GENRE_NAMES[genre]:
        language_name = LANGUAGE_NAMES[lang]
        genre_query = f"{language_name} {GENRE_NAMES[genre]} {queries[0].split()[1]} songs"
        queries.append(genre_query)

    ytmusic = get_ytmusic()
    songs: list[SongResponse] = []
    seen_video_ids: set[str] = set()
    song_search_failures = 0

    def add_results(results: list[dict]) -> None:
        for result in results:
            song = _song_from_ytmusic_result(result)
            if song and song.videoId not in seen_video_ids:
                seen_video_ids.add(song.videoId)
                songs.append(song)

    try:
        playlists = ytmusic.search(queries[0], filter="playlists", limit=10)
    except Exception:
        logger.exception("YTMusic playlist search failed for %s/%s.", emotion, lang)
        playlists = []

    for playlist in playlists[:2]:
        playlist_id = playlist.get("browseId") or playlist.get("playlistId")
        if not playlist_id:
            continue
        try:
            playlist_data = ytmusic.get_playlist(playlist_id, limit=50)
        except Exception:
            logger.exception("YTMusic playlist load failed for %s.", playlist_id)
            continue
        add_results(playlist_data.get("tracks") or [])

    for query in queries:
        try:
            add_results(ytmusic.search(query, filter="songs", limit=25))
        except Exception:
            logger.exception("YTMusic song search failed for %s/%s.", emotion, lang)
            song_search_failures += 1

    if not songs and song_search_failures == len(queries):
        raise HTTPException(
            status_code=503,
            detail="YouTube Music search is unavailable. Try again later.",
        )

    random.shuffle(songs)
    return songs[:12]


def _fallback_youtube_search(
    query: str,
    language: Language,
    api_key: str,
) -> list[SongResponse]:
    try:
        response = httpx.get(
            YOUTUBE_SEARCH_URL,
            params={
                "part": "snippet",
                "q": query,
                "type": "video",
                "videoEmbeddable": "true",
                "maxResults": 50,
                "relevanceLanguage": language,
                "key": api_key,
            },
            timeout=10,
        )
        response.raise_for_status()
    except (httpx.HTTPError, ValueError) as exc:
        logger.exception("YouTube Data API fallback search failed.")
        raise HTTPException(
            status_code=502,
            detail="YouTube fallback search failed. Try again later.",
        ) from exc

    try:
        payload = response.json()
    except ValueError as exc:
        logger.exception("YouTube Data API returned invalid JSON.")
        raise HTTPException(
            status_code=502,
            detail="YouTube fallback returned an invalid response. Try again later.",
        ) from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        logger.error("YouTube Data API returned an unexpected search response.")
        raise HTTPException(
            status_code=502,
            detail="YouTube fallback returned an invalid response. Try again later.",
        )

    songs: list[SongResponse] = []
    seen_ids: set[str] = set()
    for item in payload.get("items", []):
        video_id = (item.get("id") or {}).get("videoId")
        if not video_id or video_id in seen_ids:
            continue
        seen_ids.add(video_id)
        snippet = item.get("snippet") or {}
        thumbnails = snippet.get("thumbnails") or {}
        thumbnail = next(
            (
                thumbnails[size]["url"]
                for size in ("high", "medium", "default")
                if thumbnails.get(size, {}).get("url")
            ),
            "",
        )
        songs.append(
            SongResponse(
                videoId=video_id,
                title=snippet.get("title") or "Unknown title",
                artist=snippet.get("channelTitle") or "Unknown artist",
                duration="",
                thumbnail=thumbnail,
            )
        )
        if len(songs) == 12:
            break
    return songs


@app.get("/songs", response_model=list[SongResponse])
def songs_for_emotion(
    emotion: Emotion = Query(..., description="Mood to search for."),
    lang: Language = Query("en", description="Preferred song language."),
    genre: Genre = Query("all", description="Optional music genre."),
) -> list[SongResponse]:
    try:
        songs = get_songs(emotion, lang, genre)
    except HTTPException as exc:
        if exc.status_code != 503:
            raise
        songs = []
    if songs:
        return songs

    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        return []
    fallback_queries = build_mood_queries(emotion, lang)
    return _fallback_youtube_search(fallback_queries[0], lang, api_key)
