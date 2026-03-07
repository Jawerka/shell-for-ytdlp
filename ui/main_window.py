# -*- coding: utf-8 -*-
"""
Главное окно приложения UI-for-ytdlp.
"""

from __future__ import annotations

import os
import sys
import threading
import socket
import logging
from typing import Optional, List, Tuple

import customtkinter as ctk
from tkinter import filedialog
from urllib.request import urlopen
from urllib.error import HTTPError, URLError
from PIL import Image

# Определение корневой директории проекта
if hasattr(sys, '_MEIPASS'):
    # Запуск из exe
    project_root = os.path.dirname(sys.executable)
else:
    # Запуск из исходного кода
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger('UI-for-ytdlp.main_window')

from core.config import ConfigManager
from core.logger import GUILogger
from core.downloader import YouTubeDownloader
from core.utils import get_clipboard_url, validate_url_for_ui, find_cookies_in_utilities, normalize_path_for_display, is_supported_video_url
from core.theme import COLOR_THEME, Spacing, setup_theme
from core.icons import IconManager
from core.notifications import send_download_complete, send_download_error
from core.deno_installer import ensure_deno_exists
from core.clipboard_monitor import ClipboardMonitor
from core.sound_manager import SoundManager

from ui.components.url_input import UrlInput
from ui.components.log_viewer import LogViewer
from ui.components.progress_bar import ProgressBarWithText
from ui.components.settings_dialog import SettingsDialog
from ui.tooltip import create_tooltip
from ui.layout_config import (
    BTN_SIZE_W, BTN_SIZE_H, BTN_FONT_SIZE,
    TEXT_FONT_SIZE,
    CARD_PADX, CARD_PADY,
    ELEMENT_GAP, ELEMENT_PADX, ELEMENT_PADY,
    CORNER_RADIUS,
    URL_WIDTH, PATH_WIDTH, PATH_HEIGHT,
    WINDOW_PADX, WINDOW_PADY,
    BUTTON_GAP,
)

