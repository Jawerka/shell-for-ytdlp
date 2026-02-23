# -*- coding: utf-8 -*-
"""
Unit-тесты для модуля core/utils.py.

Тестирование функций:
- is_valid_url()
- get_clipboard_url()
- validate_url_for_ui()
- find_cookies_txt()
"""

import pytest
from unittest.mock import patch, MagicMock
import os

from core.utils import (
    is_valid_url,
    get_clipboard_url,
    validate_url_for_ui,
    find_cookies_txt,
)


class TestIsValidUrl:
    """Тесты для функции is_valid_url()."""

    def test_valid_youtube_url(self):
        """Проверка валидного YouTube URL."""
        # Используем mock для urlopen чтобы не делать реальные запросы
        with patch('core.utils.urlopen') as mock_urlopen:
            mock_response = MagicMock()
            mock_urlopen.return_value = mock_response
            result = is_valid_url('https://youtube.com/watch?v=abc123')
            assert result is True

    def test_valid_https_url(self):
        """Проверка валидного HTTPS URL."""
        with patch('core.utils.urlopen') as mock_urlopen:
            mock_response = MagicMock()
            mock_urlopen.return_value = mock_response
            result = is_valid_url('https://example.com')
            assert result is True

    def test_invalid_no_protocol(self):
        """Проверка URL без протокола."""
        result = is_valid_url('youtube.com/watch')
        assert result is False

    def test_invalid_empty_string(self):
        """Проверка пустой строки."""
        result = is_valid_url('')
        assert result is False

    def test_invalid_none(self):
        """Проверка None."""
        result = is_valid_url(None)
        assert result is False

    def test_invalid_whitespace(self):
        """Проверка строки из пробелов."""
        result = is_valid_url('   ')
        assert result is False

    def test_http_error_404(self):
        """Проверка обработки HTTP 404 ошибки."""
        from urllib.error import HTTPError
        with patch('core.utils.urlopen') as mock_urlopen:
            mock_urlopen.side_effect = HTTPError(
                url='http://example.com',
                code=404,
                msg='Not Found',
                hdrs={},
                fp=None
            )
            # 404 < 500, поэтому возвращаем True (yt-dlp попробует скачать)
            result = is_valid_url('http://example.com')
            assert result is True

    def test_http_error_500(self):
        """Проверка обработки HTTP 500 ошибки."""
        from urllib.error import HTTPError
        with patch('core.utils.urlopen') as mock_urlopen:
            mock_urlopen.side_effect = HTTPError(
                url='http://example.com',
                code=500,
                msg='Internal Server Error',
                hdrs={},
                fp=None
            )
            result = is_valid_url('http://example.com')
            assert result is False

    def test_url_error(self):
        """Проверка обработки URLError."""
        from urllib.error import URLError
        with patch('core.utils.urlopen') as mock_urlopen:
            mock_urlopen.side_effect = URLError('Network error')
            result = is_valid_url('http://example.com')
            assert result is False

    def test_timeout_error(self):
        """Проверка обработки таймаута."""
        import socket
        with patch('core.utils.urlopen') as mock_urlopen:
            mock_urlopen.side_effect = socket.timeout()
            result = is_valid_url('http://example.com')
            assert result is False


class TestGetClipboardUrl:
    """Тесты для функции get_clipboard_url()."""

    def test_valid_url_in_clipboard(self):
        """Проверка получения валидного URL из буфера обмена."""
        with patch('core.utils.pyperclip.paste') as mock_paste:
            mock_paste.return_value = 'https://youtube.com/watch?v=abc123'
            with patch('core.utils.is_valid_url') as mock_is_valid:
                mock_is_valid.return_value = True
                result = get_clipboard_url()
                assert result == 'https://youtube.com/watch?v=abc123'

    def test_invalid_url_in_clipboard(self):
        """Проверка получения невалидного URL из буфера обмена."""
        with patch('core.utils.pyperclip.paste') as mock_paste:
            mock_paste.return_value = 'not a url'
            with patch('core.utils.is_valid_url') as mock_is_valid:
                mock_is_valid.return_value = False
                result = get_clipboard_url()
                assert result is None

    def test_empty_clipboard(self):
        """Проверка пустого буфера обмена."""
        with patch('core.utils.pyperclip.paste') as mock_paste:
            mock_paste.return_value = ''
            result = get_clipboard_url()
            assert result is None

    def test_whitespace_clipboard(self):
        """Проверка буфера с пробелами."""
        with patch('core.utils.pyperclip.paste') as mock_paste:
            mock_paste.return_value = '   '
            result = get_clipboard_url()
            assert result is None

    def test_clipboard_exception(self):
        """Проверка обработки исключения при чтении буфера."""
        with patch('core.utils.pyperclip.paste') as mock_paste:
            mock_paste.side_effect = Exception('Clipboard error')
            result = get_clipboard_url()
            assert result is None


