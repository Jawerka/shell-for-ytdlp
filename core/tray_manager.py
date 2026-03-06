# -*- coding: utf-8 -*-
"""
Менеджер системного трея.

Отвечает за:
- Отображение иконки в трее
- Контекстное меню (ПКМ)
- Обработку команд меню
- Синхронизацию состояния с приложением
"""

import logging
import sys
import os
from typing import Optional, Callable

try:
    import pystray
    from pystray import Icon, MenuItem, Menu
    from PIL import Image
    
    PYSTRAY_AVAILABLE = True
except ImportError:
    PYSTRAY_AVAILABLE = False
    logger = logging.getLogger('UI-for-ytdlp.tray_manager')
    logger.warning("pystray не установлен. Функционал трея будет отключён.")

from core.clipboard_monitor import ClipboardMonitor
from core.sound_manager import SoundManager
from core.config import ConfigManager

logger = logging.getLogger('UI-for-ytdlp.tray_manager')


class TrayManager:
    """
    Менеджер системного трея приложения.

    Создаёт иконку в трее с контекстным меню для быстрого управления.
    Позволяет сворачивать приложение в трей и восстанавливать из него.

    Attributes:
        clipboard_monitor: Менеджер буфера обмена
        sound_manager: Менеджер звуковых эффектов
        config_manager: Менеджер конфигурации
    """

    def __init__(
        self,
        clipboard_monitor: ClipboardMonitor,
        sound_manager: SoundManager,
        config_manager: ConfigManager,
        on_restore: Callable[[], None],
        on_paste_and_download: Callable[[], None],
        on_open_settings: Callable[[], None],
        on_exit: Callable[[], None],
        root_window=None
    ):
        """
        Инициализировать менеджер трея.

        Args:
            clipboard_monitor: Менеджер буфера обмена
            sound_manager: Менеджер звуковых эффектов
            config_manager: Менеджер конфигурации
            on_restore: Callback для восстановления окна
            on_paste_and_download: Callback для вставки и загрузки URL
            on_open_settings: Callback для открытия настроек
            on_exit: Callback для выхода из приложения
            root_window: Корневое окно tkinter (для after())
        """
        self.clipboard_monitor = clipboard_monitor
        self.sound_manager = sound_manager
        self.config_manager = config_manager
        self.on_restore = on_restore
        self.on_paste_and_download = on_paste_and_download
        self.on_open_settings = on_open_settings
        self.on_exit = on_exit
        self.root_window = root_window

        self._icon: Optional[Icon] = None
        self._visible = False

        logger.debug("TrayManager инициализирован")

    def _get_icon_path(self) -> Optional[str]:
        """
        Получить путь к файлу иконки.

        Returns:
            Путь к icon.ico или None если не найден
        """
        # Проверка различных путей
        possible_paths = [
            os.path.join(os.getcwd(), 'icon.ico'),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'icon.ico'),
        ]

        # Для PyInstaller
        if hasattr(sys, '_MEIPASS'):
            possible_paths.insert(0, os.path.join(sys._MEIPASS, 'icon.ico'))
            possible_paths.insert(1, os.path.join(os.path.dirname(sys.executable), 'icon.ico'))

        for path in possible_paths:
            if os.path.exists(path):
                logger.debug(f"Иконка найдена: {path}")
                return path

        logger.warning("icon.ico не найден")
        return None

    def _create_icon(self) -> Optional[Icon]:
        """
        Создать иконку трея.

        Returns:
            Icon pystray или None если не удалось создать
        """
        icon_path = self._get_icon_path()

        if not icon_path:
            # Создаём заглушку если иконка не найдена
            logger.warning("Создание иконки-заглушки")
            img = Image.new('RGB', (64, 64), color=(59, 130, 246))
            return Icon("UI-for-ytdlp", img, "UI-for-ytdlp")

        try:
            icon_img = Image.open(icon_path)
            # Убедимся что размер подходящий
            if icon_img.size != (256, 256):
                icon_img = icon_img.resize((256, 256), Image.Resampling.LANCZOS)

            return Icon(
                "UI-for-ytdlp",
                icon_img,
                "UI-for-ytdlp",
                menu=self._build_menu()
            )
        except Exception as e:
            logger.error(f"Ошибка создания иконки: {e}", exc_info=True)
            return None

    def _on_icon_clicked(self, icon: Icon, item: MenuItem) -> None:
        """
        Обработчик одинарного клика по иконке - восстановление окна.

        Args:
            icon: Иконка pystray
            item: MenuItem
        """
        logger.debug("Клик по иконке в трее - восстановление окна")
        self._safe_callback(self.on_restore)

    def _build_menu(self) -> Menu:
        """
        Построить контекстное меню трея.

        Returns:
            Menu pystray с пунктами
        """
        return Menu(
            # Пункт восстановления окна (первый в меню)
            MenuItem("🖼 Показать окно", self._on_icon_clicked),
            Menu.SEPARATOR,
            
            # Быстрые переключатели
            MenuItem(
                "📋 Перехват ссылок из буфера",
                self._toggle_clipboard_monitoring,
                checked=lambda item: self._get_clipboard_state()
            ),
            MenuItem(
                "🔊 Проигрывание звуков",
                self._toggle_sound_enabled,
                checked=lambda item: self._get_sound_state()
            ),
            Menu.SEPARATOR,

            # Действия
            MenuItem("📋 Вставить ссылку и скачать", self._on_paste_and_download),
            Menu.SEPARATOR,

            MenuItem("⚙ Настройки", self._on_open_settings),
            MenuItem("❌ Выход", self._on_exit),
        )

    def _get_clipboard_state(self) -> bool:
        """
        Получить состояние мониторинга буфера обмена.

        Returns:
            True если мониторинг включён
        """
        return self.clipboard_monitor.is_running() and not self.clipboard_monitor.is_paused()

    def _toggle_clipboard_monitoring(self, item=None) -> None:
        """Переключить мониторинг буфера обмена."""
        if self.clipboard_monitor.is_running() and not self.clipboard_monitor.is_paused():
            self.clipboard_monitor.pause()
            self.config_manager.set('CLIPBOARD_MONITORING', False)
            logger.info("Мониторинг буфера обмена приостановлен")
        else:
            if self.clipboard_monitor.is_paused():
                self.clipboard_monitor.resume()
            elif not self.clipboard_monitor.is_running():
                self.clipboard_monitor.start()
            self.config_manager.set('CLIPBOARD_MONITORING', True)
            logger.info("Мониторинг буфера обмена включён")
        
        self.config_manager.save()

    def _get_sound_state(self) -> bool:
        """
        Получить состояние звуковых уведомлений.

        Returns:
            True если звуки включены
        """
        return self.sound_manager.is_enabled()

    def _toggle_sound_enabled(self, item=None) -> None:
        """Переключить звуковые уведомления."""
        current_state = self.sound_manager.is_enabled()
        new_state = not current_state
        
        self.sound_manager.set_enabled(new_state)
        self.config_manager.set('ENABLE_SOUND_NOTIFICATIONS', new_state)
        self.config_manager.save()
        
        logger.info(f"Звуковые уведомления {'включены' if new_state else 'отключены'}")

    def _safe_callback(self, callback: Callable) -> None:
        """
        Безопасно вызвать callback в главном потоке tkinter.

        Args:
            callback: Функция для вызова
        """
        if self.root_window:
            try:
                self.root_window.after(0, callback)
            except Exception as e:
                logger.error(f"Ошибка вызова callback: {e}", exc_info=True)
        else:
            # Если root_window не указан, вызываем напрямую
            try:
                callback()
            except Exception as e:
                logger.error(f"Ошибка вызова callback: {e}", exc_info=True)

    def _on_restore(self, icon: Icon, item: MenuItem) -> None:
        """
        Обработчик восстановления окна (двойной клик).

        Args:
            icon: Иконка pystray
            item: MenuItem
        """
        logger.debug("Восстановление окна из трея")
        self._safe_callback(self.on_restore)

    def _on_paste_and_download(self, icon: Icon, item: MenuItem) -> None:
        """
        Обработчик вставки и загрузки URL.

        Args:
            icon: Иконка pystray
            item: MenuItem
        """
        logger.debug("Вставить ссылку и скачать (из трея)")
        self._safe_callback(self.on_paste_and_download)

    def _on_open_settings(self, icon: Icon, item: MenuItem) -> None:
        """
        Обработчик открытия настроек.

        Args:
            icon: Иконка pystray
            item: MenuItem
        """
        logger.debug("Открытие настроек (из трея)")
        self._safe_callback(self.on_open_settings)

    def _on_exit(self, icon: Icon, item: MenuItem) -> None:
        """
        Обработчик выхода из приложения.

        Args:
            icon: Иконка pystray
            item: MenuItem
        """
        logger.debug("Выход из приложения (из трея)")
        self._safe_callback(self.on_exit)

    def show(self) -> None:
        """Показать иконку в трее."""
        if self._visible or not PYSTRAY_AVAILABLE:
            return

        try:
            self._icon = self._create_icon()

            if self._icon:
                # Запуск в отдельном потоке
                self._icon.run_detached()
                self._visible = True
                logger.info("Иконка показана в трее")
        except Exception as e:
            logger.error(f"Ошибка показа иконки: {e}", exc_info=True)

    def hide(self) -> None:
        """Скрыть иконку из трея."""
        if not self._visible or not self._icon:
            return

        try:
            self._icon.stop()
            self._icon = None
            self._visible = False
            logger.info("Иконка скрыта из трея")
        except Exception as e:
            logger.error(f"Ошибка скрытия иконки: {e}", exc_info=True)

    def is_visible(self) -> bool:
        """
        Проверить видимость иконки.

        Returns:
            True если иконка видима в трее
        """
        return self._visible

    def stop(self) -> None:
        """Остановить иконку трея и очистить ресурсы."""
        logger.debug("Остановка TrayManager")
        self.hide()
