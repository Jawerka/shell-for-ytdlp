"""Real yt-dlp/FFmpeg: format selection and muxing, with no external network."""
import functools
import http.server
import json
import os
import re
import struct
import subprocess
import threading
from pathlib import Path
from unittest.mock import Mock

import pytest

from core.downloader import YouTubeDownloader
from core.download_handlers import DownloadHints

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope='module')
def tools():
    paths = {name: ROOT / 'utilities' / f'{name}.exe' for name in ('yt-dlp', 'ffmpeg', 'ffprobe')}
    if not all(path.exists() for path in paths.values()):
        pytest.skip('Requires local yt-dlp.exe, ffmpeg.exe and ffprobe.exe')
    return paths


def run(command):
    return subprocess.run([str(arg) for arg in command], capture_output=True, text=True,
                          encoding='utf-8', errors='replace', timeout=30,
                          creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)


@pytest.fixture
def downloader(tmp_path, tools):
    settings = {
        'YTDLP_PATH': str(tools['yt-dlp']), 'UTILITIES_PATH': str(tools['ffmpeg'].parent),
        'COOKIES_PATH': '', 'SPONSORBLOCK_REMOVE_LIST': [], 'VIDEO_QUALITY': 'max',
    }
    # Build options only; never search or use the user's cookies in these tests.
    config = Mock()
    config.get.side_effect = lambda key, default=None: settings.get(key, default)
    return YouTubeDownloader(config, Mock(), Mock()), settings


def selection(tools, tmp_path, downloader, formats, mode, quality='max', hints=None):
    dl, settings = downloader
    settings.update(OUTPUT_CONTAINER=mode, VIDEO_QUALITY=quality)
    info = tmp_path / 'input.info.json'
    info.write_text(json.dumps({'id': 'test', 'title': 'Test', 'extractor': 'generic',
                               'formats': formats}), encoding='utf-8')
    return run([tools['yt-dlp'], '--ignore-config', '--no-cache-dir', '--simulate',
                '--no-check-formats', '--load-info-json', info,
                *dl._get_base_ytdlp_options(hints), '--print', '%(format_id)s'])


def format_info(fid, height=None, video='none', audio='none', ext='mp4', url=None):
    return dict(format_id=fid, height=height, vcodec=video, acodec=audio, ext=ext,
                url=url or f'https://example.invalid/{fid}')


@pytest.fixture
def formats():
    return [
        *(format_info(f'avc{height}', height, 'avc1.640028') for height in (480, 720, 1080)),
        *(format_info(f'av1{height}', height, 'av01.0.08M.08') for height in (480, 720, 1080, 2160)),
        format_info('aacaudio', audio='mp4a.40.2', ext='m4a'),
        format_info('opusaudio', audio='opus', ext='webm'),
    ]


@pytest.mark.parametrize('mode', ['auto', 'mp4', 'webm', 'mkv'])
@pytest.mark.parametrize('quality', ['480', '720', '1080', 'max'])
def test_real_selector_matrix(tools, tmp_path, downloader, formats, mode, quality):
    result = selection(tools, tmp_path, downloader, formats, mode, quality)
    height = ('1080' if mode == 'mp4' else '2160') if quality == 'max' else quality
    expected = f'avc{height}+aacaudio' if mode == 'mp4' else f'av1{height}+opusaudio'
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == expected


@pytest.mark.parametrize('mode,video,audio,ext', [
    ('mp4', 'avc1.42001e', 'mp4a.40.2', 'mp4'),
    ('webm', 'vp9', 'opus', 'webm'),
    ('webm', 'av01.0.08M.08', 'vorbis', 'webm'),
    ('webm', 'vp8', 'vorbis', 'webm'),
])
def test_combined_file_fallback(tools, tmp_path, downloader, mode, video, audio, ext):
    result = selection(tools, tmp_path, downloader,
                       [format_info('combined', 480, video, audio, ext)], mode, '720')
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'combined'


@pytest.mark.parametrize('mode,video,audio,height', [
    ('mp4', 'av01.0.08M.08', 'mp4a.40.2', 480),
    ('mp4', 'avc1.640028', 'opus', 480),
    ('webm', 'avc1.640028', 'opus', 480),
    ('webm', 'vp9', 'mp4a.40.2', 480),
    ('mp4', None, None, 480),
    ('webm', None, None, 480),
    ('mp4', 'avc1.640028', 'mp4a.40.2', 1080),
    ('webm', 'vp9', 'opus', 1080),
])
def test_incompatible_or_oversized_fallback_rejected(tools, tmp_path, downloader,
                                                    mode, video, audio, height):
    result = selection(tools, tmp_path, downloader,
                       [format_info('combined', height, video, audio)], mode, '720')
    assert result.returncode != 0
    assert 'Requested format is not available' in result.stderr


@pytest.mark.parametrize('mode', ['auto', 'mp4', 'webm', 'mkv'])
def test_combined_fallback_never_exceeds_quality_limit(tools, tmp_path, downloader, mode):
    formats = [format_info('combined', 1080, 'avc1.640028', 'mp4a.40.2'),
               format_info('modern', 1080, 'vp9', 'opus', 'webm')]
    result = selection(tools, tmp_path, downloader, formats, mode, '720')
    assert result.returncode != 0
    assert 'Requested format is not available' in result.stderr


