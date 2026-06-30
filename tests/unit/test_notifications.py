# -*- coding: utf-8 -*-
"""Тесты для core/notifications.py."""

import os
import sys
from unittest.mock import Mock, patch, MagicMock

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.notifications import NotificationManager, send_download_complete, send_download_error


class TestNotificationManager:
    def test_respects_disabled_config(self):
        config = Mock()
        config.get.return_value = False
        manager = NotificationManager(config_manager=config)
        assert manager.send('Title', 'Message') is False

    @patch('core.notifications.NotificationManager._get_notification')
    def test_send_success(self, mock_get):
        mock_notify = MagicMock()
        mock_get.return_value = mock_notify
        config = Mock()
        config.get.return_value = True
        manager = NotificationManager(config_manager=config)

        assert manager.send('Title', 'Message') is True
        mock_notify.notify.assert_called_once()

    @patch('core.notifications.NotificationManager._get_notification')
    def test_send_handles_exception(self, mock_get):
        mock_notify = MagicMock()
        mock_notify.notify.side_effect = RuntimeError('fail')
        mock_get.return_value = mock_notify
        config = Mock()
        config.get.return_value = True
        manager = NotificationManager(config_manager=config)

        assert manager.send('Title', 'Message') is False

    def test_send_download_complete_delegates(self):
        config = Mock()
        config.get.return_value = False
        manager = NotificationManager(config_manager=config)
        assert manager.send_download_complete() is False

    @patch('core.notifications.get_notification_manager')
    def test_module_helpers(self, mock_get_manager):
        mock_manager = Mock()
        mock_manager.send_download_complete.return_value = True
        mock_manager.send_download_error.return_value = True
        mock_get_manager.return_value = mock_manager

        assert send_download_complete('t', 'm') is True
        assert send_download_error('t', 'm') is True
