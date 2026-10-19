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
from zipfile import ZipFile, BadZipFile

# Добавляем корень проекта в path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.updater import (
    unzipping_ffmpeg,
    check_needs_update,
    update_utilities,
    update_loop,
    _parse_content_length,
    ffmpeg_extracted,
    FFMPEG_FILE_LIST,
)


def _write_ffmpeg_zip(archive_path, files=('ffmpeg.exe', 'ffplay.exe', 'ffprobe.exe')):
    with ZipFile(archive_path, 'w') as zf:
        for name in files:
            zf.writestr(f'ffmpeg-master/bin/{name}', b'bin')


class TestUnzippingFFmpeg:
    """Тесты распаковки ffmpeg."""

    def test_unzipping_ffmpeg_replaces_binaries(self, tmp_path):
        utilities = tmp_path / 'utilities'
        utilities.mkdir()
        (utilities / 'ffmpeg.exe').write_bytes(b'old')
        archive = tmp_path / 'ffmpeg-master.zip'
        _write_ffmpeg_zip(archive)

        unzipping_ffmpeg(str(archive), str(utilities))

        assert (utilities / 'ffmpeg.exe').read_bytes() == b'bin'
        assert all((utilities / name).exists() for name in FFMPEG_FILE_LIST)

    def test_unzipping_ffmpeg_keeps_old_on_bad_zip(self, tmp_path):
        utilities = tmp_path / 'utilities'
        utilities.mkdir()
        (utilities / 'ffmpeg.exe').write_bytes(b'old')
        archive = tmp_path / 'ffmpeg-master.zip'
        archive.write_bytes(b'not a zip')

        with pytest.raises(BadZipFile):
            unzipping_ffmpeg(str(archive), str(utilities))

        assert (utilities / 'ffmpeg.exe').read_bytes() == b'old'

    def test_unzipping_ffmpeg_keeps_old_when_archive_incomplete(self, tmp_path):
        utilities = tmp_path / 'utilities'
        utilities.mkdir()
        (utilities / 'ffmpeg.exe').write_bytes(b'old')
        archive = tmp_path / 'ffmpeg-master.zip'
        _write_ffmpeg_zip(archive, files=('ffmpeg.exe',))

        with pytest.raises(BadZipFile):
            unzipping_ffmpeg(str(archive), str(utilities))

        assert (utilities / 'ffmpeg.exe').read_bytes() == b'old'
        assert not (utilities / 'ffprobe.exe').exists()

    def test_unzipping_ffmpeg_rejects_path_traversal(self, tmp_path):
        utilities = tmp_path / 'utilities'
        utilities.mkdir()
        (utilities / 'ffmpeg.exe').write_bytes(b'old')
        archive = tmp_path / 'ffmpeg-master.zip'
        with ZipFile(archive, 'w') as zf:
            zf.writestr('ffmpeg-master/bin/ffmpeg.exe', b'new')
            zf.writestr('../evil.exe', b'evil')

        with pytest.raises(BadZipFile):
            unzipping_ffmpeg(str(archive), str(utilities))

        assert (utilities / 'ffmpeg.exe').read_bytes() == b'old'
        assert not (tmp_path / 'evil.exe').exists()


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


    def test_check_needs_update_missing_content_length(self):
        """При отсутствии Content-Length безопаснее обновиться."""
        mock_response = Mock()
        mock_response.getheader.return_value = None

        with patch('core.updater.urlopen', return_value=mock_response):
            with patch('core.updater.os.path.exists', return_value=True):
                with patch('core.updater.os.path.getsize', return_value=1000):
                    result = check_needs_update('http://test.com/file.exe', '/test/path/file.exe')
                    assert result is True
        mock_response.close.assert_called_once()

    def test_parse_content_length_none(self):
        """Тест безопасного парсинга отсутствующего Content-Length."""
        mock_response = Mock()
        mock_response.getheader.return_value = None
        assert _parse_content_length(mock_response) is None

    def test_parse_content_length_valid(self):
        """Тест парсинга валидного Content-Length."""
        mock_response = Mock()
        mock_response.getheader.return_value = ' 12345 '
        assert _parse_content_length(mock_response) == 12345


