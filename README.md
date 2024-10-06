<div align="center">
    <h1>shell-for-ytdlp</h1>
    <img src="https://github.com/Jawerka/shell-for-ytdlp/blob/master/icon.png?raw=true" alt="Описание изображения" width="200" height="200" />
</div>

#### Features:
- Downloading videos from youtube
- Download playlist from youtube
- Automatic removal of sponsored inserts based on SponsorBlock database

#### Usage:
- Download [lasted executable file](https://github.com/Jawerka/shell-for-ytdlp/releases/latest/download/shell-for-ytdlp.exe)
- Place it in a folder that is convenient for you
- Run
- At the first startup, ``ytdlp`` and ``ffmpeg`` will be loaded into the ``./utilites`` folder.
- After the first successful download, your settings will be written to the ``config.json`` file.

#### Using the script
#### Requirements:
[Python 3.10+](https://www.python.org/downloads/)
Should work on earlier versions as well

requirements:
```
python -m pip install --upgrade pip
pip install -r requirements.txt
```

#### Or use [pyinstaller](https://pyinstaller.org/en/stable/index.html)
- Download the git repository archive (green button)
- Unzip this archive
- Navigate inside the directory
- Hold down Shift and right-click the mouse
- Select Open Power Shell\CMD here.
- [Install pip](https://pip.pypa.io/en/stable/installation/)
```
pip install pyinstaller
python -m venv venv
venv/Scripts/activate
python -m pip install -r requirements.txt --no-cache-dir
```
```
pyinstaller --onefile --path venv/Lib/site-packages --hidden-import pyperclip,inputimeout --name 'shell-for-ytdlp' -i icon.ico main.py
```
``shell-for-ytdlp.exe`` will be located in the ``dist`` directory.

#### Known issues:
- No support for space characters in the startup path

#### Links to the resources used:
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [FFmpeg](https://github.com/FFmpeg/FFmpeg)
- [SponsorBlock](https://wiki.sponsor.ajay.app/)
