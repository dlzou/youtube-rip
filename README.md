# youtube-rip

Download audio from YouTube using [youtube-dl](https://github.com/ytdl-org/youtube-dl). Either download a single file or multiple files from a playlist. The multiprocessing library is used to speed up playlist downloads. Downloaded files are tracked in an archive using SQLite.

Next steps: find a way to fetch URLs in playlists without breaking the youtube-dl API, playlist syncing?

### How to use

```
$ python3 -m pip install youtube-dl
$ python3 downloader.py [--format EXT] [--location /PATH/TO/FOLDER] URL
$ python3 downloader.py --info
```

### Disclaimer

This personal project is not intended for commercialization or distribution. 