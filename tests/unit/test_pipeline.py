# -*- coding: utf-8 -*-
"""Тесты для core/pipeline.py."""

import os
import sys
from unittest.mock import Mock, patch

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.pipeline import (
    UtilitySeverity,
    DOWNLOAD_TEMP_DIR_NAME,
    check_ytdlp_ready,
    classify_utility_update_result,
    cleanup_download_temp_directory,
    ensure_download_directory,
    ensure_download_temp_directory,
    get_download_temp_dir,
    get_ytdlp_download_url,
    validate_url_for_download,
)


class TestValidateUrlForDownload:
    @patch('core.pipeline.urlopen')
    def test_success(self, mock_urlopen):
        mock_urlopen.return_value.close = Mock()
        ok, url, warning = validate_url_for_download('https://youtube.com/watch?v=test')
        assert ok is True
        assert url == 'https://youtube.com/watch?v=test'
        assert warning == ''

    @patch('core.pipeline.urlopen')
    def test_http_error_continues(self, mock_urlopen):
        from urllib.error import HTTPError
        mock_urlopen.side_effect = HTTPError('url', 404, 'Not Found', {}, None)
        ok, url, warning = validate_url_for_download('https://youtube.com/watch?v=test')
        assert ok is True
        assert '404' in warning

    @patch('core.pipeline.urlopen')
    def test_timeout_soft_fail_for_youtube(self, mock_urlopen):
        import socket
        mock_urlopen.side_effect = socket.timeout()
        ok, url, warning = validate_url_for_download('https://youtube.com/watch?v=test')
        assert ok is True
        assert 'таймаут' in warning.lower() or 'yt-dlp' in warning

    @patch('core.pipeline.urlopen')
    def test_timeout_hard_fail_for_unknown(self, mock_urlopen):
        import socket
        mock_urlopen.side_effect = socket.timeout()
        ok, message, warning = validate_url_for_download('https://unknown-site.example/video')
        assert ok is False
        assert warning == ''

    def test_empty_url(self):
        ok, message, warning = validate_url_for_download('')
        assert ok is False
        assert message == 'Введите URL'


class TestEnsureDownloadDirectory:
    def test_existing_directory(self, tmp_path):
        ok, message = ensure_download_directory(str(tmp_path))
        assert ok is True
        assert message == ''

    def test_creates_missing_directory(self, tmp_path):
        new_dir = tmp_path / 'downloads'
        ok, message = ensure_download_directory(str(new_dir))
        assert ok is True
        assert new_dir.is_dir()

    @patch('core.pipeline.os.makedirs', side_effect=PermissionError())
    def test_permission_error(self, _mock_makedirs):
        ok, message = ensure_download_directory('/fake/path')
        assert ok is False
        assert 'доступ' in message.lower()


class TestDownloadTempDirectory:
    def test_get_download_temp_dir(self, tmp_path):
        download_dir = tmp_path / 'videos'
        download_dir.mkdir()
        temp_dir = get_download_temp_dir(str(download_dir))
        assert temp_dir.endswith(DOWNLOAD_TEMP_DIR_NAME)
        assert os.path.basename(temp_dir) == '_UI-for-ytdlp-temp'
        assert os.path.dirname(temp_dir) == str(download_dir.resolve())

    def test_ensure_download_temp_directory(self, tmp_path):
        download_dir = tmp_path / 'videos'
        ok, message = ensure_download_temp_directory(str(download_dir))
        assert ok is True
        assert message == ''
        assert (download_dir / DOWNLOAD_TEMP_DIR_NAME).is_dir()

    def test_cleanup_removes_temp_directory(self, tmp_path):
        download_dir = tmp_path / 'videos'
        temp_dir = download_dir / DOWNLOAD_TEMP_DIR_NAME
        temp_dir.mkdir(parents=True)
        (temp_dir / 'fragment.mp4.part').write_bytes(b'x')

        cleanup_download_temp_directory(str(download_dir))

        assert not temp_dir.exists()

    def test_cleanup_missing_directory_is_noop(self, tmp_path):
        cleanup_download_temp_directory(str(tmp_path / 'missing'))


class TestCheckYtdlpReady:
    def test_ready_when_exists(self, tmp_path):
        ytdlp = tmp_path / 'yt-dlp.exe'
        ytdlp.write_bytes(b'')
        config = Mock()
        config.get.return_value = str(ytdlp)
        ready, message = check_ytdlp_ready(config)
        assert ready is True

    def test_not_ready_when_missing(self):
        config = Mock()
        config.get.return_value = '/nonexistent/yt-dlp.exe'
        ready, message = check_ytdlp_ready(config)
        assert ready is False
        assert 'yt-dlp' in message


class TestClassifyUtilityUpdateResult:
    def test_ytdlp_failure_is_critical(self):
        assert classify_utility_update_result('yt-dlp.exe', False) == UtilitySeverity.CRITICAL

    def test_deno_failure_is_non_critical(self):
        assert classify_utility_update_result('deno.zip', False) == UtilitySeverity.NON_CRITICAL

    def test_success_is_non_critical(self):
        assert classify_utility_update_result('yt-dlp.exe', True) == UtilitySeverity.NON_CRITICAL


class TestGetYtdlpDownloadUrl:
    def test_finds_ytdlp_url(self):
        config = Mock()
        config.get.return_value = [
            'https://example.com/yt-dlp.exe',
            'https://example.com/ffmpeg.zip',
        ]
        assert get_ytdlp_download_url(config) == 'https://example.com/yt-dlp.exe'

    def test_returns_none_when_missing(self):
        config = Mock()
        config.get.return_value = ['https://example.com/ffmpeg.zip']
        assert get_ytdlp_download_url(config) is None
