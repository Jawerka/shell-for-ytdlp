"""Сбой необязательного API не маскирует ошибки основного скачивания."""
from unittest.mock import Mock, MagicMock, patch
from io import BytesIO
from urllib.error import HTTPError

import pytest

from core.pipeline import SponsorBlockAvailability, is_sponsorblock_network_error
from core.downloader import YouTubeDownloader


@pytest.mark.parametrize('line,expected', [
    ("ERROR: HTTPSConnectionPool(host='sponsor.ajay.app'): Read timed out.", True),
    ('ERROR: Preprocessing: Unable to communicate with SponsorBlock API: HTTP Error 503', True),
    ("ERROR: HTTPSConnectionPool(host='rr1.googlevideo.com'): Read timed out.", False),
    ('ERROR: ffmpeg exited with code 1', False),
    ('[SponsorBlock] No matching segments were found', False),
    ('Starting new HTTPS connection (1): sponsor.ajay.app:443', False),
])
def test_error_classification(line, expected):
    assert is_sponsorblock_network_error(line) is expected


def test_cooldown_and_recovery():
    clock = [0]
    state = SponsorBlockAvailability(lambda: clock[0])
    state.failed()
    with patch('core.pipeline.urlopen') as request:
        assert state.probe() is None
        request.assert_not_called()
        clock[0] = 30
        request.side_effect = TimeoutError()
        assert state.probe() is False
        assert state.next_probe == 150
        request.side_effect = None
        request.return_value.__enter__.return_value.read.return_value = b'[]'
        clock[0] = 150
        assert state.probe() is True
        assert not state.unavailable


def test_no_segments_is_healthy():
    state = SponsorBlockAvailability()
    error = HTTPError('https://sponsor.ajay.app/api/skipSegments/0000', 404, 'none', {}, None)
    with patch('core.pipeline.urlopen', side_effect=error):
        assert state.probe(force=True)


def downloader(tmp_path, policy='ask', question=None, state=None):
    exe = tmp_path / 'yt-dlp.exe'
    exe.touch()
    values = {'DOWNLOAD_PATH': str(tmp_path), 'YTDLP_PATH': str(exe),
              'UTILITIES_PATH': str(tmp_path), 'SPONSORBLOCK_REMOVE_LIST': ['sponsor'],
              'SPONSORBLOCK_FAILURE_POLICY': policy}
    config = Mock()
    config.get.side_effect = lambda key, default=None: values.get(key, default)
    config.set.side_effect = lambda key, value: values.update({key: value})
    return YouTubeDownloader(config, Mock(), Mock(), sponsorblock_question=question,
                             sponsorblock_state=state)


def process(lines, code):
    proc = MagicMock()
    proc.stdout = BytesIO(''.join(line + '\n' for line in lines).encode())
    proc.wait.return_value = code
    return proc


FAIL = ['[SponsorBlock] Fetching SponsorBlock segments',
        "ERROR: HTTPSConnectionPool(host='sponsor.ajay.app'): Read timed out."]
URL = 'https://www.youtube.com/watch?v=test1234567'


@pytest.fixture(autouse=True)
def no_real_taskkill_for_mock_processes(monkeypatch):
    monkeypatch.setattr('core.downloader._terminate_process_tree', lambda process: process.kill())


def test_consent_retries_without_sponsorblock_and_remembers(tmp_path):
    question = Mock(return_value=('bypass', True))
    dl = downloader(tmp_path, question=question)
    with patch('core.downloader.subprocess.Popen', side_effect=[process(FAIL, 1), process([], 0)]) as popen:
        assert dl.download(URL)
    assert '--sponsorblock-remove' in popen.call_args_list[0].args[0]
    assert '--sponsorblock-remove' not in popen.call_args_list[1].args[0]
    assert '--continue' in popen.call_args_list[1].args[0]
    question.assert_called_once()
    dl.config.set.assert_called_once_with('SPONSORBLOCK_FAILURE_POLICY', 'bypass')
    assert dl.result_message == 'Скачано без вырезания вставок'


def test_cancel_does_not_restart_or_save(tmp_path):
    dl = downloader(tmp_path, question=Mock(return_value=('cancel', False)))
    with patch('core.downloader.subprocess.Popen', return_value=process(FAIL, 1)) as popen:
        assert not dl.download(URL)
    assert dl._cancelled
    assert popen.call_count == 1
    dl.config.set.assert_not_called()


