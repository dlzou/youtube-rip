import youtube_dl as dl
import sqlite3
import re
import sys
from os import path
from traceback import print_exc

CURRENT_DIR = path.dirname(path.abspath(__file__))
MUSIC_DIR = path.expanduser('~/Music/YouTube')
EXT = 'm4a'
ARCHIVE_DB = path.join(CURRENT_DIR, 'archive.sqlite')

OPTIONS = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': EXT,
        'preferredquality': '192'
    }],
    'hls_prefer_native': True,
    'nooverwrites': True,
    'outtmpl': path.join(MUSIC_DIR, '%(title)s.%(ext)s'),
    'quiet': True,
    'forcefilename': True,
    'forceduration': True
}


def download_single(video_id):
    conn = sqlite3.connect(ARCHIVE_DB)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS Archive(video_id UNIQUE, filepath)')
    c.execute('SELECT filepath FROM archive WHERE video_id=?', (video_id,))
    filepath = c.fetchone()[0]

    if filepath is None or not path.exists(filepath):
        try:
            with dl.YoutubeDL(OPTIONS) as ydl:
                ydl.download([video_id])
                title = ydl.extract_info(video_id, download=False).get('title', None)
                if filepath is None and title is not None:
                    filepath = path.join(MUSIC_DIR, f'{title}.{EXT}')
                    c.execute('INSERT INTO Archive VALUES(?, ?)', (video_id, filepath))
        except Exception:
            print_exc()
    else:
        print(f'Already downloaded at {filepath}')

    conn.commit()
    conn.close()


def parse_url(url):
    if re.match(r'https:\/\/www.youtube.com|youtu.be', url) is None:
        raise ValueError('invalid URL')
        return None

    tokens = re.split(r'[/]+|\?', url)[-2:]
    id_tokens = tokens[-1].split('&')
    id_dict = {}
    for token in id_tokens:
        pair = token.split('=')
        id_dict[pair[0]] = pair[1]

    parsed = {
        'type': tokens[-2],
        'id': id_dict
    }
    return parsed


if __name__ == "__main__":
    url = 'https://www.youtube.com/watch?v=kl4_Z7_0rmA'
    parsed = parse_url(url)
    if parsed is not None:
        video_id = parsed['id']['v']
    download_single(video_id)