class TestFFmpegExtracted:
    """Тесты проверки распакованного ffmpeg."""

    def test_ffmpeg_extracted_all_present(self, tmp_path):
        for name in ('ffmpeg.exe', 'ffplay.exe', 'ffprobe.exe'):
            (tmp_path / name).write_bytes(b'x')
        assert ffmpeg_extracted(str(tmp_path)) is True

    def test_ffmpeg_extracted_missing_one(self, tmp_path):
        (tmp_path / 'ffmpeg.exe').write_bytes(b'x')
        assert ffmpeg_extracted(str(tmp_path)) is False


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
                with patch('core.updater.download_file', return_value=True) as mock_download:
                    result = update_utilities('http://test.com/file.exe', temp_dir)

                    mock_download.assert_called_once()
                    assert result is True

    def test_interrupted_update_keeps_old_binary(self, temp_dir):
        """Прерванное обновление не должно удалять рабочий yt-dlp."""
        save_path = os.path.join(temp_dir, 'yt-dlp.exe')
        with open(save_path, 'wb') as f:
            f.write(b'old')

        mock_response = Mock()
        mock_response.getheader.return_value = '999'

        with patch('core.updater.urlopen', return_value=mock_response):
            with patch('core.updater.download_file', side_effect=OSError('interrupted')):
                result = update_utilities('http://test.com/yt-dlp.exe', temp_dir)

        assert result is False
        with open(save_path, 'rb') as f:
            assert f.read() == b'old'

    def test_update_utilities_cancelled(self, temp_dir):
        """При отмене загрузка возвращает False и не распаковывает ffmpeg."""
        mock_response = Mock()
        mock_response.getheader.return_value = '1000'

        with patch('core.updater.urlopen', return_value=mock_response):
            with patch('core.updater.os.path.exists', return_value=False):
                with patch('core.updater.download_file', return_value=False):
                    with patch('core.updater._try_unzip_ffmpeg') as mock_unzip:
                        result = update_utilities('http://test.com/ffmpeg-master.zip', temp_dir)

        assert result is False
        mock_unzip.assert_not_called()

    def test_update_utilities_passes_cancel_event(self, temp_dir):
        """Событие отмены передаётся в потоковую загрузку."""
        mock_response = Mock()
        mock_response.getheader.return_value = '1000'
        cancel_event = Mock()

        with patch('core.updater.urlopen', return_value=mock_response):
            with patch('core.updater.os.path.exists', return_value=False):
                with patch('core.updater.download_file', return_value=True) as mock_download:
                    update_utilities(
                        'http://test.com/file.exe',
                        temp_dir,
                        cancel_event=cancel_event,
                    )

        assert mock_download.call_args[0][3] is cancel_event

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
        """Тест что ffmpeg распаковывается если файлы отсутствуют (нет zip)."""
        mock_response = Mock()
        mock_response.getheader.return_value = '1000'

        with patch('core.updater.urlopen', return_value=mock_response):
            with patch('core.updater.os.path.exists', return_value=False):
                with patch('core.updater.download_file', return_value=True):
                    with patch('core.updater._try_unzip_ffmpeg', return_value=True) as mock_unzip:
                        result = update_utilities(
                            'http://test.com/ffmpeg-master.zip',
                            temp_dir
                        )

                        mock_unzip.assert_called_once()
                        assert result is True

    def test_update_utilities_ffmpeg_zip_exists_not_extracted(self, temp_dir):
        """Тест: zip есть, exe нет — распаковка без повторной загрузки."""
        mock_response = Mock()
        mock_response.getheader.return_value = '1000'
        zip_path = os.path.join(temp_dir, 'ffmpeg-master.zip')

        def mock_exists(path):
            if path == zip_path:
                return True
            if path.endswith(('.exe',)):
                return False
            return False

        with patch('core.updater.urlopen', return_value=mock_response):
            with patch('core.updater.os.path.exists', side_effect=mock_exists):
                with patch('core.updater.os.path.getsize', return_value=1000):
                    with patch('core.updater.download_file') as mock_download:
                        with patch('core.updater._try_unzip_ffmpeg', return_value=True) as mock_unzip:
                            result = update_utilities(
                                'http://test.com/ffmpeg-master.zip',
                                temp_dir
                            )

                            mock_unzip.assert_called_once_with(zip_path, temp_dir)
                            mock_download.assert_not_called()
                            assert result is True

    def test_update_utilities_corrupt_ffmpeg_zip_redownloads(self, temp_dir):
        """Тест: битый zip без exe — повторная загрузка без предварительного удаления."""
        mock_response = Mock()
        mock_response.getheader.return_value = '1000'
        zip_path = os.path.join(temp_dir, 'ffmpeg-master.zip')
        (open(zip_path, 'wb').close())

        def mock_exists(path):
            if path == zip_path:
                return True
            return False

        with patch('core.updater.urlopen', return_value=mock_response):
            with patch('core.updater.os.path.exists', side_effect=mock_exists):
                with patch('core.updater.os.path.getsize', return_value=9):
                    with patch('core.updater.os.remove') as mock_remove:
                        with patch('core.updater.download_file', return_value=True) as mock_download:
                            with patch('core.updater._try_unzip_ffmpeg', side_effect=[False, True]):
                                result = update_utilities(
                                    'http://test.com/ffmpeg-master.zip',
                                    temp_dir
                                )

                                mock_remove.assert_not_called()
                                mock_download.assert_called_once()
                                assert result is True

    def test_update_utilities_missing_content_length_no_exception(self, temp_dir):
        """Тест что отсутствие Content-Length не вызывает исключение."""
        mock_response = Mock()
        mock_response.getheader.return_value = None

        with patch('core.updater.urlopen', return_value=mock_response):
            with patch('core.updater.os.path.exists', return_value=False):
                with patch('core.updater.download_file', return_value=True):
                    result = update_utilities('http://test.com/file.exe', temp_dir)
                    assert result is True

    def test_update_utilities_progress_callback(self, temp_dir):
        """Тест что callback прогресса передаётся в загрузку."""
        mock_response = Mock()
        mock_response.getheader.return_value = '1000'

        progress_callback = Mock()

        with patch('core.updater.urlopen', return_value=mock_response):
            with patch('core.updater.os.path.exists', return_value=False):
                with patch('core.updater.download_file', return_value=True) as mock_download:
                    update_utilities(
                        'http://test.com/file.exe',
                        temp_dir,
                        progress_callback
                    )

        assert mock_download.call_args[0][2] is progress_callback

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

        with patch('core.updater.urlopen', return_value=mock_response):
            with patch('core.updater.os.path.exists', return_value=False):
                with patch('core.updater.download_file', side_effect=KeyboardInterrupt()):
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
        
        with patch('core.updater.update_utilities', return_value=True) as mock_update:
            update_loop(urls, temp_dir, progress_callback)

            assert mock_update.call_count == 2

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