@pytest.mark.parametrize('policy,count,success', [('bypass', 2, True), ('stop', 1, False)])
def test_policy(tmp_path, policy, count, success):
    question = Mock()
    dl = downloader(tmp_path, policy, question)
    with patch('core.downloader.subprocess.Popen', side_effect=[process(FAIL, 1), process([], 0)]) as popen:
        assert dl.download(URL) is success
    assert popen.call_count == count
    question.assert_not_called()


def test_unrelated_failure_does_not_bypass(tmp_path):
    question = Mock()
    dl = downloader(tmp_path, question=question)
    with patch('core.downloader.subprocess.Popen', return_value=process([
        '[SponsorBlock] Found 2 segments', 'ERROR: ffmpeg exited with code 1'], 1)) as popen:
        assert not dl.download(URL)
    question.assert_not_called()
    assert popen.call_count == 1


def test_api_warning_requires_consent_but_video_error_is_not_retried(tmp_path):
    question = Mock(return_value=('bypass', False))
    dl = downloader(tmp_path, question=question)
    with patch('core.downloader.subprocess.Popen', side_effect=[process([
        'WARNING: Unable to communicate with SponsorBlock API: HTTP Error 503',
    ], 1), process([
        '[info] Downloading 1 format(s): 299+140',
        'ERROR: unable to download video data: HTTP Error 403'], 1)]) as popen:
        assert not dl.download(URL)
    question.assert_called_once()
    assert popen.call_count == 2


def test_next_download_skips_during_cooldown_and_recovers(tmp_path):
    state = SponsorBlockAvailability()
    state.failed()
    dl = downloader(tmp_path, 'bypass', state=state)
    with patch('core.downloader.subprocess.Popen', return_value=process([], 0)) as popen:
        assert dl.download(URL)
    assert '--sponsorblock-remove' not in popen.call_args.args[0]
    state.next_probe = 0
    dl.sponsorblock_notice = Mock()
    with patch('core.pipeline.urlopen') as request:
        request.return_value.__enter__.return_value.read.return_value = b'[]'
        with patch('core.downloader.subprocess.Popen', return_value=process([], 0)) as popen:
            assert dl.download(URL)
    assert '--sponsorblock-remove' in popen.call_args.args[0]
    dl.sponsorblock_notice.assert_called_once()


def test_manual_retry_can_restore_service(tmp_path):
    dl = downloader(tmp_path, question=Mock(return_value=('retry', False)))
    with patch('core.pipeline.urlopen') as request:
        request.return_value.__enter__.return_value.read.return_value = b'[]'
        with patch('core.downloader.subprocess.Popen', side_effect=[process(FAIL, 1), process([], 0)]) as popen:
            assert dl.download(URL)
    assert '--sponsorblock-remove' in popen.call_args_list[1].args[0]
    assert not dl._bypass_sponsorblock


@pytest.mark.parametrize('cancel', [False, True])
@pytest.mark.parametrize('fault', ['none', 'sound', 'notification', 'dialog'])
def test_question_is_scheduled_on_tk_and_worker_can_be_cancelled(cancel, fault):
    import queue
    import threading
    from ui.main_window import MainWindow

    window = MainWindow.__new__(MainWindow)
    window.config_manager = Mock()
    window._cancel_event = threading.Event()
    window._sponsorblock_state = SponsorBlockAvailability()
    window.sound_manager = Mock()
    window.state = Mock(return_value='withdrawn' if fault == 'notification' else 'normal')
    if fault == 'sound':
        window.sound_manager.play_attention.side_effect = RuntimeError('sound unavailable')
    window.log_viewer = Mock()
    window.progress_bar = Mock()
    pending = queue.Queue()
    window.after = lambda delay, callback: pending.put(callback)
    dl = Mock()
    dl._cancelled = False
    dl.result_message = 'Файл скачан'
    answers = []

    def construct(*args, **kwargs):
        def download(url):
            answers.append(kwargs['sponsorblock_question']('timeout'))
            return False
        dl.download.side_effect = download
        return dl

    def dialog(parent, respond, cancelled):
        assert threading.current_thread() is threading.main_thread()
        respond(('bypass', True))

    with patch('ui.main_window.NotificationManager') as notifications, \
         patch('ui.main_window.YouTubeDownloader', side_effect=construct), \
         patch('ui.main_window.SponsorBlockDialog', side_effect=dialog) as show:
        if fault == 'notification':
            notifications.return_value.send.side_effect = RuntimeError('notifications unavailable')
        if fault == 'dialog':
            show.side_effect = RuntimeError('dialog unavailable')
        worker = threading.Thread(target=window._download_thread, args=(URL,), daemon=True)
        worker.start()
        callback = pending.get(timeout=2)
        show.assert_not_called()
        if cancel:
            window._cancel_event.set()
        callback()
        worker.join(timeout=2)
        assert not worker.is_alive()
    assert answers == [('cancel', False) if cancel or fault == 'dialog' else ('bypass', True)]


