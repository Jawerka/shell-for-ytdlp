# -*- coding: utf-8 -*-
"""
Диалог расширенных настроек (cookies + SponsorBlock).
"""

from typing import Callable, List, Optional
import sys
import os

import customtkinter as ctk
from tkinter import filedialog

from core.theme import COLOR_THEME, Spacing, setup_theme
from core.icons import IconManager
from core.utils import find_cookies_txt, normalize_path_for_display
from ui.tooltip import create_tooltip


# Категории SponsorBlock
SPONSORBLOCK_CATEGORIES = {
    'sponsor': 'Спонсоры (встроенная реклама)',
    'selfpromo': 'Самореклама',
    'interaction': 'Напоминания о подписке/лайке',
    'intro': 'Заставка (вступление)',
    'outro': 'Заставка (концовка)',
    'preview': 'Анонс предыдущих серий',
    'music_offtopic': 'Музыка не по теме',
    'poi_highlight': 'Важные моменты',
}


class SettingsDialog(ctk.CTkToplevel):
    def __init__(
        self,
        parent,
        cookies_path: Optional[str],
        sponsorblock_categories: List[str],
        clipboard_monitoring: bool = False,
        on_save: Callable[[Optional[str], List[str], bool, bool], None] = None,
        config_manager=None
    ):
        self.parent = parent
        self.config_manager = config_manager
        
        setup_theme()
        super().__init__(parent)

        self.cookies_path = cookies_path
        self.sponsorblock_categories = set(sponsorblock_categories)
        self.clipboard_monitoring = clipboard_monitoring
        self.on_save_callback = on_save

        self.title("Настройки")
        self.geometry("620x700")
        self.minsize(620, 700)
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
        # Основной контейнер окна
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=Spacing.LG, pady=Spacing.LG)

        # Карточка с настройками (занимает всё доступное место)
        card = ctk.CTkFrame(
            main_frame,
            fg_color=COLOR_THEME["bg_card"],
            corner_radius=COLOR_THEME["radius_lg"],
            border_width=COLOR_THEME.get("border_width", 1),
            border_color=COLOR_THEME.get("border", "#252525")
        )
        card.pack(fill="both", expand=True)

        # Контент без прокрутки (занимает всё место внутри card)
        content_frame = ctk.CTkFrame(
            card,
            fg_color="transparent",
            corner_radius=COLOR_THEME["radius_md"]
        )
        content_frame.pack(fill="both", expand=True, padx=Spacing.LG, pady=(0, Spacing.MD))

        # === Секция 1: Cookies ===
        cookies_section = ctk.CTkFrame(content_frame, fg_color="transparent")
        cookies_section.pack(fill="x", pady=(0, Spacing.LG))

        cookies_title = ctk.CTkLabel(
            cookies_section,
            text="Cookies.txt",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLOR_THEME["text_primary"],
            anchor="w"
        )
        cookies_title.pack(fill="x", pady=(0, Spacing.SM))

        # Описание и help-ссылка в одной строке
        desc_frame = ctk.CTkFrame(cookies_section, fg_color="transparent")
        desc_frame.pack(fill="x", pady=(0, Spacing.SM))

        cookies_desc = ctk.CTkLabel(
            desc_frame,
            text="Файл cookies.txt позволяет скачивать приватные видео и контент по подписке ",
            font=ctk.CTkFont(size=12),
            text_color=COLOR_THEME["text_muted"],
            anchor="w"
        )
        cookies_desc.pack(side="left")

        # Интерактивная ссылка на документацию
        help_label = ctk.CTkLabel(
            desc_frame,
            text="(help)",
            font=ctk.CTkFont(size=12, underline=True),
            text_color=COLOR_THEME["primary"],
            cursor="hand2",
            anchor="w"
        )
        help_label.pack(side="left")
        
        # Открытие ссылки при клике
        def _open_help(event=None):
            import webbrowser
            webbrowser.open("https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp")
        
        help_label.bind("<Button-1>", _open_help)
        help_label.bind("<Enter>", lambda e: help_label.configure(text_color=COLOR_THEME["primary_hover"]))
        help_label.bind("<Leave>", lambda e: help_label.configure(text_color=COLOR_THEME["primary"]))

        # Поле ввода пути
        cookies_path_frame = ctk.CTkFrame(cookies_section, fg_color="transparent")
        cookies_path_frame.pack(fill="x", pady=(0, Spacing.SM))

        self.cookies_entry = ctk.CTkEntry(
            cookies_path_frame,
            height=40,
            corner_radius=COLOR_THEME["radius_md"],
            border_width=1,
            border_color=COLOR_THEME["border"],
            fg_color=COLOR_THEME["bg_primary"],
            text_color=COLOR_THEME["text_primary"],
            font=ctk.CTkFont(size=13),
            placeholder_text="Путь к файлу cookies.txt",
        )
        self.cookies_entry.pack(side="left", fill="x", expand=True, padx=(0, Spacing.SM))

        # Установить текущий путь
        if self.cookies_path:
            self.cookies_entry.insert(0, normalize_path_for_display(self.cookies_path))

        # Кнопка обзора
        browse_icon = IconManager.get("folder", "📂")
        browse_btn = ctk.CTkButton(
            cookies_path_frame,
            text=browse_icon,
            width=50,
            height=40,
            command=self._browse_cookies,
            fg_color=COLOR_THEME["accent"],
            hover_color=COLOR_THEME["accent_hover"],
            corner_radius=COLOR_THEME["radius_md"],
            text_color=COLOR_THEME["text_primary"],
            font=ctk.CTkFont(size=18),
        )
        browse_btn.pack(side="right")

        # Кнопка очистки
        if self.cookies_path:
            clear_icon = IconManager.get("clear", "✕")
            clear_btn = ctk.CTkButton(
                cookies_path_frame,
                text=clear_icon,
                width=40,
                height=40,
                command=self._clear_cookies,
                fg_color=COLOR_THEME["bg_card"],
                hover_color=COLOR_THEME["accent"],
                corner_radius=COLOR_THEME["radius_md"],
                text_color=COLOR_THEME["text_primary"],
                font=ctk.CTkFont(size=16),
            )
            clear_btn.pack(side="right", padx=(0, Spacing.SM))

        # === Разделитель ===
        separator = ctk.CTkFrame(content_frame, height=2, fg_color=COLOR_THEME["border"])
        separator.pack(fill="x", pady=Spacing.LG)

        # === Секция 2: SponsorBlock ===
        sponsorblock_section = ctk.CTkFrame(content_frame, fg_color="transparent")
        sponsorblock_section.pack(fill="x", pady=(0, Spacing.LG))

        sponsorblock_title = ctk.CTkLabel(
            sponsorblock_section,
            text="SponsorBlock",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLOR_THEME["text_primary"],
            anchor="w"
        )
        sponsorblock_title.pack(fill="x", pady=(0, Spacing.SM))

        sponsorblock_desc = ctk.CTkLabel(
            sponsorblock_section,
            text="Автоматически пропускать выбранные категории в видео",
            font=ctk.CTkFont(size=12),
            text_color=COLOR_THEME["text_muted"],
            wraplength=560,
            justify="left",
            anchor="w"
        )
        sponsorblock_desc.pack(fill="x", pady=(0, Spacing.SM))

        # Чекбоксы категорий
        self.checkbox_vars = {}
        checkboxes_frame = ctk.CTkFrame(sponsorblock_section, fg_color="transparent")
        checkboxes_frame.pack(fill="x")

        # Две колонки чекбоксов
        left_frame = ctk.CTkFrame(checkboxes_frame, fg_color="transparent")
        left_frame.pack(side="left", fill="x", expand=True)
        right_frame = ctk.CTkFrame(checkboxes_frame, fg_color="transparent")
        right_frame.pack(side="right", fill="x", expand=True)

        categories_list = list(SPONSORBLOCK_CATEGORIES.items())
        mid = len(categories_list) // 2

        for i, (cat_id, cat_name) in enumerate(categories_list):
            var = ctk.BooleanVar(value=(cat_id in self.sponsorblock_categories))
            self.checkbox_vars[cat_id] = var

            checkbox_frame = ctk.CTkFrame(
                left_frame if i < mid else right_frame,
                fg_color="transparent"
            )
            checkbox_frame.pack(fill="x", pady=4)

            checkbox = ctk.CTkCheckBox(
                checkbox_frame,
                text="",
                variable=var,
                width=20,
                height=20,
                checkbox_width=20,
                checkbox_height=20,
                font=ctk.CTkFont(size=1),
                text_color=COLOR_THEME["text_primary"],
                fg_color=COLOR_THEME["bg_card"],
                border_color=COLOR_THEME["text_muted"],
                hover_color=COLOR_THEME["primary"],
                corner_radius=4,
            )
            checkbox.pack(side="left", padx=(0, 12))

            label = ctk.CTkLabel(
                checkbox_frame,
                text=cat_name,
                font=ctk.CTkFont(size=12),
                text_color=COLOR_THEME["text_primary"],
                anchor="w"
            )
            label.pack(side="left", fill="x", expand=True)

        # === Разделитель ===
        separator2 = ctk.CTkFrame(content_frame, height=2, fg_color=COLOR_THEME["border"])
        separator2.pack(fill="x", pady=Spacing.LG)

        # === Секция 3: Автоматизация (звуки + буфер обмена) ===
        auto_section = ctk.CTkFrame(content_frame, fg_color="transparent")
        auto_section.pack(fill="x", pady=(0, Spacing.LG))

        # Чекбокс: Мониторинг буфера обмена
        self.clipboard_monitor_var = ctk.BooleanVar(value=self.clipboard_monitoring)

        clipboard_frame = ctk.CTkFrame(auto_section, fg_color="transparent")
        clipboard_frame.pack(fill="x", pady=Spacing.SM)

        clipboard_checkbox = ctk.CTkCheckBox(
            clipboard_frame,
            text="Автозагрузка из буфера обмена",
            variable=self.clipboard_monitor_var,
            width=20,
            height=20,
            checkbox_width=20,
            checkbox_height=20,
            font=ctk.CTkFont(size=12),
            text_color=COLOR_THEME["text_primary"],
            fg_color=COLOR_THEME["bg_card"],
            border_color=COLOR_THEME["text_muted"],
            hover_color=COLOR_THEME["primary"],
            corner_radius=4,
        )
        clipboard_checkbox.pack(side="left")

        # Тултип для буфера обмена (задержка 3000мс по умолчанию)
        create_tooltip(
            clipboard_checkbox,
            "Автоматически начинать загрузку при появлении ссылки в буфере обмена"
        )

        # Чекбокс: Звуковые уведомления
        self.sound_enabled_var = ctk.BooleanVar(
            value=self.config_manager.get('ENABLE_SOUND_NOTIFICATIONS', True)
        )

        sound_frame = ctk.CTkFrame(auto_section, fg_color="transparent")
        sound_frame.pack(fill="x", pady=Spacing.SM)

        sound_checkbox = ctk.CTkCheckBox(
            sound_frame,
            text="Звуковые уведомления",
            variable=self.sound_enabled_var,
            width=20,
            height=20,
            checkbox_width=20,
            checkbox_height=20,
            font=ctk.CTkFont(size=12),
            text_color=COLOR_THEME["text_primary"],
            fg_color=COLOR_THEME["bg_card"],
            border_color=COLOR_THEME["text_muted"],
            hover_color=COLOR_THEME["primary"],
            corner_radius=4,
        )
        sound_checkbox.pack(side="left")

        # Тултип для звуков (задержка 3000мс по умолчанию)
        create_tooltip(
            sound_checkbox,
            "Воспроизводить звуковые сигналы при событиях (начало/окончание загрузки)"
        )

        # Кнопки действий (фиксированная высота 46px, прижаты к низу main_frame)
        buttons_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        buttons_frame.pack(fill="x", side="bottom", pady=(Spacing.XS, 0))
        
        # Фиксируем высоту кнопок: 40px кнопка + 6px отступы = 46px
        buttons_frame.configure(height=46)
        buttons_frame.pack_propagate(False)  # Запретить изменение высоты

        # Пространство
        spacer = ctk.CTkFrame(buttons_frame, fg_color="transparent")
        spacer.pack(side="left", fill="x", expand=True)

        # Кнопка "Отмена"
        cancel_btn = ctk.CTkButton(
            buttons_frame,
            text="Отмена",
            width=100,
            height=40,
            command=self.destroy,
            fg_color=COLOR_THEME["bg_card"],
            hover_color=COLOR_THEME.get("accent", COLOR_THEME["primary"]),
            corner_radius=COLOR_THEME["radius_md"],
            text_color=COLOR_THEME["text_primary"],
            font=ctk.CTkFont(size=13),
        )
        cancel_btn.pack(side="right", padx=(6, 0))

        # Кнопка "Сохранить"
        save_icon = IconManager.get("check", "✓")
        save_btn = ctk.CTkButton(
            buttons_frame,
            text=save_icon + " Сохранить",
            width=120,
            height=40,
            command=self._save_and_close,
            fg_color=COLOR_THEME["primary"],
            hover_color=COLOR_THEME["primary_hover"],
            corner_radius=COLOR_THEME["radius_md"],
            text_color=COLOR_THEME["primary_foreground"],
            font=ctk.CTkFont(size=13),
        )
        save_btn.pack(side="right", padx=(0, 6))

    def _browse_cookies(self) -> None:
        """Открыть диалог выбора файла cookies.txt."""
        initial_dir = os.path.dirname(self.cookies_path) if self.cookies_path else None
        if not initial_dir or not os.path.exists(initial_dir):
            initial_dir = os.path.expanduser("~")

        file_path = filedialog.askopenfilename(
            title="Выберите файл cookies.txt",
            initialdir=initial_dir,
            filetypes=[("Cookies files", "*.txt"), ("All files", "*.*")]
        )

        if file_path:
            self.cookies_entry.delete(0, "end")
            self.cookies_entry.insert(0, normalize_path_for_display(file_path))

    def _clear_cookies(self) -> None:
        """Очистить путь к файлу cookies.txt."""
        self.cookies_entry.delete(0, "end")

    def _save_and_close(self) -> None:
        """Сохранить настройки и закрыть диалог."""
        # Cookies path
        cookies_path = self.cookies_entry.get().strip()
        if not cookies_path:
            cookies_path = None

        # SponsorBlock категории
        selected_categories = [
            cat_id for cat_id, var in self.checkbox_vars.items() if var.get()
        ]

        # Clipboard monitoring
        clipboard_monitoring = self.clipboard_monitor_var.get()
        
        # Sound notifications
        sound_enabled = self.sound_enabled_var.get()

        if self.on_save_callback:
            self.on_save_callback(
                cookies_path, 
                selected_categories, 
                clipboard_monitoring,
                sound_enabled
            )

        self.destroy()

    def get_cookies_path(self) -> Optional[str]:
        """Получить выбранный путь к cookies.txt."""
        path = self.cookies_entry.get().strip()
        return path if path else None
