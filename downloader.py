import youtube_dl as dl
import multiprocessing as mp
import sqlite3
import argparse
import re
import sys
from os import path
from traceback import print_exc

CURRENT_DIR = path.dirname(path.abspath(__file__))
ARCHIVE_DB = path.join(CURRENT_DIR, 'archive.sqlite')
DEFAULT_LOCATION = path.expanduser('~/Music/YouTube')
DEFAULT_EXT = 'm4a'
VALID_EXT = ('m4a', 'mp3', 'aac', 'wav', 'opus', 'vorbis', 'best')


class Options:
    """Contains options passed by user"""

    def __init__(self, extension, location):
        self.extension = extension
        self.location = location

    def dl(self):
        opt = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': extension,
                'preferredquality': '192'
            }],
            'outtmpl': path.join(location, f'%(title)s.{extension}'),
            'quiet': True,
            'forcefilename': True
        }
        return opt


def download_single(video_id, options):
    """Download a single file and write to archive"""

    conn = sqlite3.connect(ARCHIVE_DB)
    c = conn.cursor()
    c.execute('SELECT filepath FROM archive WHERE video_id=?', (video_id,))
    filepath = c.fetchone()

    if not filepath:
        try:
            print(f'Downloading video <{video_id}>...')
            ydl = dl.YoutubeDL(options.dl())
            info_dict = ydl.extract_info(video_id, download=True)
            title = info_dict.get('title', None)
            duration = info_dict.get('duration', None)

            if title is not None and duration is not None:
                filepath = path.join(options.location, f'{title}.{options.extension}')
                c.execute('INSERT INTO archive VALUES(?, ?, ?)', (video_id, filepath, duration))

        except Exception:
            print_exc()
    else:
        print(f'Already downloaded {filepath[0]}')

    conn.commit()
    conn.close()


def download_playlist(list_url, list_id, options):
    """Download multiple files from a playlist, single process execution"""

    try:
        print(f'Extracting video IDs from playlist <{list_id}>...')
        ydl = dl.YoutubeDL({'quiet': True})

        # Slower because a lot of extra info downloaded
        info_dict = ydl.extract_info(list_id, download=False)
        video_ids = [entry.get('id', None) for entry in info_dict.get('entries', None)]

        # Breaking the api for speed, limit of 35 videos
        # extractor = ydl.get_info_extractor('YoutubePlaylist')
        # page = extractor._download_webpage(list_url, list_id)
        # video_ids = [id for id, titles in extractor.extract_videos_from_page(page)]

        for video_id in video_ids:
            download_single(video_id, options)

    except Exception:
        print_exc()


def _download(video_id, options):
    """Single process to download a file, used in multiprocessing"""

    try:
        ydl = dl.YoutubeDL(options.dl())
        print(f'Downloading video <{video_id}>...')
        info_dict = ydl.extract_info(video_id, download=True)
        title = info_dict.get('title', None)
        duration = info_dict.get('duration', None)
        info = {
            'title': title,
            'duration': duration
        }
        return info

    except Exception:
        print_exc()


def download_playlist_mp(list_url, list_id, options):
    """Download multiple files from a playlist, single process execution"""

    try:
        ydl = dl.YoutubeDL({'quiet': True})
        print(f'Extracting video IDs from playlist <{list_id}>...')

        info_dict = ydl.extract_info(list_id, download=False)
        video_ids = [entry.get('id', None) for entry in info_dict.get('entries', None)]
        filter_existing(video_ids)

        # multiprocessing


    except Exception:
        print_exc()


def filter_existing(video_ids):
    conn = sqlite3.connect(ARCHIVE_DB)
    c = conn.cursor()
    i = 0

    while i < len(video_ids):
        filepath = c.execute('SELECT filepath FROM archive WHERE video_id=?', (video_ids[i],))
        if not filepath:
            i += 1
        else:
            print(f'Already downloaded {filepath[0]}')
            video_ids.pop(i)

    conn.commit()
    conn.close()


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
    print('Refreshed archive')


def archive_info():
    conn = sqlite3.connect(ARCHIVE_DB)
    c = conn.cursor()
    c.execute('SELECT filepath FROM archive')
    filepaths = c.fetchall()
    c.execute('SELECT SUM(duration) FROM archive')
    total_duration = c.fetchone()[0]
    conn.commit()
    conn.close()

    size = 0
    for f in filepaths:
        size += path.getsize(f[0])
    size = int((size / (1000 ** 2)) * 100) / 100

    info = {
        'num_files': len(filepaths),
        'total_size': size,
        'total_duration': total_duration
    }
    return info


def parse_url(url):
    yt_regex = r'(https?://)?(www\.)?youtube\.com/(watch|playlist)\?([-\w=]+)(&[-\w=]+)*'
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

    parser = argparse.ArgumentParser()
    parser.add_argument('url', nargs='?', help='video or playlist url')
    parser.add_argument('-f', '--format', nargs=1, help='file download format')
    parser.add_argument('-l', '--location', nargs=1, help='download location in filesystem')
    parser.add_argument('-i', '--info', action='store_true', help='information about archive')
    args = parser.parse_args()

    if args.url:
        if not args.format:
            extension = DEFAULT_EXT
        else:
            extension = args.format[0]
        if extension not in VALID_EXT:
            print(f'Not a valid format {VALID_EXT}')
            sys.exit(0)

        if not args.location:
            location = DEFAULT_LOCATION
        else:
            location = args.location[0]
        if not path.isdir(location):
            print('Not a valid directory')
            sys.exit(0)
        options = Options(extension, location)

        parsed = parse_url(args.url)
        if parsed is not None:
            if parsed['type'] == 'watch':
                video_id = parsed['info']['v']
                download_single(video_id, options)

            elif parsed['type'] == 'playlist':
                list_id = parsed['info']['list']
                download_playlist(args.url, list_id, options)

            else:
                print('URL not recognized, should contain \'watch\' or \'playlist\'')

    elif args.info:
        info = archive_info()
        print('Number of files: ' + str(info.get('num_files', None)))
        print('Total size: ' + str(info.get('total_size', None)) + ' MB')
        print('Total duration: ' + seconds_to_hours(info.get('total_duration', None)))

    else:
        print('Invalid arguments, see --help')
