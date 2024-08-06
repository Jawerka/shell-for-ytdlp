#### Requirements:
[Python 3.10+](https://www.python.org/downloads/)
Should work on earlier versions as well

#### Features:
- Downloading videos from youtube
- Download playlist from youtube
- Automatic removal of sponsored inserts based on SponsorBlock database

#### Usage:
- Place the script in a folder convenient for you
- Run the main.py file through the python interpreter

#### Or use [pyinstaller](https://pyinstaller.org/en/stable/index.html) for Windows users:
- Download the git repository archive (green button)
- Unzip this archive
- Navigate inside the directory
- Hold down Shift and right-click the mouse
- Select Open Power Shell\CMD here.
- [Install pip](https://pip.pypa.io/en/stable/installation/)
```
pip install pyinstaller
pyinstaller --onefile --name 'shell-for-ytdlp' -i icon.ico main.py
```
``shell-for-ytdlp.exe`` will be located in the ``dist`` directory.

#### Links to the resources used:
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [FFmpeg](https://github.com/FFmpeg/FFmpeg)
- [SponsorBlock](https://wiki.sponsor.ajay.app/)
