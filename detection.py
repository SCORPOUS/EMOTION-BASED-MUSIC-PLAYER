import cv2
import numpy as np
from deepface import DeepFace
from collections import Counter
import threading
import time
import streamlit as st

EMO = {
    "happy":    {"emoji": "😊", "color": "#1DB954", "q": "happy upbeat feel good hits"},
    "sad":      {"emoji": "😢", "color": "#74b9ff", "q": "sad emotional heartbreak songs"},
    "angry":    {"emoji": "😠", "color": "#ff7675", "q": "angry intense rock workout"},
    "surprise": {"emoji": "😲", "color": "#fdcb6e", "q": "exciting energetic party songs"},
    "fear":     {"emoji": "😰", "color": "#a29bfe", "q": "calming peaceful relaxing songs"},
    "disgust":  {"emoji": "🤢", "color": "#55efc4", "q": "powerful empowering anthems"},
    "neutral":  {"emoji": "😐", "color": "#b3b3b3", "q": "chill lofi study relaxing beats"},
}


@st.cache_resource
def preload_model():
    """Pre-load DeepFace emotion model so the first detection is fast."""
    try:
        dummy = np.zeros((48, 48, 3), dtype=np.uint8)
        DeepFace.analyze(dummy, actions=["emotion"], enforce_detection=False)
    except Exception:
        pass


def detect_mood_live(placeholder, duration=5):
    """Run live camera with emotion overlay for *duration* seconds.

    Frames are displayed at ~30 fps in the Streamlit *placeholder*.
    DeepFace runs in a background thread every ~1.5 s so the video
    stays smooth.  A countdown timer is shown on-screen.

    Returns
    -------
    (dominant_emotion : str, error : str | None)
    """
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return None, "Could not access webcam"

    state = {"emotion": "scanning...", "history": [], "busy": False}
    lock = threading.Lock()

    def _analyze(frame_bgr):
        """Background worker — runs DeepFace on one frame."""
        try:
            r = DeepFace.analyze(frame_bgr, actions=["emotion"],
                                 enforce_detection=False)
            detected = r[0]["dominant_emotion"]
            with lock:
                state["emotion"] = detected
                state["history"].append(detected)
        except Exception:
            pass
        finally:
            with lock:
                state["busy"] = False

    start = time.time()
    last_trigger = 0.0

    while True:
        elapsed = time.time() - start
        if elapsed >= duration:
            break

        ret, frame = cap.read()
        if not ret:
            time.sleep(0.03)
            continue

        now = time.time()
        remaining = max(0, duration - elapsed)

        with lock:
            is_busy = state["busy"]
        if not is_busy and (now - last_trigger) > 1.5:
            with lock:
                state["busy"] = True
            last_trigger = now
            threading.Thread(target=_analyze, args=(frame.copy(),),
                             daemon=True).start()

        with lock:
            emo_text = state["emotion"]

        # Draw overlay
        h, w = frame.shape[:2]
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, h - 34), (w, h), (0, 0, 0), -1)
        frame = cv2.addWeighted(overlay, 0.55, frame, 0.45, 0)
        cv2.putText(frame, emo_text.upper(), (10, h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 255, 180), 2)
        cv2.putText(frame, f"{remaining:.0f}s", (w - 50, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)

        # Push frame to Streamlit
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        placeholder.image(rgb, use_container_width=True)

        time.sleep(0.033)  # cap at ~30 fps

    cap.release()

    history = state["history"]
    if not history:
        return "neutral", None

    dominant = Counter(history).most_common(1)[0][0]
    return dominant, None
