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
from unittest.mock import patch, MagicMock, Mock
import os

from core.utils import (
    is_valid_url,
    get_clipboard_url,
    extract_video_url,
    validate_url_for_ui,
    find_cookies_txt,
    strip_youtube_playlist_params,
    download_file,
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
        with patch('core.utils.pyperclip.paste') as mock_paste:
            mock_paste.return_value = 'https://www.youtube.com/watch?v=abc1234567'
            result = get_clipboard_url()
            assert result == 'https://www.youtube.com/watch?v=abc1234567'

    def test_invalid_url_in_clipboard(self):
        with patch('core.utils.pyperclip.paste') as mock_paste:
            mock_paste.return_value = 'not a url at all here'
            result = get_clipboard_url()
            assert result is None

    def test_empty_clipboard(self):
        with patch('core.utils.pyperclip.paste') as mock_paste:
            mock_paste.return_value = ''
            result = get_clipboard_url()
            assert result is None

    def test_whitespace_clipboard(self):
        with patch('core.utils.pyperclip.paste') as mock_paste:
            mock_paste.return_value = '   '
            result = get_clipboard_url()
            assert result is None

    def test_clipboard_exception(self):
        with patch('core.utils.pyperclip.paste') as mock_paste:
            mock_paste.side_effect = Exception('Clipboard error')
            result = get_clipboard_url()
            assert result is None

    def test_no_http_request(self):
        with patch('core.utils.pyperclip.paste') as mock_paste:
            mock_paste.return_value = 'https://www.youtube.com/watch?v=abc1234567'
            with patch('core.utils.urlopen') as mock_urlopen:
                result = get_clipboard_url()
                assert result is not None
                mock_urlopen.assert_not_called()


class TestExtractVideoUrl:
    """Тесты для extract_video_url()."""

    def test_plain_https_url(self):
        url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        assert extract_video_url(url) == url

    def test_url_in_quotes(self):
        assert extract_video_url(
            '"https://www.youtube.com/watch?v=dQw4w9WgXcQ"'
        ) == 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'

    def test_url_with_trailing_period(self):
        result = extract_video_url('https://www.youtube.com/watch?v=dQw4w9WgXcQ.')
        assert result == 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'

    def test_url_without_protocol(self):
        result = extract_video_url('youtube.com/watch?v=dQw4w9WgXcQ')
        assert result == 'https://youtube.com/watch?v=dQw4w9WgXcQ'

    def test_url_embedded_in_text(self):
        result = extract_video_url('Смотри https://youtu.be/dQw4w9WgXcQ сейчас')
        assert result == 'https://youtu.be/dQw4w9WgXcQ'

    def test_multiline_second_line(self):
        text = "intro\nhttps://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert extract_video_url(text) == 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'

    def test_unsupported_domain(self):
        assert extract_video_url('https://example.com/video') is None


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

    def test_valid_url_without_network(self):
        """Валидация не делает сетевых запросов."""
        with patch('core.utils.urlopen') as mock_urlopen:
            is_valid, message = validate_url_for_ui('https://example.com?a=1&b=2')
            assert is_valid is True
            assert message == "URL принят"
            mock_urlopen.assert_not_called()

    @pytest.mark.parametrize('url', ['https://', 'https:///path'])
    def test_url_without_host(self, url):
        is_valid, message = validate_url_for_ui(url)
        assert is_valid is False
        assert "хост" in message

    def test_malformed_url_does_not_raise(self):
        is_valid, message = validate_url_for_ui('http://[::1')
        assert is_valid is False
        assert "формат" in message

    @pytest.mark.parametrize('url', ['https://example.com:bad/', 'https://example.com:99999/'])
    def test_invalid_port(self, url):
        is_valid, message = validate_url_for_ui(url)
        assert is_valid is False
        assert "формат" in message

    def test_normal_url_with_host(self):
        is_valid, message = validate_url_for_ui('https://example.com/path?x=1')
        assert is_valid is True


class TestStripYoutubePlaylistParams:
    def test_watch_keeps_other_params(self):
        url = 'https://youtube.com/watch?v=abc&list=PL1&index=3&t=10s'
        assert strip_youtube_playlist_params(url) == 'https://youtube.com/watch?v=abc&t=10s'

    def test_playlist_url_is_untouched(self):
        url = 'https://youtube.com/playlist?list=PL1'
        assert strip_youtube_playlist_params(url) == url

    def test_non_youtube_signed_url_is_untouched(self):
        url = 'https://cdn.example.com/v.mp4?token=a&sig=b%2B&expires=1'
        assert strip_youtube_playlist_params(url) == url


class TestDownloadFile:
    def test_writes_and_replaces_atomically(self, tmp_path):
        dest = tmp_path / 'file.bin'
        response = MagicMock()
        response.getheader.return_value = '5'
        response.read.side_effect = [b'abc', b'de', b'']

        with patch('core.utils.urlopen', return_value=response):
            assert download_file('http://example.com/file.bin', str(dest)) is True

        assert dest.read_bytes() == b'abcde'
        assert not (tmp_path / 'file.bin.part').exists()
        response.close.assert_called_once()

    def test_cancel_removes_partial_file(self, tmp_path):
        dest = tmp_path / 'file.bin'
        response = MagicMock()
        response.getheader.return_value = '100'
        response.read.return_value = b'x'
        cancel_event = Mock()
        cancel_event.is_set.side_effect = [False, True]

        with patch('core.utils.urlopen', return_value=response):
            assert download_file(
                'http://example.com/file.bin', str(dest), cancel_event=cancel_event
            ) is False

        assert not dest.exists()
        assert not (tmp_path / 'file.bin.part').exists()

    def test_short_response_is_an_error(self, tmp_path):
        dest = tmp_path / 'file.bin'
        response = MagicMock()
        response.getheader.return_value = '4'
        response.read.side_effect = [b'a', b'']

        with patch('core.utils.urlopen', return_value=response):
            with pytest.raises(OSError):
                download_file('http://example.com/file.bin', str(dest))

        assert not dest.exists()
        assert not (tmp_path / 'file.bin.part').exists()

    def test_zero_content_length_is_an_error(self, tmp_path):
        dest = tmp_path / 'file.bin'
        response = MagicMock()
        response.getheader.return_value = '0'
        response.read.return_value = b''

        with patch('core.utils.urlopen', return_value=response):
            with pytest.raises(OSError):
                download_file('http://example.com/file.bin', str(dest))

        assert not dest.exists()
        assert not (tmp_path / 'file.bin.part').exists()

    def test_unknown_length_accepts_received_bytes(self, tmp_path):
        dest = tmp_path / 'file.bin'
        response = MagicMock()
        response.getheader.return_value = None
        response.read.side_effect = [b'abc', b'']

        with patch('core.utils.urlopen', return_value=response):
            assert download_file('http://example.com/file.bin', str(dest)) is True

        assert dest.read_bytes() == b'abc'


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
        import ntpath
        with patch('core.utils.os.walk') as mock_walk:
            with patch('core.utils.os.path.join', ntpath.join):
                mock_walk.return_value = [
                    (r'C:\fake\path\older', [], ['cookies.txt']),
                    (r'C:\fake\path\newer', [], ['cookies.txt']),
                ]
                with patch('core.utils.os.path.getmtime') as mock_mtime:
                    def get_mtime(path):
                        if 'older' in path:
                            return 1234567890
                        return 1234567899
                    mock_mtime.side_effect = get_mtime
                    result = find_cookies_txt(r'C:\fake\path')
                    assert result is not None
                    assert 'newer' in result

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


class TestIsYoutubeUrl:
    def test_youtube_watch(self):
        from core.utils import is_youtube_url
        assert is_youtube_url('https://www.youtube.com/watch?v=abc') is True

    def test_youtu_be(self):
        from core.utils import is_youtube_url
        assert is_youtube_url('https://youtu.be/abc123') is True

    def test_goodgame_not_youtube(self):
        from core.utils import is_youtube_url
        assert is_youtube_url('https://goodgame.ru/vods/6/2026-06-27T18:52:42Z') is False

    def test_vk_not_youtube(self):
        from core.utils import is_youtube_url
        assert is_youtube_url('https://vk.com/video-1_2') is False


class TestIsSupportedVideoUrl:
    def test_youtube_url(self):
        from core.utils import is_supported_video_url
        assert is_supported_video_url('https://www.youtube.com/watch?v=abc') is True

    def test_youtu_be(self):
        from core.utils import is_supported_video_url
        assert is_supported_video_url('https://youtu.be/abc123') is True

    def test_unknown_domain(self):
        from core.utils import is_supported_video_url
        assert is_supported_video_url('https://unknown.example/video') is False

    def test_no_protocol(self):
        from core.utils import is_supported_video_url
        assert is_supported_video_url('youtube.com/watch?v=abc') is False

    def test_goodgame_vod_without_config(self):
        from core.utils import is_supported_video_url
        url = 'https://goodgame.ru/vods/6/2026-06-27T18:52:42Z'
        assert is_supported_video_url(url) is True

    def test_goodgame_domain_with_config_enabled(self):
        from core.utils import is_supported_video_url
        from unittest.mock import Mock

        config = Mock()
        config.get.return_value = True
        url = 'https://goodgame.ru/channel/123'
        assert is_supported_video_url(url, config) is True

    def test_goodgame_domain_with_config_disabled(self):
        from core.utils import is_supported_video_url
        from unittest.mock import Mock

        config = Mock()
        config.get.side_effect = lambda key, default=None: {
            'ENABLE_GOODGAME_VOD_HANDLER': False,
        }.get(key, default)
        url = 'https://goodgame.ru/channel/123'
        assert is_supported_video_url(url, config) is False


class TestNormalizePathForDisplay:
    def test_forward_slashes_to_backslashes(self):
        from core.utils import normalize_path_for_display
        assert normalize_path_for_display('C:/Users/Downloads') == 'C:\\Users\\Downloads'

    def test_empty_path(self):
        from core.utils import normalize_path_for_display
        assert normalize_path_for_display('') == ''

    def test_already_windows_path(self):
        from core.utils import normalize_path_for_display
        path = 'C:\\Users\\Downloads'
        assert normalize_path_for_display(path) == path
