# -*- coding: utf-8 -*-
"""Размер окна настроек не должен превышать экран после DPI-масштабирования."""

import pytest

from ui.components.settings_dialog import _fit_dialog_size


@pytest.mark.parametrize(
    'screen_w,screen_h,scaling,expected',
    [
        (1920, 1080, 1.0, (620, 780)),
        (1920, 1080, 1.25, (620, 768)),
        (1366, 768, 1.0, (620, 648)),
        (1920, 1080, 2.0, (620, 480)),
        (300, 300, 1.0, (220, 180)),
        (1920, 1080, 0.0, (620, 780)),
    ],
)
def test_fit_dialog_size(screen_w, screen_h, scaling, expected):
    assert _fit_dialog_size(screen_w, screen_h, scaling) == expected
