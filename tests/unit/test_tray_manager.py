# -*- coding: utf-8 -*-
"""Тесты для core/tray_manager.py."""

import os
import sys
import threading
from unittest.mock import MagicMock, Mock, patch

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


@pytest.fixture
def mock_deps():
    clipboard = Mock()
    clipboard.is_running.return_value = False
    clipboard.is_paused.return_value = False
    sound = Mock()
    sound.is_enabled.return_value = True
    config = Mock()
    root = Mock()
    root.after = Mock(side_effect=lambda delay, cb: cb())
    return clipboard, sound, config, root


@pytest.fixture
def tray_manager(mock_deps):
    from core.tray_manager import TrayManager

    clipboard, sound, config, root = mock_deps
    return TrayManager(
        clipboard_monitor=clipboard,
        sound_manager=sound,
        config_manager=config,
        on_restore=Mock(),
        on_paste_and_download=Mock(),
        on_open_settings=Mock(),
        on_exit=Mock(),
        root_window=root,
    )


class TestTrayManagerLifecycle:
    @patch('core.tray_manager.PYSTRAY_AVAILABLE', True)
    @patch('core.tray_manager.Icon')
    @patch('core.tray_manager.threading.Thread')
    def test_prepare_starts_thread_once(self, mock_thread_cls, mock_icon_cls, tray_manager):
        icon = MagicMock()
        mock_icon_cls.return_value = icon
        thread = MagicMock()
        thread.is_alive.return_value = True
        mock_thread_cls.return_value = thread

        assert tray_manager.prepare() is True
        assert tray_manager.is_ready() is True
        mock_thread_cls.assert_called_once()
        icon.run.assert_not_called()

        tray_manager.prepare()
        mock_thread_cls.assert_called_once()

    @patch('core.tray_manager.PYSTRAY_AVAILABLE', True)
    @patch('core.tray_manager.Icon')
    @patch('core.tray_manager.threading.Thread')
    def test_show_hide_use_visible_not_stop(self, mock_thread_cls, mock_icon_cls, tray_manager):
        icon = MagicMock()
        mock_icon_cls.return_value = icon
        thread = MagicMock()
        thread.is_alive.return_value = True
        mock_thread_cls.return_value = thread

        tray_manager.prepare()
        tray_manager.show()
        assert icon.visible is True
        assert tray_manager.is_visible() is True
        icon.stop.assert_not_called()

        tray_manager.hide()
        assert icon.visible is False
        assert tray_manager.is_visible() is False
        icon.stop.assert_not_called()

    @patch('core.tray_manager.PYSTRAY_AVAILABLE', True)
    @patch('core.tray_manager.Icon')
    @patch('core.tray_manager.threading.Thread')
    def test_stop_hides_and_joins_thread(self, mock_thread_cls, mock_icon_cls, tray_manager):
        icon = MagicMock()
        mock_icon_cls.return_value = icon
        thread = MagicMock()
        thread.is_alive.return_value = False
        mock_thread_cls.return_value = thread

        tray_manager.prepare()
        tray_manager.show()
        tray_manager.stop()

        assert icon.visible is False
        icon.stop.assert_called_once()
        thread.join.assert_called_once()
        assert tray_manager.is_ready() is False

    @patch('core.tray_manager.PYSTRAY_AVAILABLE', True)
    @patch('core.tray_manager.Icon')
    @patch('core.tray_manager.threading.Thread')
    def test_stop_idempotent(self, mock_thread_cls, mock_icon_cls, tray_manager):
        icon = MagicMock()
        mock_icon_cls.return_value = icon
        thread = MagicMock()
        thread.is_alive.return_value = False
        mock_thread_cls.return_value = thread

        tray_manager.prepare()
        tray_manager.stop()
        tray_manager.stop()
        icon.stop.assert_called_once()

    def test_safe_callback_uses_root_after(self, tray_manager, mock_deps):
        _, _, _, root = mock_deps
        callback = Mock()
        tray_manager._safe_callback(callback)
        root.after.assert_called_once_with(0, callback)

    @patch('core.tray_manager.sys._MEIPASS', '/tmp/meipass', create=True)
    def test_get_icon_path_meipass(self, tray_manager):
        with patch('core.tray_manager.os.path.exists') as exists:
            exists.side_effect = lambda p: p.replace('\\', '/').endswith('icon.ico')
            path = tray_manager._get_icon_path()
            assert path is not None
            assert path.endswith('icon.ico')
