# -*- coding: utf-8 -*-
"""Тесты для core/deno_installer.py."""

import os
import sys
from unittest.mock import Mock, patch, MagicMock
from zipfile import ZipFile

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.deno_installer import (
    check_deno_installed,
    download_deno,
    ensure_deno_exists,
)


class TestCheckDenoInstalled:
    def test_not_installed(self, tmp_path):
        assert check_deno_installed(str(tmp_path)) is False

    def test_installed(self, tmp_path):
        (tmp_path / 'deno.exe').write_bytes(b'')
        assert check_deno_installed(str(tmp_path)) is True


class TestDownloadDeno:
    @patch('core.deno_installer.urlretrieve')
    def test_download_and_extract(self, mock_retrieve, tmp_path):
        def fake_retrieve(url, dest, hook=None):
            with ZipFile(dest, 'w') as zf:
                zf.writestr('deno.exe', b'fake')

        mock_retrieve.side_effect = fake_retrieve

        result = download_deno(str(tmp_path))

        assert result is True
        assert (tmp_path / 'deno.exe').exists()

    @patch('core.deno_installer.urlretrieve', side_effect=OSError('network'))
    def test_download_failure(self, _mock_retrieve, tmp_path):
        callback = Mock()
        result = download_deno(str(tmp_path), callback)
        assert result is False
        callback.assert_called()


class TestEnsureDenoExists:
    def test_skips_when_installed(self, tmp_path):
        (tmp_path / 'deno.exe').write_bytes(b'')
        with patch('core.deno_installer.download_deno') as mock_download:
            assert ensure_deno_exists(str(tmp_path)) is True
            mock_download.assert_not_called()

    @patch('core.deno_installer.download_deno', return_value=True)
    def test_downloads_when_missing(self, mock_download, tmp_path):
        assert ensure_deno_exists(str(tmp_path)) is True
        mock_download.assert_called_once()
