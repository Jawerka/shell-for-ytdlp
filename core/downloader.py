# -*- coding: utf-8 -*-
"""
Модуль загрузчика YouTube.

Содержит:
- YouTubeDownloader: обёртка над yt-dlp для загрузки видео
"""

import os
import re
import subprocess
import logging
from typing import Callable, Optional, Tuple, List

from .config import ConfigManager
from .utils import find_cookies_txt, normalize_path_for_display

# Логгер для отладки
logger = logging.getLogger('UI-for-ytdlp.downloader')


class YouTubeDownloader:
    """Загрузчик видео через yt-dlp."""

    YTDLP_OPTIONS = [
        '--continue',
        '--retries', '100',
        '--retry-sleep', '5',
        '--no-mtime',
        '--windows-filenames',
        '--concurrent-fragments', '8',
        # Выводить прогресс с новой строки (вместо \r)
        '--newline',
        # Лучшее качество видео и аудио
        '-f', 'bestvideo+bestaudio/best',
    ]

    def __init__(
        self,
        config: ConfigManager,
        log_callback: Callable[[str, str], None],
        progress_callback: Callable[[float, str], None]
    ):
        """
        Инициализация загрузчика.

        Args:
            config: Менеджер конфигурации
            log_callback: Функция для логирования
            progress_callback: Функция для отображения прогресса
        """
        logger.debug("YouTubeDownloader: Инициализация")
        self.config = config
        self.log_callback = log_callback
        self.progress_callback = progress_callback
        self._process: Optional[subprocess.Popen] = None
        self._cancelled = False
        logger.debug(f"YouTubeDownloader: DOWNLOAD_PATH = {config.get('DOWNLOAD_PATH')}")
        logger.debug(f"YouTubeDownloader: YTDLP_PATH = {config.get('YTDLP_PATH')}")
    
    def _log(self, message: str, level: str = 'info') -> None:
        """Внутренний метод логирования."""
        if self.log_callback:
            self.log_callback(message, level)
    
    def _progress(self, percent: float, info: str) -> None:
        """Внутренний метод обновления прогресса."""
        if self.progress_callback:
            self.progress_callback(percent, info)

    def _build_command(self, url: str, download_path: str) -> List[str]:
        """
        Построить команду для yt-dlp.

        Args:
            url: URL для загрузки
            download_path: Путь для сохранения

        Returns:
            Список аргументов команды
        """
        logger.debug(f"_build_command: URL = {url[:50]}...")
        logger.debug(f"_build_command: download_path = {download_path}")

        utilities_path = self.config.get('UTILITIES_PATH', '')
        ytdlp_path = self.config.get('YTDLP_PATH', '')

        logger.debug(f"_build_command: utilities_path = {utilities_path}")
        logger.debug(f"_build_command: ytdlp_path = {ytdlp_path}")

        # Для Windows используем двойные кавычки для путей с пробелами
        def quote_path(path: str) -> str:
            """Экранировать путь для Windows."""
            if ' ' in path:
                return f'"{path}"'
            return path

        # Всегда используем лучшее качество видео и аудио
        cmd = [
            ytdlp_path,
            '-P', quote_path(download_path),
            *self.YTDLP_OPTIONS,
            # Путь к ffmpeg передаётся как путь к директории (согласно документации yt-dlp)
            '--ffmpeg-location', quote_path(utilities_path),
        ]

        logger.debug(f"_build_command: Базовая команда: {len(cmd)} аргументов")

        # Поиск cookies.txt
        # Сначала проверяем конфигурацию COOKIES_PATH
        cookies_file = self.config.get('COOKIES_PATH', '')
        if cookies_file and os.path.exists(cookies_file):
            logger.debug(f"_build_command: Используется cookies.txt из конфигурации: {cookies_file}")
            self._log(f"Используется cookies.txt")
            cmd.append('--cookies')
            cmd.append(quote_path(cookies_file))
        else:
            # Если не указан в конфигурации, ищем в utilities
            cookies_file = find_cookies_txt(utilities_path)
            if cookies_file:
                logger.debug(f"_build_command: Найден cookies.txt: {cookies_file}")
                self._log(f"Найден cookies.txt: {os.path.basename(cookies_file)}")
                cmd.append('--cookies')
                cmd.append(quote_path(cookies_file))
            else:
                logger.debug("_build_command: cookies.txt не найден")

        # SponsorBlock
        sponsorblock_list = self.config.get('SPONSORBLOCK_REMOVE_LIST', [])
        if sponsorblock_list:
            categories = ','.join(sponsorblock_list)
            logger.debug(f"_build_command: SponsorBlock категории = {sponsorblock_list}")
            cmd.append('--sponsorblock-remove')
            cmd.append(categories)
        else:
            logger.debug("_build_command: SponsorBlock отключен")

        # Формат вывода для плейлистов
        if 'playlist' in url:
            logger.debug("_build_command: Обнаружен плейлист, специальный формат вывода")
            cmd.append('-o')
            cmd.append('%(playlist)s/%(title)s [%(id)s].%(ext)s')

        # Очистка URL от параметров
        clean_url = url.split('&')[0]
        logger.debug(f"_build_command: clean_url = {clean_url}")
        cmd.append(clean_url)

        # Логирование финальной команды
        cmd_str = ' '.join(cmd)
        logger.debug(f"_build_command: Финальная команда: {cmd_str[:200]}...")

        return cmd
    
    def _parse_progress(self, line: str) -> Optional[Tuple[float, str, str, str]]:
        """
        Распарсить прогресс из вывода yt-dlp.

        Args:
            line: Строка вывода

        Returns:
            Кортеж (процент, информация, скорость, ETA) или None
        """
        if not line or not isinstance(line, str):
            return None

        # Пропускаем строки которые точно не содержат прогресс
        if '[download]' not in line and '%' not in line:
            return None

        # Паттерны для парсинга
        # Процент: "45.2%" или "100%"
        percent_pattern = r'(\d{1,3}\.?\d*)%'
        # Размер: "47.41MiB" или "2.5 GiB"
        size_pattern = r'(\d+\.?\d*)\s*(MiB|GiB|KiB)'
        # Скорость: "at 2.50MiB/s" или "at 670.99KiB/s"
        speed_pattern = r'at\s+(\d+\.?\d*)\s*(KiB|MiB|GiB)/s'
        # ETA: "ETA 00:42" или "ETA 01:23:45" или "in 00:01:12"
        eta_pattern = r'(?:ETA\s+|in\s+)([\d:]+)'

        percent_match = re.search(percent_pattern, line)
        if not percent_match:
            return None

        percent = float(percent_match.group(1))

        # Размер
        size_info = ""
        size_match = re.search(size_pattern, line)
        if size_match:
            size_val = size_match.group(1)
            size_unit = size_match.group(2)
            size_info = f"{percent:.1f}% of {size_val}{size_unit}"
        else:
            size_info = f"{percent:.1f}%"

        # Скорость
        speed = ""
        speed_match = re.search(speed_pattern, line)
        if speed_match:
            speed_val = speed_match.group(1)
            speed_unit = speed_match.group(2)
            speed = f"{speed_val} {speed_unit}/s"

        # ETA
        eta = ""
        eta_match = re.search(eta_pattern, line)
        if eta_match:
            eta = f"ETA: {eta_match.group(1)}"

        logger.debug(f"_parse_progress: line={line[:80]}... percent={percent} size={size_info} speed={speed} eta={eta}")
        return (percent, size_info, speed, eta)
    
    def download(self, url: str) -> bool:
        """
        Начать загрузку.

        Args:
            url: URL для загрузки

        Returns:
            True если загрузка успешна
        """
        logger.debug(f"download: Начало загрузки URL = {url[:50]}...")
        
        self._cancelled = False
        download_path = self.config.get('DOWNLOAD_PATH', '')
        ytdlp_path = self.config.get('YTDLP_PATH', '')
        
        logger.debug(f"download: download_path = {download_path}")
        logger.debug(f"download: ytdlp_path = {ytdlp_path}")
        logger.debug(f"download: ytdlp exists = {os.path.exists(ytdlp_path)}")

        if not os.path.exists(ytdlp_path):
            logger.error(f"download: yt-dlp не найден по пути {ytdlp_path}")
            self._log("yt-dlp не найден. Запустите обновление утилит.", 'error')
            return False

        cmd = self._build_command(url, download_path)

        logger.debug(f"download: Команда: {cmd}")

        self._log(f"Запуск загрузки: {url}")
        self._log(f"Путь сохранения: {normalize_path_for_display(download_path)}")

        logger.debug("download: Запуск subprocess.Popen")

        try:
            # Используем список аргументов без shell=True для безопасности
            self._process = subprocess.Popen(
                cmd,
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            logger.debug(f"download: Process PID = {self._process.pid}")

            if self._process.stdout:
                line_count = 0
                for line in self._process.stdout:
                    if self._cancelled:
                        logger.warning("download: Отмена пользователем")
                        self._process.kill()
                        self._log("Загрузка отменена пользователем", 'warning')
                        return False

                    line = line.strip()
                    if not line:
                        continue
                    
                    line_count += 1
                    
                    # Логирование каждой 10-й строки для отладки
                    if line_count % 10 == 0:
                        logger.debug(f"download: Строка {line_count}: {line[:50]}...")

                    progress = self._parse_progress(line)
                    if progress:
                        percent, info, speed, eta = progress
                        # Формируем полную информацию для отображения
                        progress_info = info
                        if speed or eta:
                            parts = [info]
                            if speed:
                                parts.append(f" | {speed}")
                            if eta:
                                parts.append(f" | {eta}")
                            progress_info = "".join(parts)
                        self._progress(percent, progress_info)
                    else:
                        # Логируем все сообщения от yt-dlp
                        self._log(line)
                
                logger.debug(f"download: Всего строк вывода: {line_count}")

            return_code = self._process.wait()
            logger.debug(f"download: Return code = {return_code}")
            
            if return_code == 0:
                logger.debug("download: Загрузка успешна")
                self._log("Загрузка завершена успешно", 'success')
                self._progress(100.0, "Завершено")
                return True
            else:
                logger.error(f"download: Ошибка, return code = {return_code}")
                self._log(f"yt-dlp завершил с кодом {return_code}", 'error')
                return False

        except KeyboardInterrupt:
            logger.warning("download: Прервано пользователем (KeyboardInterrupt)")
            self._log("Прервано пользователем", 'warning')
            if self._process:
                self._process.kill()
            return False
        except Exception as e:
            logger.error(f"download: Исключение: {e}", exc_info=True)
            self._log(f"Ошибка загрузки: {e}", 'error')
            return False
        finally:
            logger.debug("download: Очистка process")
            self._process = None
    
    def cancel(self) -> None:
        """Отменить загрузку."""
        self._cancelled = True
        if self._process:
            try:
                # Используем kill() вместо terminate() для гарантированной остановки
                self._process.kill()
                logger.debug(f"cancel: Процесс {self._process.pid} завершён принудительно")
            except Exception as e:
                logger.error(f"cancel: Ошибка при завершении процесса: {e}")
            finally:
                self._process = None
