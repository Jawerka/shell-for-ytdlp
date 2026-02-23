# -*- coding: utf-8 -*-
"""
Компонент поля ввода URL.
"""

from typing import Callable, Optional

import customtkinter as ctk
import pyperclip

from core.theme import COLOR_THEME, Spacing
from ui.layout_config import CORNER_RADIUS, ELEMENT_PADX


class UrlInput(ctk.CTkFrame):
    """Поле ввода URL."""

    def __init__(
        self,
        master,
        on_paste: Optional[Callable[[], None]] = None,
        entry_width: int = 500,
        entry_height: int = 42,
        corner_radius: int = None,
        **kwargs
    ):
        self.entry_width = entry_width
        self.entry_height = entry_height
        self.on_paste_callback = on_paste
        self.corner_radius = corner_radius or CORNER_RADIUS

        super().__init__(master, fg_color="transparent", **kwargs)

        # Карточка поля ввода
        self.container = ctk.CTkFrame(
            self,
            fg_color=COLOR_THEME["bg_card"],
            corner_radius=self.corner_radius,
            border_width=0,
            height=self.entry_height
        )
        self.container.pack(fill="both", expand=True)

        # Внутренняя область
        inner = ctk.CTkFrame(self.container, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=ELEMENT_PADX)

        # Поле ввода
        self.url_entry = ctk.CTkEntry(
            inner,
            placeholder_text="Введите URL...",
            width=self.entry_width,
            height=self.entry_height,
            font=ctk.CTkFont(size=12),
            border_width=0,
            fg_color="transparent",
            text_color=COLOR_THEME["text_primary"],
            placeholder_text_color=COLOR_THEME["text_muted"],
        )
        self.url_entry.pack(side="left", fill="both", expand=True)

        # Горячие клавиши
        self.url_entry.bind("<Control-v>", lambda e: self._paste_from_clipboard())
        self.url_entry.bind("<Control-V>", lambda e: self._paste_from_clipboard())

    def _paste_from_clipboard(self) -> None:
        """Вставить URL из буфера обмена."""
        try:
            text = pyperclip.paste().strip()
        except Exception:
            try:
                text = self.clipboard_get().strip()
            except Exception:
                text = ""

        if text:
            self.url_entry.delete(0, "end")
            self.url_entry.insert(0, text)
            if self.on_paste_callback:
                try:
                    self.on_paste_callback()
                except Exception:
                    pass

    def get_url(self) -> str:
        return self.url_entry.get().strip()

    def set_url(self, url: str) -> None:
        self.url_entry.delete(0, "end")
        self.url_entry.insert(0, url)

    def clear(self) -> None:
        self.url_entry.delete(0, "end")
