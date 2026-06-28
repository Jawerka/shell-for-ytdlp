# -*- coding: utf-8 -*-
"""
Менеджер системного трея.

Lifecycle: prepare() один раз при старте → show/hide через visible → stop() при выходе.
"""

import logging
import sys
import os
import threading
from typing import Optional, Callable

try:
    from pystray import Icon, MenuItem, Menu
    from PIL import Image

    PYSTRAY_AVAILABLE = True
except ImportError:
    PYSTRAY_AVAILABLE = False
    Icon = None  # type: ignore
    logger = logging.getLogger('UI-for-ytdlp.tray_manager')
    logger.warning("pystray не установлен. Функционал трея будет отключён.")

from core.clipboard_monitor import ClipboardMonitor
from core.sound_manager import SoundManager
from core.config import ConfigManager

logger = logging.getLogger('UI-for-ytdlp.tray_manager')

_THREAD_JOIN_TIMEOUT = 2.0


class TrayManager:
    """
    Менеджер системного трея приложения.

    Иконка создаётся один раз в prepare(); show/hide переключают visible;
    stop() вызывается только при завершении приложения.
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
        root_window=None,
    ):
        self.clipboard_monitor = clipboard_monitor
        self.sound_manager = sound_manager
        self.config_manager = config_manager
        self.on_restore = on_restore
        self.on_paste_and_download = on_paste_and_download
        self.on_open_settings = on_open_settings
        self.on_exit = on_exit
        self.root_window = root_window

        self._icon: Optional[Icon] = None
        self._icon_thread: Optional[threading.Thread] = None
        self._visible = False
        self._prepared = False
        self._stopped = False
        self._lock = threading.Lock()

        logger.debug("TrayManager инициализирован")

    def _get_icon_path(self) -> Optional[str]:
        possible_paths = [
            os.path.join(os.getcwd(), 'icon.ico'),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'icon.ico'),
        ]

        if hasattr(sys, '_MEIPASS'):
            possible_paths.insert(0, os.path.join(sys._MEIPASS, 'icon.ico'))
            possible_paths.insert(1, os.path.join(os.path.dirname(sys.executable), 'icon.ico'))

        for path in possible_paths:
            if os.path.exists(path):
                logger.debug(f"Иконка найдена: {path}")
                return path

        logger.warning("icon.ico не найден")
        return None

    def _load_tray_image(self):
        icon_path = self._get_icon_path()
        tray_size = 64

        if not icon_path:
            logger.warning("Создание иконки-заглушки")
            return Image.new('RGB', (tray_size, tray_size), color=(59, 130, 246))

        icon_img = Image.open(icon_path)
        if icon_img.mode not in ("RGB", "RGBA"):
            icon_img = icon_img.convert("RGBA")
        if icon_img.size != (tray_size, tray_size):
            icon_img = icon_img.resize(
                (tray_size, tray_size), Image.Resampling.LANCZOS
            )
        return icon_img

    def _create_icon(self) -> Optional[Icon]:
        if not PYSTRAY_AVAILABLE:
            return None

        try:
            return Icon(
                "UI-for-ytdlp",
                self._load_tray_image(),
                "UI-for-ytdlp",
                menu=self._build_menu(),
            )
        except Exception as e:
            logger.error(f"Ошибка создания иконки: {e}", exc_info=True)
            return None

    def _on_icon_clicked(self, icon: Icon, item: MenuItem = None) -> None:
        logger.info("Восстановление окна из трея")
        self._safe_callback(self.on_restore)

    def _build_menu(self) -> Menu:
        return Menu(
            MenuItem("🖼 Показать окно", self._on_icon_clicked, default=True),
            Menu.SEPARATOR,
            MenuItem(
                "📋 Перехват ссылок из буфера",
                self._toggle_clipboard_monitoring,
                checked=lambda item: self._get_clipboard_state(),
            ),
            MenuItem(
                "🔊 Проигрывание звуков",
                self._toggle_sound_enabled,
                checked=lambda item: self._get_sound_state(),
            ),
            Menu.SEPARATOR,
            MenuItem("📋 Вставить ссылку и скачать", self._on_paste_and_download),
            Menu.SEPARATOR,
            MenuItem("⚙ Настройки", self._on_open_settings),
            MenuItem("❌ Выход", self._on_exit),
        )

    def _get_clipboard_state(self) -> bool:
        return self.clipboard_monitor.is_running() and not self.clipboard_monitor.is_paused()

    def _toggle_clipboard_monitoring(self, item=None) -> None:
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
        return self.sound_manager.is_enabled()

    def _toggle_sound_enabled(self, item=None) -> None:
        new_state = not self.sound_manager.is_enabled()
        self.sound_manager.set_enabled(new_state)
        self.config_manager.set('ENABLE_SOUND_NOTIFICATIONS', new_state)
        self.config_manager.save()
        logger.info(f"Звуковые уведомления {'включены' if new_state else 'отключены'}")

    def _safe_callback(self, callback: Callable) -> None:
        if self.root_window:
            try:
                self.root_window.after(0, callback)
            except Exception as e:
                logger.error(f"Ошибка вызова callback: {e}", exc_info=True)
        else:
            try:
                callback()
            except Exception as e:
                logger.error(f"Ошибка вызова callback: {e}", exc_info=True)

    def _on_paste_and_download(self, icon: Icon, item: MenuItem) -> None:
        logger.debug("Вставить ссылку и скачать (из трея)")
        self._safe_callback(self.on_paste_and_download)

    def _on_open_settings(self, icon: Icon, item: MenuItem) -> None:
        logger.debug("Открытие настроек (из трея)")
        self._safe_callback(self.on_open_settings)

    def _on_exit(self, icon: Icon, item: MenuItem) -> None:
        logger.debug("Выход из приложения (из трея)")
        self._safe_callback(self.on_exit)

    def prepare(self) -> bool:
        """
        Создать иконку и запустить message loop один раз (visible=False).

        Returns:
            True если трей готов к использованию
        """
        if not PYSTRAY_AVAILABLE or self._prepared or self._stopped:
            return self.is_ready()

        with self._lock:
            if self._prepared:
                return self.is_ready()

            self._icon = self._create_icon()
            if not self._icon:
                return False

            if hasattr(self._icon, 'set_on_click'):
                try:
                    self._icon.set_on_click(self._on_icon_clicked)
                except Exception as e:
                    logger.debug(f"set_on_click() не поддерживается: {e}")

            self._icon.visible = False

            if sys.platform == "darwin":
                self._icon.run_detached()
            else:
                self._icon_thread = threading.Thread(
                    target=self._icon.run,
                    daemon=True,
                    name="UI-for-ytdlp.pystray",
                )
                self._icon_thread.start()

            self._prepared = True
            logger.info("TrayManager подготовлен (icon.run в фоне, visible=False)")
            return True

    def show(self) -> None:
        """Показать иконку в трее (visible=True)."""
        if not self.is_ready() or self._visible or self._stopped:
            return

        with self._lock:
            if not self._icon or self._stopped:
                return
            try:
                self._icon.visible = True
                self._visible = True
                logger.info("Иконка показана в трее (ПКМ для меню)")
            except Exception as e:
                logger.error(f"Ошибка показа иконки: {e}", exc_info=True)

    def hide(self) -> None:
        """Скрыть иконку из трея (visible=False, без stop)."""
        if not self._visible or not self._icon or self._stopped:
            return

        with self._lock:
            if not self._icon:
                return
            try:
                self._icon.visible = False
                self._visible = False
                logger.info("Иконка скрыта из трея")
            except Exception as e:
                logger.error(f"Ошибка скрытия иконки: {e}", exc_info=True)

    def is_visible(self) -> bool:
        return self._visible

    def is_ready(self) -> bool:
        """Проверить, что иконка создана и поток pystray активен."""
        if not PYSTRAY_AVAILABLE or not self._prepared or self._stopped:
            return False
        if not self._icon:
            return False
        if sys.platform == "darwin":
            return True
        return self._icon_thread is not None and self._icon_thread.is_alive()

    def stop(self) -> None:
        """Безопасно удалить иконку из трея при завершении приложения."""
        with self._lock:
            if self._stopped:
                return

            logger.debug("Остановка TrayManager")
            self._stopped = True

            if not self._icon:
                self._prepared = False
                self._visible = False
                return

            try:
                self._icon.visible = False
            except Exception as e:
                logger.debug(f"Не удалось скрыть иконку перед stop: {e}")

            try:
                self._icon.stop()
            except Exception as e:
                logger.error(f"Ошибка icon.stop(): {e}", exc_info=True)

            if self._icon_thread is not None:
                if self._icon_thread.is_alive():
                    self._icon_thread.join(timeout=_THREAD_JOIN_TIMEOUT)
                    if self._icon_thread.is_alive():
                        logger.warning(
                            "Поток pystray не завершился за %.1fs после stop()",
                            _THREAD_JOIN_TIMEOUT,
                        )
                else:
                    self._icon_thread.join(timeout=0)

            self._icon = None
            self._icon_thread = None
            self._visible = False
            self._prepared = False
            logger.info("TrayManager остановлен, иконка удалена из трея")
