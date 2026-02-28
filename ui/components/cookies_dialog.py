# -*- coding: utf-8 -*-
"""
Диалог настройки cookies.txt.
"""

import os
from typing import Callable, Optional
import sys

import customtkinter as ctk
from tkinter import filedialog

from core.theme import COLOR_THEME, Spacing, setup_theme
from core.icons import IconManager
from core.utils import find_cookies_txt, normalize_path_for_display


class CookiesDialog(ctk.CTkToplevel):
    def __init__(
        self,
        parent,
        current_cookies_path: Optional[str],
        on_save: Callable[[Optional[str]], None]
    ):
        self.parent = parent
        setup_theme()
        super().__init__(parent)

        self.current_cookies_path = current_cookies_path
        self.on_save_callback = on_save

        self.title("Настройка cookies.txt")
        self.geometry("540x350")
        self.minsize(540, 350)
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=COLOR_THEME["bg_primary"])

        try:
            if sys.platform == "win32":
                self.after(100, lambda: self._set_dark_title())
        except Exception:
            pass

        if not sys.platform == "win32":
            self._create_ui()

    def _set_dark_title(self) -> None:
        try:
            ctk.set_appearance_mode("dark")
        except Exception:
            pass

        try:
            self.update_idletasks()
            x = self.parent.winfo_x() + (self.parent.winfo_width() - self.winfo_width()) // 2
            y = self.parent.winfo_y() + (self.parent.winfo_height() - self.winfo_height()) // 2
            self.geometry(f"+{x}+{y}")
        except Exception:
            pass

        self._create_ui()

    def _create_ui(self) -> None:
        card = ctk.CTkFrame(
            self,
            fg_color=COLOR_THEME["bg_card"],
            corner_radius=COLOR_THEME["radius_lg"],
            border_width=COLOR_THEME.get("border_width", 1),
            border_color=COLOR_THEME.get("border", "#252525")
        )
        card.pack(fill="both", expand=True, padx=Spacing.LG, pady=Spacing.LG)

        # Заголовок
        title_label = ctk.CTkLabel(
            card,
            text="Выберите файл cookies.txt",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLOR_THEME["text_primary"],
            wraplength=460,
            justify="left",
        )
        title_label.pack(pady=(Spacing.LG, Spacing.SM), padx=Spacing.LG, anchor="w")

        # Поле ввода пути
        path_frame = ctk.CTkFrame(card, fg_color="transparent")
        path_frame.pack(fill="x", padx=Spacing.LG, pady=(Spacing.SM, Spacing.MD))

        self.path_entry = ctk.CTkEntry(
            path_frame,
            height=40,
            corner_radius=COLOR_THEME["radius_md"],
            border_width=1,
            border_color=COLOR_THEME["border"],
            fg_color=COLOR_THEME["bg_primary"],
            text_color=COLOR_THEME["text_primary"],
            font=ctk.CTkFont(size=13),
            placeholder_text="Путь к файлу cookies.txt",
        )
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, Spacing.SM))

        # Установить текущий путь
        if self.current_cookies_path:
            self.path_entry.insert(0, normalize_path_for_display(self.current_cookies_path))

        # Кнопка обзора
        browse_icon = IconManager.get("folder", "📂")
        browse_btn = ctk.CTkButton(
            path_frame,
            text=browse_icon,
            width=42,
            height=40,
            command=self._browse_file,
            fg_color=COLOR_THEME["accent"],
            hover_color=COLOR_THEME["accent_hover"],
            corner_radius=COLOR_THEME["radius_md"],
            text_color=COLOR_THEME["text_primary"],
            font=ctk.CTkFont(size=18),
        )
        browse_btn.pack(side="right")

        # Пояснение
        info_text = (
            "cookies.txt — это файл с куками вашего браузера. "
            "Позволяет скачивать приватные видео и контент по подписке. "
            "Поддерживаются форматы Netscape и Mozilla cookies.\n\n"
            "Для создания файла используйте расширение для браузера:\n"
            "• Chrome/Edge: 'Get cookies.txt LOCALLY'\n"
            "• Firefox: 'cookies.txt'"
        )

        info_label = ctk.CTkLabel(
            card,
            text=info_text,
            font=ctk.CTkFont(size=12),
            text_color=COLOR_THEME["text_muted"],
            wraplength=460,
            justify="left",
            anchor="w"
        )
        info_label.pack(fill="x", padx=Spacing.LG, pady=(Spacing.SM, Spacing.MD))

        # Кнопки действий
        buttons_frame = ctk.CTkFrame(card, fg_color="transparent")
        buttons_frame.pack(fill="x", padx=Spacing.LG, pady=(Spacing.MD, Spacing.LG))

        # Кнопка "Очистить" (если файл выбран)
        if self.current_cookies_path:
            clear_icon = IconManager.get("clear", "✕")
            clear_btn = ctk.CTkButton(
                buttons_frame,
                text=clear_icon + " Очистить",
                width=70,
                height=40,
                command=self._clear_path,
                fg_color=COLOR_THEME["bg_card"],
                hover_color=COLOR_THEME["primary"],
                corner_radius=COLOR_THEME["radius_md"],
                text_color=COLOR_THEME["text_primary"],
                font=ctk.CTkFont(size=13),
            )
            clear_btn.pack(side="left", padx=(0, Spacing.SM))

        # Пространство
        spacer = ctk.CTkFrame(buttons_frame, fg_color="transparent")
        spacer.pack(side="left", fill="x", expand=True)

        # Кнопка "Отмена"
        cancel_btn = ctk.CTkButton(
            buttons_frame,
            text="Отмена",
            width=70,
            height=40,
            command=self.destroy,
            fg_color=COLOR_THEME["bg_card"],
            hover_color=COLOR_THEME.get("accent", COLOR_THEME["primary"]),
            corner_radius=COLOR_THEME["radius_md"],
            text_color=COLOR_THEME["text_primary"],
            font=ctk.CTkFont(size=13),
        )
        cancel_btn.pack(side="right", padx=(6, 0))

        # Кнопка "OK"
        save_icon = IconManager.get("check", "✓")
        save_btn = ctk.CTkButton(
            buttons_frame,
            text=save_icon + " OK",
            width=70,
            height=40,
            command=self._save_and_close,
            fg_color=COLOR_THEME["primary"],
            hover_color=COLOR_THEME["primary_hover"],
            corner_radius=COLOR_THEME["radius_md"],
            text_color=COLOR_THEME["primary_foreground"],
            font=ctk.CTkFont(size=13),
        )
        save_btn.pack(side="right", padx=(0, 6))

    def _browse_file(self) -> None:
        """Открыть диалог выбора файла cookies.txt."""
        initial_dir = os.path.dirname(self.current_cookies_path) if self.current_cookies_path else None
        if not initial_dir or not os.path.exists(initial_dir):
            initial_dir = os.path.expanduser("~")

        file_path = filedialog.askopenfilename(
            title="Выберите файл cookies.txt",
            initialdir=initial_dir,
            filetypes=[("Cookies files", "*.txt"), ("All files", "*.*")]
        )

        if file_path:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, file_path)

    def _clear_path(self) -> None:
        """Очистить путь к файлу cookies.txt."""
        self.path_entry.delete(0, "end")

    def _save_and_close(self) -> None:
        """Сохранить путь и закрыть диалог."""
        path = self.path_entry.get().strip()
        if path and not os.path.exists(path):
            # Файл не существует - показать предупреждение
            from tkinter import messagebox
            if messagebox.askyesno(
                "Файл не найден",
                f"Файл не существует:\n{path}\n\nПродолжить?"
            ):
                if self.on_save_callback:
                    self.on_save_callback(path)
                self.destroy()
        else:
            if self.on_save_callback:
                self.on_save_callback(path if path else None)
            self.destroy()

    def get_cookies_path(self) -> Optional[str]:
        """Получить выбранный путь к cookies.txt."""
        path = self.path_entry.get().strip()
        return path if path else None
