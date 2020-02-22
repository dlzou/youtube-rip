import youtube_dl
import sqlite3
import os

OPTIONS = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
MP3_DIR = os.path.join(CURRENT_DIR, 'mp3')
