# -*- coding: utf-8 -*-
"""
Всплывающие подсказки (tooltips) для элементов интерфейса.
"""

import customtkinter as ctk
from typing import Optional
from core.theme import COLOR_THEME


class Tooltip:
    """
    Всплывающая подсказка для виджетов.
    
    Появляется через заданную задержку при наведении курсора.
    """

    def __init__(
        self,
        widget: ctk.CTkBaseClass,
        text: str,
        delay: int = 500,
        bg_color: Optional[str] = None,
        text_color: Optional[str] = None,
    ):
        """
        Создать тултип для виджета.

        Args:
            widget: Виджет, для которого создаётся тултип
            text: Текст подсказки
            delay: Задержка перед показом в мс (по умолчанию 500мс)
            bg_color: Цвет фона (по умолчанию тёмный из темы)
            text_color: Цвет текста (по умолчанию светлый из темы)
        """
        self.widget = widget
        self.text = text
        self.delay = delay
        self.bg_color = bg_color or COLOR_THEME["bg_card"]
        self.text_color = text_color or COLOR_THEME["text_primary"]

        self.tip_window: Optional[ctk.CTkToplevel] = None
        self._job: Optional[str] = None

        # Привязка событий
        self.widget.bind("<Enter>", self._schedule, add="+")
        self.widget.bind("<Leave>", self._hide, add="+")
        self.widget.bind("<Button>", self._hide, add="+")
        self.widget.bind("<Destroy>", self._on_destroy, add="+")

    def _schedule(self, event=None) -> None:
        """Запланировать показ тултипа."""
        self._unschedule()
        self._job = self.widget.after(self.delay, self._show)

    def _unschedule(self) -> None:
        """Отменить показ тултипа."""
        if self._job:
            self.widget.after_cancel(self._job)
            self._job = None

    def _show(self) -> None:
        """Показать тултип."""
        if self.tip_window or not self.text:
            return

        # Получаем координаты виджета
        x = self.widget.winfo_rootx()
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4

        # Создаём окно тултипа
        self.tip_window = tw = ctk.CTkToplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.wm_attributes("-topmost", True)

        # Создаём фрейм для стилизации
        frame = ctk.CTkFrame(
            tw,
            fg_color=self.bg_color,
            corner_radius=6,
            border_width=1,
            border_color=COLOR_THEME["border"],
        )
        frame.pack(fill="both", expand=True, padx=0, pady=0)

        # Создаём метку с текстом
        label = ctk.CTkLabel(
            frame,
            text=self.text,
            text_color=self.text_color,
            font=ctk.CTkFont(size=11),
            padx=8,
            pady=4,
        )
        label.pack(fill="both", expand=True)

        # Обновляем позицию при движении окна
        self.widget.bind("<Configure>", self._update_position, add="+")

    def _update_position(self, event=None) -> None:
        """Обновить позицию тултипа."""
        if self.tip_window:
            x = self.widget.winfo_rootx()
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
            self.tip_window.wm_geometry(f"+{x}+{y}")

    def _hide(self, event=None) -> None:
        """Скрыть тултип."""
        self._unschedule()
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

    def _on_destroy(self, event=None) -> None:
        """Очистка при уничтожении виджета."""
        self._unschedule()
        self._hide()

    def configure(self, **kwargs) -> None:
        """Обновить параметры тултипа."""
        if "text" in kwargs:
            self.text = kwargs.pop("text")
        if "delay" in kwargs:
            self.delay = kwargs.pop("delay")
        if "bg_color" in kwargs:
            self.bg_color = kwargs.pop("bg_color")
        if "text_color" in kwargs:
            self.text_color = kwargs.pop("text_color")

        # Если тултип уже показан - обновить текст
        if self.tip_window and "text" in kwargs:
            for child in self.tip_window.winfo_children():
                for label in child.winfo_children():
                    if isinstance(label, ctk.CTkLabel):
                        label.configure(text=self.text)
                        break


def create_tooltip(widget: ctk.CTkBaseClass, text: str, delay: int = 500) -> Tooltip:
    """
    Создать тултип для виджета.

    Args:
        widget: Виджет для тултипа
        text: Текст подсказки
        delay: Задержка перед показом в мс

    Returns:
        Экземпляр Tooltip
    """
    return Tooltip(widget, text, delay)
