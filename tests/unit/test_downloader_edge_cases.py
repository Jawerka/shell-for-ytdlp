"""Failures at each download stage and cancellation at subprocess boundaries."""
from unittest.mock import MagicMock, Mock, patch

import pytest

from core.download_handlers import DownloadHints, HandlerError
from core.downloader import YouTubeDownloader, _terminate_process_tree


@pytest.fixture
def downloader(tmp_path):
    binary = tmp_path/'yt-dlp.exe'
    binary.touch()
    settings = dict(YTDLP_PATH=str(binary), DOWNLOAD_PATH=str(tmp_path/'output'),
                    UTILITIES_PATH=str(tmp_path), COOKIES_PATH='', SPONSORBLOCK_REMOVE_LIST=[])
    config = Mock()
    config.get.side_effect = lambda key, default=None: settings.get(key, default)
    return YouTubeDownloader(config, Mock(), Mock())


@pytest.mark.parametrize('clear_process', [False, True])
def test_cancel_at_end_of_output_is_not_success(downloader, clear_process):
    process = MagicMock()
    process.wait.return_value = 0

    def output():
        yield b'[download] 100%\n'
        downloader._cancelled = True
        if clear_process:
            downloader._process = None  # cancel() clears the shared reference.

    process.stdout = output()
    with patch('core.downloader.subprocess.Popen', return_value=process):
        assert downloader._run_process(['yt-dlp.exe']) is None
    assert not any(level == 'success' for _, level in downloader.log_callback.call_args_list)


@pytest.mark.parametrize('phase,expected', [
    ('[VideoRemuxer] Remuxing video', 'Перепаковка контейнера (ffmpeg)...'),
    ('[FixupM3u8] Fixing MPEG-TS in MP4 container', 'Обработка ffmpeg...'),
])
def test_remux_phase_is_visible(downloader, phase, expected):
    assert downloader._parse_phase_status(phase) == expected


def test_cancel_during_process_start_is_not_lost(downloader):
    process = MagicMock()

    def start(*args, **kwargs):
        downloader._cancelled = True
        return process

    with patch('core.downloader.subprocess.Popen', side_effect=start), \
            patch('core.downloader._terminate_process_tree') as terminate:
        assert downloader._run_process(['yt-dlp.exe']) is None
    terminate.assert_called_once_with(process)
    process.wait.assert_called_once()


def test_callbacks_are_optional(downloader):
    downloader.log_callback = None
    downloader.progress_callback = None
    downloader._log('message')
    downloader._progress(50, 'progress')
    assert downloader._logs_buffer == ['message']


def test_terminate_absent_process():
    _terminate_process_tree(None)


def test_terminate_failure_is_logged(caplog):
    process = Mock()
    with patch('core.downloader.os.name', 'posix'):
        process.kill.side_effect = OSError('cannot kill')
        _terminate_process_tree(process)
    assert 'cannot kill' in caplog.text


def test_custom_base_options_can_omit_format(downloader):
    downloader.YTDLP_OPTIONS = ['--continue']
    assert downloader._get_base_ytdlp_options() == ['--continue', '-f', 'bestvideo+bestaudio/best']


def test_discovered_cookie_is_used(downloader):
    # This is a mocked path, not a real credential file.
    with patch('core.downloader.find_cookies_txt', return_value='mock-cookies.txt'):
        command = downloader._build_command('https://example.com/', '/output')
    assert command[command.index('--cookies') + 1] == 'mock-cookies.txt'


@pytest.mark.parametrize('line', ['', None, 123, '[download] No percentage'])
def test_nonprogress_lines_are_ignored(downloader, line):
    assert downloader._parse_progress(line) is None


@pytest.mark.parametrize('line', ['', None, 123, '[VideoRemuxer] Not remuxing media file'])
def test_nonphase_lines_are_ignored(downloader, line):
    assert downloader._parse_phase_status(line) is None


def test_incomplete_file_retry_line_is_ignored(downloader):
    assert downloader._parse_file_access_retry('ERROR: unable to rename file') is None


