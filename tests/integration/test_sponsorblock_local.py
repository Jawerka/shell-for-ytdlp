"""Real yt-dlp/ffmpeg and local HTTP faults; no YouTube or user credentials."""
import hashlib
import http.server
import json
import os
from pathlib import Path
import subprocess
import threading
import time
from unittest.mock import Mock

import pytest

from core.config import ConfigManager
from core.downloader import YouTubeDownloader
from core.pipeline import SponsorBlockAvailability

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[2]
URL = 'https://www.youtube.com/watch?v=test1234567'


@pytest.fixture(scope='module')
def service(tmp_path_factory):
    binaries = {key: ROOT / 'utilities' / f'{key}.exe' for key in ('yt-dlp', 'ffmpeg', 'ffprobe')}
    if not all(path.exists() for path in binaries.values()):
        pytest.skip('Requires local yt-dlp, ffmpeg and ffprobe')
    directory = tmp_path_factory.mktemp('sponsorblock media')
    media = directory / 'sample.mp4'
    generated = subprocess.run([
        str(binaries['ffmpeg']), '-v', 'error', '-f', 'lavfi', '-i',
        'color=red:s=160x90:r=10', '-f', 'lavfi', '-i', 'sine=frequency=440',
        '-t', '4', '-c:v', 'libx264', '-g', '1', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', str(media),
    ], capture_output=True, timeout=20,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    assert generated.returncode == 0, generated.stderr
    control = {'mode': '503', 'requests': [], 'binaries': binaries, 'media': media}
    control['api_started'] = threading.Event()

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            control['requests'].append(self.path)
            if self.path == '/media.mp4':
                data = media.read_bytes()
                self.send_response(200)
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            mode = control['mode']
            control['api_started'].set()
            if mode == 'timeout':
                time.sleep(1.5)
                self.close_connection = True
                return
            if mode == 'disconnect':
                self.close_connection = True
                return
            status = int(mode) if mode.isdigit() else 200
            if mode == 'segments':
                data = json.dumps([{'videoID': 'test1234567', 'segments': [{
                    'segment': [1.5, 2.5], 'category': 'sponsor', 'actionType': 'skip',
                    'videoDuration': 4, 'UUID': 'test-segment',
                }]}]).encode()
            else:
                data = b'not json' if mode == 'badjson' else b'[]'
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    control['url'] = f'http://127.0.0.1:{server.server_port}'
    try:
        yield control
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


@pytest.fixture
def make_download(tmp_path, service, monkeypatch):
    service.update(mode='503', requests=[])
    service['api_started'].clear()
    monkeypatch.setattr('core.downloader.find_cookies_txt', lambda path: None)
    state = SponsorBlockAvailability()
    config = ConfigManager.__new__(ConfigManager)
    config.config_path = str(tmp_path / 'config.json')
    config.bkp_path = str(tmp_path / 'config.bkp')
    config.config = {
        'YTDLP_PATH': str(service['binaries']['yt-dlp']),
        'UTILITIES_PATH': str(tmp_path), 'COOKIES_PATH': '',
        'SPONSORBLOCK_REMOVE_LIST': ['sponsor'], 'SPONSORBLOCK_FAILURE_POLICY': 'ask',
        'VERBOSE_DOWNLOAD_LOG': True,
    }
    info = tmp_path / 'source.info.json'
    info.write_text(json.dumps({
        'id': 'test1234567', 'title': 'Fixture', 'extractor': 'youtube',
        'extractor_key': 'Youtube', 'webpage_url': URL, 'duration': 4,
        'formats': [{'format_id': 'fixture', 'url': service['url'] + '/media.mp4',
                     'ext': 'mp4', 'vcodec': 'avc1.42001e', 'acodec': 'mp4a.40.2',
                     'width': 160, 'height': 90}],
    }), encoding='utf-8')
    instances = []

    def make(name='download', policy=None, answer=('bypass', False)):
        config.set('DOWNLOAD_PATH', str(tmp_path / name))
        if policy is not None:
            config.set('SPONSORBLOCK_FAILURE_POLICY', policy)
        dl = YouTubeDownloader(config, Mock(), Mock(), sponsorblock_state=state,
                               sponsorblock_question=Mock(return_value=answer),
                               sponsorblock_notice=Mock())
        original = dl._build_command
        commands = []

        def command(*args, **kwargs):
            cmd = original(*args, **kwargs)[:-1] + [
                '--ignore-config', '--no-cache-dir', '--socket-timeout', '0.4',
                '--retries', '0', '--extractor-retries', '0',
                '--ffmpeg-location', str(service['binaries']['ffmpeg'].parent),
                '--sponsorblock-api', service['url'], '--load-info-json', str(info),
                '-o', 'result.%(ext)s',
            ]
            commands.append(cmd)
            return cmd

        monkeypatch.setattr(dl, '_build_command', command)
        instances.append(dl)
        return dl, commands

    yield make, config, state
    for dl in instances:
        if dl._process and dl._process.poll() is None:
            dl.cancel()


@pytest.mark.parametrize('fault', ['503', '500', '403', '429', 'timeout', 'disconnect', 'badjson'])
def test_real_fault_then_bypass_downloads_identical_media(service, make_download, fault):
    make, config, state = make_download
    service['mode'] = fault
    dl, commands = make()
    def consent(reason):
        assert '/media.mp4' not in service['requests'], 'Media started before consent'
        assert dl._process is None, 'yt-dlp must be stopped while asking'
        return 'bypass', False
    dl.sponsorblock_question.side_effect = consent
    assert dl.download(URL), dl.log_callback.call_args_list
    dl.sponsorblock_question.assert_called_once()
    assert len(commands) == 2
    assert '--sponsorblock-remove' in commands[0]
    assert '--sponsorblock-remove' not in commands[1]
    result = Path(config.get('DOWNLOAD_PATH')) / 'result.mp4'
    assert hashlib.sha256(result.read_bytes()).digest() == hashlib.sha256(service['media'].read_bytes()).digest()
    assert dl.result_message == 'Скачано без вырезания вставок'


def test_real_consent_next_download_and_recovery_with_actual_cut(service, make_download):
    make, config, state = make_download
    first, _ = make('first', answer=('bypass', True))
    assert first.download(URL), first.log_callback.call_args_list
    assert json.loads(Path(config.config_path).read_text())['SPONSORBLOCK_FAILURE_POLICY'] == 'bypass'
    service['requests'].clear()
    second, commands = make('second')
    assert second.download(URL), second.log_callback.call_args_list
    second.sponsorblock_question.assert_not_called()
    assert not any('/api/' in path for path in service['requests'])
    assert '--sponsorblock-remove' not in commands[0]
    # Real HTTP probe, only its endpoint is redirected to our isolated server.
    from urllib.request import urlopen
    from unittest.mock import patch
    service['mode'] = 'segments'
    state.next_probe = 0
    with patch('core.pipeline.urlopen', side_effect=lambda url, **kw:
               urlopen(service['url'] + '/api/skipSegments/0000', **kw)):
        third, commands = make('third')
        assert third.download(URL), third.log_callback.call_args_list
    assert '--sponsorblock-remove' in commands[0]
    third.sponsorblock_question.assert_not_called()
    third.sponsorblock_notice.assert_called_once()
    result = Path(config.get('DOWNLOAD_PATH')) / 'result.mp4'
    probe = subprocess.run([str(service['binaries']['ffprobe']), '-v', 'error',
                            '-show_entries', 'format=duration', '-of', 'json', str(result)],
                           capture_output=True, text=True, timeout=10,
                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    assert probe.returncode == 0, probe.stderr
    assert 2.7 < float(json.loads(probe.stdout)['format']['duration']) < 3.3


@pytest.mark.parametrize('answer', [('cancel', False), ('bypass', False)])
def test_real_cancel_or_single_use_consent(service, make_download, answer):
    make, config, state = make_download
    first, commands = make('first', answer=answer)
    assert first.download(URL) is (answer[0] == 'bypass')
    assert len(commands) == (2 if answer[0] == 'bypass' else 1)
    assert config.get('SPONSORBLOCK_FAILURE_POLICY') == 'ask'
    if answer[0] == 'cancel':
        assert '/media.mp4' not in service['requests']
        assert not list(Path(config.get('DOWNLOAD_PATH')).glob('*.mp4'))
    second, _ = make('second', answer=('cancel', False))
    assert not second.download(URL)
    second.sponsorblock_question.assert_called_once()


@pytest.mark.parametrize('mode', ['404', 'empty'])
def test_real_no_segments_is_not_a_service_failure(service, make_download, mode):
    make, config, state = make_download
    service['mode'] = mode
    dl, commands = make()
    assert dl.download(URL), dl.log_callback.call_args_list
    assert len(commands) == 1
    dl.sponsorblock_question.assert_not_called()
    assert not state.unavailable
    assert not dl._bypass_sponsorblock


def test_real_stop_policy_never_starts_media_or_asks(service, make_download):
    make, config, state = make_download
    dl, commands = make(policy='stop')
    assert not dl.download(URL)
    dl.sponsorblock_question.assert_not_called()
    assert len(commands) == 1
    assert '/media.mp4' not in service['requests']


def test_real_cancel_while_api_is_not_responding(service, make_download):
    make, config, state = make_download
    service['mode'] = 'timeout'
    dl, _ = make()
    outcomes = []
    worker = threading.Thread(target=lambda: outcomes.append(dl.download(URL)), daemon=True)
    worker.start()
    try:
        assert service['api_started'].wait(timeout=5)
        proc = dl._process
        dl.cancel()
        worker.join(timeout=5)
        assert not worker.is_alive()
        assert outcomes == [False]
        assert proc.poll() is not None
        assert '/media.mp4' not in service['requests']
        dl.sponsorblock_question.assert_not_called()
        assert dl._cancelled
    finally:
        if worker.is_alive():
            dl.cancel()
            worker.join(timeout=5)


def test_real_gate_prevents_download_even_if_app_does_not_read_stdout(service, make_download):
    """No timing assumption: yt-dlp itself must wait before transferring media."""
    make, config, state = make_download
    dl, _ = make('unread output')
    command = dl._build_command(URL, config.get('DOWNLOAD_PATH'))
    output = Path(config.config_path).parent / 'unread-process.log'
    with output.open('wb') as log:
        proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=log,
                                stderr=subprocess.STDOUT,
                                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        try:
            assert service['api_started'].wait(timeout=5)
            deadline = time.monotonic() + 5
            while '(Y/n)' not in output.read_text(encoding='utf-8', errors='replace'):
                assert time.monotonic() < deadline, 'yt-dlp did not reach its pre-download gate'
                time.sleep(0.01)
            assert proc.poll() is None
            assert '/media.mp4' not in service['requests']
            assert not list(Path(config.get('DOWNLOAD_PATH')).rglob('*.mp4'))
        finally:
            proc.kill()
            proc.wait(timeout=5)
            proc.stdin.close()


def test_real_external_quiet_and_color_settings_cannot_stall_gate(service, make_download, monkeypatch):
    make, config, state = make_download
    service['mode'] = 'empty'
    dl, _ = make()
    command = dl._build_command

    def external_output_settings(*args, **kwargs):
        cmd = command(*args, **kwargs)
        # Options loaded from yt-dlp.conf precede app command-line options.
        return [cmd[0], '--quiet', '--color', 'always', *cmd[1:]]

    monkeypatch.setattr(dl, '_build_command', external_output_settings)
    outcomes = []
    worker = threading.Thread(target=lambda: outcomes.append(dl.download(URL)), daemon=True)
    worker.start()
    worker.join(timeout=7)
    try:
        assert not worker.is_alive(), 'External quiet/color settings stalled the pre-download gate'
        assert outcomes == [True]
        dl.sponsorblock_question.assert_not_called()
    finally:
        if worker.is_alive():
            dl.cancel()
            worker.join(timeout=5)
