# ============================
# music_tool.py
# KhinsGPT Music Tools (YouTube + VLC)
# ============================

import logging
from typing import Optional
from livekit.agents import function_tool, RunContext
from ytmusicapi import YTMusic
import yt_dlp
import vlc

# ✅ Initialize YTMusic
ytmusic = YTMusic()

# 🎵 VLC Player instance
player: Optional[vlc.MediaPlayer] = None
last_song = {"title": None, "url": None}


async def _get_stream_url(song: str) -> Optional[str]:
    """Search song on YouTube Music and get a direct audio stream URL."""
    try:
        results = ytmusic.search(song, filter="songs")
        if not results:
            return None

        video_id = results[0]["videoId"]
        url = f"https://www.youtube.com/watch?v={video_id}"

        # Extract audio stream using yt-dlp
        ydl_opts = {"format": "bestaudio/best", "quiet": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info["url"]
    except Exception as e:
        logging.error(f"Error fetching stream URL: {e}")
        return None


# -------------------------
# Play Music
# -------------------------
@function_tool()
async def play_music(ctx: RunContext, song: str, platform: Optional[str] = "ytmusic") -> str:
    """Play a song with real playback control."""
    global player, last_song

    stream_url = await _get_stream_url(song)
    if not stream_url:
        return f"Sorry, couldn’t find '{song}'."

    # Stop previous playback if active
    if player:
        player.stop()

    # Start new playback
    instance = vlc.Instance()
    player = instance.media_player_new()
    media = instance.media_new(stream_url)
    player.set_media(media)
    player.play()

    last_song = {"title": song, "url": stream_url}

    return f"▶️ Now playing: {song}"


# -------------------------
# Pause Music
# -------------------------
@function_tool()
async def pause_music(ctx: RunContext) -> str:
    """Pause playback."""
    global player
    if player and player.is_playing():
        player.pause()
        return "⏸️ Music paused."
    return "No music is currently playing."


# -------------------------
# Resume Music
# -------------------------
@function_tool()
async def resume_music(ctx: RunContext) -> str:
    """Resume playback."""
    global player
    if player:
        player.play()
        return "▶️ Resumed music."
    return "No song to resume."


# -------------------------
# Stop Music
# -------------------------
@function_tool()
async def stop_music(ctx: RunContext) -> str:
    """Stop playback completely."""
    global player, last_song
    if player:
        player.stop()
        player = None
        last_song = {"title": None, "url": None}
        return "⏹️ Music stopped."
    return "No music is currently playing."


# -------------------------
# Volume Control
# -------------------------
@function_tool()
async def set_volume(ctx: RunContext, level: int) -> str:
    """Set volume (0–100)."""
    global player
    if not player:
        return "No music is playing to adjust volume."
    if level < 0 or level > 100:
        return "Volume level must be between 0 and 100."
    player.audio_set_volume(level)
    return f"🔊 Volume set to {level}%"
