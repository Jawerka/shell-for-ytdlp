# -*- coding: utf-8 -*-
"""
Диалог настройки SponsorBlock.
"""

from typing import Callable, List
import sys

import customtkinter as ctk

from core.theme import COLOR_THEME, Spacing, setup_theme
from core.icons import IconManager


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


class SponsorBlockDialog(ctk.CTkToplevel):
    def __init__(self, parent, selected_categories: List[str], on_save: Callable[[List[str]], None]):
        self.parent = parent
        setup_theme()
        super().__init__(parent)

        self.selected_categories = set(selected_categories)
        self.on_save_callback = on_save

        self.title("Настройка SponsorBlock")
        self.geometry("500x500")
        self.minsize(500, 500)
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

        title_label = ctk.CTkLabel(
            card,
            text="Отметьте категории видео, которые нужно автоматически пропускать",
            font=ctk.CTkFont(size=13),
            text_color=COLOR_THEME["text_muted"],
            wraplength=440,
            justify="left",
        )
        title_label.pack(pady=(Spacing.LG, Spacing.MD), padx=Spacing.LG, anchor="w")

        self.checkboxes_frame = ctk.CTkFrame(card, fg_color="transparent")
        self.checkboxes_frame.pack(fill="both", expand=True, padx=Spacing.LG, pady=(0, Spacing.SM))

        self.checkbox_vars = {}
        for cat_id, cat_name in SPONSORBLOCK_CATEGORIES.items():
            var = ctk.BooleanVar(value=(cat_id in self.selected_categories))
            self.checkbox_vars[cat_id] = var

            checkbox_frame = ctk.CTkFrame(self.checkboxes_frame, fg_color="transparent")
            checkbox_frame.pack(fill="x", pady=6)

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
                font=ctk.CTkFont(size=13),
                text_color=COLOR_THEME["text_primary"],
                anchor="w"
            )
            label.pack(side="left", fill="x", expand=True)

        buttons_frame = ctk.CTkFrame(card, fg_color="transparent")
        buttons_frame.pack(fill="x", padx=Spacing.LG, pady=(Spacing.MD, Spacing.LG))

        spacer = ctk.CTkFrame(buttons_frame, fg_color="transparent")
        spacer.pack(side="left", fill="x", expand=True)

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

        save_icon = IconManager.get("save", "💾")
        save_btn = ctk.CTkButton(
            buttons_frame,
            text=save_icon,
            width=42,
            height=40,
            command=self._save_and_close,
            fg_color=COLOR_THEME["primary"],
            hover_color=COLOR_THEME["primary_hover"],
            corner_radius=COLOR_THEME["radius_md"],
            text_color=COLOR_THEME["primary_foreground"],
            font=ctk.CTkFont(size=18),
        )
        save_btn.pack(side="right", padx=(0, 6))

    def _save_and_close(self) -> None:
        selected = [cat_id for cat_id, var in self.checkbox_vars.items() if var.get()]
        if self.on_save_callback:
            self.on_save_callback(selected)
        self.destroy()

    def get_selected_categories(self) -> List[str]:
        return [cat_id for cat_id, var in self.checkbox_vars.items() if var.get()]
