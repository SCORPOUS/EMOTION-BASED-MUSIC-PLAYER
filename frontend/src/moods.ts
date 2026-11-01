import type { Emotion } from './types'

export const MOODS: Record<
  Emotion,
  { emoji: string; color: string; label: string; query: string; gradient: string }
> = {
  happy: {
    emoji: '😊',
    color: '#47d7a1',
    label: 'Happy',
    query: 'happy upbeat feel good hits',
    gradient: 'linear-gradient(135deg, #f8c87a 0%, #ff8faa 44%, #a67aff 100%)',
  },
  sad: {
    emoji: '😢',
    color: '#74b9ff',
    label: 'Sad',
    query: 'sad emotional heartbreak songs',
    gradient: 'linear-gradient(135deg, #7a9bea 0%, #89c9e8 48%, #9a8bdf 100%)',
  },
  angry: {
    emoji: '😠',
    color: '#ff7675',
    label: 'Angry',
    query: 'angry intense rock workout',
    gradient: 'linear-gradient(135deg, #ff625e 0%, #ff9a65 48%, #ed5c91 100%)',
  },
  surprise: {
    emoji: '😲',
    color: '#fdcb6e',
    label: 'Surprised',
    query: 'exciting energetic party songs',
    gradient: 'linear-gradient(135deg, #ffd36e 0%, #ff8fc0 48%, #9e82ff 100%)',
  },
  fear: {
    emoji: '😰',
    color: '#a29bfe',
    label: 'Uneasy',
    query: 'calming peaceful relaxing songs',
    gradient: 'linear-gradient(135deg, #8e9df7 0%, #a6a4ed 48%, #69c8d8 100%)',
  },
  disgust: {
    emoji: '🤢',
    color: '#55efc4',
    label: 'Disgusted',
    query: 'powerful empowering anthems',
    gradient: 'linear-gradient(135deg, #4fd8ae 0%, #87d9a8 48%, #78b9e8 100%)',
  },
  neutral: {
    emoji: '😐',
    color: '#b3b3c7',
    label: 'Neutral',
    query: 'chill lofi study relaxing beats',
    gradient: 'linear-gradient(135deg, #9b91d6 0%, #a8c1da 48%, #86c9c4 100%)',
  },
}

export const EMOTIONS = Object.keys(MOODS) as Emotion[]

export function isEmotion(value: unknown): value is Emotion {
  return typeof value === 'string' && value in MOODS
}
