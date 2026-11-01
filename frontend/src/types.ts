export type Emotion =
  | 'happy'
  | 'sad'
  | 'angry'
  | 'surprise'
  | 'fear'
  | 'disgust'
  | 'neutral'

export type MusicLanguage = 'en' | 'es' | 'hi' | 'fr' | 'de' | 'pt' | 'ja' | 'ko'

export type MusicGenre =
  | 'all'
  | 'pop'
  | 'rock'
  | 'hip-hop'
  | 'r-and-b'
  | 'electronic'
  | 'indie'
  | 'classical'
  | 'jazz'
  | 'lofi'
  | 'country'

export type Song = {
  videoId: string
  title: string
  artist: string
  duration: string
  thumbnail: string
  previewUrl?: string
}

export type MoodCheckIn = {
  emotion: Emotion
  timestamp: number
}
