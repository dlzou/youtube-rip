import youtube_dl as dl
import sqlite3
import re
import argparse
from os import path
from traceback import print_exc

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
                print(f'Downloading video <{video_id}>...')
                info_dict = ydl.extract_info(video_id, download=True)
                title = info_dict.get('title', None)
                duration = info_dict.get('duration', None)

                if title is not None and duration is not None:
                    filepath = path.join(DOWNLOAD_DIR, f'{title}.{EXT}')
                    c.execute('INSERT INTO archive VALUES(?, ?, ?)', (video_id, filepath, duration))

        except Exception:
            print_exc()
    else:
        print(f'Already downloaded {filepath[0]}')

    conn.commit()
    conn.close()


def download_playlist(list_url, list_id):
    try:
        with dl.YoutubeDL({'quiet': True}) as ydl:
            # Breaking the api for speed
            print(f'Extracting video IDs from playlist <{list_id}>...')
            extractor = ydl.get_info_extractor('YoutubePlaylist')
            page = extractor._download_webpage(list_url, list_id)
            video_ids = [id for id, titles in extractor.extract_videos_from_page(page)]

            # Slow because a lot of extra info downloaded
            # info_dict = ydl.extract_info(list_id, download=False)
            # video_ids = [entry.get('id', None) for entry in info_dict.get('entries', None)]

            for video_id in video_ids:
                download_single(video_id)

    except Exception:
        print_exc()


def refresh_archive():
    conn = sqlite3.connect(ARCHIVE_DB)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS archive(video_id UNIQUE, filepath, duration)')
    c.execute('SELECT filepath FROM archive')
    filepaths = c.fetchall()

    if filepaths:
        for f in filepaths:
            if not path.exists(f[0]):
                c.execute('DELETE FROM archive WHERE filepath=?', (f[0],))
    conn.commit()
    conn.close()


def archive_info():
    conn = sqlite3.connect(ARCHIVE_DB)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM archive')
    num_files = c.fetchone()[0]
    c.execute('SELECT SUM(duration) FROM archive')
    total_duration = seconds_to_hours(c.fetchone()[0])
    conn.commit()
    conn.close()

    info = {
        'num_files': num_files,
        'total_duration': total_duration
    }
    return info


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


def seconds_to_hours(seconds):
    hours = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    return f'{hours}:{minutes}:{seconds}'


if __name__ == "__main__":
    refresh_archive()

    # Positional args must be before optional args
    parser = argparse.ArgumentParser()
    parser.add_argument('url', nargs='?', help='video or playlist url')
    parser.add_argument('-i', '--info', action='store_true', help='information about archive')
    args = parser.parse_args()

    if args.url:
        parsed = parse_url(args.url)
        if parsed is not None:
            if parsed['type'] == 'watch':
                video_id = parsed['info']['v']
                download_single(video_id)

            elif parsed['type'] == 'playlist':
                list_id = parsed['info']['list']
                download_playlist(args.url, list_id)

            else:
                print('URL not recognized, should contain \'watch\' or \'playlist\'')

    elif args.info:
        info = archive_info()
        print('Number of files: ' + str(info.get('num_files', None)))
        print('Total duration: ' + info.get('total_duration', None))

    else:
        print('No arguments specified, use --help')
