# -*- coding: utf-8 -*-
"""Тесты для core/download_handlers.py."""

import os
import sys
from unittest.mock import Mock, patch

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.download_handlers import (
    DownloadHints,
    HandlerError,
    can_handle_by_plugins,
    get_plugin_domains,
    resolve_download_hints,
)

GG_VOD_URL = 'https://goodgame.ru/vods/6/2026-06-27T18:52:42Z'


class TestResolveDownloadHints:
    def test_passthrough_youtube_url(self):
        config = Mock()
        config.get.return_value = True
        hints = resolve_download_hints('https://youtube.com/watch?v=test', config)
        assert hints.url == 'https://youtube.com/watch?v=test'
        assert hints.format_selector is None

    @patch('core.plugins.goodgame_vod.resolve_goodgame_vod')
    def test_goodgame_vod_enabled(self, mock_resolve):
        mock_resolve.return_value = (
            'https://storage3.goodgame.ru/hls_vod/test/index.m3u8',
            'Test Stream',
            '2026-06-27T18:52:42Z',
        )
        config = Mock()
        config.get.side_effect = lambda key, default=None: {
            'ENABLE_GOODGAME_VOD_HANDLER': True,
        }.get(key, default)

        hints = resolve_download_hints(GG_VOD_URL, config)

        assert hints.url.endswith('index.m3u8')
        assert hints.format_selector == '0'
        assert hints.referer == 'https://goodgame.ru/'
        assert hints.merge_output_format == 'mp4'
        assert 'Test Stream' in hints.output_template
        assert hints.log_title == 'Test Stream'

    def test_goodgame_vod_disabled_passthrough(self):
        config = Mock()
        config.get.side_effect = lambda key, default=None: {
            'ENABLE_GOODGAME_VOD_HANDLER': False,
        }.get(key, default)

        hints = resolve_download_hints(GG_VOD_URL, config)

        assert hints.url == GG_VOD_URL
        assert hints.format_selector is None

    @patch('core.plugins.goodgame_vod.resolve_goodgame_vod')
    def test_handler_error_propagates(self, mock_resolve):
        from core.plugins.goodgame_vod import GoodGameError

        mock_resolve.side_effect = GoodGameError('Запись GoodGame не найдена')
        config = Mock()
        config.get.return_value = True

        with pytest.raises(HandlerError, match='не найдена'):
            resolve_download_hints(GG_VOD_URL, config)


class TestPluginDomains:
    def test_domains_when_enabled(self):
        config = Mock()
        config.get.return_value = True
        domains = get_plugin_domains(config)
        assert 'goodgame.ru' in domains
        assert 'www.goodgame.ru' in domains

    def test_domains_when_disabled(self):
        config = Mock()
        config.get.side_effect = lambda key, default=None: {
            'ENABLE_GOODGAME_VOD_HANDLER': False,
        }.get(key, default)
        domains = get_plugin_domains(config)
        assert domains == []


class TestCanHandleByPlugins:
    def test_goodgame_vod_url(self):
        assert can_handle_by_plugins(GG_VOD_URL) is True

    def test_youtube_url(self):
        assert can_handle_by_plugins('https://youtube.com/watch?v=test') is False
