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

MOOD_KEYWORDS = {
    "happy": ("happy", "upbeat", "feel good"),
    "sad": ("sad", "emotional", "heartbreak"),
    "angry": ("angry", "intense", "rock"),
    "surprise": ("exciting", "energetic", "party"),
    "fear": ("calming", "peaceful", "relaxing"),
    "disgust": ("powerful", "empowering", "anthem"),
    "neutral": ("chill", "lofi", "study"),
}


def build_mood_queries(emotion: str, lang: str) -> list[str]:
    language = LANGUAGE_NAMES.get(lang.lower(), lang)
    keywords = MOOD_KEYWORDS.get(emotion, MOOD_KEYWORDS["neutral"])
    return [f"{language} {keyword} songs" for keyword in keywords]
