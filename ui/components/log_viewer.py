# -*- coding: utf-8 -*-
"""
Компонент просмотра логов.
"""

import re
from typing import List, Tuple

import customtkinter as ctk

from core.theme import COLOR_THEME, Spacing
from core.logger import GUILogger, LogLevel
from core.icons import IconManager
from ui.layout_config import CORNER_RADIUS, ELEMENT_PADX, ELEMENT_PADY


class LogViewer(ctk.CTkTextbox):
    """Просмотрщик логов с цветовой дифференциацией."""

    # Паттерн для сообщений о прогрессе загрузки
    PROGRESS_PATTERN = re.compile(r'\d+\.?\d*%')

    def __init__(self, master, font=None, corner_radius: int = None, padx: int = None, pady: int = None, **kwargs):
        self.corner_radius = corner_radius or CORNER_RADIUS
        self.text_padx = padx or ELEMENT_PADX
        self.text_pady = pady or ELEMENT_PADY
        
        # Устанавливаем font по умолчанию
        if font is None:
            font = ctk.CTkFont(family="Consolas", size=12)

        # Устанавливаем значения по умолчанию для padx/pady
        if "padx" not in kwargs:
            kwargs["padx"] = self.text_padx
        if "pady" not in kwargs:
            kwargs["pady"] = self.text_pady

        super().__init__(
            master,
            font=font,
            text_color=COLOR_THEME["text_muted"],
            fg_color=COLOR_THEME["bg_card"],
            border_color=COLOR_THEME["border"],
            border_width=0,
            corner_radius=self.corner_radius,
            **kwargs
        )

        self.configure(wrap="word")
        self.configure(state="disabled")

        self.clear_button = None  # type: ignore
        self._log_history: List[Tuple[str, str]] = []
        self._last_was_progress: bool = False  # Было ли последнее сообщение прогрессом

        self._create_close_button()
        self._show_placeholder()

    def _create_close_button(self) -> None:
        close_icon = IconManager.get("clear", "✕")

        self.clear_button = ctk.CTkButton(
            self,
            text=close_icon,
            width=28,
            height=28,
            command=self.clear,
            fg_color=COLOR_THEME["accent"],
            text_color=COLOR_THEME["text_primary"],
            hover_color=COLOR_THEME["accent_hover"],
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=COLOR_THEME["radius_sm"],
        )
        self.clear_button.place(relx=1.0, rely=0.0, anchor="ne", x=-Spacing.MD, y=Spacing.MD)
        self.clear_button.place_forget()

    def _show_placeholder(self) -> None:
        internal = getattr(self, "_textbox", None) or getattr(self, "textbox", None) or self
        try:
            internal.configure(state="normal")
            internal.insert("1.0", "Нет активности\n")
            internal.insert("2.0", "Начните загрузку для отображения логов")
            internal.configure(state="disabled")
        except Exception:
            pass

    def _clear_placeholder(self) -> None:
        internal = getattr(self, "_textbox", None) or getattr(self, "textbox", None) or self
        try:
            internal.configure(state="normal")
            internal.delete("1.0", "end")
            internal.configure(state="disabled")
        except Exception:
            pass

    def _show_button(self) -> None:
        if self.clear_button and not self.clear_button.winfo_ismapped():
            try:
                self.clear_button.place(relx=1.0, rely=0.0, anchor="ne", x=-Spacing.MD, y=Spacing.MD)
            except Exception:
                self.clear_button.place(relx=1.0, rely=0.0, anchor="ne", x=-8, y=8)

    def _hide_button(self) -> None:
        if self.clear_button and self.clear_button.winfo_ismapped():
            self.clear_button.place_forget()

    def _is_progress_message(self, message: str) -> bool:
        """Проверить, является ли сообщение сообщением о прогрессе (содержит XX.X%)."""
        return bool(self.PROGRESS_PATTERN.search(message))

    def _update_last_line(self, message: str, color: str) -> None:
        """Обновить последнюю строку."""
        internal = getattr(self, "_textbox", None) or getattr(self, "textbox", None) or self
        try:
            internal.configure(state="normal")
            # Удаляем последнюю строку
            last_line = int(internal.index("end-1c").split(".")[0])
            internal.delete(f"{last_line}.0", "end")
            # Вставляем новое сообщение
            internal.insert("end-1c", message)
            # Применяем цвет
            tag_name = f"color_{color.replace('#', '')}"
            try:
                internal.tag_configure(tag_name, foreground=color)
            except Exception:
                pass
            internal.tag_add(tag_name, f"{last_line}.0", f"{last_line}.end")
            internal.configure(state="disabled")
            internal.see("end")
        except Exception:
            pass

    def _insert_colored(self, message: str, color: str) -> None:
        if self._log_history == []:
            self._clear_placeholder()

        is_progress = self._is_progress_message(message)

        # Если текущее и предыдущее сообщения - прогресс, обновляем последнюю строку
        if is_progress and self._last_was_progress:
            self._update_last_line(message, color)
            # Обновляем историю — заменяем последнюю запись
            if self._log_history:
                self._log_history[-1] = (message, color)
        else:
            # Если предыдущее было прогрессом, а текущее нет - добавляем \n перед сообщением
            if self._last_was_progress and not is_progress:
                message = "\n" + message

            # Добавляем новую строку
            internal = getattr(self, "_textbox", None) or getattr(self, "textbox", None) or self
            try:
                internal.configure(state="normal")
            except Exception:
                pass

            internal.insert("end", message + "\n")

            try:
                last_line = int(internal.index("end-1c").split(".")[0])
                tag_name = f"color_{color.replace('#', '')}"
                try:
                    internal.tag_configure(tag_name, foreground=color)
                except Exception:
                    pass
                internal.tag_add(tag_name, f"{last_line}.0", f"{last_line}.end")
            except Exception:
                pass

            try:
                internal.configure(state="disabled")
            except Exception:
                pass

            try:
                internal.see("end")
            except Exception:
                pass

        # Сохраняем статус последнего сообщения
        self._last_was_progress = is_progress

    def _log(self, message: str, level: LogLevel) -> None:
        color = GUILogger.COLORS.get(level, GUILogger.COLORS.get(LogLevel.INFO, COLOR_THEME["text_muted"]))
        self._insert_colored(message, color)
        self._log_history.append((message, color))
        self._show_button()

    # публичные методы логирования без изменений API:
    def info(self, message: str) -> None:
        self._log(message, LogLevel.INFO)

    def success(self, message: str) -> None:
        self._log(message, LogLevel.SUCCESS)

    def warning(self, message: str) -> None:
        self._log(message, LogLevel.WARNING)

    def error(self, message: str) -> None:
        self._log(message, LogLevel.ERROR)

    def debug(self, message: str) -> None:
        self._log(message, LogLevel.DEBUG)

    def clear(self) -> None:
        """Очистить логи."""
        internal = getattr(self, "_textbox", None) or getattr(self, "textbox", None) or self
        try:
            internal.configure(state="normal")
            internal.delete("1.0", "end")
            internal.configure(state="disabled")
        except Exception:
            pass
        self._log_history.clear()
        self._last_was_progress = False
        self._hide_button()
        self._show_placeholder()

    def get_history(self) -> List[Tuple[str, str]]:
        """Получить историю логов."""
        return self._log_history.copy()