from core.tray_manager import TrayManager


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.config_manager = ConfigManager()
        self.logger = GUILogger()

        self.is_downloading = False
        self.downloader: Optional[YouTubeDownloader] = None

        self.icon_download = IconManager.get("download", "⭳")
        self.icon_folder = IconManager.get("folder", "📂")
        self.icon_settings = IconManager.get("settings", "⚙")
        self.icon_clear = IconManager.get("clear", "✕")
        self.icon_paste = IconManager.get("paste", "📋")

        # Инициализация монитора буфера обмена
        self.clipboard_monitor = ClipboardMonitor(
            check_interval=2.0,
            on_url_detected=self._on_clipboard_url_detected
        )

        # Инициализация менеджера звуковых эффектов
        self.sound_manager = SoundManager(enabled=True, config_manager=self.config_manager)

        # Инициализация менеджера трея (будет создан при сворачивании)
        self.tray_manager: Optional[TrayManager] = None

        setup_theme()
        self._setup_window()
        self._create_ui()
        self._setup_hotkeys()
        self._init_path_label()
        self._init_cookies_path()

        # Запуск мониторинга буфера обмена если включено
        self.after(500, self._initialize_clipboard_monitoring)

    def _setup_window(self) -> None:
        self.title("UI-for-ytdlp")
        
        # Стандартные размеры по умолчанию (минимальные)
        default_width = 740
        default_height = 520
        
        # Восстанавливаем ТОЛЬКО позицию из настроек (размеры всегда минимальные)
        pos_x = self.config_manager.get('WINDOW_POS_X')
        pos_y = self.config_manager.get('WINDOW_POS_Y')
        
        # Устанавливаем минимальный размер
        self.minsize(default_width, default_height)
        self.configure(fg_color=COLOR_THEME["bg_primary"])
        
        # Обновляем окно чтобы получить корректные размеры экрана
        self.update()
        
        # Получаем размеры экрана после обновления
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        
        # Используем минимальные размеры
        width = default_width
        height = default_height
        
        if pos_x is not None and pos_y is not None:
            # Проверяем что позиция в пределах экрана (с запасом)
            if pos_x < -100 or pos_x > screen_w - 100 or pos_y < -100 or pos_y > screen_h - 100:
                # Если окно ушло за пределы - центрируем
                self._center_window(width, height)
            else:
                # Восстанавливаем сохранённую позицию
                self.geometry(f"{width}x{height}+{pos_x}+{pos_y}")
        else:
            # Позиционируем окно по центру экрана
            self._center_window(width, height)

        # Обработчик закрытия окна (крестик) — полное закрытие
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        # Установка иконки окна
        try:
            icon_path = os.path.join(project_root, 'icon.ico')
            if hasattr(sys, '_MEIPASS'):
                # Запуск из exe: иконка в папке с исполняемым файлом
                icon_path = os.path.join(os.path.dirname(sys.executable), 'icon.ico')
            else:
                # Запуск из исходного кода: иконка в корне проекта
                icon_path = os.path.join(project_root, 'icon.ico')
            if os.path.exists(icon_path):
                icon_img = ctk.CTkImage(light_image=Image.open(icon_path), size=(32, 32))
                self.iconphoto(True, icon_img)
        except Exception as e:
            logger.warning(f"Не удалось установить иконку окна: {e}")

    def _center_window(self, width: int, height: int) -> None:
        """
        Расположить окно по центру экрана.

        Args:
            width: Ширина окна
            height: Высота окна
        """
        # Получаем размеры экрана
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Вычисляем координаты центра
        pos_x = (screen_width // 2) - (width // 2)
        pos_y = (screen_height // 2) - (height // 2)

        # Устанавливаем позицию
        self.geometry(f"{width}x{height}+{pos_x}+{pos_y}")

    def _save_window_position(self) -> None:
        """Сохранить позицию окна в настройках (размеры не сохраняем)."""
        # Получаем текущую позицию
        pos_x = self.winfo_x()
        pos_y = self.winfo_y()

        # Сохраняем в конфиг
        self.config_manager.set('WINDOW_POS_X', pos_x)
        self.config_manager.set('WINDOW_POS_Y', pos_y)
        self.config_manager.save()

        logger.debug(f"Позиция окна сохранена: x={pos_x}, y={pos_y}")

    def _init_path_label(self) -> None:
        """Инициализировать поле пути загрузки."""
        saved_path = self.config_manager.get('DOWNLOAD_PATH', '')
        if saved_path:
            self.path_label.configure(text=saved_path, text_color=COLOR_THEME["text_primary"])

    def _init_cookies_path(self) -> None:
        """Инициализировать путь к cookies.txt."""
        saved_path = self.config_manager.get('COOKIES_PATH', '')
        if not saved_path:
            # Автоматически найти cookies.txt в utilities
            auto_path = find_cookies_in_utilities()
            if auto_path:
                self.config_manager.set('COOKIES_PATH', auto_path)
                self.config_manager.save()
                self.log_viewer.info(f"Найден cookies.txt: {normalize_path_for_display(auto_path)}")

    def _initialize_clipboard_monitoring(self) -> None:
        """Инициализировать мониторинг буфера обмена."""
        clipboard_monitoring_enabled = self.config_manager.get('CLIPBOARD_MONITORING', False)

        if clipboard_monitoring_enabled:
            self.clipboard_monitor.start()
            self.log_viewer.info("Мониторинг буфера обмена включён")
            # Проверяем буфер при старте
            self.after(300, self._check_clipboard_and_download)
        else:
            # Старая логика - просто проверяем буфер при старте
            self._check_clipboard_and_download()

    def _on_clipboard_url_detected(self, url: str) -> None:
        """
        Обработать URL, обнаруженный в буфере обмена.

        Args:
            url: Обнаруженный URL
        """
        # Используем call_soon_threadsafe для безопасного вызова из потока
        self.after(0, lambda: self._handle_clipboard_url(url))

    def _handle_clipboard_url(self, url: str) -> None:
        """
        Обработать URL из буфера обмена в главном потоке.

        Args:
            url: Обнаруженный URL
        """
        try:
            # Проверяем, не загружается ли уже что-то
            if self.is_downloading:
                self.log_viewer.info(f"Обнаружена ссылка в буфере: {url[:80]}... (загрузка уже идёт)")
                return

            # Проверяем, не та же ли это ссылка, что уже в поле ввода
            current_url = self.url_input.get_url()
            if current_url and current_url.strip() == url.strip():
                return

            # Проверяем, не загружали ли уже этот URL последним
            last_url = self.config_manager.get('LAST_DOWNLOADED_URL', '')
            if last_url and last_url.strip() == url.strip():
                self.log_viewer.info(f"📋 Ссылка уже была загружена: {url[:80]}... (пропуск)")
                return

            # Устанавливаем URL и начинаем загрузку
            self.url_input.set_url(url)
            self.log_viewer.info(f"📋 Обнаружена новая ссылка: {url[:80]}...")
            self.log_viewer.info("Начинаю загрузку автоматически...")
            self.after(500, self._start_download)
        except Exception as e:
            logger.error(f"_handle_clipboard_url: Ошибка обработки URL: {e}", exc_info=True)
            self.log_viewer.error(f"Ошибка обработки ссылки: {e}")

    def _check_clipboard_and_download(self) -> None:
        """Проверить буфер обмена и начать загрузку если есть URL."""
        url = get_clipboard_url()
        if url:
            self.url_input.set_url(url)
            self.log_viewer.info(f"Обнаружена ссылка в буфере: {url}")
            self.after(800, self._start_download)
        else:
            self.log_viewer.info("Вставьте URL или нажмите кнопку Скачать")

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
            height=BTN_SIZE_H + ELEMENT_PADY * 2
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
            entry_height=BTN_SIZE_H,
            corner_radius=CORNER_RADIUS
        )
        self.url_input.pack(side="left", fill="x", expand=True)

        # Кнопки
        buttons_frame = ctk.CTkFrame(header_inner, fg_color="transparent")
        buttons_frame.pack(side="right", padx=(ELEMENT_GAP, 0))

        btn_kwargs = {
            "width": BTN_SIZE_W,
            "height": BTN_SIZE_H,
            "corner_radius": CORNER_RADIUS,
            "text_color": COLOR_THEME["text_primary"],
            "font": ctk.CTkFont(size=BTN_FONT_SIZE),
            "anchor": "center",
        }

        # Кнопка очистки
        self.clear_button = ctk.CTkButton(
            buttons_frame,
            text=self.icon_clear,
            command=self._clear_all,
            fg_color=COLOR_THEME["accent"],
            hover_color=COLOR_THEME["accent_hover"],
            **btn_kwargs
        )
        self.clear_button.pack(side="left", padx=(0, BUTTON_GAP), fill="y")
        create_tooltip(self.clear_button, "Очистить URL, логи и прогресс", delay=3000)

        # Кнопка настроек (cookies + SponsorBlock)
        self.settings_button = ctk.CTkButton(
            buttons_frame,
            text=self.icon_settings,
            command=self._open_settings,
            fg_color=COLOR_THEME["accent"],
            hover_color=COLOR_THEME["accent_hover"],
            **btn_kwargs
        )
        self.settings_button.pack(side="left", padx=(0, BUTTON_GAP), fill="y")
        create_tooltip(self.settings_button, "Настройки (cookies.txt, SponsorBlock)", delay=3000)

        # Кнопка выбора папки
        self.folder_button = ctk.CTkButton(
            buttons_frame,
            text=self.icon_folder,
            command=self._select_folder,
            fg_color=COLOR_THEME["accent"],
            hover_color=COLOR_THEME["accent_hover"],
            **btn_kwargs
        )
        self.folder_button.pack(side="left", padx=(0, BUTTON_GAP), fill="y")
        create_tooltip(self.folder_button, "Выбрать папку для загрузки (Ctrl+O)", delay=3000)

        # Кнопка вставки
        self.paste_button = ctk.CTkButton(
            buttons_frame,
            text=self.icon_paste,
            command=lambda: self.url_input._paste_from_clipboard(),
            fg_color=COLOR_THEME["accent"],
            hover_color=COLOR_THEME["accent_hover"],
            **btn_kwargs
        )
        self.paste_button.pack(side="left", padx=(0, BUTTON_GAP), fill="y")
        create_tooltip(self.paste_button, "Вставить URL из буфера обмена (Ctrl+V)", delay=3000)

        # Кнопка загрузки
        self.download_button = ctk.CTkButton(
            buttons_frame,
            text=self.icon_download,
            command=self._start_download,
            fg_color=COLOR_THEME["primary"],
            hover_color=COLOR_THEME["primary_hover"],
            **btn_kwargs
        )
        self.download_button.pack(side="left", fill="y")
        create_tooltip(self.download_button, "Начать загрузку (Ctrl+Enter)", delay=3000)

        # Поле пути загрузки
        self.path_label = ctk.CTkLabel(
            self.main_frame,
            text="Выберите папку для загрузки",
            font=ctk.CTkFont(size=TEXT_FONT_SIZE),
            text_color=COLOR_THEME["text_muted"],
            height=PATH_HEIGHT,
            corner_radius=CORNER_RADIUS,
            fg_color=COLOR_THEME["bg_card"],
            anchor="center"
        )
        self.path_label.pack(fill="x", padx=0, pady=(0, ELEMENT_GAP))
        create_tooltip(self.path_label, "Текущая папка для загрузок. Нажмите 📂 для изменения", delay=3000)

        # Подсветка поля пути при наведении
        self._setup_path_hover()

        # Добавляем возможность открытия папки по клику
        self._setup_path_click()

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
            bar_height=BTN_SIZE_H,
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
            self.path_label.configure(text=folder, text_color=COLOR_THEME["text_primary"])
            self.log_viewer.success(f"Папка загрузки: {normalize_path_for_display(folder)}")
    
    def _open_settings(self) -> None:
        """Открыть объединённые настройки (cookies + SponsorBlock)."""
        current_cookies_path = self.config_manager.get('COOKIES_PATH', '')
        current_categories = self.config_manager.get('SPONSORBLOCK_REMOVE_LIST', ['sponsor', 'selfpromo'])

        def on_save(
            cookies_path: Optional[str], 
            categories: List[str], 
            clipboard_monitoring: bool,
            sound_enabled: bool
        ):
            # Сохранение cookies path
            self.config_manager.set('COOKIES_PATH', cookies_path if cookies_path else '')

            # Сохранение категорий SponsorBlock
            self.config_manager.set('SPONSORBLOCK_REMOVE_LIST', categories)
            self.config_manager.save()

            # Логи
            if cookies_path:
                if os.path.exists(cookies_path):
                    self.log_viewer.success(f"cookies.txt: {normalize_path_for_display(cookies_path)}")
                else:
                    self.log_viewer.warning(f"cookies.txt не найден: {normalize_path_for_display(cookies_path)}")
            else:
                self.log_viewer.info("cookies.txt отключен")

            if categories:
                self.log_viewer.info(f"SponsorBlock: {len(categories)} категорий выбрано")
            else:
                self.log_viewer.info("SponsorBlock отключен")

            # Сохранение настройки мониторинга буфера обмена
            self.config_manager.set('CLIPBOARD_MONITORING', clipboard_monitoring)
            self.config_manager.save()

            # Сохранение настройки звуковых уведомлений
            self.config_manager.set('ENABLE_SOUND_NOTIFICATIONS', sound_enabled)
            self.config_manager.save()

            # Запуск или остановка мониторинга
            if clipboard_monitoring:
                self.clipboard_monitor.start()
                self.log_viewer.info("Мониторинг буфера обмена включён")
            else:
                self.clipboard_monitor.stop()
                self.log_viewer.info("Мониторинг буфера обмена отключён")

            # Обновление настройки звуков
            self.sound_manager.set_enabled(sound_enabled)
            if sound_enabled:
                self.log_viewer.info("Звуковые уведомления включены")
            else:
                self.log_viewer.info("Звуковые уведомления отключены")

        clipboard_monitoring_enabled = self.config_manager.get('CLIPBOARD_MONITORING', False)
        dialog = SettingsDialog(
            self,
            current_cookies_path,
            current_categories,
            clipboard_monitoring_enabled,
            on_save,
            config_manager=self.config_manager
        )
        dialog.focus()

    def _setup_path_hover(self) -> None:
        """Настроить hover-эффект для поля пути."""
        normal_color = COLOR_THEME["bg_card"]
        hover_color = COLOR_THEME["bg_secondary"]

        def on_enter(event):
            self.path_label.configure(fg_color=hover_color)

        def on_leave(event):
            self.path_label.configure(fg_color=normal_color)

        self.path_label.bind("<Enter>", on_enter)
        self.path_label.bind("<Leave>", on_leave)

    def _setup_path_click(self) -> None:
        """Настроить открытие папки по клику на поле пути."""
        import subprocess
        import sys

        def on_click(event):
            current_path = self.path_label.cget("text")
            
            # Проверка: путь не выбран
            if current_path == "Выберите папку для загрузки":
                self.log_viewer.info("Нажмите 📂 для выбора папки")
                return
            
            # Проверка: пустой путь
            if not current_path or not current_path.strip():
                self.log_viewer.warning("Путь к папке не указан")
                return
            
            # Проверка: папка существует
            if not os.path.exists(current_path):
                self.log_viewer.error(f"Папка не найдена: {normalize_path_for_display(current_path)}")
                return
            
            # Проверка: это действительно папка
            if not os.path.isdir(current_path):
                self.log_viewer.error(f"Указанный путь не является папкой: {normalize_path_for_display(current_path)}")
                return
            
            # Попытка открыть папку
            try:
                if sys.platform == "win32":
                    os.startfile(current_path)
                    self.log_viewer.info(f"Открыта папка: {normalize_path_for_display(current_path)}")
                elif sys.platform == "darwin":  # macOS
                    subprocess.run(["open", current_path], check=True, timeout=5)
                    self.log_viewer.info(f"Открыта папка: {normalize_path_for_display(current_path)}")
                else:  # Linux и другие Unix-системы
                    subprocess.run(["xdg-open", current_path], check=True, timeout=5)
                    self.log_viewer.info(f"Открыта папка: {normalize_path_for_display(current_path)}")
            except subprocess.TimeoutExpired:
                self.log_viewer.warning("Превышено время открытия папки")
            except FileNotFoundError:
                self.log_viewer.error("Не найдена команда для открытия папки")
            except PermissionError:
                self.log_viewer.error(f"Нет доступа к папке: {normalize_path_for_display(current_path)}")
            except OSError as e:
                self.log_viewer.error(f"Системная ошибка: {e}")
            except Exception as e:
                self.log_viewer.error(f"Не удалось открыть папку: {e}")

        self.path_label.bind("<Button-1>", on_click)

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

        # Проверка: не загружали ли уже этот URL
        last_url = self.config_manager.get('LAST_DOWNLOADED_URL', '')
        if last_url and last_url == url:
            self.log_viewer.warning("Этот URL уже был загружен последним. Пропускаю повторную загрузку.")
            return

        # Воспроизведение звука начала загрузки (сразу при нажатии кнопки)
        self.sound_manager.play_start_download()

        # Приостановка мониторинга буфера обмена на время загрузки
        if self.clipboard_monitor.is_running():
            self.clipboard_monitor.pause()
            logger.debug("Мониторинг буфера обмена приостановлен на время загрузки")

        # Сохранение конфигурации перед загрузкой
        self.config_manager.save()
        logger.debug("_start_download: Конфигурация сохранена")

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
        """Обновить утилиты в отдельном потоке.
        Обновляется только yt-dlp, ffmpeg не обновляется если существует.
        """
        logger.debug("_update_utilities: Начало")

        self.after(0, lambda: self.log_viewer.info("Проверка обновлений утилит..."))

        # Проверка и установка deno (JavaScript runtime для YouTube)
        utilities_path = self.config_manager.get('UTILITIES_PATH', '')
        if utilities_path:
            self.after(0, lambda: self.log_viewer.info("Проверка JavaScript runtime (deno)..."))
            
            def deno_progress(msg):
                """Обновление прогресса загрузки deno."""
                self.after(0, lambda: self.log_viewer.info(msg))
                # Обновляем прогресс-бар если есть процент
                if '%' in msg:
                    try:
                        percent = float(msg.split('%')[0].split(': ')[1])
                        self.after(0, lambda p=percent, m=msg: self.progress_bar.update_progress(p, text=m))
                    except (ValueError, IndexError):
                        pass
            
            if not ensure_deno_exists(utilities_path, deno_progress):
                self.after(0, lambda: self.log_viewer.warning(
                    "deno не установлен. Некоторые форматы YouTube могут быть недоступны.\n"
                    "Скачайте с https://github.com/denoland/deno/releases/latest"
                ))
            else:
                self.after(0, lambda: self.log_viewer.success("JavaScript runtime (deno) готов"))

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

                from core.updater import check_needs_update
                save_path = os.path.join(utilities_path, save_name)

                # ffmpeg не обновляем если файлы уже распакованы
                if 'ffmpeg' in save_name.lower():
                    ffmpeg_file_list = ['ffmpeg.exe', 'ffplay.exe', 'ffprobe.exe']
                    # Проверяем наличие ВСЕХ файлов ffmpeg
                    ffmpeg_exists = all(
                        os.path.exists(os.path.join(utilities_path, ff_file))
                        for ff_file in ffmpeg_file_list
                    )
                    if ffmpeg_exists:
                        logger.debug(f"_update_utilities: ffmpeg уже распакован, пропускаем")
                        self.after(0, lambda sn=save_name: self.log_viewer.success(f"{sn} актуален"))
                        continue
                    else:
                        # Логируем каких файлов не хватает
                        missing_files = [
                            ff_file for ff_file in ffmpeg_file_list
                            if not os.path.exists(os.path.join(utilities_path, ff_file))
                        ]
                        logger.debug(f"_update_utilities: Отсутствуют ffmpeg утилиты: {missing_files}")
                        self.after(0, lambda mf=missing_files: self.log_viewer.info(
                            f"Распаковка ffmpeg (отсутствуют: {', '.join(mf)})"))
                        # Форсируем загрузку если файлы отсутствуют
                        force_update = True
                else:
                    force_update = False

                if force_update or check_needs_update(url, save_path):
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
            # Сохраняем последний успешно загруженный URL
            self.config_manager.set('LAST_DOWNLOADED_URL', url)
            self.config_manager.save()
            
            self.after(0, lambda: self.log_viewer.success("Загрузка завершена"))
            self.after(100, lambda: send_download_complete("Загрузка завершена", "Видео успешно загружено"))
            self.after(150, lambda: self.sound_manager.play_end_download())
        else:
            self.after(0, lambda: self.log_viewer.error("Ошибка загрузки"))
            self.after(100, lambda: send_download_error("Ошибка загрузки", "Произошла ошибка при загрузке видео"))
            # Звук ошибки зарезервирован на будущее
            # self.after(150, lambda: self.sound_manager.play_error_download())

    def _on_download_complete(self) -> None:
        """Завершение загрузки."""
        self.is_downloading = False
        self.download_button.configure(
            state="normal",
            text=self.icon_download,
            font=ctk.CTkFont(size=18)
        )
        self.downloader = None

        # Возобновляем мониторинг буфера обмена после завершения загрузки
        if self.clipboard_monitor.is_running():
            self.clipboard_monitor.resume()
            logger.debug("Мониторинг буфера обмена возобновлен")

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

        # Ctrl+S — настройки (cookies + SponsorBlock)
        self.bind('<Control-s>', lambda e: self._open_settings())
        self.bind('<Control-S>', lambda e: self._open_settings())

        # Esc — отмена загрузки
        self.bind('<Escape>', lambda e: self._cancel_download())
        
        # Обработчик сворачивания окна — в трей
        self.bind('<Unmap>', lambda e: self._on_minimize())

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

    def _on_minimize(self) -> None:
        """Обработчик события сворачивания окна."""
        # Проверка: окно действительно свёрнуто (не закрыто)
        if self.state() == 'iconic':
            self._minimize_to_tray()

    def _minimize_to_tray(self) -> None:
        """Свернуть окно в трей."""
        # Скрыть окно
        self.withdraw()
        
        # Создать и показать иконку в трее если ещё не создана
        if self.tray_manager is None:
            self.tray_manager = TrayManager(
                clipboard_monitor=self.clipboard_monitor,
                sound_manager=self.sound_manager,
                config_manager=self.config_manager,
                on_restore=self._restore_from_tray,
                on_paste_and_download=self._paste_and_download_from_tray,
                on_open_settings=self._open_settings_from_tray,
                on_exit=self._exit_application,
                root_window=self
            )
        
        if not self.tray_manager.is_visible():
            self.tray_manager.show()
        
        logger.debug("_minimize_to_tray: Окно свёрнуто в трей")

    def _on_closing(self) -> None:
        """Обработчик закрытия окна (крестик) — полное закрытие приложения."""
        logger.debug("_on_closing: Закрытие приложения")

        # Сохранить позицию окна перед закрытием
        self._save_window_position()

        # Остановить трей если есть
        if self.tray_manager:
            self.tray_manager.stop()

        # Остановить мониторинг буфера обмена
        if self.clipboard_monitor.is_running():
            self.clipboard_monitor.stop()

        # Остановить звуковой менеджер
        self.sound_manager.shutdown()

        # Сохранить конфигурацию
        self.config_manager.save()
        logger.debug("_on_closing: Конфигурация сохранена")

        # Закрыть окно
        self.destroy()

    def _restore_from_tray(self) -> None:
        """Восстановить окно из трея (вызывается из главного потока)."""
        self.deiconify()
        self.focus_force()
        if self.tray_manager:
            self.tray_manager.hide()
        logger.debug("_restore_from_tray: Окно восстановлено")

    def _paste_and_download_from_tray(self) -> None:
        """Вставить URL из буфера и начать загрузку (из трея)."""
        from core.utils import get_clipboard_url
        
        url = get_clipboard_url()
        if url:
            self.url_input.set_url(url)
            self.log_viewer.info(f"📋 URL из буфера: {url[:80]}...")
            self._start_download()
        else:
            self.log_viewer.warning("📋 Буфер обмена не содержит URL")

    def _open_settings_from_tray(self) -> None:
        """Открыть настройки из трея."""
        # Восстановить окно перед открытием настроек
        self._restore_from_tray()
        self.after(200, self._open_settings)

    def _exit_application(self) -> None:
        """Полный выход из приложения."""
        logger.debug("_exit_application: Выход из приложения")
        
        # Остановить трей
        if self.tray_manager:
            self.tray_manager.stop()
        
        # Остановить мониторинг
        if self.clipboard_monitor.is_running():
            self.clipboard_monitor.stop()
        
        # Остановить звук
        self.sound_manager.shutdown()
        
        # Сохранить конфиг
        self.config_manager.save()
        logger.debug("_exit_application: Конфигурация сохранена")
        
        # Закрыть окно
        self.destroy()