@pytest.mark.parametrize('line', [
    'ERROR: unable to download video data: HTTP Error 503',
    'ERROR: ffmpeg connection failed',
    'ERROR: [youtube] Unable to download webpage: timed out',
])
def test_other_subsystems_are_not_classified_as_api_errors(line):
    assert not is_sponsorblock_network_error(line, fetching=True)


@pytest.mark.parametrize('order', [('sponsor', 'range'), ('range', 'sponsor')])
def test_sponsorblock_and_range_retries_are_independent(tmp_path, order):
    dl = downloader(tmp_path, question=Mock(return_value=('bypass', False)))
    lines = {'sponsor': FAIL, 'range': ['ERROR: HTTP Error 416: Range Not Satisfiable']}
    with patch('core.downloader.subprocess.Popen', side_effect=[
        process(lines[order[0]], 1), process(lines[order[1]], 1), process([], 0),
    ]) as popen:
        assert dl.download(URL)
    commands = [call.args[0] for call in popen.call_args_list]
    assert len(commands) == 3
    assert '--sponsorblock-remove' not in commands[-1]
    assert '--no-continue' in commands[-1]


def test_failure_to_save_consent_does_not_stop_authorized_download(tmp_path):
    dl = downloader(tmp_path, question=Mock(return_value=('bypass', True)))
    dl.config.save.side_effect = PermissionError('read only configuration')
    with patch('core.downloader.subprocess.Popen', side_effect=[process(FAIL, 1), process([], 0)]):
        assert dl.download(URL)
    assert dl.config.get('SPONSORBLOCK_FAILURE_POLICY') == 'bypass'
    assert any('Не удалось сохранить' in call.args[0] for call in dl.log_callback.call_args_list)


def test_recovery_notification_failure_does_not_stop_download(tmp_path):
    state = SponsorBlockAvailability()
    state.failed()
    state.next_probe = 0
    dl = downloader(tmp_path, 'bypass', state=state)
    dl.sponsorblock_notice = Mock(side_effect=RuntimeError('notification failed'))
    with patch('core.pipeline.urlopen') as request:
        request.return_value.__enter__.return_value.read.return_value = b'[]'
        with patch('core.downloader.subprocess.Popen', return_value=process([], 0)):
            assert dl.download(URL)
    assert not dl._bypass_sponsorblock


@pytest.mark.parametrize('manual', [False, True])
def test_cancellation_during_recovery_probe_does_not_start_process_or_notify(tmp_path, manual):
    state = SponsorBlockAvailability()
    state.failed()
    state.next_probe = 0
    dl = downloader(tmp_path, 'ask' if manual else 'bypass',
                    question=Mock(return_value=('retry', False)), state=state)
    dl.sponsorblock_notice = Mock()

    def probe(force=False):
        if manual and not force:
            return None
        dl._cancelled = True
        state.recovered()
        return True

    with patch.object(state, 'probe', side_effect=probe), \
         patch('core.downloader.subprocess.Popen') as popen:
        assert not dl.download(URL)
    popen.assert_not_called()
    dl.sponsorblock_notice.assert_not_called()


