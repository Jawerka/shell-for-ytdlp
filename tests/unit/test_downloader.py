# -*- coding: utf-8 -*-
"""
Тесты для модуля downloader.py.

Проверяют:
- Построение команды для yt-dlp
- Парсинг прогресса загрузки
- Обработку ошибок
- Валидацию путей
"""

import os
import sys
import pytest
from unittest.mock import Mock, MagicMock, patch

# Добавляем корень проекта в path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.downloader import YouTubeDownloader
from core.config import ConfigManager
from core.download_handlers import DownloadHints


class TestYouTubeDownloaderInit:
    """Тесты инициализации YouTubeDownloader."""

    def test_init_with_valid_config(self):
        """Тест инициализации с валидной конфигурацией."""
        config = Mock(spec=ConfigManager)
        config.get.side_effect = lambda key, default=None: {
            'DOWNLOAD_PATH': '/test/path',
            'YTDLP_PATH': '/test/path/yt-dlp.exe'
        }.get(key, default)
        
        log_callback = Mock()
        progress_callback = Mock()
        
        downloader = YouTubeDownloader(config, log_callback, progress_callback)
        
        assert downloader.config == config
        assert downloader.log_callback == log_callback
        assert downloader.progress_callback == progress_callback
        assert downloader._process is None
        assert downloader._cancelled is False
        assert downloader._logs_buffer == []

    def test_init_initializes_empty_buffer(self):
        """Тест что буфер логов инициализируется пустым."""
        config = Mock(spec=ConfigManager)
        config.get.side_effect = lambda key, default=None: {
            'DOWNLOAD_PATH': '/test/path',
            'YTDLP_PATH': '/test/path/yt-dlp.exe'
        }.get(key, default)
        
        downloader = YouTubeDownloader(config, Mock(), Mock())
        
        assert downloader._logs_buffer == []


