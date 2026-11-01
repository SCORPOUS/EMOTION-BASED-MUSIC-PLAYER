import type { Emotion, MusicGenre, MusicLanguage, Song } from './types'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init)
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as
      | { detail?: string }
      | null
    throw new Error(body?.detail ?? `Request failed (${response.status})`)
  }
  return (await response.json()) as T
}

export function detectFrame(frame: string): Promise<{ emotion: Emotion; emoji: string }> {
  return request('/detect', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ frame }),
  })
}

export function fetchSongs(
  emotion: Emotion,
  language: MusicLanguage,
  genre: MusicGenre,
): Promise<Song[]> {
  const params = new URLSearchParams({
    emotion,
    lang: language,
    genre,
  })
  return request(`/songs?${params.toString()}`, { cache: 'no-store' })
}

type ITunesTrack = {
  trackId: number
  trackName: string
  artistName: string
  artworkUrl100?: string
  previewUrl?: string
  trackTimeMillis?: number
}

type ITunesSearchResponse = {
  results: ITunesTrack[]
}

export async function fetchPreviewSongs(
  emotion: Emotion,
  language: string,
): Promise<Song[]> {
  const moodKeywords: Record<Emotion, string> = {
    happy: 'upbeat',
    sad: 'sad',
    angry: 'rock',
    surprise: 'party',
    fear: 'calming',
    disgust: 'empowering',
    neutral: 'chill',
  }
  const params = new URLSearchParams({
    term: `${language} ${moodKeywords[emotion]} songs`,
    country: 'IN',
    entity: 'song',
    limit: '12',
  })
  const response = await fetch(`https://itunes.apple.com/search?${params.toString()}`)
  if (!response.ok) {
    throw new Error(`Preview search failed (${response.status})`)
  }
  const data = (await response.json()) as ITunesSearchResponse
  return data.results
    .filter((track) => track.previewUrl)
    .map((track) => ({
      videoId: `itunes-${track.trackId}`,
      title: track.trackName,
      artist: track.artistName,
      duration: track.trackTimeMillis
        ? `${Math.floor(track.trackTimeMillis / 60_000)}:${String(
            Math.floor((track.trackTimeMillis % 60_000) / 1_000),
          ).padStart(2, '0')}`
        : '30s preview',
      thumbnail: track.artworkUrl100 ?? '',
      previewUrl: track.previewUrl,
    }))
}
