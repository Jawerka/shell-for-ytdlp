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

    @patch('core.deno_installer._deno_runs', return_value=True)
    def test_installed_and_runs(self, _mock_runs, tmp_path):
        (tmp_path / 'deno.exe').write_bytes(b'')
        assert check_deno_installed(str(tmp_path)) is True

    @patch('core.deno_installer._deno_runs', return_value=False)
    def test_installed_but_broken(self, _mock_runs, tmp_path):
        (tmp_path / 'deno.exe').write_bytes(b'broken')
        assert check_deno_installed(str(tmp_path)) is False


class TestDownloadDeno:
    @patch('core.deno_installer._deno_runs', return_value=True)
    @patch('core.deno_installer.download_file')
    def test_download_and_extract(self, mock_download, _mock_runs, tmp_path):
        def fake_download(url, dest, hook=None, cancel_event=None):
            with ZipFile(dest, 'w') as zf:
                zf.writestr('deno.exe', b'fake')
            return True

        mock_download.side_effect = fake_download

        result = download_deno(str(tmp_path))

        assert result is True
        assert (tmp_path / 'deno.exe').exists()
        assert not (tmp_path / 'deno.zip').exists()

    @patch('core.deno_installer.download_file', side_effect=OSError('network'))
    def test_download_failure(self, _mock_download, tmp_path):
        callback = Mock()
        result = download_deno(str(tmp_path), callback)
        assert result is False
        callback.assert_called()

    @patch('core.deno_installer.download_file', return_value=False)
    def test_download_cancelled(self, _mock_download, tmp_path):
        result = download_deno(str(tmp_path))
        assert result is False
        assert not (tmp_path / 'deno.exe').exists()

    @patch('core.deno_installer._deno_runs', return_value=False)
    @patch('core.deno_installer.download_file')
    def test_invalid_deno_not_kept(self, mock_download, _mock_runs, tmp_path):
        def fake_download(url, dest, hook=None, cancel_event=None):
            with ZipFile(dest, 'w') as zf:
                zf.writestr('deno.exe', b'bad')
            return True

        mock_download.side_effect = fake_download

        result = download_deno(str(tmp_path))

        assert result is False
        assert not (tmp_path / 'deno.exe').exists()


class TestEnsureDenoExists:
    @patch('core.deno_installer.check_deno_installed', return_value=True)
    @patch('core.deno_installer.download_deno')
    def test_skips_when_installed(self, mock_download, _mock_check, tmp_path):
        assert ensure_deno_exists(str(tmp_path)) is True
        mock_download.assert_not_called()

    @patch('core.deno_installer.check_deno_installed', return_value=False)
    @patch('core.deno_installer.download_deno', return_value=True)
    def test_downloads_when_missing(self, mock_download, _mock_check, tmp_path):
        assert ensure_deno_exists(str(tmp_path)) is True
        mock_download.assert_called_once()
