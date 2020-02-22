import youtube_dl as dl
import sqlite3
import sys
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
M4A_DIR = os.path.join(CURRENT_DIR, 'm4a')

OPTIONS = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'm4a',
        'preferredquality': '192'
    }],
    'hls_prefer_native': True,
    'outtmpl': os.path.join(M4A_DIR, '%(title)s.%(ext)s'),
    'forcetitle': True,
    'forcefilename': True
}

def download(yt_url):
    with dl.YoutubeDL(OPTIONS) as ydl:
        ydl.download([yt_url])

if __name__ == "__main__":
    download('https://www.youtube.com/watch?v=kl4_Z7_0rmA')