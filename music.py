import json
import logging
import streamlit as st
from ytmusicapi import YTMusic
import html as html_lib
import random
import re
from mood_queries import build_mood_queries


logger = logging.getLogger(__name__)


@st.cache_resource
def _yt():
    """Cached YTMusic client instance."""
    return YTMusic()


def _song_from_result(result):
    video_id = result.get("videoId")
    if not video_id:
        return None
    artists = result.get("artists") or []
    thumbnails = result.get("thumbnails") or []
    return {
        "title": result.get("title") or "Unknown",
        "artist": ", ".join(artist["name"] for artist in artists if artist.get("name")) or "Unknown",
        "duration": result.get("duration") or "",
        "videoId": video_id,
        "thumb": thumbnails[-1].get("url", "") if thumbnails else "",
    }


def get_songs(emotion, lang):
    """Search mood playlists and songs in the selected language."""
    yt = _yt()
    queries = build_mood_queries(emotion, lang)
    songs = []
    seen_video_ids = set()

    def add_results(results):
        for result in results:
            song = _song_from_result(result)
            if song and song["videoId"] not in seen_video_ids:
                seen_video_ids.add(song["videoId"])
                songs.append(song)

    failures = []
    try:
        playlists = yt.search(queries[0], filter="playlists", limit=10)
    except Exception as exc:
        logger.exception("YTMusic playlist search failed for %s/%s.", emotion, lang)
        failures.append(exc)
        playlists = []

    for playlist in playlists[:2]:
        playlist_id = playlist.get("browseId") or playlist.get("playlistId")
        if not playlist_id:
            continue
        try:
            playlist_data = yt.get_playlist(playlist_id, limit=50)
        except Exception as exc:
            logger.exception("YTMusic playlist load failed for %s.", playlist_id)
            failures.append(exc)
            continue
        add_results(playlist_data.get("tracks") or [])

    for query in queries:
        try:
            add_results(yt.search(query, filter="songs", limit=25))
        except Exception as exc:
            logger.exception("YTMusic song search failed for %s/%s.", emotion, lang)
            failures.append(exc)

    if not songs and failures:
        st.error("Could not load music suggestions. Check your connection and try again.")
        return []

    random.shuffle(songs)
    return songs[:12]


def player_html(song, playlist):
    """Build a custom audio-only player using YouTube IFrame API."""
    vid = song["videoId"]
    t = html_lib.escape(song["title"])
    a = html_lib.escape(song["artist"])
    th = html_lib.escape(song["thumb"], quote=True)
    queue = [
        {
            "videoId": track["videoId"],
            "title": track.get("title", "Unknown"),
            "artist": track.get("artist", "Unknown"),
            "thumb": track.get("thumb", ""),
        }
        for track in playlist
        if re.fullmatch(r"[A-Za-z0-9_-]{11}", track.get("videoId", ""))
    ]
    queue_json = json.dumps(queue).replace("<", "\\u003c")
    return """<!DOCTYPE html><html><head>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#121212;font-family:'Inter',sans-serif;overflow:hidden}
.w{padding:4px 0}
.r{display:flex;align-items:center;gap:11px}
.r img{width:42px;height:42px;border-radius:5px;object-fit:cover}
.r .i{flex:1;min-width:0}
.r .t{color:#fff;font-size:0.78rem;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.r .a{color:#b3b3b3;font-size:0.66rem;margin-top:1px}
.b{background:rgba(255,255,255,0.1);border:none;color:#fff;
   width:30px;height:30px;border-radius:50%;font-size:0.85rem;cursor:pointer;
   display:flex;align-items:center;justify-content:center;transition:all 0.12s}
.b:hover{transform:scale(1.1);background:rgba(255,255,255,0.2)}
.pr{display:flex;align-items:center;gap:6px;margin-top:6px}
.bar{flex:1;height:3px;background:rgba(255,255,255,0.08);border-radius:2px;cursor:pointer;overflow:hidden}
.fl{height:100%;background:#1DB954;width:0%;transition:width 0.3s linear}
.tm{color:#727272;font-size:0.58rem;min-width:24px}
#yt{position:absolute;left:-9999px}
</style></head><body>
<div class="w">
<div class="r">
<img src="__TH__" alt="">
<div class="i"><div class="t">__T__</div><div class="a">__A__</div></div>
<button class="b" id="pp" onclick="tog()">▶</button>
</div>
<div class="pr">
<span class="tm" id="ct">0:00</span>
<div class="bar" id="br" onclick="sk(event)"><div class="fl" id="fl"></div></div>
<span class="tm" id="dt">0:00</span>
</div>
</div>
<div id="yt"><div id="yp-__V__"></div></div>
<script>
var tag=document.createElement("script");tag.src="https://www.youtube.com/iframe_api";document.head.appendChild(tag);
var p,ok=0,tracks=__QUEUE__,current=tracks.findIndex(function(track){return track.videoId==="__V__"});
function onYouTubeIframeAPIReady(){p=new YT.Player("yp-__V__",{height:"1",width:"1",videoId:"__V__",playerVars:{autoplay:1,controls:0},events:{onReady:function(e){ok=1;e.target.playVideo();ub(1)},onStateChange:function(e){ub(e.data==YT.PlayerState.PLAYING);if(e.data==YT.PlayerState.ENDED)nextTrack()}}})}
function ub(v){document.getElementById("pp").textContent=v?"⏸":"▶"}
function tog(){if(!ok)return;p.getPlayerState()==YT.PlayerState.PLAYING?p.pauseVideo():p.playVideo()}
function nextTrack(){if(!ok||tracks.length<2)return;current=(current+1)%tracks.length;var track=tracks[current];document.querySelector(".r img").src=track.thumb;document.querySelector(".r .t").textContent=track.title;document.querySelector(".r .a").textContent=track.artist;p.loadVideoById(track.videoId)}
function sk(e){if(!ok)return;var b=document.getElementById("br"),r=(e.clientX-b.getBoundingClientRect().left)/b.offsetWidth;p.seekTo(p.getDuration()*Math.max(0,Math.min(1,r)),!0)}
function f(s){var m=Math.floor(s/60),c=Math.floor(s%60);return m+":"+(c<10?"0":"")+c}
setInterval(function(){if(!ok||!p.getDuration)return;var c=p.getCurrentTime(),d=p.getDuration();if(d>0){document.getElementById("fl").style.width=c/d*100+"%";document.getElementById("ct").textContent=f(c);document.getElementById("dt").textContent=f(d)}},500);
</script></body></html>""".replace("__QUEUE__", queue_json).replace("__V__", vid).replace("__T__", t).replace("__A__", a).replace("__TH__", th)
