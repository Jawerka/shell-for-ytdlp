# -*- coding: utf-8 -*-
"""Тесты для плагина core/plugins/goodgame_vod.py."""

import json
import os
import sys
from io import BytesIO
from unittest.mock import Mock, patch

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.plugins.goodgame_vod import (
    GoodGameError,
    GoodGameVodHandler,
    is_goodgame_vod_url,
    parse_goodgame_vod_url,
    resolve_goodgame_vod,
)

GG_VOD_URL = 'https://goodgame.ru/vods/6/2026-06-27T18:52:42Z'
MODDATE = '2026-06-27T18:52:42Z'

SAMPLE_API_RESPONSE = {
    'vods': [
        {
            'title': 'Test Stream Title',
            'moddate': MODDATE,
            'm3u8path': 'https://storage3.goodgame.ru/hls_vod/test/index.m3u8',
            'mp4path': 'https://storage3.goodgame.ru/vod/test/6.mp4',
        }
    ]
}


class TestParseGoodgameVodUrl:
    def test_valid_url(self):
        assert parse_goodgame_vod_url(GG_VOD_URL) == ('6', MODDATE)

    def test_www_prefix(self):
        url = f'https://www.goodgame.ru/vods/6/{MODDATE}'
        assert parse_goodgame_vod_url(url) == ('6', MODDATE)

    def test_invalid_url(self):
        assert parse_goodgame_vod_url('https://youtube.com/watch?v=test') is None

    def test_is_goodgame_vod_url(self):
        assert is_goodgame_vod_url(GG_VOD_URL) is True
        assert is_goodgame_vod_url('https://goodgame.ru/Miker') is False


class TestResolveGoodgameVod:
    def _mock_urlopen(self, data: dict):
        payload = json.dumps(data).encode('utf-8')
        mock_response = Mock()
        mock_response.read.return_value = payload
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        return mock_response

    @patch('core.plugins.goodgame_vod.urlopen')
    def test_resolve_success_m3u8(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_urlopen(SAMPLE_API_RESPONSE)

        media_url, title, moddate = resolve_goodgame_vod(GG_VOD_URL)

        assert media_url.endswith('index.m3u8')
        assert title == 'Test Stream Title'
        assert moddate == MODDATE

    @patch('core.plugins.goodgame_vod.urlopen')
    def test_resolve_fallback_mp4(self, mock_urlopen):
        data = {
            'vods': [{
                'title': 'No HLS',
                'moddate': MODDATE,
                'm3u8path': '',
                'mp4path': 'https://storage3.goodgame.ru/vod/test/6.mp4',
            }]
        }
        mock_urlopen.return_value = self._mock_urlopen(data)

        media_url, title, _ = resolve_goodgame_vod(GG_VOD_URL)

        assert media_url.endswith('6.mp4')
        assert title == 'No HLS'

    @patch('core.plugins.goodgame_vod.urlopen')
    def test_record_not_found(self, mock_urlopen):
        data = {'vods': [{'title': 'Other', 'moddate': '2020-01-01T00:00:00Z', 'm3u8path': 'x'}]}
        mock_urlopen.return_value = self._mock_urlopen(data)

        with pytest.raises(GoodGameError, match='не найдена'):
            resolve_goodgame_vod(GG_VOD_URL)

    def test_invalid_url_raises(self):
        with pytest.raises(GoodGameError, match='Неверный URL'):
            resolve_goodgame_vod('https://youtube.com/watch?v=test')


class TestGoodGameVodHandler:
    @patch('core.plugins.goodgame_vod.resolve_goodgame_vod')
    def test_prepare_returns_hints(self, mock_resolve):
        mock_resolve.return_value = (
            'https://storage3.goodgame.ru/hls_vod/test/index.m3u8',
            'My Title',
            MODDATE,
        )
        handler = GoodGameVodHandler()
        hints = handler.prepare(GG_VOD_URL)

        assert hints.format_selector == '0'
        assert hints.merge_output_format == 'mp4'
        assert hints.referer == 'https://goodgame.ru/'
        assert 'My Title' in hints.output_template
        assert hints.log_title == 'My Title'

    def test_is_enabled_from_config(self):
        handler = GoodGameVodHandler()
        config_on = Mock()
        config_on.get.return_value = True
        config_off = Mock()
        config_off.get.return_value = False

        assert handler.is_enabled(config_on) is True
        assert handler.is_enabled(config_off) is False

    def test_extra_domains(self):
        handler = GoodGameVodHandler()
        assert 'goodgame.ru' in handler.extra_domains()
