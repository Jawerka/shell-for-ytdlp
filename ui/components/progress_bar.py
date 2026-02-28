# -*- coding: utf-8 -*-
from typing import Any
import customtkinter as ctk
from core.theme import COLOR_THEME, Spacing
from ui.layout_config import CARD_PADX

class ProgressBarWithText(ctk.CTkFrame):
    """Прогресс-бар с текстовым отображением процента.
    Все части видимы, без двойного вложения.
    """

    def __init__(self, master: Any, bar_height: int = None, font_size: int = 13, corner_radius: int = None, **kwargs):
        requested = bar_height or 42
        MAX_BAR_HEIGHT = 56
        MIN_BAR_HEIGHT = 18
        self.bar_height = max(MIN_BAR_HEIGHT, min(requested, MAX_BAR_HEIGHT))
        self.font_size = font_size
        self.corner_radius = corner_radius or COLOR_THEME["radius_lg"]

        super().__init__(master, fg_color="transparent", **kwargs)

        # Единая видимая карточка
        self.progress_frame = ctk.CTkFrame(
            self,
            fg_color=COLOR_THEME["bg_card"],
            corner_radius=self.corner_radius,
            border_width=0,
            height=self.bar_height,
        )
        self.progress_frame.pack(fill="x", expand=False)
        try:
            self.progress_frame.pack_propagate(False)
        except Exception:
            pass

        # Высота трека
        self.bar_inner_height = int(self.bar_height-4)
        self.corner = 14

        # Прогресс-бар напрямую в progress_frame с отступами CARD_PADX
        self.progress_bar = ctk.CTkProgressBar(
            self.progress_frame,
            height=self.bar_inner_height,
            fg_color=COLOR_THEME["bg_card"],  # Фон трека = фон карточки
            progress_color=COLOR_THEME["progress_fill"],
            corner_radius=self.corner,
            mode="determinate"
        )
        # Отступы только для заполняющей полоски
        self.progress_bar.pack(fill="x", expand=True, padx=CARD_PADX, pady=0)
        self._bar_visible = False

        # Процент поверх бара
        self.percent_label = ctk.CTkLabel(
            self.progress_frame,
            text="0%",
            font=ctk.CTkFont(size=self.font_size, weight="bold"),
            text_color=COLOR_THEME["text_primary"],
            fg_color="transparent"
        )
        self.percent_label.place(relx=0.5, rely=0.5, anchor="center")
        try:
            self.percent_label.lift()
        except Exception:
            pass

        # Обработчик изменения размера
        def _on_frame_configure(event=None):
            w = self.progress_frame.winfo_width()
            h = self.progress_frame.winfo_height()
            if w <= 1 or h <= 1:
                return
            try:
                self.progress_bar.update_idletasks()
            except Exception:
                pass
            try:
                self.percent_label.lift()
            except Exception:
                pass

        self.progress_frame.bind("<Configure>", _on_frame_configure)
        self.after(10, _on_frame_configure)

        # Изначально скрываем трек
        self._hide_bar()

    # Вспомогательные методы для управления видимостью трека
    def _show_bar(self) -> None:
        """Показать трек."""
        if self._bar_visible:
            return
        self.progress_bar.pack(fill="x", expand=True, pady=0)
        self._bar_visible = True
        try:
            self.percent_label.lift()
        except Exception:
            pass

    def _hide_bar(self) -> None:
        """Скрыть трек."""
        if not self._bar_visible:
            try:
                self.progress_bar.pack_forget()
            except Exception:
                pass
            self._bar_visible = False
            return
        try:
            self.progress_bar.pack_forget()
        except Exception:
            pass
        self._bar_visible = False

    def update_progress(self, percent: float, text: str = "", info: str = None) -> None:
        """Обновить прогресс."""
        percent = max(0.0, min(100.0, float(percent)))

        # Всегда показываем прогресс-бар если есть прогресс
        if percent > 0.0:
            if not self._bar_visible:
                self._show_bar()
            self.progress_bar.set(percent / 100.0)
        else:
            # Скрываем только если процент = 0 и нет текста
            if not text and self._bar_visible:
                self._hide_bar()
            try:
                self.progress_bar.set(0.0)
            except Exception:
                pass

        if text:
            self.percent_label.configure(text=text)
        else:
            self.percent_label.configure(text=f"{percent:.1f}%")

        try:
            self.percent_label.lift()
        except Exception:
            pass

    def reset(self) -> None:
        """Сброс прогресса."""
        self._hide_bar()
        self.percent_label.configure(text="0%")
