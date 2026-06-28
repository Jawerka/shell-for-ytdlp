# -*- coding: utf-8 -*-
"""Тесты логики сворачивания в трей (MainWindow helpers)."""

import os
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestTrayMinimizeLogic:
    def _make_window_stub(self):
        from ui.main_window import MainWindow

        window = MainWindow.__new__(MainWindow)
        window._tray_ready = True
        window._suppress_tray_unmap = False
        window._shutting_down = False
        window.tray_manager = Mock()
        window.tray_manager.is_visible.return_value = False
        window.tray_manager.is_ready.return_value = True
        window.withdraw = Mock()
        window.after = Mock()
        return window

    def test_is_wm_minimized_iconic(self):
        window = self._make_window_stub()
        window.state = Mock(return_value='iconic')
        assert window._is_wm_minimized() is True

    def test_is_wm_minimized_fallback_not_viewable(self):
        window = self._make_window_stub()
        window.state = Mock(return_value='normal')
        window.winfo_viewable = Mock(return_value=0)
        assert window._is_wm_minimized() is True

    def test_is_wm_minimized_rejects_normal_visible(self):
        window = self._make_window_stub()
        window.state = Mock(return_value='normal')
        window.winfo_viewable = Mock(return_value=1)
        assert window._is_wm_minimized() is False

    @patch('ui.main_window.PYSTRAY_AVAILABLE', False)
    def test_minimize_skips_withdraw_without_pystray(self):
        window = self._make_window_stub()
        window.tray_manager = Mock()
        window.tray_manager.is_ready.return_value = True
        window._minimize_to_tray()
        window.withdraw.assert_not_called()

    @patch('ui.main_window.PYSTRAY_AVAILABLE', True)
    def test_minimize_shows_tray_before_withdraw(self):
        window = self._make_window_stub()
        order = []
        window.tray_manager.show = Mock(side_effect=lambda: order.append('show'))
        window.withdraw = Mock(side_effect=lambda: order.append('withdraw'))
        window._minimize_to_tray()
        assert order == ['show', 'withdraw']

    def test_schedule_respects_suppress_flag(self):
        window = self._make_window_stub()
        window._suppress_tray_unmap = True
        window.after_idle = Mock()
        window.after = Mock()
        window._schedule_tray_minimize_check()
        window.after_idle.assert_not_called()
        window.after.assert_not_called()