@pytest.mark.parametrize('show_before_cancel', [False, True])
def test_old_question_stays_cancelled_after_next_download_clears_event(show_before_cancel):
    import queue
    import threading
    from ui.main_window import MainWindow

    window = MainWindow.__new__(MainWindow)
    window.config_manager = Mock()
    window._cancel_event = threading.Event()
    window._sponsorblock_state = SponsorBlockAvailability()
    window.sound_manager = Mock()
    window.state = Mock(return_value='normal')
    pending = queue.Queue()
    window.after = lambda delay, callback: pending.put(callback)
    dl = Mock(_cancelled=True, result_message='')
    predicates = []

    def construct(*args, **kwargs):
        dl.download.side_effect = lambda url: kwargs['sponsorblock_question']('timeout')
        return dl

    def dialog(parent, respond, cancelled):
        predicates.append(cancelled)

    with patch('ui.main_window.YouTubeDownloader', side_effect=construct), \
         patch('ui.main_window.SponsorBlockDialog', side_effect=dialog) as show:
        worker = threading.Thread(target=window._download_thread, args=(URL,), daemon=True)
        worker.start()
        callback = pending.get(timeout=2)
        if show_before_cancel:
            callback()
        window._cancel_event.set()
        worker.join(timeout=2)
        assert not worker.is_alive()
        window._cancel_event.clear()
        if show_before_cancel:
            assert predicates[0](), 'An old question must close even after the event is cleared'
        else:
            callback()
            show.assert_not_called()


def test_repeated_api_failure_after_manual_recovery_is_bounded_and_remembered(tmp_path):
    dl = downloader(tmp_path, question=Mock(return_value=('retry', False)))
    with patch('core.pipeline.urlopen') as request:
        request.return_value.__enter__.return_value.read.return_value = b'[]'
        with patch('core.downloader.subprocess.Popen', side_effect=[process(FAIL, 1), process(FAIL, 1)]) as popen:
            assert not dl.download(URL)
    assert popen.call_count == 2
    assert dl.sponsorblock_state.unavailable
    dl.sponsorblock_question.assert_called_once()


@pytest.mark.parametrize('body', [b'<html>proxy error</html>', b'{}', b'invalid JSON'])
def test_probe_does_not_mistake_invalid_api_response_for_recovery(body):
    state = SponsorBlockAvailability()
    with patch('core.pipeline.urlopen') as request:
        request.return_value.__enter__.return_value.read.return_value = body
        assert state.probe(force=True) is False
    assert state.unavailable
    request.return_value.__exit__.assert_called_once()


@pytest.mark.parametrize('fetching', [False, True])
def test_invalid_json_is_only_a_sponsorblock_error_during_its_fetch(fetching):
    assert is_sponsorblock_network_error(
        'json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)',
        fetching=fetching,
    ) is fetching


def test_scheduled_recovery_notification_failure_is_noncritical():
    import threading
    from ui.main_window import MainWindow

    window = MainWindow.__new__(MainWindow)
    window.config_manager = Mock()
    window._cancel_event = threading.Event()
    window._sponsorblock_state = SponsorBlockAvailability()
    callbacks = []
    window.after = lambda delay, callback: callbacks.append(callback)
    dl = Mock(_cancelled=False, result_message='Файл скачан')

    def construct(*args, **kwargs):
        def download(url):
            kwargs['sponsorblock_notice']('SponsorBlock снова доступен')
            return True
        dl.download.side_effect = download
        return dl

    with patch('ui.main_window.YouTubeDownloader', side_effect=construct), \
         patch('ui.main_window.NotificationManager') as notifications:
        notifications.return_value.send.side_effect = RuntimeError('notification unavailable')
        assert window._download_thread(URL)
        for callback in callbacks:
            callback()  # Must not raise out of the Tk after() callback.
    assert window._download_result_message == 'Файл скачан'


@pytest.mark.parametrize('marker', [
    '[SponsorBlock] Found 1 segments in the SponsorBlock database',
    '[SponsorBlock] No matching segments were found in the SponsorBlock database',
])
def test_stdin_gate_is_released_only_after_successful_api_response(tmp_path, marker):
    dl = downloader(tmp_path)
    proc = process(['[SponsorBlock] Fetching SponsorBlock segments', marker], 0)
    with patch('core.downloader.subprocess.Popen', return_value=proc):
        assert dl._run_process(['yt-dlp.exe', '--sponsorblock-remove', 'sponsor', '--match-filter', '-']) == 0
    proc.stdin.write.assert_called_once_with(b'y\n')
    proc.stdin.flush.assert_called_once()


def test_api_failure_never_releases_stdin_gate(tmp_path):
    dl = downloader(tmp_path)
    proc = process(FAIL, 1)
    with patch('core.downloader.subprocess.Popen', return_value=proc):
        assert dl._run_process(['yt-dlp.exe', '--sponsorblock-remove', 'sponsor', '--match-filter', '-']) == 1
    proc.stdin.write.assert_not_called()
    assert dl._process is None
