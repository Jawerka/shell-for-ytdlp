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
from .download_handlers import DownloadHints, HandlerError, resolve_download_hints
from .pipeline import (
    ensure_download_directory,
    ensure_download_temp_directory,
    cleanup_download_temp_directory,
    get_download_temp_dir,
)
from .utils import find_cookies_txt, is_youtube_url, normalize_path_for_display, strip_youtube_playlist_params

# Логгер для отладки
logger = logging.getLogger('UI-for-ytdlp.downloader')


def _terminate_process_tree(process: Optional[subprocess.Popen]) -> None:
    """Завершить yt-dlp и дочерние процессы (в т.ч. ffmpeg)."""
    if process is None:
        return
    try:
        if os.name == 'nt':
            subprocess.run(
                ['taskkill', '/PID', str(process.pid), '/T', '/F'],
                check=False,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        else:
            process.kill()
    except Exception as e:
        logger.error(f"_terminate_process_tree: {e}")


class YouTubeDownloader:
    """Загрузчик видео через yt-dlp."""

    YTDLP_OPTIONS = [
        '--continue',
        '--retries', '100',
        # Windows Defender/indexer may briefly hold a completed stream while yt-dlp renames it.
        '--file-access-retries', '10',
        '--retry-sleep', '5',
        '--retry-sleep', 'file_access:3',
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
        self._range_error = False
        self._logs_buffer: List[str] = []  # Буфер для логирования ошибок
        logger.debug(f"YouTubeDownloader: DOWNLOAD_PATH = {config.get('DOWNLOAD_PATH')}")
        logger.debug(f"YouTubeDownloader: YTDLP_PATH = {config.get('YTDLP_PATH')}")

    def _log(self, message: str, level: str = 'info') -> None:
        """Внутренний метод логирования."""
        # Сохраняем в буфер для анализа ошибок
        self._logs_buffer.append(message)
        if self.log_callback:
            self.log_callback(message, level)
    
    def _progress(self, percent: float, info: str) -> None:
        """Внутренний метод обновления прогресса."""
        if self.progress_callback:
            self.progress_callback(percent, info)

    def _get_base_ytdlp_options(
        self,
        hints: Optional[DownloadHints] = None,
        resume: bool = True,
    ) -> List[str]:
        """Базовые опции yt-dlp с учётом подсказок обработчика."""
        options = list(self.YTDLP_OPTIONS)
        if not resume:
            options[options.index('--continue')] = '--no-continue'
        if hints and hints.format_selector:
            try:
                format_index = options.index('-f')
                options[format_index + 1] = hints.format_selector
            except ValueError:
                options.extend(['-f', hints.format_selector])
        return options

    def _build_command(
        self,
        url: str,
        download_path: str,
        hints: Optional[DownloadHints] = None,
        resume: bool = True,
    ) -> List[str]:
        """
        Построить команду для yt-dlp.

        Args:
            url: URL для загрузки
            download_path: Путь для сохранения
            hints: Параметры от подключаемого обработчика URL

        Returns:
            Список аргументов команды
        """
        effective_url = hints.url if hints else url
        logger.debug(f"_build_command: URL = {effective_url[:50]}...")
        logger.debug(f"_build_command: download_path = {download_path}")

        utilities_path = self.config.get('UTILITIES_PATH', '')
        ytdlp_path = self.config.get('YTDLP_PATH', '')

        logger.debug(f"_build_command: utilities_path = {utilities_path}")
        logger.debug(f"_build_command: ytdlp_path = {ytdlp_path}")

        temp_path = get_download_temp_dir(download_path)

        cmd = [
            ytdlp_path,
            '-P', f'home:{download_path}',
            '-P', f'temp:{temp_path}',
            *self._get_base_ytdlp_options(hints, resume),
            # Путь к ffmpeg передаётся как путь к директории (согласно документации yt-dlp)
            '--ffmpeg-location', utilities_path,
        ]

        logger.debug(f"_build_command: Базовая команда: {len(cmd)} аргументов")

        # Поиск cookies.txt
        # Сначала проверяем конфигурацию COOKIES_PATH
        cookies_file = self.config.get('COOKIES_PATH', '')
        if cookies_file and os.path.exists(cookies_file):
            logger.debug(f"_build_command: Используется cookies.txt из конфигурации: {cookies_file}")
            self._log(f"Используется cookies.txt")
            cmd.append('--cookies')
            cmd.append(cookies_file)
        else:
            # Если не указан в конфигурации, ищем в utilities
            cookies_file = find_cookies_txt(utilities_path)
            if cookies_file:
                logger.debug(f"_build_command: Найден cookies.txt: {cookies_file}")
                self._log(f"Найден cookies.txt: {os.path.basename(cookies_file)}")
                cmd.append('--cookies')
                cmd.append(cookies_file)
            else:
                logger.debug("_build_command: cookies.txt не найден")

        # SponsorBlock — только для YouTube (на других сайтах сегментов нет)
        sponsorblock_list = self.config.get('SPONSORBLOCK_REMOVE_LIST', [])
        if sponsorblock_list and is_youtube_url(url):
            categories = ','.join(sponsorblock_list)
            logger.debug(f"_build_command: SponsorBlock категории = {sponsorblock_list}")
            cmd.append('--sponsorblock-remove')
            cmd.append(categories)
        elif sponsorblock_list:
            logger.debug("_build_command: SponsorBlock пропущен (не YouTube URL)")
        else:
            logger.debug("_build_command: SponsorBlock отключен")

        if hints and hints.referer:
            cmd.extend(['--referer', hints.referer])

        if hints and hints.merge_output_format:
            cmd.extend(['--merge-output-format', hints.merge_output_format])

        if hints and hints.output_template:
            cmd.extend(['-o', hints.output_template])
        elif 'playlist' in effective_url:
            logger.debug("_build_command: Обнаружен плейлист, специальный формат вывода")
            cmd.append('-o')
            cmd.append('%(playlist)s/%(title)s [%(id)s].%(ext)s')

        # Убираем только параметры плейлиста YouTube, остальные query сохраняем
        clean_url = strip_youtube_playlist_params(effective_url)
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

    def _parse_phase_status(self, line: str) -> Optional[str]:
        """Распарсить фазу post-processing (ffmpeg merge и др.) из вывода yt-dlp."""
        if not line or not isinstance(line, str):
            return None

        if '[Merger]' in line:
            return 'Слияние потоков (ffmpeg)...'
        if '[SponsorBlock]' in line:
            return 'SponsorBlock (ffmpeg)...'
        if '[ffmpeg]' in line and 'Deleting' not in line:
            return 'Обработка ffmpeg...'
        return None

    @staticmethod
    def _parse_file_access_retry(line: str) -> Optional[str]:
        """Преобразовать повтор yt-dlp из-за блокировки файла в спокойный статус UI."""
        if not line or 'unable to rename file' not in line.lower():
            return None

        match = re.search(r'retrying\s*\((\d+)\s*/\s*(\d+)\)', line, re.IGNORECASE)
        if not match:
            return None
        return (
            'Файл временно занят другой программой. '
            f'Повторяем автоматически ({match.group(1)}/{match.group(2)})...'
        )
    
    @staticmethod
    def _is_range_error(line: str) -> bool:
        """Распознать ответ сервера HTTP 416 (несовместимый частичный файл)."""
        lower = line.lower()
        return 'http error 416' in lower or ('416' in line and 'range not satisfiable' in lower)

    def _run_process(self, cmd: List[str]) -> Optional[int]:
        """
        Запустить yt-dlp и разобрать его вывод.

        Returns:
            Код возврата или None, если загрузка отменена пользователем
        """
        self._range_error = False

        # Используем список аргументов без shell=True для безопасности
        # Читаем вывод как binary, чтобы корректно обрабатывать русские символы
        self._process = subprocess.Popen(
            cmd,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )

        logger.debug(f"download: Process PID = {self._process.pid}")

        if self._process.stdout:
            line_count = 0
            last_percent = 0.0
            for line in self._process.stdout:
                if self._cancelled:
                    logger.warning("download: Отмена пользователем")
                    _terminate_process_tree(self._process)
                    self._log("Загрузка отменена пользователем", 'warning')
                    return None

                # Декодируем binary строку в UTF-8
                # yt-dlp выводит в OEM кодировке, но большинство символов совместимы
                try:
                    line_str = line.decode('utf-8').strip()
                except UnicodeDecodeError:
                    try:
                        line_str = line.decode('cp1251').strip()
                    except UnicodeDecodeError:
                        line_str = line.decode('utf-8', errors='replace').strip()

                if not line_str:
                    continue

                line_count += 1

                if line_count % 10 == 0:
                    logger.debug(f"download: Строка {line_count}: {line_str[:50]}...")

                if self._is_range_error(line_str):
                    self._range_error = True

                file_access_status = self._parse_file_access_retry(line_str)
                if file_access_status:
                    # Оставляем исходное сообщение для диагностики, но показываем пользователю
                    # понятный статус вместо англоязычной строки с ERROR.
                    self._logs_buffer.append(line_str)
                    self._log(file_access_status)
                    self._progress(last_percent, file_access_status)
                    continue

                progress = self._parse_progress(line_str)
                phase = self._parse_phase_status(line_str)
                if progress:
                    percent, info, speed, eta = progress
                    last_percent = percent
                    progress_info = info
                    if speed or eta:
                        parts = [info]
                        if speed:
                            parts.append(f" | {speed}")
                        if eta:
                            parts.append(f" | {eta}")
                        progress_info = "".join(parts)
                    self._progress(percent, progress_info)
                elif phase:
                    self._progress(last_percent, phase)
                    self._log(line_str)
                else:
                    self._log(line_str)

            logger.debug(f"download: Всего строк вывода: {line_count}")

        return_code = self._process.wait()
        logger.debug(f"download: Return code = {return_code}")
        return return_code

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
        self._logs_buffer = []  # Очищаем буфер перед загрузкой
        
        download_path = self.config.get('DOWNLOAD_PATH', '')
        ytdlp_path = self.config.get('YTDLP_PATH', '')

        logger.debug(f"download: download_path = {download_path}")
        logger.debug(f"download: ytdlp_path = {ytdlp_path}")
        logger.debug(f"download: ytdlp exists = {os.path.exists(ytdlp_path)}")
        
        # Проверка и создание пути сохранения
        if not download_path:
            logger.error("download: Путь сохранения не указан")
            self._log("Путь сохранения не указан", 'error')
            return False

        ok, message = ensure_download_directory(download_path)
        if not ok:
            logger.error(f"download: {message}")
            self._log(message, 'error')
            return False

        ok, message = ensure_download_temp_directory(download_path)
        if not ok:
            logger.error(f"download: {message}")
            self._log(message, 'error')
            return False

        if not os.path.exists(ytdlp_path):
            logger.error(f"download: yt-dlp не найден по пути {ytdlp_path}")
            self._log("yt-dlp не найден. Запустите обновление утилит.", 'error')
            return False

        try:
            hints = resolve_download_hints(url, self.config)
        except HandlerError as e:
            self._log(str(e), 'error')
            return False

        if hints.log_title:
            self._log(f"Плагин: {hints.log_title}")

        self._log(f"Запуск загрузки: {url}")
        self._log(f"Путь сохранения: {normalize_path_for_display(download_path)}")

        logger.debug("download: Запуск subprocess.Popen")

        try:
            for attempt in range(2):
                cmd = self._build_command(url, download_path, hints, resume=attempt == 0)
                logger.debug(f"download: Команда (попытка {attempt + 1}): {cmd}")

                return_code = self._run_process(cmd)

                if return_code is None:
                    return False

                if return_code == 0:
                    logger.debug("download: Загрузка успешна")
                    cleanup_download_temp_directory(download_path)
                    self._log("Загрузка завершена успешно", 'success')
                    self._progress(100.0, "Завершено")
                    return True

                if self._range_error and attempt == 0 and not self._cancelled:
                    self._log(
                        "HTTP 416: сервер не принимает продолжение. "
                        "Перезапуск загрузки с нуля (без --continue).",
                        'warning',
                    )
                    self._logs_buffer = []
                    continue

                break

            # Подробное логирование ошибок
            logger.error(f"download: Ошибка, return code = {return_code}")
            self._log(f"yt-dlp завершил с кодом {return_code}", 'error')

            error_lines = [
                line for line in self._logs_buffer
                if 'ERROR' in line or 'Error' in line or 'failed' in line.lower() or 'unable' in line.lower()
            ]
            if error_lines:
                logger.error(f"download: Ошибки в выводе: {error_lines[:5]}")
                for err_line in error_lines[:3]:  # Показываем первые 3 ошибки
                    self._log(f"Ошибка: {err_line}", 'error')

            return False

        except KeyboardInterrupt:
            logger.warning("download: Прервано пользователем (KeyboardInterrupt)")
            self._log("Прервано пользователем", 'warning')
            if self._process:
                _terminate_process_tree(self._process)
            return False
        except Exception as e:
            logger.error(f"download: Исключение: {e}", exc_info=True)
            self._log(f"Ошибка загрузки: {e}", 'error')
            return False
        finally:
            logger.debug("download: Очистка process")
            self._process = None
            self._logs_buffer = []  # Очищаем буфер после загрузки

    def cancel(self) -> None:
        """Отменить загрузку."""
        self._cancelled = True
        if self._process:
            try:
                _terminate_process_tree(self._process)
                logger.debug(f"cancel: Дерево процессов {self._process.pid} завершено принудительно")
            except Exception as e:
                logger.error(f"cancel: Ошибка при завершении процесса: {e}")
            finally:
                self._process = None
