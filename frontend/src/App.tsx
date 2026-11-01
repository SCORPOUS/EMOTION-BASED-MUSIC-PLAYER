import { lazy, Suspense, useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import type { CSSProperties } from 'react'
import {
  ArrowDownRight,
  AudioLines,
  Camera,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Heart,
  Music2,
  Pause,
  Play,
  RefreshCw,
  Shuffle,
  Sparkles,
  Sun,
  Moon,
  Volume2,
} from 'lucide-react'
import { detectFrame, fetchPreviewSongs, fetchSongs } from './api'
import { EMOTIONS, isEmotion, MOODS } from './moods'
import type { Emotion, MoodCheckIn, MusicGenre, MusicLanguage, Song } from './types'

const MoodHistoryChart = lazy(() => import('./MoodHistoryChart'))
const HISTORY_STORAGE_KEY = 'moodwave-history'
const THEME_STORAGE_KEY = 'moodwave-theme'
const SCAN_DURATION_MS = 5_000
const FRAME_INTERVAL_MS = 1_500
type PlayerOptions = {
  host: string
  videoId: string
  playerVars: { autoplay: number; controls: number; playsinline: number; rel: number }
  events: {
    onReady: (event: { target: YouTubePlayer }) => void
    onStateChange: (event: { data: number }) => void
    onError: (event: { data: number }) => void
  }
}
type YouTubePlayer = {
  playVideo: () => void
  pauseVideo: () => void
  loadVideoById: (videoId: string) => void
  getCurrentTime: () => number
  getDuration: () => number
  seekTo: (seconds: number, allowSeekAhead: boolean) => void
}
type YouTubeApi = {
  Player: new (element: HTMLElement, options: PlayerOptions) => YouTubePlayer
  PlayerState: { ENDED: number; PLAYING: number }
}

declare global {
  interface Window {
    YT?: YouTubeApi
    onYouTubeIframeAPIReady?: () => void
  }
}

let youtubeApiPromise: Promise<YouTubeApi> | undefined

function loadYouTubeApi(): Promise<YouTubeApi> {
  if (window.YT?.Player) return Promise.resolve(window.YT)
  if (!youtubeApiPromise) {
    youtubeApiPromise = new Promise((resolve, reject) => {
      const previousCallback = window.onYouTubeIframeAPIReady
      window.onYouTubeIframeAPIReady = () => {
        previousCallback?.()
        if (window.YT) resolve(window.YT)
        else reject(new Error('YouTube player API did not initialize.'))
      }
      let script = document.querySelector<HTMLScriptElement>(
        'script[src="https://www.youtube.com/iframe_api"]',
      )
      if (!script) {
        script = document.createElement('script')
        script.src = 'https://www.youtube.com/iframe_api'
        script.async = true
        document.head.appendChild(script)
      }
      script.addEventListener(
        'error',
        () => reject(new Error('Could not load the YouTube player API.')),
        { once: true },
      )
    })
  }
  return youtubeApiPromise
}

const LANGUAGES: { value: MusicLanguage; label: string }[] = [
  { value: 'en', label: 'English' },
  { value: 'hi', label: 'Hindi' },
  { value: 'es', label: 'Spanish' },
  { value: 'fr', label: 'French' },
  { value: 'de', label: 'German' },
  { value: 'pt', label: 'Portuguese' },
  { value: 'ja', label: 'Japanese' },
  { value: 'ko', label: 'Korean' },
]
const GENRES: { value: MusicGenre; label: string }[] = [
  { value: 'all', label: 'Any genre' },
  { value: 'pop', label: 'Pop' },
  { value: 'rock', label: 'Rock' },
  { value: 'hip-hop', label: 'Hip-hop' },
  { value: 'r-and-b', label: 'R&B' },
  { value: 'electronic', label: 'Electronic' },
  { value: 'indie', label: 'Indie' },
  { value: 'classical', label: 'Classical' },
  { value: 'jazz', label: 'Jazz' },
  { value: 'lofi', label: 'Lo-fi' },
  { value: 'country', label: 'Country' },
]

function formatTime(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return '0:00'
  const minutes = Math.floor(seconds / 60)
  return `${minutes}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`
}

function youtubeLink(song: Song): string {
  if (song.videoId.startsWith('itunes-')) {
    return `https://www.youtube.com/results?search_query=${encodeURIComponent(
      `${song.title} ${song.artist}`,
    )}`
  }
  return `https://www.youtube.com/watch?v=${encodeURIComponent(song.videoId)}`
}

function readHistory(): MoodCheckIn[] {
  try {
    const stored: unknown = JSON.parse(localStorage.getItem(HISTORY_STORAGE_KEY) ?? '[]')
    if (!Array.isArray(stored)) return []
    return stored.filter(
      (entry): entry is MoodCheckIn =>
        typeof entry === 'object' &&
        entry !== null &&
        isEmotion((entry as MoodCheckIn).emotion) &&
        typeof (entry as MoodCheckIn).timestamp === 'number',
    )
  } catch {
    return []
  }
}

function majorityMood(detections: Emotion[]): Emotion | null {
  if (!detections.length) return null
  const counts = new Map<Emotion, number>()
  for (const emotion of detections) counts.set(emotion, (counts.get(emotion) ?? 0) + 1)
  return detections.reduce((winner, emotion) =>
    (counts.get(emotion) ?? 0) > (counts.get(winner) ?? 0) ? emotion : winner,
  )
}

function App() {
  const [mood, setMood] = useState<Emotion>('neutral')
  const [liveMood, setLiveMood] = useState<Emotion>('neutral')
  const [history, setHistory] = useState<MoodCheckIn[]>(readHistory)
  const [songs, setSongs] = useState<Song[]>([])
  const [previewSongs, setPreviewSongs] = useState<Song[]>([])
  const [source, setSource] = useState<'youtube' | 'preview'>('youtube')
  const [activeVideoId, setActiveVideoId] = useState<string | null>(null)
  const [activePreviewId, setActivePreviewId] = useState<string | null>(null)
  const [language, setLanguage] = useState<MusicLanguage>('en')
  const [genre, setGenre] = useState<MusicGenre>('all')
  const [theme, setTheme] = useState<'dark' | 'light'>(() =>
    localStorage.getItem(THEME_STORAGE_KEY) === 'light' ? 'light' : 'dark',
  )
  const [isScanning, setIsScanning] = useState(false)
  const [remainingSeconds, setRemainingSeconds] = useState(5)
  const [isLoadingSongs, setIsLoadingSongs] = useState(true)
  const [isLoadingPreviews, setIsLoadingPreviews] = useState(false)
  const [isPlayerOpen, setIsPlayerOpen] = useState(false)
  const [isPlaying, setIsPlaying] = useState(false)
  const [error, setError] = useState('')
  const [toast, setToast] = useState('')
  const [failedIds, setFailedIds] = useState<string[]>([])
  const [songSearchKey, setSongSearchKey] = useState(0)
  const [playbackProgress, setPlaybackProgress] = useState(0)
  const [playbackDuration, setPlaybackDuration] = useState(0)
  const [showConfetti, setShowConfetti] = useState(false)
  const videoRef = useRef<HTMLVideoElement>(null)
  const audioRef = useRef<HTMLAudioElement>(null)
  const playerContainerRef = useRef<HTMLDivElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const playerRef = useRef<YouTubePlayer | null>(null)
  const playerCreatedRef = useRef(false)
  const playerReadyRef = useRef(false)
  const initialVideoIdRef = useRef<string | null>(null)
  const consecutiveFailuresRef = useRef(0)
  const failedVideoIdsRef = useRef(new Set<string>())
  const endedVideoIdRef = useRef<string | null>(null)
  const previewAutoplayRef = useRef(false)
  const playOnReadyRef = useRef(false)
  const moodStyle = {
    '--mood-gradient': MOODS[mood].gradient,
    '--mood-color': MOODS[mood].color,
  } as CSSProperties
  const activeSongs = source === 'youtube' ? songs : previewSongs
  const selectedSongId = source === 'youtube' ? activeVideoId : activePreviewId
  const currentSong = activeSongs.find((song) => song.videoId === selectedSongId)
  const selectedIndex = activeSongs.findIndex((song) => song.videoId === selectedSongId)
  const activeVideoIdRef = useRef<string | undefined>(activeVideoId ?? undefined)
  const activePreviewIdRef = useRef(activePreviewId)
  const sourceRef = useRef(source)
  const currentSongRef = useRef<Song | undefined>(currentSong)
  const isPlayerOpenRef = useRef(isPlayerOpen)
  const counts = useMemo(
    () =>
      EMOTIONS.map((emotion) => ({
        emotion,
        label: MOODS[emotion].label,
        count: history.filter((entry) => entry.emotion === emotion).length,
      })),
    [history],
  )

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
    localStorage.setItem(THEME_STORAGE_KEY, theme)
  }, [theme])

  useEffect(() => {
    localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(history))
  }, [history])

  useEffect(() => {
    currentSongRef.current = currentSong
    isPlayerOpenRef.current = isPlayerOpen
  }, [currentSong, isPlayerOpen])

  useLayoutEffect(() => {
    activeVideoIdRef.current = activeVideoId ?? undefined
  }, [activeVideoId])

  useLayoutEffect(() => {
    activePreviewIdRef.current = activePreviewId
  }, [activePreviewId])

  useLayoutEffect(() => {
    sourceRef.current = source
  }, [source])

  useEffect(() => {
    let active = true
    fetchSongs(mood, language, genre)
      .then((results) => {
        if (!active) return
        const playingSong =
          sourceRef.current === 'youtube' && isPlayerOpenRef.current
            ? currentSongRef.current
            : undefined
        const nextSongs = playingSong
          ? [playingSong, ...results.filter((song) => song.videoId !== playingSong.videoId)]
          : results
        const nextPlaylist = nextSongs.slice(0, 12)
        setSongs(nextPlaylist)
        setActiveVideoId((currentVideoId) =>
          playingSong?.videoId ??
          nextPlaylist.find((song) => song.videoId === currentVideoId)?.videoId ??
          nextPlaylist[0]?.videoId ??
          null,
        )
        setFailedIds([])
        failedVideoIdsRef.current.clear()
      })
      .catch((cause: unknown) => {
        if (active) setError(cause instanceof Error ? cause.message : 'Could not load songs.')
      })
      .finally(() => {
        if (active) setIsLoadingSongs(false)
      })
    return () => {
      active = false
    }
  }, [mood, language, genre, songSearchKey])

  useEffect(() => {
    if (source !== 'preview') return
    let active = true
    fetchPreviewSongs(
      mood,
      LANGUAGES.find((option) => option.value === language)?.label ?? language,
    )
      .then((results) => {
        if (!active) return
        const playingSong = isPlayerOpenRef.current ? currentSongRef.current : undefined
        const nextSongs = playingSong
          ? [playingSong, ...results.filter((song) => song.videoId !== playingSong.videoId)]
          : results
        const nextPlaylist = nextSongs.slice(0, 12)
        setPreviewSongs(nextPlaylist)
        setActivePreviewId(
          playingSong?.videoId ??
            nextPlaylist.find((song) => song.videoId === activePreviewIdRef.current)?.videoId ??
            nextPlaylist[0]?.videoId ??
            null,
        )
        setError('')
      })
      .catch((cause: unknown) => {
        if (active) {
          setError(cause instanceof Error ? cause.message : 'Could not load preview tracks.')
          setIsPlaying(false)
        }
      })
      .finally(() => {
        if (active) setIsLoadingPreviews(false)
      })
    return () => {
      active = false
    }
  }, [mood, language, source])

  useEffect(() => {
    if (!isPlayerOpen) return

    const updateProgress = () => {
      if (source === 'preview') {
        const audio = audioRef.current
        if (!audio || !Number.isFinite(audio.duration) || audio.duration <= 0) return
        setPlaybackDuration(audio.duration)
        setPlaybackProgress(Math.min(audio.currentTime / audio.duration, 1))
        return
      }
      const player = playerRef.current
      if (
        !player ||
        typeof player.getDuration !== 'function' ||
        typeof player.getCurrentTime !== 'function'
      ) return
      const duration = player.getDuration()
      const currentTime = player.getCurrentTime()
      if (!Number.isFinite(duration) || duration <= 0 || !Number.isFinite(currentTime)) return
      setPlaybackDuration(duration)
      setPlaybackProgress(Math.min(currentTime / duration, 1))
    }

    updateProgress()
    const interval = window.setInterval(updateProgress, 500)
    return () => window.clearInterval(interval)
  }, [isPlayerOpen, currentSong?.videoId, source])

  useEffect(() => {
    const elements = document.querySelectorAll<HTMLElement>('.reveal-on-scroll')
    if (!('IntersectionObserver' in window)) {
      elements.forEach((element) => element.classList.add('revealed'))
      return
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('revealed')
            observer.unobserve(entry.target)
          }
        })
      },
      { threshold: 0.12 },
    )
    elements.forEach((element) => observer.observe(element))
    return () => observer.disconnect()
  }, [])

  useEffect(
    () => () => {
      streamRef.current?.getTracks().forEach((track) => track.stop())
    },
    [],
  )

  const saveMood = useCallback((detectedMood: Emotion) => {
    if (detectedMood !== mood) {
      setError('')
      setIsLoadingSongs(true)
      if (sourceRef.current === 'preview') setIsLoadingPreviews(true)
    }
    setMood(detectedMood)
    setLiveMood(detectedMood)
    setHistory((previous) =>
      [...previous, { emotion: detectedMood, timestamp: Date.now() }].slice(-60),
    )
    setShowConfetti(true)
    window.setTimeout(() => setShowConfetti(false), 2_500)
    setToast(`${MOODS[detectedMood].emoji} ${MOODS[detectedMood].label} mood found`)
    window.setTimeout(() => setToast(''), 2_500)
  }, [mood])

  const scanMood = async () => {
    setError('')
    setToast('')
    setIsScanning(true)
    setRemainingSeconds(5)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } },
      })
      streamRef.current = stream
      const video = videoRef.current
      if (!video) throw new Error('Camera preview is not ready.')
      video.srcObject = stream
      await video.play()

      const canvas = document.createElement('canvas')
      const context = canvas.getContext('2d')
      if (!context) throw new Error('Could not initialize camera capture.')
      canvas.width = video.videoWidth
      canvas.height = video.videoHeight
      if (!canvas.width || !canvas.height) throw new Error('Camera returned an empty frame.')

      const detections: Emotion[] = []
      const requests: Promise<void>[] = []
      const start = Date.now()
      let nextFrameAt = start
      while (Date.now() - start < SCAN_DURATION_MS) {
        const remaining = Math.max(0, SCAN_DURATION_MS - (Date.now() - start))
        setRemainingSeconds(Math.ceil(remaining / 1_000))
        context.drawImage(video, 0, 0, canvas.width, canvas.height)
        const frame = canvas.toDataURL('image/jpeg', 0.78)
        requests.push(
          detectFrame(frame)
            .then(({ emotion }) => {
              detections.push(emotion)
              setLiveMood(emotion)
            })
            .catch((cause: unknown) => {
              setError(cause instanceof Error ? cause.message : 'Frame analysis failed.')
            }),
        )
        nextFrameAt += FRAME_INTERVAL_MS
        const delay = Math.min(nextFrameAt - Date.now(), start + SCAN_DURATION_MS - Date.now())
        if (delay > 0) await new Promise((resolve) => window.setTimeout(resolve, delay))
      }

      await Promise.all(requests)
      const result = majorityMood(detections)
      if (result) {
        saveMood(result)
      } else {
        setError((message) => message || 'No face could be analyzed. Try again with more light.')
      }
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.name === 'NotAllowedError'
            ? 'Allow camera access in your browser to scan your mood.'
            : cause.message
          : 'Could not start the camera.',
      )
    } finally {
      streamRef.current?.getTracks().forEach((track) => track.stop())
      streamRef.current = null
      if (videoRef.current) videoRef.current.srcObject = null
      setIsScanning(false)
      setRemainingSeconds(5)
    }
  }

  const setSelectedSong = (videoId: string) => {
    if (source === 'youtube') setActiveVideoId(videoId)
    else setActivePreviewId(videoId)
  }

  const moveTrack = (direction: -1 | 1) => {
    if (!activeSongs.length) return
    const failed = source === 'youtube' ? failedIds : []
    for (let offset = 1; offset <= activeSongs.length; offset += 1) {
      const candidate =
        (selectedIndex + direction * offset + activeSongs.length) % activeSongs.length
      if (!failed.includes(activeSongs[candidate].videoId)) {
        const shouldKeepPlaying = isPlayerOpen && isPlaying
        setSelectedSong(activeSongs[candidate].videoId)
        playOnReadyRef.current = shouldKeepPlaying
        setIsPlaying(shouldKeepPlaying)
        return
      }
    }
    setIsPlaying(false)
    setError('No playable tracks remain in this mix. Choose another mood to refresh it.')
  }

  const shuffleTracks = () => {
    if (activeSongs.length < 2) return
    const options = activeSongs
      .map((_, index) => index)
      .filter(
        (index) =>
          activeSongs[index].videoId !== selectedSongId &&
          (source !== 'youtube' || !failedIds.includes(activeSongs[index].videoId)),
      )
    if (!options.length) return
    const shouldKeepPlaying = isPlayerOpen && isPlaying
    setSelectedSong(activeSongs[options[Math.floor(Math.random() * options.length)]].videoId)
    playOnReadyRef.current = shouldKeepPlaying
    setIsPlaying(shouldKeepPlaying)
  }

  const handlePlayerError = (videoId: string, errorCode: number) => {
    if (!videoId || activeVideoIdRef.current !== videoId) return
    if (![101, 150, 153].includes(errorCode)) {
      setIsPlaying(false)
      setError(`YouTube player failed with error ${errorCode}.`)
      return
    }

    if (failedVideoIdsRef.current.has(videoId)) return
    failedVideoIdsRef.current.add(videoId)
    const updatedFailed = [...new Set([...failedIds, videoId])]
    setFailedIds(updatedFailed)
    consecutiveFailuresRef.current += 1
    if (consecutiveFailuresRef.current >= 3) {
      previewAutoplayRef.current = true
      playOnReadyRef.current = true
      setIsLoadingPreviews(true)
      setPreviewSongs([])
      setActivePreviewId(null)
      setSource('preview')
      setIsPlayerOpen(true)
      setIsPlaying(true)
      setToast('Switching to 30s previews after repeated YouTube playback errors')
      window.setTimeout(() => setToast(''), 3_000)
      return
    }

    let nextSong: Song | undefined
    for (let offset = 1; offset <= songs.length; offset += 1) {
      const candidate = songs[(selectedIndex + offset + songs.length) % songs.length]
      if (candidate.videoId !== videoId && !updatedFailed.includes(candidate.videoId)) {
        nextSong = candidate
        break
      }
    }
    if (!nextSong) {
      previewAutoplayRef.current = true
      playOnReadyRef.current = true
      setIsLoadingPreviews(true)
      setPreviewSongs([])
      setActivePreviewId(null)
      setSource('preview')
      setIsPlayerOpen(true)
      setIsPlaying(true)
      return
    }
    setActiveVideoId(nextSong.videoId)
    playOnReadyRef.current = true
    setIsPlaying(true)
    setToast('Skipping a video that does not allow embedding')
    window.setTimeout(() => setToast(''), 2_500)
  }

  const togglePlayback = () => {
    if (!currentSong) return
    setError('')
    if (!isPlayerOpen) {
      playOnReadyRef.current = true
      setIsPlayerOpen(true)
      setIsPlaying(false)
      return
    }
    if (isPlaying) {
      if (source === 'preview') audioRef.current?.pause()
      else playerRef.current?.pauseVideo()
      setIsPlaying(false)
    } else {
      if (source === 'preview') {
        void audioRef.current?.play().catch((cause: unknown) => {
          setError(cause instanceof Error ? cause.message : 'Could not play this preview.')
        })
      } else if (playerReadyRef.current) {
        playerRef.current?.playVideo()
      } else {
        playOnReadyRef.current = true
      }
    }
  }

  const changeSource = (nextSource: 'youtube' | 'preview') => {
    if (source === nextSource) return
    const resume = isPlayerOpen && isPlaying
    playOnReadyRef.current = resume
    previewAutoplayRef.current = nextSource === 'preview' && resume
    setError('')
    if (nextSource === 'preview') {
      setPreviewSongs([])
      setActivePreviewId(null)
      setIsLoadingPreviews(true)
    }
    setSource(nextSource)
    setIsPlaying(resume)
  }

  const playerCallbacksRef = useRef({
    onError: (_videoId: string, _errorCode: number) => {},
    next: () => {},
  })
  useLayoutEffect(() => {
    playerCallbacksRef.current = {
      onError: handlePlayerError,
      next: () => moveTrack(1),
    }
  })

  useEffect(() => {
    if (source !== 'preview' || !isPlayerOpen || !currentSong?.previewUrl) return
    const audio = audioRef.current
    if (!audio) return
    audio.load()
    if (playOnReadyRef.current || previewAutoplayRef.current) {
      playOnReadyRef.current = false
      previewAutoplayRef.current = false
      void audio.play().catch((cause: unknown) => {
        setIsPlaying(false)
        setError(cause instanceof Error ? cause.message : 'Could not play this preview.')
      })
    }
  }, [source, isPlayerOpen, currentSong?.previewUrl])

  useEffect(() => {
    if (!isPlayerOpen || source !== 'youtube') {
      if (source !== 'youtube') playerRef.current?.pauseVideo()
      return
    }
    if (!songs.length || playerCreatedRef.current || !playerContainerRef.current) return
    playerCreatedRef.current = true
    const initialVideoId = activeVideoId ?? songs[0].videoId
    initialVideoIdRef.current = initialVideoId
    void loadYouTubeApi()
      .then((api) => {
        const container = playerContainerRef.current
        if (!container?.isConnected) {
          playerCreatedRef.current = false
          return
        }
        playerRef.current = new api.Player(container, {
          host: 'https://www.youtube.com',
          videoId: initialVideoId,
          playerVars: { autoplay: 0, controls: 1, playsinline: 1, rel: 0 },
          events: {
            onReady: ({ target }) => {
              playerRef.current = target
              playerReadyRef.current = true
              const latestVideoId = activeVideoIdRef.current ?? initialVideoId
              if (latestVideoId !== initialVideoIdRef.current) {
                target.loadVideoById(latestVideoId)
                initialVideoIdRef.current = latestVideoId
              }
              if (sourceRef.current === 'youtube' && playOnReadyRef.current) {
                playOnReadyRef.current = false
                target.playVideo()
              }
            },
            onStateChange: ({ data }) => {
              if (sourceRef.current !== 'youtube') return
              if (data === api.PlayerState.PLAYING) {
                consecutiveFailuresRef.current = 0
                endedVideoIdRef.current = null
                setIsPlaying(true)
              } else if (data === api.PlayerState.ENDED) {
                const endedVideoId = activeVideoIdRef.current
                if (!endedVideoId || endedVideoIdRef.current === endedVideoId) return
                endedVideoIdRef.current = endedVideoId
                setIsPlaying(false)
                playerCallbacksRef.current.next()
              }
            },
            onError: ({ data }) => {
              playerCallbacksRef.current.onError(
                activeVideoIdRef.current ?? initialVideoId,
                data,
              )
            },
          },
        })
      })
      .catch((cause: unknown) => {
        playerCreatedRef.current = false
        setError(cause instanceof Error ? cause.message : 'Could not start YouTube playback.')
      })
  }, [isPlayerOpen, source, songs, activeVideoId])

  useEffect(() => {
    if (source !== 'youtube' || !isPlayerOpen || !playerReadyRef.current || !activeVideoId) {
      return
    }
    if (initialVideoIdRef.current === activeVideoId) {
      if (playOnReadyRef.current) {
        playOnReadyRef.current = false
        playerRef.current?.playVideo()
      }
      return
    }
    initialVideoIdRef.current = activeVideoId
    setPlaybackProgress(0)
    setPlaybackDuration(0)
    playerRef.current?.loadVideoById(activeVideoId)
    if (playOnReadyRef.current || isPlaying) {
      playOnReadyRef.current = false
    } else {
      playerRef.current?.pauseVideo()
    }
  }, [activeVideoId, source, isPlayerOpen, isPlaying])

  useEffect(() => {
    if (source !== 'youtube') playerRef.current?.pauseVideo()
    if (source !== 'preview') audioRef.current?.pause()
  }, [source])

  const clearHistory = () => {
    setHistory([])
  }

  const retrySongSearch = () => {
    setError('')
    setIsLoadingSongs(true)
    setSongSearchKey((key) => key + 1)
  }

  return (
    <main className="moodscape min-h-screen overflow-x-clip px-4 pb-20 text-slate-950 transition-colors duration-500 dark:text-white sm:px-7 lg:px-10" style={moodStyle}>
      <div className="ambient ambient-one" />
      <div className="ambient ambient-two" />
      <div className="relative z-10 mx-auto max-w-7xl">
        <header className="glass-nav sticky top-4 z-30 mt-4 flex items-center justify-between gap-4 rounded-2xl px-4 py-3 sm:px-6">
          <a className="flex items-center gap-3 font-display text-lg font-bold tracking-tight" href="#home">
            <span className="brand-icon"><Music2 size={19} /></span>
            <span>Moodwave</span>
          </a>
          <nav className="hidden items-center gap-7 text-sm font-medium text-slate-600 dark:text-white/70 md:flex">
            <a className="nav-link" href="#home">Home</a>
            <a className="nav-link" href="#mood-check">Mood scan</a>
            <a className="nav-link" href="#history">Mood history</a>
          </nav>
          <button
            type="button"
            className="theme-toggle"
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          >
            {theme === 'dark' ? <Sun size={17} /> : <Moon size={17} />}
            <span className="hidden sm:inline">{theme === 'dark' ? 'Light' : 'Dark'} mode</span>
          </button>
        </header>

        <section id="home" className="hero-grid grid min-h-[calc(100svh-7rem)] items-center gap-10 py-12 lg:grid-cols-[1.05fr_.95fr] lg:py-16">
          <div className="fade-up max-w-2xl">
            <div className="eyebrow"><Sparkles size={14} /> MUSIC THAT MEETS THE MOMENT</div>
            <h1 className="mt-7 font-display text-[clamp(2.15rem,8vw,5.5rem)] font-extrabold leading-[1.02] tracking-[-.065em]">
              Your mood.<br />Your <span className="gradient-text">soundtrack.</span>
            </h1>
            <p className="mt-6 max-w-xl text-base leading-8 text-slate-600 dark:text-white/65 sm:text-lg">
              A quick camera scan finds the feeling. A fresh playlist finds the sound.
              Take a breath, look at the camera, and let the music meet you where you are.
            </p>
            <div className="mt-7 flex flex-wrap gap-2.5">
              <span className="mood-chip"><span>{MOODS[mood].emoji}</span>{MOODS[mood].label} mood</span>
              <span className="mood-chip"><Camera size={14} />Private camera scan</span>
              <span className="mood-chip"><AudioLines size={14} />A mix made for now</span>
            </div>
            <a href="#mood-check" className="shimmer-cta mt-8 inline-flex items-center gap-2">
              <Camera size={17} /> Find my mood <ArrowDownRight size={17} />
            </a>
            <div className="mt-10 flex items-center gap-3 text-xs font-medium text-slate-500 dark:text-white/45">
              <span className="avatar-stack"><span>♫</span><span>♪</span><span>♬</span></span>
              Made for how you feel right now
            </div>
          </div>

          <div className="hero-art glass-panel fade-up delay-150 relative mx-auto flex aspect-[.94] w-full max-w-[530px] items-center justify-center overflow-hidden rounded-[2rem] p-8">
            <div className="hero-orbit hero-orbit-one" />
            <div className="hero-orbit hero-orbit-two" />
            <div className="hero-glow" />
            <div className="hero-emoji">{MOODS[mood].emoji}</div>
            <div className="floating-label floating-label-top"><span className="live-dot" /> mood, in motion</div>
            <div className="floating-label floating-label-bottom"><Volume2 size={15} /> feeling into frequency</div>
            <div className="sound-bars" aria-hidden="true">
              {[16, 29, 21, 39, 25, 34, 18, 30, 43, 22, 36, 16, 28, 40, 20].map((height, index) => (
                <i key={index} style={{ '--bar-height': `${height}px`, '--bar-delay': `${index * 55}ms` } as CSSProperties} />
              ))}
            </div>
          </div>
        </section>

        <section className="feature-bento grid gap-4 py-8 md:grid-cols-3" aria-label="Moodwave features">
          <article className="glass-panel feature-tile reveal-on-scroll rounded-3xl p-5 md:col-span-2">
            <div className="feature-tile-icon"><Camera size={19} /></div>
            <div className="mt-4 flex items-end justify-between gap-5">
              <div><h2 className="font-display text-xl font-bold">A little read on your mood.</h2><p className="mt-1 text-sm leading-6 text-slate-600 dark:text-white/55">A quick, private camera check-in helps the mix meet you where you are.</p></div>
              <span className="hidden text-4xl sm:inline">✦</span>
            </div>
          </article>
          <article className="glass-panel feature-tile reveal-on-scroll rounded-3xl p-5">
            <div className="feature-tile-icon"><AudioLines size={19} /></div>
            <h2 className="mt-4 font-display text-xl font-bold">Sound for right now.</h2>
            <p className="mt-1 text-sm leading-6 text-slate-600 dark:text-white/55">Each feeling opens a fresh lane to explore.</p>
          </article>
          <article className="glass-panel feature-tile reveal-on-scroll rounded-3xl p-5">
            <div className="feature-tile-icon"><Heart size={19} /></div>
            <h2 className="mt-4 font-display text-xl font-bold">Your moments stay yours.</h2>
            <p className="mt-1 text-sm leading-6 text-slate-600 dark:text-white/55">History lives in your browser. Camera frames are not stored.</p>
          </article>
          <article className="glass-panel feature-tile feature-accent reveal-on-scroll rounded-3xl p-5 md:col-span-2">
            <span className="eyebrow">LISTEN WITH INTENTION</span>
            <h2 className="mt-2 font-display text-2xl font-bold">No mood is too small for a soundtrack.</h2>
            <p className="mt-2 max-w-xl text-sm leading-6 text-slate-600 dark:text-white/55">Pick a feeling, hit play when it feels right, and let the next song find its way to you.</p>
            <a href="#player" className="text-button mt-3 inline-flex items-center gap-1">Explore your mix <ChevronRight size={15} /></a>
          </article>
        </section>

        <section id="mood-check" className="section-block scroll-mt-24 py-14 sm:py-20">
          <div className="section-heading reveal-on-scroll">
            <span className="eyebrow">YOUR LISTENING ROOM</span>
            <h2>Check in with yourself.</h2>
            <p>Scan a live camera preview or choose the mood you want to explore.</p>
          </div>
          <div className="grid gap-5 lg:grid-cols-[.9fr_1.1fr]">
            <article className="glass-panel scan-card reveal-on-scroll rounded-4xl p-5 sm:p-7">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-bold text-slate-500 dark:text-white/50">REAL-TIME CHECK-IN</p>
                  <h3 className="mt-1 font-display text-2xl font-bold">How are you feeling?</h3>
                </div>
                <span className={`scan-status ${isScanning ? 'is-scanning' : ''}`}>
                  <span className="live-dot" />{isScanning ? `Scanning · ${remainingSeconds}s` : 'Camera ready'}
                </span>
              </div>
              <div className={`camera-stage ${isScanning ? 'scanning' : ''} mt-6`}>
                <video ref={videoRef} className="camera-feed" muted playsInline aria-label="Live camera preview" />
                <div className={`scan-frame ${isScanning ? 'active' : ''}`}>
                  <span className="scan-corner corner-tl" /><span className="scan-corner corner-tr" />
                  <span className="scan-corner corner-bl" /><span className="scan-corner corner-br" />
                  <div className="scan-ring"><span /></div>
                  <div className="scan-face">{MOODS[isScanning ? liveMood : mood].emoji}</div>
                </div>
                <span className="camera-caption">{isScanning ? 'Reading your expression…' : 'Your camera stays on this device'}</span>
              </div>
              <button type="button" className="primary-button mt-5 w-full" onClick={scanMood} disabled={isScanning}>
                {isScanning ? <RefreshCw className="animate-spin" size={18} /> : <Camera size={18} />}
                {isScanning ? `Finding your mood · ${remainingSeconds}s` : 'Scan my mood'}
              </button>
              <p className="mt-3 text-center text-xs leading-5 text-slate-500 dark:text-white/45">
                Frames are sent to your local API every 1.5 seconds and never saved.
              </p>
            </article>

            <article className="glass-panel mood-select-card reveal-on-scroll rounded-4xl p-5 sm:p-7">
              <div className="flex items-center gap-3">
                <div className="section-icon"><Sparkles size={19} /></div>
                <div>
                  <p className="text-sm font-bold text-slate-500 dark:text-white/50">OR GO WITH YOUR GUT</p>
                  <h3 className="font-display text-2xl font-bold">Choose a feeling</h3>
                </div>
              </div>
              <div className="mood-options mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3">
                {EMOTIONS.map((emotion) => (
                  <button
                    className={`mood-option ${mood === emotion ? 'selected' : ''}`}
                    key={emotion}
                    type="button"
                    onClick={() => {
                      saveMood(emotion)
                      setError('')
                    }}
                  >
                    <span className="mood-option-emoji">{MOODS[emotion].emoji}</span>
                    <span>{MOODS[emotion].label}</span>
                    {mood === emotion && <Check size={14} className="mood-check" />}
                  </button>
                ))}
              </div>
              <div className="mix-callout mt-6 flex items-center justify-between gap-4 rounded-2xl p-4">
                <div className="flex items-center gap-3">
                  <div className="mix-emoji">{MOODS[mood].emoji}</div>
                  <div><p className="text-xs font-bold uppercase tracking-widest opacity-60">CURRENT VIBE</p><p className="mt-1 font-display font-bold">{MOODS[mood].label} &middot; feeling it</p></div>
                </div>
                <ChevronDown size={18} className="opacity-50" />
              </div>
            </article>
          </div>
        </section>

        <section id="player" className="section-block scroll-mt-24 py-14 sm:py-20">
          <div className="section-heading reveal-on-scroll">
            <span className="eyebrow">YOUR MOOD, IN MUSIC</span>
            <h2>A little mix for this moment.</h2>
            <p>Choose a mood and language, then play any track right here.</p>
          </div>
          <div className="grid gap-5 lg:grid-cols-[.95fr_1.05fr]">
            <article className="glass-panel now-playing-card reveal-on-scroll relative overflow-hidden rounded-4xl p-5 sm:p-7">
              <div className="album-wash" />
              <div className="relative z-10">
                <div className="flex items-center justify-between gap-4">
                  <div><span className="eyebrow">NOW PLAYING</span><h3 className="mt-1 font-display text-2xl font-bold">The {MOODS[mood].label} mix</h3></div>
                  <span className="track-count">{activeSongs.length} tracks</span>
                </div>
                {((source === 'youtube' && isLoadingSongs && songs.length === 0) ||
                  (source === 'preview' && isLoadingPreviews && previewSongs.length === 0)) ? (
                  <div className="mt-6 space-y-3" aria-label="Loading tracks">
                    {[0, 1, 2].map((item) => <div key={item} className="skeleton-row"><span className="skeleton-art" /><span className="skeleton-copy"><i /><i /></span></div>)}
                  </div>
                ) : currentSong ? (
                  <>
                    <div className="selected-track mt-6 flex items-center gap-4">
                      {currentSong.thumbnail ? <img src={currentSong.thumbnail} alt="" className="selected-art" /> : <div className="selected-art art-placeholder"><Music2 /></div>}
                      <div className="min-w-0 flex-1">
                        <p className="truncate font-display text-lg font-bold">{currentSong.title}</p>
                        <p className="mt-1 truncate text-sm text-slate-500 dark:text-white/55">{currentSong.artist}</p>
                      </div>
                      <a
                        className="text-button inline-flex flex-none items-center gap-1"
                        href={youtubeLink(currentSong)}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        Listen on YouTube <ExternalLink size={14} />
                      </a>
                    </div>
                    {source === 'preview' && (
                      <p className="mt-3 text-xs font-semibold text-slate-500 dark:text-white/50">30s preview</p>
                    )}
                    <div className="playback-wave mt-6" aria-hidden="true">{Array.from({ length: 38 }, (_, index) => <i key={index} style={{ '--wave-delay': `${index * 34}ms`, '--wave-height': `${14 + ((index * 17) % 28)}px` } as CSSProperties} />)}</div>
                    <div className="mt-5 flex items-center justify-center gap-5">
                      <button type="button" className="icon-button" aria-label="Shuffle" onClick={shuffleTracks}><Shuffle size={17} /></button>
                      <button type="button" className="icon-button" aria-label="Previous track" onClick={() => moveTrack(-1)}><ChevronLeft size={21} /></button>
                      <button type="button" className="play-button" aria-label={isPlaying ? 'Pause' : 'Play'} onClick={togglePlayback}>
                        {isPlaying ? <Pause size={20} fill="currentColor" /> : <Play size={20} fill="currentColor" />}
                      </button>
                      <button type="button" className="icon-button" aria-label="Next track" onClick={() => moveTrack(1)}><ChevronRight size={21} /></button>
                      <button type="button" className="icon-button" aria-label="Favorite" onClick={() => setToast('Favorites are ready for a future playlist session.')}><Heart size={17} /></button>
                    </div>
                    <div className="track-progress mt-5">
                      <input
                        type="range"
                        min="0"
                        max="100"
                        step="0.1"
                        value={playbackProgress * 100}
                        aria-label="Track progress"
                        disabled={!isPlayerOpen || playbackDuration === 0}
                        onChange={(event) => {
                          const nextProgress = Number(event.target.value) / 100
                          setPlaybackProgress(nextProgress)
                          if (playbackDuration > 0) {
                            if (source === 'preview' && audioRef.current) {
                              audioRef.current.currentTime = nextProgress * playbackDuration
                            } else {
                              playerRef.current?.seekTo(nextProgress * playbackDuration, true)
                            }
                          }
                        }}
                      />
                      <div className="flex justify-between text-xs text-slate-500 dark:text-white/45">
                        <span>{formatTime(playbackProgress * playbackDuration)}</span>
                        <span>{formatTime(playbackDuration)}</span>
                      </div>
                    </div>
                    <audio
                      ref={audioRef}
                      src={source === 'preview' ? currentSong.previewUrl : undefined}
                      preload="metadata"
                      onLoadedMetadata={(event) => {
                        const duration = event.currentTarget.duration
                        if (Number.isFinite(duration) && duration > 0) {
                          setPlaybackDuration(duration)
                          setPlaybackProgress(0)
                        }
                      }}
                      onTimeUpdate={(event) => {
                        const audio = event.currentTarget
                        if (Number.isFinite(audio.duration) && audio.duration > 0) {
                          setPlaybackDuration(audio.duration)
                          setPlaybackProgress(Math.min(audio.currentTime / audio.duration, 1))
                        }
                      }}
                      onPlay={() => setIsPlaying(true)}
                      onPause={() => setIsPlaying(false)}
                      onEnded={() => moveTrack(1)}
                      onError={() => {
                        if (source === 'preview') {
                          previewAutoplayRef.current = false
                          playOnReadyRef.current = false
                          setIsPlaying(false)
                          setError('This preview could not be loaded. Choose another track or switch sources.')
                        }
                      }}
                    />
                    <div
                      className="youtube-frame mt-5 overflow-hidden rounded-2xl"
                      style={{
                        display: source === 'youtube' && isPlayerOpen ? undefined : 'none',
                      }}
                    >
                      <div ref={playerContainerRef} className="youtube-player w-full aspect-video" />
                    </div>
                  </>
                ) : (
                  <div className="empty-mix mt-7">
                    <AudioLines size={25} />
                    <strong>No tracks found yet</strong>
                    <span>Try another language or genre, or refresh this mix.</span>
                    <button className="text-button mt-3" onClick={retrySongSearch} type="button">Retry song search</button>
                  </div>
                )}
              </div>
            </article>

            <article className="glass-panel playlist-card reveal-on-scroll rounded-4xl p-5 sm:p-7">
              <div className="flex items-center justify-between">
                <div>
                  <span className="eyebrow">CURATED FOR YOUR FEELING</span>
                  <h3 className="mt-1 font-display text-2xl font-bold">Your queue</h3>
                </div>
                <span className="playlist-mood">{MOODS[mood].emoji} {MOODS[mood].label}</span>
              </div>
              {error && <div className="error-message mt-4" role="alert">{error}</div>}
              <div className="filter-groups mt-5">
                <div>
                  <p className="filter-label">SOURCE</p>
                  <div className="filter-chip-row">
                    <button
                      type="button"
                      className={`filter-chip ${source === 'youtube' ? 'selected' : ''}`}
                      aria-pressed={source === 'youtube'}
                      onClick={() => changeSource('youtube')}
                    >
                      YouTube
                    </button>
                    <button
                      type="button"
                      className={`filter-chip ${source === 'preview' ? 'selected' : ''}`}
                      aria-pressed={source === 'preview'}
                      onClick={() => changeSource('preview')}
                    >
                      Preview
                    </button>
                  </div>
                </div>
                <div>
                  <p className="filter-label">LANGUAGE</p>
                  <div className="filter-chip-row">
                    {LANGUAGES.map((option) => (
                      <button
                        type="button"
                        key={option.value}
                        className={`filter-chip ${language === option.value ? 'selected' : ''}`}
                        aria-pressed={language === option.value}
                        onClick={() => {
                          if (language === option.value) return
                          setIsLoadingSongs(true)
                          if (source === 'preview') setIsLoadingPreviews(true)
                          setError('')
                          setLanguage(option.value)
                        }}
                      >
                        {option.label}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="filter-label">GENRE</p>
                  <div className="filter-chip-row">
                    {GENRES.map((option) => (
                      <button
                        type="button"
                        key={option.value}
                        className={`filter-chip ${genre === option.value ? 'selected' : ''}`}
                        aria-pressed={genre === option.value}
                        onClick={() => {
                          if (genre === option.value) return
                          setIsLoadingSongs(true)
                          setError('')
                          setGenre(option.value)
                        }}
                      >
                        {option.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
              {((source === 'youtube' && isLoadingSongs && songs.length > 0) ||
                (source === 'preview' && isLoadingPreviews && previewSongs.length > 0)) && (
                <p className="mt-4 text-xs text-slate-500 dark:text-white/45" role="status">Refreshing suggestions…</p>
              )}
              <div className="mt-3 divide-y divide-slate-200/50 dark:divide-white/10">
                {((source === 'youtube' && isLoadingSongs && songs.length === 0) ||
                  (source === 'preview' && isLoadingPreviews && previewSongs.length === 0))
                  ? [0, 1, 2, 3].map((item) => <div key={item} className="playlist-skeleton"><i /><span><b /><b /></span></div>)
                  : activeSongs.map((song, index) => (
                    <div className="playlist-row" key={song.videoId}>
                      <button
                        type="button"
                        className={`playlist-item ${selectedSongId === song.videoId ? 'active' : ''} ${source === 'youtube' && failedIds.includes(song.videoId) ? 'unavailable' : ''}`}
                        onClick={() => {
                          setError('')
                          if (source === 'youtube') setActiveVideoId(song.videoId)
                          else setActivePreviewId(song.videoId)
                          const sameSong = currentSong?.videoId === song.videoId
                          setIsPlayerOpen(true)
                          if (sameSong) {
                            setIsPlaying(true)
                            if (source === 'preview') {
                              playOnReadyRef.current = false
                              void audioRef.current?.play().catch((cause: unknown) => {
                                setError(cause instanceof Error ? cause.message : 'Could not play this preview.')
                              })
                            } else {
                              playOnReadyRef.current = !playerReadyRef.current
                              if (playerReadyRef.current) {
                                playerRef.current?.playVideo()
                                playOnReadyRef.current = false
                              }
                            }
                          } else {
                            setIsPlaying(false)
                            playOnReadyRef.current = true
                          }
                        }}
                      >
                        <span className="playlist-index">{selectedSongId === song.videoId ? <AudioLines size={16} /> : String(index + 1).padStart(2, '0')}</span>
                        {song.thumbnail ? <img src={song.thumbnail} alt="" className="playlist-thumb" /> : <span className="playlist-thumb art-placeholder"><Music2 size={16} /></span>}
                        <span className="playlist-song"><strong>{song.title}</strong><small>{song.artist}</small></span>
                        <span className="playlist-duration">{song.duration}</span>
                        <Play className="playlist-play" size={16} fill="currentColor" />
                      </button>
                      <a
                        className="playlist-youtube-link"
                        href={youtubeLink(song)}
                        target="_blank"
                        rel="noopener noreferrer"
                        aria-label={`Listen to ${song.title} on YouTube`}
                        title="Listen on YouTube"
                      >
                        <ExternalLink size={15} />
                      </a>
                    </div>
                  ))}
              </div>
              {((source === 'youtube' && !isLoadingSongs && songs.length === 0) ||
                (source === 'preview' && !isLoadingPreviews && previewSongs.length === 0)) &&
                !error && <p className="mt-5 text-sm text-slate-500 dark:text-white/55">No songs were found for this mood and selection.</p>}
              {error && activeSongs.length === 0 && (
                <button className="text-button mt-4" type="button" onClick={source === 'youtube' ? retrySongSearch : () => setSource('youtube')}>Retry</button>
              )}
            </article>
          </div>
        </section>

        <section id="history" className="section-block scroll-mt-24 py-14 sm:py-20">
          <div className="flex flex-wrap items-end justify-between gap-4 reveal-on-scroll">
            <div className="section-heading mb-0">
              <span className="eyebrow">A MOMENT TO LOOK BACK</span>
              <h2>Your mood, over time.</h2>
              <p>Your check-ins stay in this browser, saved privately on this device.</p>
            </div>
            {history.length > 0 && <button type="button" className="text-button" onClick={clearHistory}>Clear history</button>}
          </div>
          <div className="glass-panel chart-card reveal-on-scroll mt-7 rounded-4xl p-4 sm:p-7">
            {history.length === 0 ? (
              <div className="chart-empty"><span>📈</span><strong>Your check-ins will appear here</strong><p>Scan or choose a mood to start your personal mood history.</p></div>
            ) : (
              <>
                <div className="mb-4 flex items-center justify-between text-xs font-bold uppercase tracking-widest text-slate-500 dark:text-white/45">
                  <span>Check-ins by mood</span><span>{history.length} total</span>
                </div>
                <div className="h-[270px] w-full">
                  <Suspense fallback={<div className="chart-placeholder">Preparing your mood chart…</div>}>
                    <MoodHistoryChart counts={counts} />
                  </Suspense>
                </div>
                <div className="recent-moods mt-5">
                  {[...history].reverse().slice(0, 6).map((entry) => (
                    <span className="recent-chip" key={`${entry.timestamp}-${entry.emotion}`}>
                      {MOODS[entry.emotion].emoji} {new Date(entry.timestamp).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}
                    </span>
                  ))}
                </div>
              </>
            )}
          </div>
        </section>

        <footer className="footer-line flex flex-col gap-3 border-t border-white/15 py-7 text-xs text-slate-500 dark:text-white/45 sm:flex-row sm:items-center sm:justify-between">
          <span className="font-display font-bold text-slate-700 dark:text-white/70">♫ Moodwave</span>
          <span>Find your sound. Keep your moments private.</span>
          <span>Made for every mood.</span>
        </footer>
      </div>
      {currentSong && isPlayerOpen && (
        <div className="mini-player-dock">
          {currentSong.thumbnail && <img className="mini-player-backdrop" src={currentSong.thumbnail} alt="" />}
          {currentSong.thumbnail ? <img src={currentSong.thumbnail} alt="" /> : <span className="mini-player-art"><Music2 size={17} /></span>}
          <div className="mini-player-info"><strong>{currentSong.title}</strong><small>{currentSong.artist}</small></div>
          <div className="mini-player-wave" aria-hidden="true">{Array.from({ length: 12 }, (_, index) => <i key={index} style={{ '--wave-delay': `${index * 70}ms`, '--wave-height': `${8 + ((index * 11) % 17)}px` } as CSSProperties} />)}</div>
          <div className="mini-player-progress" aria-hidden="true"><i style={{ width: `${playbackProgress * 100}%` }} /></div>
          <button type="button" className="mini-player-control" onClick={togglePlayback} aria-label={isPlaying ? 'Pause current song' : 'Play current song'}>
            {isPlaying ? <Pause size={17} fill="currentColor" /> : <Play size={17} fill="currentColor" />}
          </button>
          <button type="button" className="mini-player-control next-control" onClick={() => moveTrack(1)} aria-label="Next song"><ChevronRight size={20} /></button>
        </div>
      )}
      {showConfetti && (
        <div className="confetti-overlay" aria-hidden="true">
          {Array.from({ length: 28 }, (_, index) => (
            <i
              key={index}
              style={{
                '--confetti-x': `${(index * 37) % 100}%`,
                '--confetti-delay': `${(index % 7) * 55}ms`,
                '--confetti-color': ['#ff6fa7', '#9775ff', '#64dfe0', '#ffd166'][index % 4],
              } as CSSProperties}
            />
          ))}
        </div>
      )}
      {toast && <div className="toast-message" role="status">{toast}</div>}
    </main>
  )
}

export default App
