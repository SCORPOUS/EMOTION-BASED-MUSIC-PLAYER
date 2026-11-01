from collections import Counter
from datetime import datetime
import html
import random

import streamlit as st

from detection import EMO, detect_mood_live, preload_model
from music import get_songs, player_html


st.set_page_config(
    page_title="Moodwave | Emotion-Based Music Player",
    page_icon="🎧",
    layout="wide",
    initial_sidebar_state="collapsed",
)

EMOTION_ORDER = ("happy", "sad", "angry", "surprise", "fear", "neutral")
EMOTION_VIBES = {
    "happy": "Bright, feel-good hits",
    "sad": "Soft, heartfelt songs",
    "angry": "High-energy rock",
    "surprise": "Unexpected party anthems",
    "fear": "Calm, peaceful sounds",
    "neutral": "Easygoing lo-fi beats",
}
GITHUB_URL = "https://github.com/SCORPOUS/EMOTION-BASED-MUSIC-PLAYER"
CONTACT_URL = f"{GITHUB_URL}/issues"

def initialize_state():
    defaults = {
        "playlist": [],
        "playlist_emotion": None,
        "playlist_language": None,
        "selected_language": "English",
        "current_song": None,
        "now_playing": None,
        "current_index": -1,
        "current_emotion": "neutral",
        "mood_history": [],
        "favorites": {},
        "light_mode": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def inject_styles():
    light_mode = st.session_state["light_mode"]
    page_bg = "#f7f1ff" if light_mode else "#080d1d"
    page_bg_2 = "#fff7d9" if light_mode else "#17152b"
    card_bg = "rgba(255,255,255,.52)" if light_mode else "rgba(18, 21, 38, .68)"
    text_color = "#1a1330" if light_mode else "#f3f6ff"
    muted_color = "#524c6d" if light_mode else "#c7d2ff"
    border_color = "rgba(122, 97, 255, .24)" if light_mode else "rgba(142, 165, 255, .22)"
    active_mood = st.session_state.get("current_emotion", "neutral")
    mood_info = EMO.get(active_mood, EMO["neutral"])
    mood_color = mood_info["color"]
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Sora:wght@400;500;600;700;800&display=swap');
        :root {{
            --page-bg: {page_bg};
            --page-bg-2: {page_bg_2};
            --card-bg: {card_bg};
            --text: {text_color};
            --muted: {muted_color};
            --border: {border_color};
            --shadow: rgba(20, 15, 36, .14);
            --pink: #ff5ca8;
            --purple: #8b5cf6;
            --cyan: #67e8f9;
            --orange: #ff9f6e;
            --yellow: #ffd166;
            --mood-accent: {mood_color};
            --mood-accent-soft: rgba(255,255,255,.18);
            --radius-xl: 24px;
        }}
        html, body {{ min-height: 100%; }}
        html {{ scroll-behavior: smooth; }}
        * {{ font-family: 'Inter', sans-serif; box-sizing: border-box; }}
        body, .stApp {{
            background: linear-gradient(135deg, var(--page-bg) 0%, var(--page-bg-2) 100%);
            color: var(--text);
        }}
        .stApp {{ position: relative; min-height: 100vh; overflow-x: hidden; }}
        [data-testid="stSidebar"], [data-testid="collapsedControl"],
        [data-testid="stFooter"], #MainMenu, .stDeployButton {{ display: none !important; }}
        header {{ background: transparent !important; }}
        .block-container {{
            max-width: 1180px !important;
            padding: 1.2rem clamp(1rem, 4vw, 3rem) 2rem !important;
        }}
        .app-shell {{
            position: relative; display: block;
            padding-bottom: 3rem;
        }}
        .app-shell::before {{
            content: ""; position: fixed; inset: -15% -10% auto auto; width: 48vw; height: 48vw;
            border-radius: 45% 55% 58% 42% / 45% 38% 62% 55%;
            background: radial-gradient(circle at center, rgba(255,92,168,.34), rgba(103,232,249,.18) 32%, transparent 68%);
            filter: blur(18px); opacity: .8; pointer-events: none; z-index: 0;
            animation: meshFloat 14s ease-in-out infinite alternate;
        }}
        .app-shell::after {{
            content: ""; position: fixed; inset: auto auto -12% -10%; width: 52vw; height: 52vw;
            border-radius: 52% 48% 44% 56% / 49% 58% 42% 51%;
            background: radial-gradient(circle at center, rgba(139,92,246,.28), rgba(255,159,110,.18) 33%, transparent 72%);
            filter: blur(22px); opacity: .82; pointer-events: none; z-index: 0;
            animation: meshFloat 16s ease-in-out infinite alternate-reverse;
        }}
        .app-shell[data-mood="happy"]::before {{ background: radial-gradient(circle at center, rgba(29,185,84,.38), rgba(103,232,249,.18) 32%, transparent 68%); }}
        .app-shell[data-mood="happy"]::after {{ background: radial-gradient(circle at center, rgba(255,209,102,.28), rgba(255,92,168,.18) 33%, transparent 72%); }}
        .app-shell[data-mood="sad"]::before {{ background: radial-gradient(circle at center, rgba(116,185,255,.38), rgba(142,165,255,.18) 32%, transparent 68%); }}
        .app-shell[data-mood="sad"]::after {{ background: radial-gradient(circle at center, rgba(191,219,254,.26), rgba(103,232,249,.14) 35%, transparent 72%); }}
        .app-shell[data-mood="angry"]::before {{ background: radial-gradient(circle at center, rgba(255,118,117,.4), rgba(255,159,110,.18) 30%, transparent 68%); }}
        .app-shell[data-mood="angry"]::after {{ background: radial-gradient(circle at center, rgba(255,92,168,.28), rgba(255,209,102,.16) 35%, transparent 72%); }}
        .app-shell[data-mood="surprise"]::before {{ background: radial-gradient(circle at center, rgba(253,203,110,.38), rgba(255,92,168,.18) 32%, transparent 68%); }}
        .app-shell[data-mood="surprise"]::after {{ background: radial-gradient(circle at center, rgba(255,209,102,.26), rgba(103,232,249,.2) 33%, transparent 72%); }}
        .app-shell[data-mood="fear"]::before {{ background: radial-gradient(circle at center, rgba(162,155,254,.38), rgba(103,232,249,.18) 32%, transparent 68%); }}
        .app-shell[data-mood="fear"]::after {{ background: radial-gradient(circle at center, rgba(103,232,249,.28), rgba(139,92,246,.16) 34%, transparent 72%); }}
        .app-shell[data-mood="neutral"]::before {{ background: radial-gradient(circle at center, rgba(139,92,246,.34), rgba(103,232,249,.18) 32%, transparent 68%); }}
        .app-shell[data-mood="neutral"]::after {{ background: radial-gradient(circle at center, rgba(255,92,168,.18), rgba(255,159,110,.18) 33%, transparent 72%); }}
        .topnav, .glass-card, [data-testid="stVerticalBlockBorderWrapper"], .hero-visual, .mini-player {{
            border: 1px solid var(--border) !important;
            backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
            background: linear-gradient(135deg, rgba(255,255,255,.14), rgba(255,255,255,.04));
            box-shadow: 0 18px 55px rgba(25, 16, 42, .08);
        }}
        .topnav {{
            position: sticky; top: .45rem; z-index: 10;
            display: flex; align-items: center; gap: 1.2rem;
            padding: .7rem 1rem; margin: 0 0 2.3rem;
            border-radius: 20px; background: rgba(255,255,255,.1);
            backdrop-filter: blur(18px); -webkit-backdrop-filter: blur(18px);
        }}
        .brand {{
            display: flex; align-items: center; gap: .6rem;
            color: var(--text); font-weight: 800; font-size: 1.05rem;
            font-family: 'Sora', 'Inter', sans-serif; text-decoration: none;
            white-space: nowrap;
        }}
        .brand-mark {{
            display: grid; place-items: center; width: 36px; height: 36px;
            border-radius: 50%; background: linear-gradient(135deg, var(--purple), var(--pink));
            color: #fff; box-shadow: 0 10px 24px rgba(139,92,246,.38);
        }}
        .nav-links {{ display: flex; align-items: center; gap: 1.2rem; margin-left: auto; }}
        .nav-links a {{
            color: var(--muted); font-size: .82rem; text-decoration: none; letter-spacing: .02em;
            transition: color .18s ease, transform .18s ease;
        }}
        .nav-links a:hover {{ color: var(--pink); transform: translateY(-1px); }}
        .theme-control {{ flex: 0 0 auto; }}
        .theme-control [data-testid="stToggle"] {{ justify-content: flex-end; }}
        .eyebrow {{
            color: var(--mood-accent); font-size: .78rem; font-weight: 800;
            letter-spacing: .14em; text-transform: uppercase;
        }}
        .hero {{
            position: relative; z-index: 1; display: grid; grid-template-columns: 1.05fr .95fr;
            align-items: center; gap: clamp(2rem, 7vw, 5rem); min-height: 100vh; padding: 1.5rem 0 3rem;
        }}
        .hero h1 {{
            color: var(--text); max-width: 700px; margin: .75rem 0 1rem; font-size: clamp(2.7rem, 6.4vw, 5.7rem);
            line-height: .98; letter-spacing: -.07em; font-weight: 800; font-family: 'Sora', 'Inter', sans-serif;
        }}
        .hero h1 span {{
            color: var(--mood-accent);
            background: linear-gradient(120deg, var(--mood-accent) 12%, var(--purple) 44%, var(--cyan) 100%);
            -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
        }}
        .hero-copy {{
            max-width: 560px; color: var(--muted); font-size: clamp(1rem, 1.6vw, 1.15rem); line-height: 1.8;
        }}
        .hero-cta {{
            position: relative; overflow: hidden; display: inline-flex; align-items: center; justify-content: center;
            padding: .9rem 1.35rem; border-radius: 999px; background: linear-gradient(135deg, var(--mood-accent), var(--pink));
            color: #fefcff; box-shadow: 0 16px 32px rgba(255, 92, 168, .28); font-weight: 800;
            text-decoration: none; transition: transform .2s ease, box-shadow .2s ease, filter .2s ease;
        }}
        .hero-cta::before {{
            content: ""; position: absolute; inset: 0; background: linear-gradient(120deg, transparent 0%, rgba(255,255,255,.4) 35%, transparent 70%);
            transform: translateX(-120%); animation: shimmer 2.6s ease-in-out infinite;
        }}
        .hero-cta:hover {{ transform: translateY(-3px); box-shadow: 0 20px 36px rgba(255, 92, 168, .38); }}
        .hero-visual {{
            position: relative; display: grid; place-items: center; min-height: 370px; overflow: hidden; border-radius: 34px;
            background: radial-gradient(circle at 50% 25%, rgba(255,255,255,.18), transparent 25%),
                        linear-gradient(150deg, rgba(255,255,255,.1), rgba(255,255,255,.02));
            animation: fadeUp .7s ease both;
        }}
        .hero-visual::before {{
            content: ""; position: absolute; inset: 8% 10%; border-radius: 28px;
            background: radial-gradient(circle at 50% 50%, rgba(255,255,255,.18), transparent 52%);
            filter: blur(26px);
        }}
        .scan-ring {{
            position: absolute; width: 230px; height: 230px; border-radius: 50%;
            border: 1px solid rgba(255,255,255,.5); box-shadow: inset 0 0 26px rgba(255,255,255,.14), 0 0 30px rgba(255,255,255,.1);
            animation: spin 10s linear infinite;
        }}
        .scan-ring::before, .scan-ring::after {{
            content: ""; position: absolute; inset: 18px; border-radius: 50%; border: 1px solid rgba(255,255,255,.25);
        }}
        .scan-ring::after {{ inset: 42px; border-color: rgba(255,255,255,.38); animation: spinReverse 8s linear infinite; }}
        .hero-emoji {{
            position: relative; z-index: 1; font-size: clamp(5.4rem, 11vw, 8.8rem);
            filter: drop-shadow(0 12px 30px rgba(255,255,255,.2));
            animation: float 3.6s ease-in-out infinite;
        }}
        .emoji-halo {{
            position: absolute; width: 200px; height: 200px; border-radius: 50%;
            background: radial-gradient(circle, rgba(255,255,255,.42) 0%, var(--mood-accent) 30%, rgba(255,255,255,0) 68%);
            filter: blur(16px); opacity: .36; animation: pulse 3s ease-in-out infinite;
        }}
        .hero-caption {{
            position: relative; z-index: 1; margin-top: -.6rem; color: var(--muted); font-size: .8rem;
            letter-spacing: .1em; text-transform: uppercase;
        }}
        .soundwave {{ display: flex; align-items: center; gap: 5px; height: 42px; margin-top: 1.2rem; position: relative; z-index: 1; }}
        .soundwave span {{
            width: 4px; height: var(--h); border-radius: 9px; background: linear-gradient(180deg, var(--mood-accent), var(--cyan));
            opacity: .95; animation: wave .9s ease-in-out infinite alternate; animation-delay: var(--delay);
        }}
        .chip-row {{ display: flex; flex-wrap: wrap; gap: .75rem; margin-top: 1.5rem; }}
        .mood-chip {{
            display: inline-flex; align-items: center; gap: .45rem; padding: .55rem .85rem; border-radius: 999px;
            border: 1px solid rgba(255,255,255,.18); background: rgba(255,255,255,.08); color: var(--text);
            font-size: .76rem; font-weight: 700; box-shadow: 0 8px 24px rgba(18, 10, 34, .12);
        }}
        .section {{ position: relative; z-index: 1; padding: 3rem 0; scroll-margin-top: 110px; }}
        .section-heading {{ margin-bottom: 1.3rem; }}
        .section-heading h2 {{
            color: var(--text); margin: .5rem 0 .6rem; font-size: clamp(1.7rem, 3vw, 2.6rem);
            letter-spacing: -.05em; font-weight: 800; font-family: 'Sora', 'Inter', sans-serif;
        }}
        .section-heading p {{ color: var(--muted); line-height: 1.7; max-width: 680px; }}
        .glass-card {{
            height: 100%; padding: 1.2rem; border-radius: var(--radius-xl); background: var(--card-bg);
            backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
            transition: transform .22s ease, border-color .22s ease, box-shadow .22s ease, filter .22s ease;
            animation: fadeUp .55s ease both;
        }}
        .glass-card:hover {{
            transform: translateY(-6px); border-color: rgba(103,232,249,.8);
            box-shadow: 0 24px 44px rgba(18, 12, 36, .18); filter: saturate(1.18);
        }}
        .step-number {{ color: var(--mood-accent); font-size: .72rem; font-weight: 800; letter-spacing: .12em; }}
        .step-icon {{ margin: .9rem 0 .5rem; font-size: 1.7rem; }}
        .glass-card h3 {{ color: var(--text); font-size: 1.02rem; margin: .35rem 0; font-weight: 700; }}
        .glass-card p {{ color: var(--muted); font-size: .85rem; line-height: 1.65; margin: .35rem 0 0; }}
        .feature-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 1rem; }}
        .feature-icon {{ display: inline-grid; place-items: center; width: 42px; height: 42px; border-radius: 14px; background: linear-gradient(135deg, rgba(255,92,168,.18), rgba(103,232,249,.18)); color: var(--mood-accent); font-size: 1.2rem; }}
        .emotion-card {{ position: relative; overflow: hidden; min-height: 150px; border-radius: 24px; }}
        .emotion-card:before {{
            content: ""; position: absolute; inset: 0; background: radial-gradient(circle at 110% 0%, rgba(255,255,255,.5), transparent 30%);
            pointer-events: none;
        }}
        .emotion-card:hover {{ transform: perspective(1000px) rotateX(4deg) rotateY(-5deg) translateY(-6px) scale(1.01); }}
        .emotion-card .emotion-icon {{ font-size: 2.5rem; margin-bottom: .55rem; display: block; filter: drop-shadow(0 8px 18px rgba(255,255,255,.18)); }}
        .emotion-card .emotion-name {{ text-transform: capitalize; }}
        .badge-row {{ display: flex; flex-wrap: wrap; gap: .7rem; }}
        .tech-badge {{
            display: inline-flex; align-items: center; padding: .58rem .9rem; border-radius: 999px; border: 1px solid var(--border);
            background: rgba(255,255,255,.12); color: var(--text); font-size: .74rem; font-weight: 700; letter-spacing: .03em;
        }}
        .site-footer {{
            position: relative; z-index: 1; display: flex; flex-wrap: wrap; justify-content: space-between; gap: 1rem;
            padding: 1.5rem 0 .5rem; color: var(--muted); font-size: .8rem;
        }}
        .site-footer a {{ color: var(--mood-accent); text-decoration: none; }}
        [data-testid="stVerticalBlockBorderWrapper"] {{
            border-radius: 22px !important; background: rgba(255,255,255,.07); padding: 1.15rem;
        }}
        .player-title {{ color: var(--text); font-size: 1.1rem; font-weight: 800; font-family: 'Sora', 'Inter', sans-serif; }}
        .player-subtitle {{ color: var(--muted); font-size: .85rem; }}
        .history-chart {{
            display: flex; align-items: flex-end; justify-content: space-around; gap: .45rem;
            min-height: 155px; padding: 1rem .5rem .3rem; border-bottom: 1px solid var(--border);
        }}
        .history-item {{ display: flex; flex: 1; flex-direction: column; align-items: center; gap: .4rem; min-width: 0; }}
        .history-count {{ color: var(--muted); font-size: .7rem; }}
        .history-bar {{ width: min(32px, 70%); min-height: 5px; border-radius: 13px 13px 6px 6px; transition: height .3s ease; }}
        .history-label {{ color: var(--muted); font-size: .65rem; text-transform: capitalize; }}
        .playlist-row {{
            display: flex; align-items: center; gap: .8rem; padding: .75rem .65rem; border-bottom: 1px solid var(--border);
            border-radius: 14px; transition: background .18s ease;
        }}
        .playlist-row:hover {{ background: rgba(255,255,255,.04); }}
        .track-number {{ color: var(--muted); width: 22px; text-align: right; font-size: .8rem; }}
        .track-info {{ min-width: 0; flex: 1; }}
        .track-title {{ overflow: hidden; color: var(--text); font-size: .9rem; font-weight: 700; text-overflow: ellipsis; white-space: nowrap; }}
        .track-artist {{ overflow: hidden; color: var(--muted); font-size: .75rem; text-overflow: ellipsis; white-space: nowrap; }}
        .track-duration {{ color: var(--muted); font-size: .75rem; white-space: nowrap; }}
        .empty-state {{ padding: 1.5rem; text-align: center; color: var(--muted); }}
        .empty-state strong {{ display: block; color: var(--text); font-size: 1rem; margin: .5rem; }}
        div[data-testid="stButton"] button, div[data-testid="stPageLink"] a {{
            border-radius: 999px; transition: transform .18s ease, filter .18s ease, box-shadow .18s ease;
        }}
        div[data-testid="stButton"] button:hover, div[data-testid="stPageLink"] a:hover {{
            transform: translateY(-1px); box-shadow: 0 10px 18px rgba(22, 15, 38, .12);
        }}
        div[data-testid="stButton"] button[kind="primary"] {{
            background: linear-gradient(135deg, var(--pink), var(--mood-accent)); border: 0; color: white; font-weight: 800;
        }}
        div[data-testid="stPageLink"] a {{
            border: 1px solid var(--pink); background: linear-gradient(135deg, var(--pink), var(--mood-accent)); color: white; font-weight: 800;
            text-decoration: none;
        }}
        [data-testid="stHorizontalBlock"] {{ gap: 1rem; }}
        .mini-player {{
            position: sticky; top: 5.3rem; z-index: 6; overflow: hidden; border-radius: 24px; padding: 1rem; background: linear-gradient(135deg, rgba(255,255,255,.08), rgba(255,255,255,.04));
        }}
        .mini-player .album-art {{
            position: absolute; inset: 0; background: radial-gradient(circle at 30% 20%, rgba(255,255,255,.28), transparent 38%),
                        linear-gradient(135deg, rgba(255,92,168,.25), rgba(103,232,249,.18), rgba(139,92,246,.22));
            filter: blur(10px); transform: scale(1.18);
        }}
        .confetti-wrap {{ position: absolute; inset: 0; pointer-events: none; overflow: hidden; }}
        .confetti {{
            position: absolute; width: 8px; height: 18px; border-radius: 999px; background: var(--mood-accent);
            top: -16px; opacity: .9; animation: confettiFall 2.4s ease-in forwards;
        }}
        @keyframes float {{ 0%,100% {{ transform: translateY(0) rotate(-3deg); }} 50% {{ transform: translateY(-12px) rotate(3deg); }} }}
        @keyframes wave {{ from {{ transform: scaleY(.35); opacity: .45; }} to {{ transform: scaleY(1); opacity: 1; }} }}
        @keyframes pulse {{ 0% {{ transform: scale(.75); opacity: .45; }} 100% {{ transform: scale(1.5); opacity: 0; }} }}
        @keyframes fadeUp {{ from {{ opacity: 0; transform: translateY(12px); }} to {{ opacity: 1; transform: translateY(0); }} }}
        @keyframes shimmer {{ 0% {{ transform: translateX(-120%); }} 100% {{ transform: translateX(200%); }} }}
        @keyframes meshFloat {{ 0% {{ transform: translate3d(0,0,0) scale(1) rotate(0deg); }} 100% {{ transform: translate3d(2%, -3%, 0) scale(1.08) rotate(12deg); }} }}
        @keyframes spin {{ from {{ transform: rotate(0deg); }} to {{ transform: rotate(360deg); }} }}
        @keyframes spinReverse {{ from {{ transform: rotate(360deg); }} to {{ transform: rotate(0deg); }} }}
        @keyframes confettiFall {{
            0% {{ transform: translateY(0) rotate(0deg); opacity: 0; }}
            15% {{ opacity: 1; }}
            100% {{ transform: translateY(220px) rotate(360deg); opacity: 0; }}
        }}
        @media (max-width: 760px) {{
            .block-container {{ padding: .7rem 1rem 1.5rem !important; }}
            .topnav {{ gap: .65rem; padding: .5rem .7rem; margin-bottom: 1.2rem; }}
            .brand {{ font-size: .9rem; }}
            .brand-mark {{ width: 30px; height: 30px; }}
            .nav-links {{ gap: .65rem; }}
            .nav-links a {{ font-size: .7rem; }}
            .hero {{ grid-template-columns: 1fr; gap: 1.5rem; min-height: 0; padding: 1rem 0 2rem; }}
            .hero-visual {{ min-height: 250px; }}
            .feature-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
            .section {{ padding: 2rem 0; }}
        }}
        @media (max-width: 520px) {{
            .topnav {{ flex-wrap: wrap; }}
            .brand {{ flex: 1; }}
            .nav-links {{ order: 3; width: 100%; justify-content: space-between; }}
            .theme-control {{ margin-left: auto; }}
            .site-footer {{ flex-direction: column; align-items: flex-start; }}
            .feature-grid {{ grid-template-columns: 1fr; }}
        }}
        @media (prefers-reduced-motion: reduce) {{
            *, *::before, *::after {{ scroll-behavior: auto !important; animation-duration: .01ms !important; transition-duration: .01ms !important; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
def render_nav():
    st.markdown(
        """
        <div id="top" class="topnav">
            <a class="brand" href="/"><span class="brand-mark">♫</span> Moodwave</a>
            <nav class="nav-links" aria-label="Main navigation">
                <a href="/">Home</a>
                <a href="/player">Player</a>
                <a href="/#how-it-works">How it works</a>
                <a href="/#about">About</a>
            </nav>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _, theme_col = st.columns([5, 1])
    with theme_col:
        st.toggle("Light mode", key="light_mode")


def section_heading(eyebrow, title, description, section_id=None):
    anchor = f' id="{html.escape(section_id, quote=True)}"' if section_id else ""
    st.markdown(
        f"""
        <div class="section section-heading"{anchor}>
            <div class="eyebrow">{html.escape(eyebrow)}</div>
            <h2>{html.escape(title)}</h2>
            <p>{html.escape(description)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_footer():
    st.markdown(
        f"""
        <footer class="site-footer" id="about">
            <span>© {datetime.now().year} Moodwave · Find your sound.</span>
            <span>
                <a href="{GITHUB_URL}" target="_blank" rel="noopener noreferrer">GitHub</a>
                &nbsp;·&nbsp;
                <a href="{CONTACT_URL}" target="_blank" rel="noopener noreferrer">Contact / feedback</a>
            </span>
            <span>Built with Streamlit, OpenCV, DeepFace &amp; YTMusic</span>
        </footer>
        """,
        unsafe_allow_html=True,
    )


def home_page():
    render_nav()
    mood = st.session_state.get("current_emotion", "neutral")
    mood_meta = EMO.get(mood, EMO["neutral"])
    st.markdown(f'<div class="app-shell" data-mood="{mood}">', unsafe_allow_html=True)
    st.markdown(
        f"""
        <section class="hero">
            <div>
                <div class="eyebrow">Music that meets the moment</div>
                <h1>Your mood.<br>Your <span>soundtrack.</span></h1>
                <p class="hero-copy">
                    A quick camera scan finds the feeling. A fresh playlist finds the sound.
                    Take a breath, look at the camera, and let the music meet you where you are.
                </p>
                <div class="chip-row">
                    <span class="mood-chip">{mood_meta['emoji']} {mood.title()}</span>
                    <span class="mood-chip">Live AI mood scan</span>
                    <span class="mood-chip">Glass soundboard</span>
                </div>
                <div style="height:1rem"></div>
                <a class="hero-cta" href="/player">🎧&nbsp; Detect My Mood</a>
            </div>
            <div class="hero-visual" aria-label="Animated mood and music illustration">
                <div class="emoji-halo"></div>
                <div class="scan-ring"></div>
                <div style="position:relative;display:grid;place-items:center;z-index:1">
                    <div class="hero-emoji">{mood_meta['emoji']}</div>
                    <div class="hero-caption">One feeling. A thousand songs.</div>
                    <div class="soundwave">
                        <span style="--h:16px;--delay:.0s"></span>
                        <span style="--h:28px;--delay:.1s"></span>
                        <span style="--h:21px;--delay:.2s"></span>
                        <span style="--h:36px;--delay:.3s"></span>
                        <span style="--h:17px;--delay:.4s"></span>
                        <span style="--h:30px;--delay:.5s"></span>
                        <span style="--h:22px;--delay:.6s"></span>
                        <span style="--h:34px;--delay:.7s"></span>
                        <span style="--h:15px;--delay:.8s"></span>
                    </div>
                </div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)
    section_heading(
        "Simple by design",
        "How it works",
        "Three small steps from a feeling to your next favorite song.",
        section_id="how-it-works",
    )
    steps = [
        ("01", "📷", "Scan your face", "Allow camera access and let the app read a short live preview."),
        ("02", "✨", "AI finds the mood", "DeepFace analyzes frames on the machine running this local app."),
        ("03", "🎶", "Press play", "A mood-matched playlist is ready to explore in the player."),
    ]
    columns = st.columns(3)
    for column, (number, icon, title, copy) in zip(columns, steps):
        with column:
            st.markdown(
                f"""
                <article class="glass-card">
                    <div class="step-number">STEP {number}</div>
                    <div class="step-icon">{icon}</div>
                    <h3>{title}</h3>
                    <p>{copy}</p>
                </article>
                """,
                unsafe_allow_html=True,
            )
    section_heading(
        "A playlist for every feeling",
        "Meet your moods",
        "Every emotion opens a different listening lane. Pick a mood manually any time in the player.",
    )
    columns = st.columns(3)
    for index, mood in enumerate(EMOTION_ORDER):
        emotion = EMO[mood]
        with columns[index % 3]:
            st.markdown(
                f"""
                <article class="glass-card emotion-card" style="--mood-color:{emotion['color']}">
                    <div class="emotion-icon">{emotion['emoji']}</div>
                    <h3 class="emotion-name">{html.escape(mood)}</h3>
                    <p>{html.escape(EMOTION_VIBES[mood])}</p>
                </article>
                """,
                unsafe_allow_html=True,
            )
    section_heading(
        "Thoughtful by nature",
        "Made for the moment",
        "Everything you need for a simple, personal listening experience.",
    )
    features = [
        ("◉", "Real-time detection", "A brief camera scan estimates your current expression."),
        ("♫", "Mood-matched playlists", "Discover songs selected around the detected or chosen mood."),
        ("▶", "In-app player", "Play tracks, move through a playlist, and save favorites."),
        ("⌂", "Privacy-first", "When run locally, camera frames are analyzed on your own machine."),
    ]
    columns = st.columns(4)
    for column, (icon, title, copy) in zip(columns, features):
        with column:
            st.markdown(
                f"""
                <article class="glass-card">
                    <span class="feature-icon">{icon}</span>
                    <h3 style="margin-top:1rem">{title}</h3>
                    <p>{copy}</p>
                </article>
                """,
                unsafe_allow_html=True,
            )
    section_heading(
        "Under the hood",
        "A little tech, a lot of feeling",
        "Built with familiar tools that bring camera input, emotion analysis, and music search together.",
    )
    st.markdown(
        '<div class="badge-row">'
        + "".join(
            f'<span class="tech-badge">{label}</span>'
            for label in ("Python", "Streamlit", "OpenCV", "DeepFace", "YTMusic")
        )
        + "</div>",
        unsafe_allow_html=True,
    )
    render_footer()


def record_mood(mood):
    st.session_state["mood_history"].append(
        {"mood": mood, "time": datetime.now().strftime("%H:%M")}
    )
    st.session_state["mood_history"] = st.session_state["mood_history"][-30:]


def generate_playlist(mood, lang, record=True):
    if (
        st.session_state["playlist"]
        and st.session_state["playlist_emotion"] == mood
        and st.session_state["playlist_language"] == lang
    ):
        if record:
            record_mood(mood)
        return
    st.session_state["sync_manual_mood"] = (
        st.session_state.get("manual_mood") != mood
    )
    st.session_state["current_emotion"] = mood
    st.session_state["playlist_emotion"] = mood
    st.session_state["playlist_language"] = lang
    st.session_state["current_song"] = None
    st.session_state["now_playing"] = None
    st.session_state["current_index"] = -1
    with st.spinner("Finding songs for your mood and language…"):
        st.session_state["playlist"] = get_songs(mood, lang)
    if record:
        record_mood(mood)


def refresh_selected_mood():
    generate_playlist(
        st.session_state["manual_mood"],
        st.session_state["selected_language"],
    )


def refresh_selected_language():
    generate_playlist(
        st.session_state["current_emotion"],
        st.session_state["selected_language"],
        record=False,
    )


def song_key(song):
    return song.get("videoId") or f"{song.get('title', '')}|{song.get('artist', '')}"


def play_index(index):
    songs = st.session_state["playlist"]
    if songs:
        index %= len(songs)
        play_song(songs[index]["videoId"])


def play_song(video_id):
    for index, song in enumerate(st.session_state["playlist"]):
        if song.get("videoId") == video_id:
            st.session_state["current_index"] = index
            st.session_state["current_song"] = song
            st.session_state["now_playing"] = song
            return


def render_mood_history():
    history = st.session_state["mood_history"]
    if not history:
        st.markdown(
            '<div class="empty-state">Your mood check-ins will appear here.<strong>No history yet</strong></div>',
            unsafe_allow_html=True,
        )
        return

    counts = Counter(entry["mood"] for entry in history)
    peak = max(counts.values())
    items = []
    for mood in EMOTION_ORDER:
        emotion = EMO[mood]
        count = counts.get(mood, 0)
        height = max(5, round(88 * count / peak)) if count else 5
        items.append(
            f"""
            <div class="history-item" title="{html.escape(mood)}: {count}">
                <span class="history-count">{count}</span>
                <div class="history-bar" style="height:{height}px;background:{emotion['color']};opacity:{.95 if count else .2}"></div>
                <span class="history-label">{emotion['emoji']} {html.escape(mood)}</span>
            </div>
            """
        )
    st.markdown(
        '<div class="history-chart" role="img" aria-label="Mood check-ins by emotion">'
        + "".join(items)
        + "</div>",
        unsafe_allow_html=True,
    )
    latest = history[-1]
    latest_emotion = EMO.get(latest["mood"], EMO["neutral"])
    st.caption(
        f"Latest check-in: {latest_emotion['emoji']} {latest['mood'].title()} at {latest['time']} · "
        f"{len(history)} check-in{'s' if len(history) != 1 else ''} this session"
    )


def render_favorites():
    favorites = st.session_state["favorites"]
    if not favorites:
        st.markdown(
            '<div class="empty-state">Tap the heart beside a track to keep it close.<strong>No favorites saved yet</strong></div>',
            unsafe_allow_html=True,
        )
        return
    for index, song in enumerate(list(favorites.values())):
        row, play, remove = st.columns([5, 1, 1], vertical_alignment="center")
        with row:
            st.markdown(
                f"""
                <div class="playlist-row">
                    <span class="track-info">
                        <span class="track-title">{html.escape(song.get('title', 'Unknown'))}</span><br>
                        <span class="track-artist">{html.escape(song.get('artist', 'Unknown'))}</span>
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with play:
            if st.button("▶", key=f"favorite_play_{index}", help="Play favorite"):
                playlist_index = next(
                    (
                        i
                        for i, track in enumerate(st.session_state["playlist"])
                        if song_key(track) == song_key(song)
                    ),
                    -1,
                )
                if playlist_index >= 0:
                    play_song(st.session_state["playlist"][playlist_index]["videoId"])
                else:
                    st.session_state["current_song"] = song
                    st.session_state["now_playing"] = song
                    st.session_state["current_index"] = -1
                st.rerun()
        with remove:
            if st.button("♥", key=f"favorite_remove_{index}", help="Remove favorite"):
                st.session_state["favorites"].pop(song_key(song), None)
                st.rerun()


def render_player():
    render_nav()
    if st.session_state.pop("sync_manual_mood", False):
        st.session_state["manual_mood"] = st.session_state["current_emotion"]
    mood = st.session_state.get("current_emotion", "neutral")
    st.markdown(f'<div class="app-shell" data-mood="{mood}">', unsafe_allow_html=True)
    section_heading(
        "Your listening room",
        "Find the feeling. Find the music.",
        "Scan your mood or choose one yourself, then explore a playlist made for right now.",
    )
    left, right = st.columns([1.1, .9], gap="large")
    with left:
        with st.container(border=True):
            st.markdown('<div class="player-title">Mood check-in</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="player-subtitle">Camera detection is optional; choose a mood below whenever you like.</div>',
                unsafe_allow_html=True,
            )
            selected_mood = st.selectbox(
                "Choose a mood",
                options=list(EMO),
                index=list(EMO).index(st.session_state["current_emotion"]),
                format_func=lambda mood: f"{EMO[mood]['emoji']}  {mood.title()}",
                key="manual_mood",
                on_change=refresh_selected_mood,
            )
            selected_language = st.selectbox(
                "Song language",
                options=("English", "Hindi", "Spanish", "French", "German", "Portuguese", "Japanese", "Korean"),
                key="selected_language",
                on_change=refresh_selected_language,
            )
            scan_col, choose_col = st.columns(2)
            with scan_col:
                detect_clicked = st.button(
                    "📷  Detect my mood", type="primary", use_container_width=True
                )
            with choose_col:
                choose_clicked = st.button(
                    "♫  Use selected mood", use_container_width=True
                )
            camera_area = st.empty()
            if detect_clicked:
                with st.spinner("Warming up the emotion model…"):
                    preload_model()
                emotion, error = detect_mood_live(camera_area, duration=5)
                camera_area.empty()
                if error:
                    st.error(error)
                else:
                    generate_playlist(emotion, selected_language)
            elif choose_clicked:
                generate_playlist(selected_mood, selected_language)
            elif st.session_state["playlist_language"] is None:
                generate_playlist(
                    st.session_state["current_emotion"],
                    selected_language,
                    record=False,
                )

        with st.container(border=True):
            st.markdown('<div class="player-title">Mood history</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="player-subtitle">A private snapshot of your check-ins for this session.</div>',
                unsafe_allow_html=True,
            )
            render_mood_history()
            if st.session_state["mood_history"]:
                if st.button("Clear session history", key="clear_history"):
                    st.session_state["mood_history"] = []
                    st.rerun()

    with right:
        now_playing = st.session_state["current_song"]
        if now_playing:
            with st.container(border=True):
                st.markdown('<div class="player-title">Now playing</div>', unsafe_allow_html=True)
                st.markdown(
                    f'<div class="player-subtitle">{html.escape(now_playing.get("title", "Unknown"))} · {html.escape(now_playing.get("artist", "Unknown"))}</div>',
                    unsafe_allow_html=True,
                )
                st.components.v1.html(
                    player_html(now_playing, st.session_state["playlist"]),
                    height=95,
                    scrolling=False,
                )
                current_index = st.session_state["current_index"]
                songs = st.session_state["playlist"]
                previous_col, shuffle_col, next_col, stop_col = st.columns(4)
                with previous_col:
                    if st.button("⏮", key="previous", help="Previous track", use_container_width=True):
                        if songs:
                            play_index((current_index - 1) % len(songs))
                        st.rerun()
                with shuffle_col:
                    if st.button("🔀", key="shuffle", help="Shuffle playlist", use_container_width=True):
                        if songs:
                            choices = [i for i in range(len(songs)) if i != current_index]
                            play_index(random.choice(choices) if choices else current_index)
                        st.rerun()
                with next_col:
                    if st.button("⏭", key="next", help="Next track", use_container_width=True):
                        if songs:
                            play_index((current_index + 1) % len(songs))
                        st.rerun()
                with stop_col:
                    if st.button("⏹", key="stop", help="Stop playback", use_container_width=True):
                        st.session_state["current_song"] = None
                        st.session_state["now_playing"] = None
                        st.session_state["current_index"] = -1
                        st.rerun()
        else:
            with st.container(border=True):
                st.markdown(
                    """
                    <div class="empty-state">
                        <div style="font-size:2rem">🎧</div>
                        <strong>Ready when you are</strong>
                        Your next soundtrack is just a mood away.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        with st.container(border=True):
            if st.session_state["playlist"]:
                mood = st.session_state["playlist_emotion"]
                emotion = EMO.get(mood, EMO["neutral"])
                st.markdown(
                    f'<div class="player-title">{emotion["emoji"]} {html.escape(mood.title())} mix</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div class="player-subtitle">{len(st.session_state["playlist"])} tracks picked for this mood</div>',
                    unsafe_allow_html=True,
                )
                for index, song in enumerate(st.session_state["playlist"]):
                    video_id = song["videoId"]
                    active = (
                        now_playing is not None
                        and now_playing.get("videoId") == video_id
                    )
                    favorite = song_key(song) in st.session_state["favorites"]
                    row, play, favorite_button = st.columns(
                        [5, 1, 1], vertical_alignment="center"
                    )
                    with row:
                        st.markdown(
                            f"""
                            <div class="playlist-row">
                                <span class="track-number">{'♫' if active else index + 1}</span>
                                <span class="track-info">
                                    <span class="track-title">{html.escape(song.get('title', 'Unknown'))}</span><br>
                                    <span class="track-artist">{html.escape(song.get('artist', 'Unknown'))}</span>
                                </span>
                                <span class="track-duration">{html.escape(song.get('duration', ''))}</span>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    with play:
                        if st.button(
                            "♫" if active else "▶",
                            key=f"play_{video_id}",
                            help="Play track",
                        ):
                            play_song(video_id)
                            st.rerun()
                    with favorite_button:
                        if st.button(
                            "♥" if favorite else "♡",
                            key=f"playlist_favorite_{index}",
                            help="Remove favorite" if favorite else "Save favorite",
                        ):
                            key = song_key(song)
                            if favorite:
                                st.session_state["favorites"].pop(key, None)
                            else:
                                st.session_state["favorites"][key] = song
                            st.rerun()
            else:
                st.markdown(
                    '<div class="empty-state"><strong>Your playlist will appear here</strong>Scan your mood or choose one to get started.</div>',
                    unsafe_allow_html=True,
                )

        with st.expander(f"♥  Favorites ({len(st.session_state['favorites'])})"):
            render_favorites()

    render_footer()
    st.markdown("</div>", unsafe_allow_html=True)


initialize_state()
inject_styles()
HOME_PAGE = st.Page(
    home_page,
    title="Home",
    icon="🏠",
    default=True,
)
PLAYER_PAGE = st.Page(
    render_player,
    title="Player",
    icon="🎧",
    url_path="player",
)
current_page = st.navigation(
    {"Moodwave": [HOME_PAGE, PLAYER_PAGE]},
    position="hidden",
)
current_page.run()