@pytest.mark.parametrize('mode,expected', [('auto', True), ('mkv', True), ('mp4', True), ('webm', False)])
def test_handler_format_is_checked_by_real_selector(tools, tmp_path, downloader, mode, expected):
    formats = [format_info('0', 1080, 'avc1.640028', 'mp4a.40.2'),
               format_info('other', 480, 'vp9', 'opus', 'webm')]
    hints = DownloadHints(url='https://example.invalid/', format_selector='0')
    result = selection(tools, tmp_path, downloader, formats, mode, '480', hints)
    if expected:
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == '0'
    else:
        assert result.returncode != 0
        assert 'Requested format is not available' in result.stderr


@pytest.fixture(scope='module')
def local_media(tmp_path_factory, tools):
    directory = tmp_path_factory.mktemp('media with spaces')
    for name, args in {
        'avc.mp4': ['-f', 'lavfi', '-i', 'color=red:s=160x90:r=10', '-c:v', 'libx264', '-pix_fmt', 'yuv420p'],
        'vp9.webm': ['-f', 'lavfi', '-i', 'color=blue:s=160x90:r=10', '-c:v', 'libvpx-vp9'],
        'aac.m4a': ['-f', 'lavfi', '-i', 'sine=frequency=440', '-c:a', 'aac'],
        'opus.webm': ['-f', 'lavfi', '-i', 'sine=frequency=880', '-c:a', 'libopus'],
    }.items():
        result = run([tools['ffmpeg'], '-v', 'error', *args, '-t', '1', directory / name])
        assert result.returncode == 0, result.stderr
    # A combined file in another container exercises the remux-only path.
    result = run([tools['ffmpeg'], '-v', 'error', '-i', directory/'avc.mp4',
                  '-i', directory/'aac.m4a', '-c', 'copy', directory/'combined.mkv'])
    assert result.returncode == 0, result.stderr
    result = run([tools['ffmpeg'], '-v', 'error', '-i', directory/'vp9.webm',
                  '-i', directory/'opus.webm', '-c', 'copy', directory/'combined-vp9.mkv'])
    assert result.returncode == 0, result.stderr

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0),
             functools.partial(Handler, directory=str(directory)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}'
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def assert_faststart(path):
    """Check MP4 boxes rather than matching a command-line flag."""
    boxes = []
    with path.open('rb') as stream:
        while header := stream.read(8):
            size, name = struct.unpack('>I4s', header)
            if size == 1:
                size = struct.unpack('>Q', stream.read(8))[0]
                stream.seek(size-16, 1)
            elif size:
                stream.seek(size-8, 1)
            else:
                break
            boxes.append(name)
    assert boxes.index(b'moov') < boxes.index(b'mdat')


@pytest.mark.parametrize('mode', ['auto', 'mp4', 'webm', 'mkv'])
@pytest.mark.parametrize('combined', [False, True])
def test_real_mux_and_remux(tools, tmp_path, downloader, local_media, monkeypatch, mode, combined):
    dl, settings = downloader
    settings['OUTPUT_CONTAINER'] = mode
    # This explicit patch prevents any discovery of credentials from utilities/.
    monkeypatch.setattr('core.downloader.find_cookies_txt', lambda path: None)
    if combined:
        webm = mode == 'webm'
        formats = [format_info('combined', 90, 'vp9' if webm else 'avc1.42001e',
                               'opus' if webm else 'mp4a.40.2', 'mkv',
                               f'{local_media}/combined-vp9.mkv' if webm else f'{local_media}/combined.mkv')]
    else:
        formats = [
            format_info('avc', 90, 'avc1.42001e', url=f'{local_media}/avc.mp4'),
            format_info('vp9', 90, 'vp9', ext='webm', url=f'{local_media}/vp9.webm'),
            format_info('aacaudio', audio='mp4a.40.2', ext='m4a', url=f'{local_media}/aac.m4a'),
            format_info('opusaudio', audio='opus', ext='webm', url=f'{local_media}/opus.webm'),
        ]
    info = tmp_path/'input.info.json'
    info.write_text(json.dumps(dict(id='test', title='Видео с пробелами', extractor='generic',
                                    formats=formats)), encoding='utf-8')
    output = tmp_path/'output with spaces'
    command = dl._build_command('https://example.invalid/', str(output))[:-1]
    result = run([*command, '--ignore-config', '--load-info-json', info, '-o', 'video.%(ext)s'])
    assert result.returncode == 0, result.stderr
    assert re.search(r'\[download\]\s+100(?:\.0)?%', result.stdout + result.stderr)
    files = list(output.glob('video.*'))
    assert len(files) == 1
    media = files[0]
    assert media.suffix == ('.mkv' if combined and mode == 'auto' else
                            '.webm' if mode == 'auto' else f'.{mode}')
    probe = run([tools['ffprobe'], '-v', 'error', '-show_streams', '-of', 'json', media])
    streams = json.loads(probe.stdout)['streams']
    codecs = {stream['codec_type']: stream['codec_name'] for stream in streams}
    assert codecs == ({'video': 'h264', 'audio': 'aac'} if (combined and mode != 'webm') or mode == 'mp4'
                       else {'video': 'vp9', 'audio': 'opus'})
    decoded = run([tools['ffmpeg'], '-v', 'error', '-xerror', '-i', media, '-f', 'null', '-'])
    assert decoded.returncode == 0, decoded.stderr
    if mode == 'mp4':
        assert_faststart(media)