class TestBuildCommand:
    """Тесты построения команды для yt-dlp."""

    @pytest.fixture
    def build_downloader(self):
        """Фикстура downloader с полной конфигурацией для _build_command."""
        config = Mock()
        config.get.side_effect = lambda key, default=None: {
            'DOWNLOAD_PATH': '/test/path',
            'YTDLP_PATH': '/test/yt-dlp.exe',
            'UTILITIES_PATH': '/test/utilities',
            'COOKIES_PATH': '',
            'SPONSORBLOCK_REMOVE_LIST': ['sponsor', 'selfpromo']
        }.get(key, default)

        return YouTubeDownloader(config, Mock(), Mock())

    def test_build_command_basic(self, build_downloader):
        """Тест базовой команды."""
        cmd = build_downloader._build_command('https://youtube.com/watch?v=test', '/output')
        
        assert build_downloader.config.get('YTDLP_PATH') in cmd
        assert 'home:/output' in cmd
        temp_args = [arg for arg in cmd if arg.startswith('temp:')]
        assert len(temp_args) == 1
        assert temp_args[0].endswith('_UI-for-ytdlp-temp')
        assert '--newline' in cmd  # Флаг для корректного вывода прогресса
        assert '-f' in cmd
        assert 'bestvideo+bestaudio/best' in cmd

    def test_build_command_strips_url_params(self, build_downloader):
        """Тест что URL очищается от параметров."""
        url_with_params = 'https://youtube.com/watch?v=test&list=PLtest&t=10s'
        cmd = build_downloader._build_command(url_with_params, '/output')
        
        # URL должен быть очищен
        assert 'https://youtube.com/watch?v=test' in cmd
        assert '&list=' not in cmd
        assert '&t=' not in cmd

    def test_build_command_with_sponsorblock(self, build_downloader):
        """Тест команды с SponsorBlock."""
        cmd = build_downloader._build_command('https://youtube.com/watch?v=test', '/output')

        assert '--sponsorblock-remove' in cmd
        assert 'sponsor,selfpromo' in cmd

    def test_build_command_with_playlist(self, build_downloader):
        """Тест команды с плейлистом."""
        playlist_url = 'https://youtube.com/playlist?list=PLtest'
        cmd = build_downloader._build_command(playlist_url, '/output')
        
        assert '-o' in cmd
        assert '%(playlist)s/%(title)s [%(id)s].%(ext)s' in cmd

    def test_build_command_with_cookies(self, build_downloader):
        """Тест команды с cookies.txt."""
        build_downloader.config.get.side_effect = lambda key, default=None: {
            'DOWNLOAD_PATH': '/test/path',
            'YTDLP_PATH': '/test/yt-dlp.exe',
            'UTILITIES_PATH': '/test/utilities',
            'COOKIES_PATH': '/test/cookies.txt',
            'SPONSORBLOCK_REMOVE_LIST': []
        }.get(key, default)
        
        # Мокаем os.path.exists для cookies
        with patch('core.downloader.os.path.exists', return_value=True):
            cmd = build_downloader._build_command('https://youtube.com/watch?v=test', '/output')
            
            assert '--cookies' in cmd
            assert '/test/cookies.txt' in cmd

    def test_build_command_with_download_hints(self, build_downloader):
        """Тест команды с подсказками от плагина GoodGame VOD."""
        hints = DownloadHints(
            url='https://storage3.goodgame.ru/hls_vod/test/index.m3u8',
            format_selector='0',
            referer='https://goodgame.ru/',
            merge_output_format='mp4',
            output_template='Test_Title_2026-06-27T18:52:42Z.%(ext)s',
        )
        cmd = build_downloader._build_command(
            'https://goodgame.ru/vods/6/2026-06-27T18:52:42Z',
            '/output',
            hints,
        )

        assert '0' in cmd
        assert 'bestvideo+bestaudio/best' not in cmd
        assert '--referer' in cmd
        assert 'https://goodgame.ru/' in cmd
        assert '--merge-output-format' in cmd
        assert 'mp4' in cmd
        assert 'Test_Title_2026-06-27T18:52:42Z.%(ext)s' in cmd
        assert 'https://storage3.goodgame.ru/hls_vod/test/index.m3u8' in cmd
        assert '--sponsorblock-remove' not in cmd

    def test_build_command_without_sponsorblock_for_vk(self, build_downloader):
        """SponsorBlock не добавляется для не-YouTube URL."""
        cmd = build_downloader._build_command('https://vk.com/video-1_2', '/output')
        assert '--sponsorblock-remove' not in cmd
    """Тесты парсинга прогресса."""

    @pytest.fixture
    def downloader(self):
        """Фикстура для создания downloader."""
        config = Mock(spec=ConfigManager)
        config.get.side_effect = lambda key, default=None: {
            'DOWNLOAD_PATH': '/test/path',
            'YTDLP_PATH': '/test/yt-dlp.exe'
        }.get(key, default)
        
        return YouTubeDownloader(config, Mock(), Mock())

    def test_parse_progress_percentage_only(self, downloader):
        """Тест парсинга только процента."""
        line = "[download] 45.2%"
        result = downloader._parse_progress(line)
        
        assert result is not None
        assert result[0] == 45.2  # percent

    def test_parse_progress_with_size(self, downloader):
        """Тест парсинга процента и размера."""
        line = "[download] 67.2% of  884.03MiB"
        result = downloader._parse_progress(line)
        
        assert result is not None
        assert result[0] == 67.2
        assert '884.03MiB' in result[1]

    def test_parse_progress_with_speed(self, downloader):
        """Тест парсинга скорости."""
        line = "[download] 50.0% of  500.00MiB at   15.50MiB/s"
        result = downloader._parse_progress(line)
        
        assert result is not None
        assert result[2] == '15.50 MiB/s'  # speed

    def test_parse_progress_with_eta(self, downloader):
        """Тест парсинга ETA."""
        line = "[download] 75.0% of  100.00MiB at   10.00MiB/s ETA 00:05"
        result = downloader._parse_progress(line)
        
        assert result is not None
        assert result[3] == 'ETA: 00:05'

    def test_parse_progress_with_eta_in(self, downloader):
        """Тест парсинга ETA в формате 'in 00:01:12'."""
        line = "[download] 100% of  884.03MiB in 00:01:02"
        result = downloader._parse_progress(line)
        
        assert result is not None
        assert '00:01:02' in result[3]

    def test_parse_progress_invalid_line(self, downloader):
        """Тест с невалидной строкой."""
        line = "Invalid line without percentage"
        result = downloader._parse_progress(line)
        
        assert result is None

    def test_parse_progress_empty_line(self, downloader):
        """Тест с пустой строкой."""
        result = downloader._parse_progress('')
        assert result is None
        
        result = downloader._parse_progress(None)
        assert result is None

    def test_parse_progress_kib_speed(self, downloader):
        """Тест парсинга скорости в KiB/s."""
        line = "[download] 10.0% of   50.00MiB at  796.49KiB/s ETA 00:17"
        result = downloader._parse_progress(line)
        
        assert result is not None
        assert '796.49 KiB/s' in result[2]


class TestParsePhaseStatus:
    """Тесты парсинга фаз ffmpeg post-processing."""

    @pytest.fixture
    def downloader(self):
        config = Mock(spec=ConfigManager)
        config.get.side_effect = lambda key, default=None: {
            'DOWNLOAD_PATH': '/test/path',
            'YTDLP_PATH': '/test/yt-dlp.exe',
        }.get(key, default)
        return YouTubeDownloader(config, Mock(), Mock())

    def test_parse_phase_status_merger(self, downloader):
        line = '[Merger] Merging formats into "video.mp4"'
        assert downloader._parse_phase_status(line) == 'Слияние потоков (ffmpeg)...'

    def test_parse_phase_status_ffmpeg(self, downloader):
        line = '[ffmpeg] Something'
        assert downloader._parse_phase_status(line) == 'Обработка ffmpeg...'

    def test_parse_phase_status_ffmpeg_deleting_ignored(self, downloader):
        line = '[ffmpeg] Deleting original file'
        assert downloader._parse_phase_status(line) is None

    def test_parse_phase_status_sponsorblock(self, downloader):
        line = '[SponsorBlock] Removing sponsor segments'
        assert downloader._parse_phase_status(line) == 'SponsorBlock (ffmpeg)...'


