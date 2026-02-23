# -*- coding: utf-8 -*-
"""
Главное окно приложения UI-for-ytdlp.
"""

import os
import threading
import socket
import logging
from typing import Optional, List, Tuple

import customtkinter as ctk
from tkinter import filedialog
from urllib.request import urlopen
from urllib.error import HTTPError, URLError

logger = logging.getLogger('UI-for-ytdlp.main_window')

from core.config import ConfigManager
from core.logger import GUILogger
from core.downloader import YouTubeDownloader
from core.utils import get_clipboard_url, validate_url_for_ui
from core.theme import COLOR_THEME, Spacing, setup_theme
from core.icons import IconManager
from core.notifications import send_download_complete, send_download_error

from ui.components.url_input import UrlInput
from ui.components.log_viewer import LogViewer
from ui.components.progress_bar import ProgressBarWithText
from ui.components.sponsorblock_dialog import SponsorBlockDialog
from ui.layout_config import (
    BTN_SIZE, BTN_FONT_SIZE,
    TEXT_FONT_SIZE,
    CARD_PADX, CARD_PADY,
    ELEMENT_GAP, ELEMENT_PADX, ELEMENT_PADY,
    CORNER_RADIUS,
    URL_WIDTH,
    WINDOW_PADX, WINDOW_PADY,
    BUTTON_GAP,
)


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.config_manager = ConfigManager()
        self.logger = GUILogger()

        self.is_downloading = False
        self.downloader: Optional[YouTubeDownloader] = None

        self.icon_download = IconManager.get("download", "⭳")
        self.icon_folder = IconManager.get("folder", "📂")
        self.icon_sponsorblock = IconManager.get("sponsorblock", "🛡")
        self.icon_clear = IconManager.get("clear", "✕")
        self.icon_paste = IconManager.get("paste", "⧉")

        setup_theme()
        self._setup_window()
        self._create_ui()
        self._setup_hotkeys()

        self.after(500, self._check_clipboard_and_download)

    def _setup_window(self) -> None:
        self.title("UI-for-ytdlp")
        self.geometry("740x520")
        self.minsize(740, 520)
        self.configure(fg_color=COLOR_THEME["bg_primary"])
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _create_ui(self) -> None:
        """Создать пользовательский интерфейс с едиными отступами."""
        # Внешняя область
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=WINDOW_PADX, pady=WINDOW_PADY)

        # Header карточка
        header_card = ctk.CTkFrame(
            self.main_frame,
            fg_color=COLOR_THEME["bg_card"],
            corner_radius=CORNER_RADIUS,
            border_width=0,
            height=BTN_SIZE + ELEMENT_PADY * 2
        )
        header_card.pack(fill="x", padx=0, pady=(0, ELEMENT_GAP))

        # Внутренняя область header
        header_inner = ctk.CTkFrame(header_card, fg_color="transparent")
        header_inner.pack(fill="x", padx=ELEMENT_PADX, pady=ELEMENT_PADY)

        # URL input
        self.url_input = UrlInput(
            header_inner,
            on_paste=self._on_url_paste,
            entry_width=URL_WIDTH,
            entry_height=BTN_SIZE,
            corner_radius=CORNER_RADIUS
        )
        self.url_input.pack(side="left", fill="x", expand=True)

        # Кнопки
        buttons_frame = ctk.CTkFrame(header_inner, fg_color="transparent")
        buttons_frame.pack(side="right", padx=(ELEMENT_GAP, 0))

        btn_kwargs = {
            "width": BTN_SIZE,
            "height": BTN_SIZE,
            "corner_radius": CORNER_RADIUS,
            "text_color": COLOR_THEME["text_primary"],
            "font": ctk.CTkFont(size=BTN_FONT_SIZE),
            "anchor": "center",
        }

        # Кнопка вставки (теперь такая же как остальные)
        self.paste_button = ctk.CTkButton(
            buttons_frame,
            text=self.icon_paste,
            command=lambda: self.url_input._paste_from_clipboard(),
            fg_color=COLOR_THEME["accent"],
            hover_color=COLOR_THEME["accent_hover"],
            **btn_kwargs
        )
        self.paste_button.pack(side="left", padx=(0, BUTTON_GAP))

        # Кнопка очистки (новая)
        self.clear_button = ctk.CTkButton(
            buttons_frame,
            text=self.icon_clear,
            command=self._clear_all,
            fg_color=COLOR_THEME["accent"],
            hover_color=COLOR_THEME["accent_hover"],
            **btn_kwargs
        )
        self.clear_button.pack(side="left", padx=(0, BUTTON_GAP))

        self.folder_button = ctk.CTkButton(
            buttons_frame,
            text=self.icon_folder,
            command=self._select_folder,
            fg_color=COLOR_THEME["accent"],
            hover_color=COLOR_THEME["accent_hover"],
            **btn_kwargs
        )
        self.folder_button.pack(side="left", padx=(0, BUTTON_GAP))

        self.sponsorblock_button = ctk.CTkButton(
            buttons_frame,
            text=self.icon_sponsorblock,
            command=self._open_sponsorblock_settings,
            fg_color=COLOR_THEME["accent"],
            hover_color=COLOR_THEME["accent_hover"],
            **btn_kwargs
        )
        self.sponsorblock_button.pack(side="left", padx=(0, BUTTON_GAP))

        self.download_button = ctk.CTkButton(
            buttons_frame,
            text=self.icon_download,
            command=self._start_download,
            fg_color=COLOR_THEME["primary"],
            hover_color=COLOR_THEME["primary_hover"],
            **btn_kwargs
        )
        self.download_button.pack(side="left")

        # Контент: лог + прогресс
        content = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        content.pack(fill="both", expand=True)

        # Logs карточка
        logs_card = ctk.CTkFrame(
            content,
            fg_color=COLOR_THEME["bg_card"],
            corner_radius=CORNER_RADIUS,
            border_width=0
        )
        logs_card.pack(fill="both", expand=True, padx=0, pady=(0, ELEMENT_GAP))

        # LogViewer
        self.log_viewer = LogViewer(
            logs_card,
            font=ctk.CTkFont(family="Consolas", size=TEXT_FONT_SIZE),
            corner_radius=CORNER_RADIUS,
            padx=ELEMENT_PADX,
            pady=ELEMENT_PADY
        )
        self.log_viewer.pack(fill="both", expand=True, padx=CARD_PADX, pady=CARD_PADY)

        # Progress bar (на всю ширину карточки, отступы только у полоски)
        self.progress_bar = ProgressBarWithText(
            content,
            bar_height=BTN_SIZE,
            font_size=TEXT_FONT_SIZE,
            corner_radius=CORNER_RADIUS
        )
        self.progress_bar.pack(fill="x", side="bottom")

    def _clear_all(self) -> None:
        """Сбросить URL, логи и прогресс-бар для новой загрузки."""
        # Очистить URL
        self.url_input.clear()
        # Очистить логи
        self.log_viewer.clear()
        # Сбросить прогресс-бар
        self.progress_bar.reset()
        # Разблокировать кнопку загрузки
        if self.is_downloading:
            self.is_downloading = False
            self.download_button.configure(
                state="normal",
                text=self.icon_download,
                font=ctk.CTkFont(size=BTN_FONT_SIZE)
            )
            if self.downloader:
                self.downloader.cancel()
                self.downloader = None
    
    def _check_clipboard_and_download(self) -> None:
        """Проверить буфер обмена и начать загрузку если есть URL."""
        url = get_clipboard_url()
        if url:
            self.url_input.set_url(url)
            self.log_viewer.info(f"Обнаружена ссылка в буфере: {url}")
            self.after(800, self._start_download)
        else:
            self.log_viewer.info("Вставьте URL или нажмите кнопку Скачать")
    
    def _on_url_paste(self) -> None:
        """Обработчик вставки URL."""
        url = self.url_input.get_url()
        is_valid, message = validate_url_for_ui(url)
        if is_valid:
            self.log_viewer.info(f"URL вставлен: {url[:100]}")
        else:
            self.log_viewer.warning(f"Невалидный URL: {message}")
    
    def _select_folder(self) -> None:
        """Выбрать папку для загрузки."""
        initial_dir = self.config_manager.get('DOWNLOAD_PATH', os.path.expanduser("~"))
        folder = filedialog.askdirectory(
            title="Выберите папку для загрузки",
            initialdir=initial_dir
        )
        if folder:
            self.config_manager.set('DOWNLOAD_PATH', folder)
            self.config_manager.save()
            self.log_viewer.success(f"Папка загрузки: {folder}")
    
    def _open_sponsorblock_settings(self) -> None:
        """Открыть настройки SponsorBlock."""
        current_categories = self.config_manager.get('SPONSORBLOCK_REMOVE_LIST', ['sponsor', 'selfpromo'])

        def on_save(categories: List[str]):
            self.config_manager.set('SPONSORBLOCK_REMOVE_LIST', categories)
            self.config_manager.save()
            if categories:
                self.log_viewer.info(f"SponsorBlock: {len(categories)} категорий выбрано")
            else:
                self.log_viewer.info("SponsorBlock отключен")

        dialog = SponsorBlockDialog(self, current_categories, on_save)
        dialog.focus()

    def _validate_and_prepare_url(self, url: str) -> Tuple[bool, str]:
        """
        Проверить и подготовить URL.

        Args:
            url: URL для проверки

        Returns:
            Кортеж (валиден, результат)
        """
        if not url:
            return False, "Введите URL"

        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            return False, "URL должен начинаться с http:// или https://"

        try:
            response = urlopen(url, timeout=10)
            response.close()
            return True, url
        except HTTPError as err:
            self.log_viewer.warning(f"Сервер ответил кодом {err.code}")
            return True, url
        except socket.timeout:
            return False, "Превышено время ожидания (таймаут)"
        except URLError as err:
            return False, f"Ошибка сети: {err.reason}"
        except ValueError:
            return False, "Неверный формат URL"
    
    def _start_download(self) -> None:
        """Начать загрузку."""
        if self.is_downloading:
            self.log_viewer.warning("Загрузка уже выполняется")
            return

        url = self.url_input.get_url()
        is_valid, result = self._validate_and_prepare_url(url)

        if not is_valid:
            self.log_viewer.error(result)
            return

        url = result

        # Блокировка кнопки
        self.is_downloading = True
        self.download_button.configure(
            state="disabled",
            text=self.icon_download,
            font=ctk.CTkFont(size=18)
        )
        self.progress_bar.reset()
        
        # Показываем статус обновления утилит
        self.progress_bar.update_progress(0, text="Проверка утилит...")

        # Запуск потока обновления и загрузки
        thread = threading.Thread(target=self._update_and_download, args=(url,), daemon=True)
        thread.start()

    def _update_and_download(self, url: str) -> None:
        """
        Поток обновления утилит и загрузки.
        
        Args:
            url: URL для загрузки
        """
        # Обновление утилит
        self._update_utilities()
        
        # Если загрузка ещё актуальна - продолжаем
        if not self.is_downloading:
            return
        
        # Запуск загрузки
        self._download_thread(url)

    def _update_utilities(self) -> None:
        """Обновить утилиты в отдельном потоке."""
        logger.debug("_update_utilities: Начало")
        
        self.after(0, lambda: self.log_viewer.info("Проверка обновлений утилит..."))
        
        urls = self.config_manager.get('URL_UTILITIES_UPDATE', [])
        utilities_path = self.config_manager.get('UTILITIES_PATH', '')
        
        updated_count = 0
        
        def progress_callback(filename: str, uploaded: int, total: int):
            percent = (uploaded / total * 100) if total > 0 else 0
            size_uploaded = uploaded // 1024 // 1024
            size_total = total // 1024 // 1024
            self.after(0, lambda: self.log_viewer.info(
                f"{filename}: {percent:.1f}% ({size_uploaded}MB / {size_total}MB)"
            ))
            # Обновляем прогресс-бар
            self.after(0, lambda: self.progress_bar.update_progress(
                percent,
                text=f"Обновление {filename}: {size_uploaded}MB / {size_total}MB"
            ))

        try:
            for url in urls:
                if not self.is_downloading:  # Проверка отмены
                    break
                    
                save_name = os.path.basename(url)
                logger.debug(f"_update_utilities: Проверка {save_name}")
                
                # Быстрая проверка по размеру
                from core.updater import check_needs_update
                save_path = os.path.join(utilities_path, save_name)
                
                if check_needs_update(url, save_path):
                    self.after(0, lambda: self.log_viewer.info(f"Загрузка {save_name}..."))
                    
                    def _progress_wrapper(uploaded, total, fn=save_name):
                        progress_callback(fn, uploaded, total)
                    
                    from core.updater import update_utilities
                    if update_utilities(url, utilities_path, _progress_wrapper):
                        updated_count += 1
                        logger.debug(f"_update_utilities: {save_name} обновлён")
                    else:
                        logger.debug(f"_update_utilities: {save_name} ошибка")
                else:
                    logger.debug(f"_update_utilities: {save_name} актуален")
                    self.after(0, lambda: self.log_viewer.success(f"{save_name} актуален"))
            
            if updated_count > 0:
                self.after(0, lambda: self.log_viewer.success(f"Обновлено утилит: {updated_count}"))
            else:
                self.after(0, lambda: self.log_viewer.success("Утилиты актуальны"))
                
        except Exception as e:
            logger.error(f"_update_utilities: Ошибка: {e}", exc_info=True)
            self.after(0, lambda: self.log_viewer.warning(f"Ошибка обновления: {e}"))
        
        # Сброс прогресс-бара после обновления
        self.after(0, lambda: self.progress_bar.reset())
        logger.debug("_update_utilities: Завершено")
    
    def _download_thread(self, url: str) -> None:
        """
        Поток загрузки.

        Args:
            url: URL для загрузки
        """
        def log_callback(message: str, level: str):
            self.after(0, lambda: getattr(self.log_viewer, level)(message))

        def progress_callback(percent: float, info: str):
            self.after(0, lambda: self.progress_bar.update_progress(percent, info=info))

        self.downloader = YouTubeDownloader(self.config_manager, log_callback, progress_callback)
        success = self.downloader.download(url)

        self.after(0, self._on_download_complete)

        if success:
            self.after(0, lambda: self.log_viewer.success("Загрузка завершена"))
            self.after(100, lambda: send_download_complete("Загрузка завершена", "Видео успешно загружено"))
        else:
            self.after(0, lambda: self.log_viewer.error("Ошибка загрузки"))
            self.after(100, lambda: send_download_error("Ошибка загрузки", "Произошла ошибка при загрузке видео"))

    def _on_download_complete(self) -> None:
        """Завершение загрузки."""
        self.is_downloading = False
        self.download_button.configure(
            state="normal",
            text=self.icon_download,
            font=ctk.CTkFont(size=18)
        )
        self.downloader = None

    def _setup_hotkeys(self) -> None:
        """Настроить горячие клавиши."""
        # Ctrl+Enter — начать загрузку
        self.bind('<Control-Return>', lambda e: self._start_download())
        self.bind('<Control-KP_Enter>', lambda e: self._start_download())  # Для цифровой клавиатуры

        # Ctrl+O — выбрать папку
        self.bind('<Control-o>', lambda e: self._select_folder())
        self.bind('<Control-O>', lambda e: self._select_folder())

        # Ctrl+L — очистить логи
        self.bind('<Control-l>', lambda e: self.log_viewer.clear())
        self.bind('<Control-L>', lambda e: self.log_viewer.clear())

        # Ctrl+S — настройки SponsorBlock
        self.bind('<Control-s>', lambda e: self._open_sponsorblock_settings())
        self.bind('<Control-S>', lambda e: self._open_sponsorblock_settings())

        # Esc — отмена загрузки
        self.bind('<Escape>', lambda e: self._cancel_download())

    # Drag & Drop требует tkinterdnd2, отключено до установки зависимости
    # def _setup_drag_and_drop(self) -> None:
    #     """Настроить поддержку Drag & Drop."""
    #     self.drop_target_register()
    #     self.bind("<<Drop>>", self._on_drop)

    def _cancel_download(self) -> None:
        """Отменить загрузку."""
        if self.is_downloading:
            if self.downloader:
                self.downloader.cancel()
                self.log_viewer.warning("Загрузка отменена пользователем")

    def _on_closing(self) -> None:
        """Обработчик закрытия окна."""
        if self.is_downloading:
            # Создаём кастомный диалог подтверждения в тёмной теме
            dialog = ctk.CTkToplevel(self)
            dialog.title("Загрузка выполняется")
            dialog.geometry("400x150")
            dialog.transient(self)
            dialog.grab_set()
            
            # Настройка тёмной темы
            dialog.configure(fg_color=COLOR_THEME["bg_primary"])
            
            # Заголовок
            title_label = ctk.CTkLabel(
                dialog,
                text="Загрузка ещё не завершена",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=COLOR_THEME["text_primary"]
            )
            title_label.pack(pady=(Spacing.LG, Spacing.SM))
            
            # Сообщение
            msg_label = ctk.CTkLabel(
                dialog,
                text="Закрыть приложение?",
                font=ctk.CTkFont(size=12),
                text_color=COLOR_THEME["text_muted"]
            )
            msg_label.pack(pady=(0, Spacing.LG))
            
            # Кнопки
            buttons_frame = ctk.CTkFrame(dialog, fg_color="transparent")
            buttons_frame.pack(pady=Spacing.SM)
            
            def on_cancel():
                dialog.destroy()
            
            def on_ok():
                if self.downloader:
                    self.downloader.cancel()
                dialog.destroy()
                self.destroy()
            
            cancel_btn = ctk.CTkButton(
                buttons_frame,
                text="Отмена",
                width=100,
                command=on_cancel,
                fg_color=COLOR_THEME["bg_card"],
                hover_color=COLOR_THEME["accent"],
                text_color=COLOR_THEME["text_primary"],
                font=ctk.CTkFont(size=12),
                corner_radius=COLOR_THEME["radius_md"],
            )
            cancel_btn.pack(side="left", padx=(0, Spacing.SM))
            
            ok_btn = ctk.CTkButton(
                buttons_frame,
                text="Закрыть",
                width=100,
                command=on_ok,
                fg_color=COLOR_THEME["primary"],
                hover_color=COLOR_THEME["primary_hover"],
                text_color=COLOR_THEME["primary_foreground"],
                font=ctk.CTkFont(size=12),
                corner_radius=COLOR_THEME["radius_md"],
            )
            ok_btn.pack(side="left")
        else:
            self.destroy()