class TestValidateUrlForUi:
    """Тесты для функции validate_url_for_ui()."""

    def test_empty_url(self):
        """Проверка пустого URL."""
        is_valid, message = validate_url_for_ui('')
        assert is_valid is False
        assert message == "Введите URL"

    def test_no_protocol(self):
        """Проверка URL без протокола."""
        is_valid, message = validate_url_for_ui('youtube.com/watch')
        assert is_valid is False
        assert "http://" in message or "https://" in message

    def test_valid_url(self):
        """Проверка валидного URL."""
        with patch('core.utils.urlopen') as mock_urlopen:
            mock_response = MagicMock()
            mock_urlopen.return_value = mock_response
            is_valid, message = validate_url_for_ui('https://example.com')
            assert is_valid is True
            assert message == "Ссылка доступна"

    def test_http_error(self):
        """Проверка HTTP ошибки."""
        from urllib.error import HTTPError
        with patch('core.utils.urlopen') as mock_urlopen:
            mock_urlopen.side_effect = HTTPError(
                url='http://example.com',
                code=404,
                msg='Not Found',
                hdrs={},
                fp=None
            )
            is_valid, message = validate_url_for_ui('http://example.com')
            assert is_valid is True  # yt-dlp попробует скачать
            assert '404' in message

    def test_timeout(self):
        """Проверка таймаута."""
        import socket
        with patch('core.utils.urlopen') as mock_urlopen:
            mock_urlopen.side_effect = socket.timeout()
            is_valid, message = validate_url_for_ui('http://example.com')
            assert is_valid is False
            assert "таймаут" in message.lower()

    def test_url_error(self):
        """Проверка ошибки сети."""
        from urllib.error import URLError
        with patch('core.utils.urlopen') as mock_urlopen:
            mock_urlopen.side_effect = URLError('Network error')
            is_valid, message = validate_url_for_ui('http://example.com')
            assert is_valid is False
            assert "Ошибка сети" in message

    def test_value_error(self):
        """Проверка неверного формата URL."""
        with patch('core.utils.urlopen') as mock_urlopen:
            mock_urlopen.side_effect = ValueError('Invalid URL')
            is_valid, message = validate_url_for_ui('http://example.com')
            assert is_valid is False
            assert "Неверный формат" in message


class TestFindCookiesTxt:
    """Тесты для функции find_cookies_txt()."""

    def test_no_cookies_file(self):
        """Проверка отсутствия cookies.txt."""
        with patch('core.utils.os.walk') as mock_walk:
            mock_walk.return_value = []
            result = find_cookies_txt('/fake/path')
            assert result is None

    def test_single_cookies_file(self):
        """Проверка одного файла cookies.txt."""
        import ntpath
        with patch('core.utils.os.walk') as mock_walk:
            with patch('core.utils.os.path.join', ntpath.join):
                mock_walk.return_value = [
                    ('/fake/path', [], ['cookies.txt'])
                ]
                with patch('core.utils.os.path.getmtime') as mock_mtime:
                    mock_mtime.return_value = 1234567890
                    result = find_cookies_txt('/fake/path')
                    assert result is not None
                    assert 'cookies.txt' in result

    def test_multiple_cookies_files(self):
        """Проверка выбора последнего изменённого файла."""
        with patch('core.utils.os.walk') as mock_walk:
            mock_walk.return_value = [
                (r'C:\fake\path', [], ['cookies1.txt', 'cookies2.txt'])
            ]
            with patch('core.utils.os.path.getmtime') as mock_mtime:
                # cookies2.txt новее
                def get_mtime(path):
                    if 'cookies1' in path:
                        return 1234567890
                    return 1234567899
                mock_mtime.side_effect = get_mtime
                result = find_cookies_txt(r'C:\fake\path')
                assert result is not None
                assert 'cookies2.txt' in result

    def test_cookies_in_subdirectory(self):
        """Проверка поиска в поддиректории."""
        import ntpath
        with patch('core.utils.os.walk') as mock_walk:
            with patch('core.utils.os.path.join', ntpath.join):
                mock_walk.return_value = [
                    ('/fake/path', ['subdir'], []),
                    ('/fake/path/subdir', [], ['cookies.txt'])
                ]
                with patch('core.utils.os.path.getmtime') as mock_mtime:
                    mock_mtime.return_value = 1234567890
                    result = find_cookies_txt('/fake/path')
                    assert result is not None
                    assert 'cookies.txt' in result
                    assert 'subdir' in result