class TestLogBuffer:
    """Тесты буфера логов."""

    @pytest.fixture
    def downloader(self):
        """Фикстура для создания downloader."""
        config = Mock(spec=ConfigManager)
        config.get.side_effect = lambda key, default=None: {
            'DOWNLOAD_PATH': '/test/path',
            'YTDLP_PATH': '/test/yt-dlp.exe'
        }.get(key, default)
        
        return YouTubeDownloader(config, Mock(), Mock())

    def test_log_appends_to_buffer(self, downloader):
        """Тест что _log добавляет сообщения в буфер."""
        downloader._log("Test message 1")
        downloader._log("Test message 2")
        
        assert len(downloader._logs_buffer) == 2
        assert "Test message 1" in downloader._logs_buffer
        assert "Test message 2" in downloader._logs_buffer

    def test_log_calls_callback(self, downloader):
        """Тест что _log вызывает callback."""
        callback = Mock()
        downloader.log_callback = callback
        
        downloader._log("Test message", 'info')
        
        callback.assert_called_once_with("Test message", 'info')

    def test_buffer_cleared_on_download_start(self, downloader):
        """Тест что буфер очищается перед загрузкой."""
        downloader._logs_buffer = ["old message"]
        
        # Симуляция начала загрузки
        downloader._cancelled = False
        downloader._logs_buffer = []
        
        assert downloader._logs_buffer == []


class TestDownloadValidation:
    """Тесты валидации перед загрузкой."""

    @pytest.fixture
    def downloader(self):
        """Фикстура для создания downloader."""
        config = Mock(spec=ConfigManager)
        config.get.side_effect = lambda key, default=None: {
            'DOWNLOAD_PATH': '/test/path',
            'YTDLP_PATH': '/test/yt-dlp.exe'
        }.get(key, default)
        
        return YouTubeDownloader(config, Mock(), Mock())

    def test_download_checks_path_exists(self, downloader):
        """Тест что проверяется существование пути."""
        with patch('core.downloader.ensure_download_directory', return_value=(False, 'Путь сохранения не существует')):
            with patch('core.downloader.os.path.exists', return_value=True):
                result = downloader.download('https://youtube.com/watch?v=test')

                assert result is False
                downloader.log_callback.assert_called()
                calls = downloader.log_callback.call_args_list
                error_called = any(
                    'не существует' in str(call) or 'Путь' in str(call)
                    for call in calls
                )
                assert error_called

    def test_download_checks_ytdlp_exists(self, downloader):
        """Тест что проверяется существование yt-dlp."""
        def mock_exists(path):
            if 'yt-dlp' in path:
                return False
            return True
        
        with patch('core.downloader.os.path.exists', side_effect=mock_exists):
            result = downloader.download('https://youtube.com/watch?v=test')
            
            assert result is False


class TestErrorHandling:
    """Тесты обработки ошибок."""

    @pytest.fixture
    def downloader(self):
        """Фикстура для создания downloader."""
        config = Mock(spec=ConfigManager)
        config.get.side_effect = lambda key, default=None: {
            'DOWNLOAD_PATH': '/test/path',
            'YTDLP_PATH': '/test/yt-dlp.exe'
        }.get(key, default)
        
        return YouTubeDownloader(config, Mock(), Mock())

    def test_error_logging_includes_details(self, downloader):
        """Тест что ошибки логируются с деталями."""
        # Симуляция ошибки
        error_msg = "Test error message"
        downloader._log(f"Ошибка: {error_msg}", 'error')
        
        assert any(error_msg in msg for msg in downloader._logs_buffer)

    def test_cancel_sets_flag(self, downloader):
        """Тест что cancel устанавливает флаг."""
        downloader.cancel()
        
        assert downloader._cancelled is True

    def test_cancel_kills_process(self, downloader):
        """Тест что cancel убивает дерево процессов."""
        mock_process = Mock()
        mock_process.pid = 4242
        downloader._process = mock_process

        with patch('core.downloader.os.name', 'nt'):
            with patch('core.downloader.subprocess.run') as mock_run:
                downloader.cancel()
                mock_run.assert_called_once()
                args = mock_run.call_args[0][0]
                assert args == ['taskkill', '/PID', '4242', '/T', '/F']

    def test_cancel_kills_process_posix(self, downloader):
        """На POSIX cancel вызывает process.kill()."""
        mock_process = Mock()
        mock_process.pid = 4242
        downloader._process = mock_process

        with patch('core.downloader.os.name', 'posix'):
            downloader.cancel()
            mock_process.kill.assert_called_once()

    def test_cancel_handles_exception(self, downloader):
        """Тест что cancel обрабатывает исключения."""
        mock_process = Mock()
        mock_process.pid = 4242
        downloader._process = mock_process

        with patch('core.downloader._terminate_process_tree', side_effect=Exception("Test exception")):
            downloader.cancel()

        assert downloader._cancelled is True