def test_stream_without_stdout_still_waits(downloader):
    process = Mock(stdout=None)
    process.wait.return_value = 7
    with patch('core.downloader.subprocess.Popen', return_value=process):
        assert downloader._run_process(['yt-dlp.exe']) == 7
    process.wait.assert_called_once()


def test_output_decoding_progress_and_file_lock_retries(downloader):
    process = MagicMock()
    process.stdout = iter([
        b'\x98\n', b'\n',
        b'[download] 10% at 2.00MiB/s\n',
        b'[download] 20% ETA 00:01\n',
        b'ERROR: unable to rename file: Retrying (2/10)\n',
        b'[VideoRemuxer] Remuxing video\n',
        b'ERROR: HTTP Error 416\n',
        *([b'[download] segment\n'] * 10),
    ])
    process.wait.return_value = 1
    with patch('core.downloader.subprocess.Popen', return_value=process):
        assert downloader._run_process(['yt-dlp.exe']) == 1
    assert downloader._range_error
    messages = [call.args[0] for call in downloader.log_callback.call_args_list]
    assert any('временно занят' in message for message in messages)
    assert any('Перепаковка' in call.args[1] for call in downloader.progress_callback.call_args_list)


@pytest.mark.parametrize('stage,message', [
    ('ensure_download_directory', 'no directory access'),
    ('ensure_download_temp_directory', 'no temp access'),
])
def test_directory_failures_do_not_start_process(downloader, stage, message):
    with patch(f'core.downloader.{stage}', return_value=(False, message)), \
            patch('core.downloader.subprocess.Popen') as popen:
        assert downloader.download('https://example.com/') is False
    popen.assert_not_called()
    downloader.log_callback.assert_called_with(message, 'error')


@pytest.mark.parametrize('missing', ['DOWNLOAD_PATH', 'YTDLP_PATH'])
def test_missing_required_paths_stop_download(downloader, missing):
    getter = downloader.config.get.side_effect
    downloader.config.get.side_effect = lambda key, default=None: '' if key == missing else getter(key, default)
    with patch('core.downloader.subprocess.Popen') as popen:
        assert downloader.download('https://example.com/') is False
    popen.assert_not_called()


def test_handler_failure_stops_before_process(downloader):
    with patch('core.downloader.resolve_download_hints', side_effect=HandlerError('bad VOD')), \
            patch('core.downloader.subprocess.Popen') as popen:
        assert downloader.download('https://example.com/') is False
    popen.assert_not_called()
    downloader.log_callback.assert_called_with('bad VOD', 'error')


@pytest.mark.parametrize('error', [OSError('process unavailable'), KeyboardInterrupt()])
def test_process_exceptions_restore_state_and_keep_temporary_files(downloader, error):
    process = Mock()

    def fail(command):
        downloader._process = process
        raise error

    with patch.object(downloader, '_run_process', side_effect=fail), \
            patch('core.downloader._terminate_process_tree') as terminate, \
            patch('core.downloader.cleanup_download_temp_directory') as cleanup:
        assert downloader.download('https://example.com/') is False
    assert downloader._process is None
    assert downloader._logs_buffer == []
    cleanup.assert_not_called()
    if isinstance(error, KeyboardInterrupt):
        terminate.assert_called_once_with(process)


def test_keyboard_interrupt_before_process_exists(downloader):
    with patch.object(downloader, '_run_process', side_effect=KeyboardInterrupt()), \
            patch('core.downloader._terminate_process_tree') as terminate:
        assert downloader.download('https://example.com/') is False
    terminate.assert_not_called()


def test_handler_title_and_silent_failure_are_logged(downloader):
    with patch('core.downloader.resolve_download_hints', return_value=DownloadHints(
            url='https://example.com/video.mp4', log_title='Test handler')), \
            patch.object(downloader, '_run_process', return_value=1):
        assert downloader.download('https://example.com/') is False
    messages = [call.args[0] for call in downloader.log_callback.call_args_list]
    assert 'Плагин: Test handler' in messages
    assert any('кодом 1' in message for message in messages)
