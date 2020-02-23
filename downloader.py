import youtube_dl as dl
import sqlite3
import re
import sys
from os import path
from traceback import print_stack

CURRENT_DIR = path.dirname(path.abspath(__file__))
DOWNLOAD_DIR = path.expanduser('~/Music/YouTube')
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
    'outtmpl': path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
    'quiet': True,
    'forcefilename': True
}


def download_single(video_id):
    conn = sqlite3.connect(ARCHIVE_DB)
    c = conn.cursor()
    c.execute('SELECT filepath FROM archive WHERE video_id=?', (video_id,))
    filepath = c.fetchone()

    if not filepath:
        try:
            with dl.YoutubeDL(OPTIONS) as ydl:
                print(f'Downloading <{video_id}>...')
                info_dict = ydl.extract_info(video_id, download=True)
                title = info_dict.get('title', None)
                if title is not None:
                    filepath = path.join(DOWNLOAD_DIR, f'{title}.{EXT}')
                    c.execute('INSERT INTO archive VALUES(?, ?)', (video_id, filepath))
        except Exception:
            print_stack()
    else:
        print(f'Already downloaded at {filepath[0]}')

    conn.commit()
    conn.close()


def download_playlist(list_id):
    try:
        with dl.YoutubeDL({'quiet': True}) as ydl:
            print(f'Extracting playlist <{list_id}>...')
            info_dict = ydl.extract_info(list_id, download=False)

            video_ids = [entry.get('id', None) for entry in info_dict.get('entries', None)]
            for video_id in video_ids:
                download_single(video_id)

    except Exception:
        print_stack()


def refresh_archive():
    conn = sqlite3.connect(ARCHIVE_DB)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS archive(video_id UNIQUE, filepath)')
    c.execute('SELECT filepath FROM archive')
    filepaths = c.fetchall()

    if filepaths:
        for f in filepaths:
            if not path.exists(f[0]):
                c.execute('DELETE FROM archive WHERE filepath=?', (f[0],))
    conn.commit()
    conn.close()


def parse_url(url):
    yt_regex = r'(https?://)?(www\.)?youtube\.com/(watch|playlist)\?([-\w&=]+)'
    if re.match(yt_regex, url) is None:
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
        'info': id_dict
    }
    return parsed


if __name__ == "__main__":
    refresh_archive()

    url = sys.argv[1]
    parsed = parse_url(url)
    if parsed is not None:
        if parsed['type'] == 'watch':
            video_id = parsed['info']['v']
            download_single(video_id)
        elif parsed['type'] == 'playlist':
            list_id = parsed['info']['list']
            download_playlist(list_id)
        else:
            print('URL not recognized, should contain \'watch\' or \'playlist\'')
