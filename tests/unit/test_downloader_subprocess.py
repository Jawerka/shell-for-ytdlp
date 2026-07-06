# -*- coding: utf-8 -*-
"""Тесты subprocess-цикла YouTubeDownloader.download()."""

import os
import sys
from unittest.mock import Mock, patch, MagicMock

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.downloader import YouTubeDownloader


def _make_downloader(tmp_path):
    config = Mock()
    config.get.side_effect = lambda key, default=None: {
        'DOWNLOAD_PATH': str(tmp_path),
        'YTDLP_PATH': str(tmp_path / 'yt-dlp.exe'),
        'UTILITIES_PATH': str(tmp_path),
        'COOKIES_PATH': '',
        'SPONSORBLOCK_REMOVE_LIST': [],
    }.get(key, default)
    log_callback = Mock()
    progress_callback = Mock()
    return YouTubeDownloader(config, log_callback, progress_callback), log_callback, progress_callback


class TestBuildCommandPaths:
    def test_paths_with_spaces_not_quoted(self, tmp_path):
        download_path = str(tmp_path / 'My Downloads')
        os.makedirs(download_path)
        downloader, _, _ = _make_downloader(tmp_path)
        (tmp_path / 'yt-dlp.exe').write_bytes(b'')

        cmd = downloader._build_command('https://youtube.com/watch?v=test', download_path)

        assert f'home:{download_path}' in cmd
        assert f'temp:{download_path}\\_UI-for-ytdlp-temp' in cmd or (
            f'temp:{download_path}/_UI-for-ytdlp-temp' in cmd
        )
        assert f'"{download_path}"' not in cmd
        assert str(tmp_path) in cmd


class TestDownloadSubprocess:
    def test_success(self, tmp_path):
        (tmp_path / 'yt-dlp.exe').write_bytes(b'')
        downloader, log_callback, progress_callback = _make_downloader(tmp_path)

        lines = [
            b'[download] 50.0% of  100.00MiB at   10.00MiB/s ETA 00:05\n',
            b'[download] 100% of  100.00MiB\n',
        ]

        mock_process = MagicMock()
        mock_process.pid = 1234
        mock_process.stdout = iter(lines)
        mock_process.wait.return_value = 0

        with patch('core.downloader.subprocess.Popen', return_value=mock_process):
            with patch('core.downloader.cleanup_download_temp_directory') as mock_cleanup:
                result = downloader.download('https://youtube.com/watch?v=test')

        assert result is True
        mock_cleanup.assert_called_once_with(str(tmp_path))
        progress_callback.assert_called()

    def test_merge_phase_updates_progress(self, tmp_path):
        (tmp_path / 'yt-dlp.exe').write_bytes(b'')
        downloader, _, progress_callback = _make_downloader(tmp_path)

        lines = [
            b'[download] 100% of  100.00MiB\n',
            b'[Merger] Merging formats into "video.mp4"\n',
        ]

        mock_process = MagicMock()
        mock_process.pid = 1234
        mock_process.stdout = iter(lines)
        mock_process.wait.return_value = 0

        with patch('core.downloader.subprocess.Popen', return_value=mock_process):
            result = downloader.download('https://youtube.com/watch?v=test')

        assert result is True
        phase_calls = [
            c for c in progress_callback.call_args_list
            if c[0][1] == 'Слияние потоков (ffmpeg)...'
        ]
        assert phase_calls

    def test_failure_return_code(self, tmp_path):
        (tmp_path / 'yt-dlp.exe').write_bytes(b'')
        downloader, log_callback, _ = _make_downloader(tmp_path)

        mock_process = MagicMock()
        mock_process.pid = 1234
        mock_process.stdout = iter([b'ERROR: unable to download\n'])
        mock_process.wait.return_value = 1

        with patch('core.downloader.subprocess.Popen', return_value=mock_process):
            result = downloader.download('https://youtube.com/watch?v=test')

        assert result is False
        error_calls = [c for c in log_callback.call_args_list if c[0][1] == 'error']
        assert error_calls

    def test_cancel_mid_stream(self, tmp_path):
        (tmp_path / 'yt-dlp.exe').write_bytes(b'')
        downloader, log_callback, _ = _make_downloader(tmp_path)

        lines = [b'[download] 10.0%\n', b'[download] 20.0%\n']

        class CancellingStdout:
            def __init__(self, data, dl):
                self._data = iter(data)
                self._dl = dl

            def __iter__(self):
                return self

            def __next__(self):
                self._dl._cancelled = True
                return next(self._data)

        mock_process = MagicMock()
        mock_process.pid = 1234
        mock_process.stdout = CancellingStdout(lines, downloader)
        mock_process.wait.return_value = -9

        with patch('core.downloader.subprocess.Popen', return_value=mock_process):
            with patch('core.downloader._terminate_process_tree') as mock_terminate:
                result = downloader.download('https://youtube.com/watch?v=test')

        assert result is False
        mock_terminate.assert_called_once_with(mock_process)

    def test_utf8_decoding(self, tmp_path):
        (tmp_path / 'yt-dlp.exe').write_bytes(b'')
        downloader, log_callback, _ = _make_downloader(tmp_path)

        line = 'Загрузка видео\n'.encode('utf-8')
        mock_process = MagicMock()
        mock_process.stdout = iter([line])
        mock_process.wait.return_value = 0

        with patch('core.downloader.subprocess.Popen', return_value=mock_process):
            result = downloader.download('https://youtube.com/watch?v=test')

        assert result is True
        info_calls = [str(c) for c in log_callback.call_args_list]
        assert any('Загрузка' in c for c in info_calls)

    def test_cp1251_fallback(self, tmp_path):
        (tmp_path / 'yt-dlp.exe').write_bytes(b'')
        downloader, log_callback, _ = _make_downloader(tmp_path)

        line = 'Видео'.encode('cp1251') + b'\n'
        mock_process = MagicMock()
        mock_process.stdout = iter([line])
        mock_process.wait.return_value = 0

        with patch('core.downloader.subprocess.Popen', return_value=mock_process):
            result = downloader.download('https://youtube.com/watch?v=test')

        assert result is True

    def test_creates_download_directory(self, tmp_path):
        (tmp_path / 'yt-dlp.exe').write_bytes(b'')
        new_dir = tmp_path / 'new downloads'
        config = Mock()
        config.get.side_effect = lambda key, default=None: {
            'DOWNLOAD_PATH': str(new_dir),
            'YTDLP_PATH': str(tmp_path / 'yt-dlp.exe'),
            'UTILITIES_PATH': str(tmp_path),
            'COOKIES_PATH': '',
            'SPONSORBLOCK_REMOVE_LIST': [],
        }.get(key, default)
        downloader = YouTubeDownloader(config, Mock(), Mock())

        mock_process = MagicMock()
        mock_process.stdout = iter([])
        mock_process.wait.return_value = 0

        with patch('core.downloader.subprocess.Popen', return_value=mock_process):
            result = downloader.download('https://youtube.com/watch?v=test')

        assert result is True
        assert new_dir.is_dir()
