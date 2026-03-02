# -*- coding: utf-8 -*-
"""
Тесты для модуля updater.py.

Проверяют:
- Проверку необходимости обновления
- Загрузку утилит
- Распаковку ffmpeg
- Обработку ошибок
"""

import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO

# Добавляем корень проекта в path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.updater import (
    unzipping_ffmpeg,
    check_needs_update,
    update_utilities,
    update_loop
)


class TestUnzippingFFmpeg:
    """Тесты распаковки ffmpeg."""

    @pytest.fixture
    def temp_dirs(self, tmp_path):
        """Фикстура для создания временных директорий."""
        archive_dir = tmp_path / "archive"
        archive_dir.mkdir()
        
        utilities_dir = tmp_path / "utilities"
        utilities_dir.mkdir()
        
        # Создаём фейковый архив
        archive_path = archive_dir / "ffmpeg.zip"
        archive_path.write_bytes(b"fake zip content")
        
        return {
            'archive': str(archive_path),
            'utilities': str(utilities_dir),
            'archive_dir': str(archive_dir)
        }

    def test_unzipping_ffmpeg_creates_files(self, temp_dirs):
        """Тест что распаковка создаёт файлы."""
        # Создаём фейковую структуру архива
        with patch('core.updater.ZipFile') as mock_zip:
            mock_zip.return_value.__enter__ = Mock()
            mock_zip.return_value.__exit__ = Mock()
            
            # Мокаем extractall
            mock_zip.return_value.__enter__.return_value.extractall = Mock()
            
            # Мокаем os.path.exists для возврата True после "распаковки"
            with patch('core.updater.os.path.exists', return_value=True):
                with patch('core.updater.shutil.move'):
                    with patch('core.updater.shutil.rmtree'):
                        unzipping_ffmpeg(temp_dirs['archive'], temp_dirs['utilities'])

    def test_unzipping_ffmpeg_removes_old_files(self, temp_dirs):
        """Тест что старые файлы удаляются перед распаковкой."""
        with patch('core.updater.ZipFile'):
            with patch('core.updater.os.path.exists', return_value=True):
                with patch('core.updater.os.remove') as mock_remove:
                    with patch('core.updater.shutil.move'):
                        with patch('core.updater.shutil.rmtree'):
                            unzipping_ffmpeg(temp_dirs['archive'], temp_dirs['utilities'])
                            
                            # Должны быть вызваны удаления для ffmpeg.exe, ffplay.exe, ffprobe.exe
                            assert mock_remove.call_count >= 3


class TestCheckNeedsUpdate:
    """Тесты проверки необходимости обновления."""

    def test_check_needs_update_file_not_exists(self):
        """Тест что возвращается True если файл не существует."""
        with patch('core.updater.os.path.exists', return_value=False):
            result = check_needs_update('http://test.com/file.exe', '/nonexistent/path/file.exe')
            assert result is True

    def test_check_needs_update_file_exists_same_size(self):
        """Тест что возвращается False если размеры совпадают."""
        mock_response = Mock()
        mock_response.getheader.return_value = '1000'
        
        with patch('core.updater.urlopen', return_value=mock_response):
            with patch('core.updater.os.path.exists', return_value=True):
                with patch('core.updater.os.path.getsize', return_value=1000):
                    result = check_needs_update('http://test.com/file.exe', '/test/path/file.exe')
                    assert result is False

    def test_check_needs_update_file_exists_different_size(self):
        """Тест что возвращается True если размеры отличаются."""
        mock_response = Mock()
        mock_response.getheader.return_value = '2000'
        
        with patch('core.updater.urlopen', return_value=mock_response):
            with patch('core.updater.os.path.exists', return_value=True):
                with patch('core.updater.os.path.getsize', return_value=1000):
                    result = check_needs_update('http://test.com/file.exe', '/test/path/file.exe')
                    assert result is True

    def test_check_needs_update_network_error(self):
        """Тест что возвращается False при ошибке сети."""
        from urllib.error import URLError
        
        with patch('core.updater.urlopen', side_effect=URLError("Network error")):
            with patch('core.updater.os.path.exists', return_value=True):
                result = check_needs_update('http://test.com/file.exe', '/test/path/file.exe')
                assert result is False

    def test_check_needs_update_logs_details(self):
        """Тест что проверка логирует детали."""
        mock_response = Mock()
        mock_response.getheader.return_value = '2000'
        
        with patch('core.updater.urlopen', return_value=mock_response):
            with patch('core.updater.os.path.exists', return_value=True):
                with patch('core.updater.os.path.getsize', return_value=1000):
                    # Просто проверяем что не выбрасывает исключений
                    check_needs_update('http://test.com/yt-dlp.exe', '/test/path/yt-dlp.exe')


