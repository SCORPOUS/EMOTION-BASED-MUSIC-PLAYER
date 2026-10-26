import streamlit as st
import html as html_lib

from detection import EMO, detect_mood_live, preload_model
from music import get_songs, player_html

st.set_page_config(
    page_title="EmotionBasedMusicPlayer",
    page_icon="🎵",
    layout="centered",
    initial_sidebar_state="collapsed",
)
preload_model()

#CSS
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
*{font-family:'Inter',sans-serif!important;box-sizing:border-box}

/* ── Page ── */
.stApp{background:#000!important}
[data-testid="stSidebar"],
[data-testid="collapsedControl"],
#MainMenu,footer,header,.stDeployButton{display:none!important;visibility:hidden!important}

/* ── Card ── */
div.block-container{
    max-width:min(420px,calc(100% - 1.5rem))!important;
    background:#121212;border-radius:18px;
    padding:0 0 0.6rem 0!important;
    margin:1.2rem auto!important;
    box-shadow:0 12px 48px rgba(0,0,0,0.65);
    overflow:hidden;
}

/* ── Spacing ── */
div[data-testid="stVerticalBlock"]{gap:0!important}

/* ── Video image ── */
div[data-testid="stImage"]{margin:0!important;padding:0!important}
div[data-testid="stImage"] img{border-radius:0!important;width:100%}

/* ── Emotion line ── */
.emo-row{
    display:flex;align-items:center;justify-content:center;gap:10px;
    padding:0.9rem 1.2rem 0.5rem;
}
.emo-row .e{font-size:1.3rem}
.emo-row .l{font-size:0.92rem;font-weight:600;text-transform:capitalize}

/* ── Primary buttons (green pill) ── */
div[data-testid="stButton"] button[kind="primary"]{
    background:#1DB954!important;color:#000!important;
    border:none!important;border-radius:24px!important;
    font-weight:600!important;font-size:0.8rem!important;
    padding:0.45rem 1.4rem!important;transition:all 0.15s!important;
}
div[data-testid="stButton"] button[kind="primary"]:hover{
    background:#1ed760!important;transform:scale(1.04)!important;
}

/* ── Secondary buttons ── */
div[data-testid="stButton"] button[kind="secondary"]{
    background:rgba(255,255,255,0.06)!important;
    border:1px solid rgba(255,255,255,0.15)!important;
    color:#b3b3b3!important;font-size:0.78rem!important;
    padding:0.3rem 0.8rem!important;min-height:0!important;
    border-radius:20px!important;transition:all 0.15s!important;
    line-height:1!important;
}
div[data-testid="stButton"] button[kind="secondary"]:hover{
    color:#fff!important;border-color:rgba(255,255,255,0.3)!important;
    background:rgba(255,255,255,0.1)!important;
}
div[data-testid="stButton"] button:disabled{
    opacity:1!important;color:#1DB954!important;
    border-color:#1DB954!important;
}

/* ── Section label ── */
.slbl{
    color:#b3b3b3;font-size:0.68rem;font-weight:700;
    text-transform:uppercase;letter-spacing:1px;
    padding:0.7rem 1.2rem 0.35rem;
}

/* ── Track row ── */
.tk{
    display:flex;align-items:center;gap:10px;
    padding:7px 1.2rem;transition:background 0.12s;
}
.tk:hover{background:rgba(255,255,255,0.04)}
.tk.on{background:rgba(29,185,84,0.07)}
.tk .n{color:#b3b3b3;font-size:0.75rem;width:16px;text-align:right;flex-shrink:0}
.tk .n.g{color:#1DB954}
.tk .i{flex:1;min-width:0}
.tk .t{color:#fff;font-size:0.84rem;font-weight:500;
    white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tk .t.g{color:#1DB954}
.tk .a{color:#727272;font-size:0.7rem;margin-top:1px;
    white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tk .d{color:#727272;font-size:0.7rem;flex-shrink:0}

/* ── Divider ── */
.dv{height:1px;background:rgba(255,255,255,0.05);margin:0.3rem 1.2rem}

/* ── Now playing label ── */
.npl{color:#1DB954;font-size:0.66rem;font-weight:700;text-transform:uppercase;
     letter-spacing:1.2px;padding:0.5rem 1.2rem 0.2rem}

/* ── Empty state ── */
.emp{text-align:center;padding:2rem 1.5rem;color:#535353}
.emp .ic{font-size:2.2rem;margin-bottom:0.4rem}
.emp .tt{color:#b3b3b3;font-size:0.92rem;font-weight:500}
.emp .dd{font-size:0.78rem;margin-top:0.2rem;line-height:1.5}

/* ── Column spacing ── */
div[data-testid="stHorizontalBlock"]{gap:0!important;padding:0!important}
div[data-testid="column"]{padding:0!important}
div[data-testid="column"] div[data-testid="stVerticalBlock"]{
    justify-content:center;align-items:center;
}

/* ── Stop button (red accent) ── */
.stop-wrap div[data-testid="stButton"] button{
    background:rgba(255,80,80,0.12)!important;
    border:1px solid rgba(255,80,80,0.3)!important;
    color:#ff5050!important;border-radius:20px!important;
    font-size:0.76rem!important;font-weight:600!important;
    padding:0.35rem 1.2rem!important;
}
.stop-wrap div[data-testid="stButton"] button:hover{
    background:rgba(255,80,80,0.22)!important;
    border-color:rgba(255,80,80,0.5)!important;
}
</style>""", unsafe_allow_html=True)

for k, v in {"pl": [], "pe": None, "np": None, "ni": -1, "cur": "neutral"}.items():
    if k not in st.session_state:
        st.session_state[k] = v

cur = st.session_state["cur"]
ec = EMO.get(cur, EMO["neutral"])

st.markdown(f"""
<div class="emo-row">
    <span class="e">{ec['emoji']}</span>
    <span class="l" style="color:{ec['color']}">{cur}</span>
</div>""", unsafe_allow_html=True)

_, btn_col, _ = st.columns([1, 2, 1])
with btn_col:
    detect_clicked = st.button("Detect Mood", type="primary",
                               use_container_width=True)

video_area = st.empty()

if detect_clicked:
    emotion, error = detect_mood_live(video_area, duration=5)
    video_area.empty()

    if error:
        st.error(error)
    else:
        st.session_state["cur"] = emotion
        st.session_state["pe"] = emotion
        with st.spinner("Generating playlist…"):
            st.session_state["pl"] = get_songs(emotion)
        st.session_state["np"] = None
        st.session_state["ni"] = -1
        st.rerun()

st.markdown('<div class="dv"></div>', unsafe_allow_html=True)

if st.session_state["np"]:
    st.markdown('<div class="npl">♫ now playing</div>', unsafe_allow_html=True)
    st.components.v1.html(
        player_html(st.session_state["np"]),
        height=82,
        scrolling=False,
    )
    st.markdown('<div class="stop-wrap">', unsafe_allow_html=True)
    _, sc, _ = st.columns([1, 2, 1])
    with sc:
        if st.button("⏹  Stop", key="stop_btn", use_container_width=True):
            st.session_state["np"] = None
            st.session_state["ni"] = -1
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="dv"></div>', unsafe_allow_html=True)



# UI — PLAYLIST
songs = st.session_state["pl"]

if songs:
    pe = st.session_state["pe"]
    pc = EMO.get(pe, EMO["neutral"])
    st.markdown(
        f'<div class="slbl">{pc["emoji"]}  {pe} · {len(songs)} songs</div>',
        unsafe_allow_html=True,
    )

    for i, s in enumerate(songs):
        active = st.session_state["ni"] == i
        rc  = "tk on" if active else "tk"
        nc  = "n g"   if active else "n"
        tc  = "t g"   if active else "t"
        idx = "♫"     if active else str(i + 1)
        st_ = html_lib.escape(s["title"])
        sa  = html_lib.escape(s["artist"])

        left, right = st.columns([13, 1])
        with left:
            st.markdown(f"""<div class="{rc}">
                <span class="{nc}">{idx}</span>
                <div class="i"><div class="{tc}">{st_}</div>
                <div class="a">{sa}</div></div>
                <span class="d">{s['duration']}</span>
            </div>""", unsafe_allow_html=True)
        with right:
            if st.button(
                "▶" if not active else "♫",
                key=f"p{i}",
                disabled=active,
            ):
                st.session_state["np"] = s
                st.session_state["ni"] = i
                st.rerun()
else:
    st.markdown("""
    <div class="emp">
        <div class="ic">🎧</div>
        <div class="tt">Ready to read your mood</div>
        <div class="dd">Tap <b>Detect Mood</b> — the camera will scan<br>
        your face and build a playlist automatically</div>
    </div>""", unsafe_allow_html=True)