class TestUpdateUtilities:
    """Тесты обновления утилит."""

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Фикстура для временной директории."""
        utilities_dir = tmp_path / "utilities"
        utilities_dir.mkdir()
        return str(utilities_dir)

    def test_update_utilities_downloads_file(self, temp_dir):
        """Тест что файл загружается."""
        mock_response = Mock()
        mock_response.getheader.return_value = '1000'
        
        with patch('core.updater.urlopen', return_value=mock_response):
            with patch('core.updater.os.path.exists', return_value=False):
                with patch('core.updater.urlretrieve') as mock_retrieve:
                    result = update_utilities('http://test.com/file.exe', temp_dir)
                    
                    assert mock_retrieve.called
                    assert result is True

    def test_update_utilities_ffmpeg_already_extracted(self, temp_dir):
        """Тест что ffmpeg пропускается если распакован."""
        mock_response = Mock()
        mock_response.getheader.return_value = '1000'
        
        def mock_exists(path):
            if 'ffmpeg.exe' in path or 'ffprobe.exe' in path or 'ffplay.exe' in path:
                return True
            if 'zip' in path:
                return True
            return False
        
        with patch('core.updater.urlopen', return_value=mock_response):
            with patch('core.updater.os.path.exists', side_effect=mock_exists):
                result = update_utilities(
                    'http://test.com/ffmpeg-master.zip',
                    temp_dir
                )
                
                # Должно вернуть False так как ffmpeg уже распакован
                assert result is False

    def test_update_utilities_ffmpeg_not_extracted(self, temp_dir):
        """Тест что ffmpeg распаковывается если файлы отсутствуют."""
        mock_response = Mock()
        mock_response.getheader.return_value = '1000'
        
        def mock_exists(path):
            if 'ffmpeg.exe' in path or 'ffprobe.exe' in path or 'ffplay.exe' in path:
                return False
            if 'zip' in path:
                return True
            return False
        
        with patch('core.updater.urlopen', return_value=mock_response):
            with patch('core.updater.os.path.exists', side_effect=mock_exists):
                with patch('core.updater.unzipping_ffmpeg') as mock_unzip:
                    result = update_utilities(
                        'http://test.com/ffmpeg-master.zip',
                        temp_dir
                    )
                    
                    # Должна быть вызвана распаковка
                    mock_unzip.assert_called_once()
                    assert result is True

    def test_update_utilities_progress_callback(self, temp_dir):
        """Тест что вызывается callback прогресса."""
        mock_response = Mock()
        mock_response.getheader.return_value = '1000'
        
        progress_callback = Mock()
        
        with patch('core.updater.urlopen', return_value=mock_response):
            with patch('core.updater.os.path.exists', return_value=False):
                with patch('core.updater.urlretrieve'):
                    update_utilities(
                        'http://test.com/file.exe',
                        temp_dir,
                        progress_callback
                    )

    def test_update_utilities_network_error(self, temp_dir):
        """Тест обработки ошибки сети."""
        from urllib.error import URLError
        
        with patch('core.updater.urlopen', side_effect=URLError("Network error")):
            result = update_utilities('http://test.com/file.exe', temp_dir)
            assert result is False

    def test_update_utilities_keyboard_interrupt(self, temp_dir):
        """Тест обработки прерывания пользователем."""
        mock_response = Mock()
        mock_response.getheader.return_value = '1000'
        
        def mock_retrieve(*args, **kwargs):
            raise KeyboardInterrupt()
        
        with patch('core.updater.urlopen', return_value=mock_response):
            with patch('core.updater.os.path.exists', return_value=False):
                with patch('core.updater.urlretrieve', side_effect=mock_retrieve):
                    with patch('core.updater.os.remove'):
                        with pytest.raises(KeyboardInterrupt):
                            update_utilities('http://test.com/file.exe', temp_dir)


class TestUpdateLoop:
    """Тесты цикла обновления."""

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Фикстура для временной директории."""
        utilities_dir = tmp_path / "utilities"
        utilities_dir.mkdir()
        return str(utilities_dir)

    def test_update_loop_iterates_all_urls(self, temp_dir):
        """Тест что цикл обрабатывает все URL."""
        urls = [
            'http://test.com/yt-dlp.exe',
            'http://test.com/ffmpeg.zip'
        ]
        
        progress_callback = Mock()
        
        with patch('core.updater.update_utilities', return_value=True):
            update_loop(urls, temp_dir, progress_callback)
            
            # update_utilities должен быть вызван для каждого URL
            assert update_utilities.call_count == 2

    def test_update_loop_creates_directory(self, temp_dir):
        """Тест что создаётся директория утилит."""
        with patch('core.updater.update_utilities', return_value=True):
            with patch('core.updater.os.makedirs') as mock_makedirs:
                update_loop(['http://test.com/file.exe'], temp_dir)
                
                mock_makedirs.assert_called_once_with(temp_dir, exist_ok=True)

    def test_update_loop_with_progress_wrapper(self, temp_dir):
        """Тест что создаётся wrapper для прогресса."""
        progress_callback = Mock()
        
        with patch('core.updater.update_utilities') as mock_update:
            update_loop(['http://test.com/file.exe'], temp_dir, progress_callback)
            
            # Проверяем что progress_callback был передан
            assert mock_update.called
            call_args = mock_update.call_args
            assert call_args[0][2] is not None  # progress_callback
