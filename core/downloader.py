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
import time
from typing import Callable, Optional, Tuple, List

from .config import ConfigManager
from .download_handlers import DownloadHints, HandlerError, resolve_download_hints
from .pipeline import (
    VIDEO_QUALITY_DEFAULT,
    OUTPUT_CONTAINER_DEFAULT,
    normalize_output_container,
    ensure_download_directory,
    ensure_download_temp_directory,
    cleanup_download_temp_directory,
    get_download_temp_dir,
    ytdlp_format_selector_for_container,
    ytdlp_container_options,
    SponsorBlockAvailability,
    is_sponsorblock_network_error,
)
from .utils import find_cookies_txt, is_youtube_url, normalize_path_for_display, strip_youtube_playlist_params
from .verbose_log import VERBOSE_YTDLP_OPTIONS, VerboseDownloadLog, is_verbose_download_log_enabled

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
        # Единая кодировка вывода, в том числе без консоли Windows.
        '--encoding', 'utf-8',
        # Выводить прогресс с новой строки (вместо \r)
        '--newline',
        # Лучшее качество видео и аудио
        '-f', 'bestvideo+bestaudio/best',
    ]

    def __init__(
        self,
        config: ConfigManager,
        log_callback: Callable[[str, str], None],
        progress_callback: Callable[[float, str], None],
        sponsorblock_state=None,
        sponsorblock_question=None,
        sponsorblock_notice=None,
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
        self._verbose_log: Optional[VerboseDownloadLog] = None
        self.sponsorblock_state = sponsorblock_state or SponsorBlockAvailability()
        self.sponsorblock_question = sponsorblock_question
        self.sponsorblock_notice = sponsorblock_notice
        self._bypass_sponsorblock = False
        self._sponsorblock_error = False
        self._sponsorblock_reason = ''
        self.already_downloaded = False
        self.result_message = ''
        logger.debug(f"YouTubeDownloader: DOWNLOAD_PATH = {config.get('DOWNLOAD_PATH')}")
        logger.debug(f"YouTubeDownloader: YTDLP_PATH = {config.get('YTDLP_PATH')}")

    def _log(self, message: str, level: str = 'info', *, from_ytdlp: bool = False) -> None:
        """Внутренний метод логирования."""
        if self._verbose_log and not from_ytdlp:
            message = self._verbose_log.write_app_line(message)
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
        quality = self.config.get('VIDEO_QUALITY', VIDEO_QUALITY_DEFAULT)
        container = self.config.get('OUTPUT_CONTAINER', OUTPUT_CONTAINER_DEFAULT)
        format_selector = ytdlp_format_selector_for_container(
            quality, container, hints.format_selector if hints else None,
        )
        try:
            format_index = options.index('-f')
            options[format_index + 1] = format_selector
        except ValueError:
            options.extend(['-f', format_selector])
        if self._verbose_log is not None:
            options.extend(VERBOSE_YTDLP_OPTIONS)
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
        if sponsorblock_list and is_youtube_url(url) and not self._bypass_sponsorblock:
            categories = ','.join(sponsorblock_list)
            logger.debug(f"_build_command: SponsorBlock категории = {sponsorblock_list}")
            cmd.append('--sponsorblock-remove')
            cmd.append(categories)
            # yt-dlp откладывает некоторые ошибки SponsorBlock до конца загрузки.
            # Его штатный интерактивный фильтр держит передачу на паузе,
            # пока мы не подтвердим успешное получение отметок через stdin.
            cmd.extend(['--match-filter', '-', '--no-quiet', '--color', 'never'])
        elif self._bypass_sponsorblock:
            # Переопределить также SponsorBlock из внешнего yt-dlp.conf.
            cmd.append('--no-sponsorblock')
            logger.debug('_build_command: SponsorBlock временно пропущен')
        elif sponsorblock_list:
            logger.debug("_build_command: SponsorBlock пропущен (не YouTube URL)")
        else:
            logger.debug("_build_command: SponsorBlock отключен")

        if hints and hints.referer:
            cmd.extend(['--referer', hints.referer])

        container = normalize_output_container(
            self.config.get('OUTPUT_CONTAINER', OUTPUT_CONTAINER_DEFAULT)
        )
        cmd.extend(ytdlp_container_options(container))
        if container == 'auto' and hints and hints.merge_output_format:
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

        # Только прогресс yt-dlp. Иначе «29.0%» из статистики libx264 двигает бар.
        if not re.match(r'^\[download\]\s+\d{1,3}(?:\.\d+)?%', line):
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
            return 'Объединение дорожек (ffmpeg). Большие файлы могут занять несколько минут...'
        if '[SponsorBlock]' in line:
            return 'Получение отметок SponsorBlock...'
        if '[VideoRemuxer]' in line and 'Not remuxing' not in line:
            return 'Перепаковка контейнера (ffmpeg)...'
        if '[FixupM3u8]' in line:
            return 'Обработка ffmpeg...'
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
        self._sponsorblock_error = False
        fetching_sponsorblock = False
        sponsorblock_gate = '--sponsorblock-remove' in cmd and '--match-filter' in cmd
        gate_approved = False

        # Используем список аргументов без shell=True для безопасности
        # Читаем вывод как binary, чтобы корректно обрабатывать русские символы
        process = subprocess.Popen(
            cmd,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE if sponsorblock_gate else None,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        self._process = process

        logger.debug(f"download: Process PID = {process.pid}")

        if self._cancelled:
            _terminate_process_tree(process)
            process.wait()
            self._log("Загрузка отменена пользователем", 'warning')
            return None

        if process.stdout:
            line_count = 0
            last_percent = 0.0
            last_data_at = time.monotonic()
            stream_label = 'Получение информации'
            for line in process.stdout:
                if self._cancelled:
                    logger.warning("download: Отмена пользователем")
                    _terminate_process_tree(process)
                    process.wait()
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

                if '[SponsorBlock] Fetching' in line_str:
                    fetching_sponsorblock = True
                    gate_approved = False
                if sponsorblock_gate and not gate_approved and re.search(
                    r'^\[SponsorBlock\] (?:Found \d+ segments|No matching segments were found)', line_str,
                ):
                    if self._cancelled:
                        _terminate_process_tree(process)
                        process.wait()
                        return None
                    process.stdin.write(b'y\n')
                    process.stdin.flush()
                    gate_approved = True
                if '[info]' in line_str or '[download]' in line_str or '[Merger]' in line_str:
                    fetching_sponsorblock = False
                    # Предупреждение API, после которого yt-dlp продолжил работу,
                    # не должно объяснять последующую ошибку видео/ffmpeg.
                    self._sponsorblock_error = False
                if is_sponsorblock_network_error(line_str, fetching_sponsorblock):
                    self._sponsorblock_error = True
                    self._sponsorblock_reason = line_str
                    # yt-dlp может отложить эту ошибку и продолжить скачивание.
                    # Не ждём его завершения: решение о пропуске принимает пользователь.
                    if self._verbose_log is not None:
                        self._verbose_log.handle_ytdlp_line(line_str)
                    self._log(line_str, 'warning', from_ytdlp=True)
                    if fetching_sponsorblock:
                        # На этапе получения отметок ffmpeg ещё не запущен.
                        process.kill()
                    else:
                        _terminate_process_tree(process)
                    process.wait()
                    if process.stdout is not None:
                        process.stdout.close()
                    if process.stdin is not None:
                        process.stdin.close()
                    self._process = None
                    return None if self._cancelled else 1
                if 'has already been downloaded' in line_str:
                    self.already_downloaded = True
                if '[download]' in line_str and 'Destination:' in line_str:
                    stream_label = ('Аудио' if re.search(r'\.(m4a|opus|mp3|aac|ogg)(?:\.part)?$', line_str, re.I)
                                    else 'Видео')

                line_count += 1

                if line_count % 10 == 0:
                    logger.debug(f"download: Строка {line_count}: {line_str[:50]}...")

                if self._is_range_error(line_str):
                    self._range_error = True

                file_access_status = self._parse_file_access_retry(line_str)
                gui_line = line_str
                if self._verbose_log is not None:
                    gui_line = self._verbose_log.handle_ytdlp_line(line_str)

                if file_access_status:
                    # Оставляем исходное сообщение для диагностики, но показываем пользователю
                    # понятный статус вместо англоязычной строки с ERROR.
                    self._logs_buffer.append(gui_line or file_access_status)
                    self._log(file_access_status, from_ytdlp=True)
                    self._progress(last_percent, file_access_status)
                    continue

                progress = self._parse_progress(line_str)
                phase = self._parse_phase_status(line_str)
                if progress:
                    percent, info, speed, eta = progress
                    if percent != last_percent:
                        last_data_at = time.monotonic()
                    last_percent = percent
                    progress_info = f'{stream_label} · {info}'
                    if speed or eta:
                        parts = [progress_info]
                        if speed:
                            parts.append(f" | {speed}")
                        if eta:
                            parts.append(f" | {eta}")
                        progress_info = "".join(parts)
                    self._progress(percent, progress_info)
                elif phase:
                    self._progress(last_percent, phase)
                    if gui_line:
                        self._log(gui_line, from_ytdlp=True)
                elif gui_line:
                    self._log(gui_line, from_ytdlp=True)

                retry = re.search(r'Retrying\s*\((\d+)/(\d+)\)', line_str, re.I)
                if retry and not file_access_status:
                    idle = int(time.monotonic() - last_data_at)
                    self._progress(last_percent,
                        f'{stream_label} · Передача прервана или сервер не отвечает. '
                        f'Повтор {retry[1]}/{retry[2]}, без продвижения {idle} с...')

            logger.debug(f"download: Всего строк вывода: {line_count}")

        # cancel() может очистить self._process, пока поток читает stdout/ждёт EOF.
        return_code = process.wait()
        if process.stdin is not None:
            process.stdin.close()
        if self._cancelled:
            self._log("Загрузка отменена пользователем", 'warning')
            return None
        logger.debug(f"download: Return code = {return_code}")
        return return_code

    def _allow_sponsorblock_bypass(self) -> bool:
        if self._cancelled:
            return False
        policy = self.config.get('SPONSORBLOCK_FAILURE_POLICY', 'ask')
        if policy == 'bypass':
            return True
        if policy == 'stop' or self.sponsorblock_question is None:
            return False
        while not self._cancelled:
            decision, remember = self.sponsorblock_question(self._sponsorblock_reason)
            if self._cancelled:
                return False
            if decision == 'retry':
                self._progress(0, 'Проверка SponsorBlock...')
                healthy = self.sponsorblock_state.probe(force=True)
                if self._cancelled:
                    return False
                if healthy:
                    self._notify_sponsorblock_recovered()
                    return True
                continue
            if decision == 'bypass':
                if remember:
                    self.config.set('SPONSORBLOCK_FAILURE_POLICY', 'bypass')
                    try:
                        self.config.save()
                    except OSError:
                        self._log('Не удалось сохранить согласие на обход SponsorBlock. '
                                  'Оно действует до закрытия приложения.', 'warning')
                return True
            self._cancelled = True
            self._log('Загрузка отменена пользователем в вопросе SponsorBlock.', 'info')
            return False
        return False

    def _notify_sponsorblock_recovered(self):
        message = 'SponsorBlock снова доступен. Вырезание вставок возобновлено.'
        self._log(message, 'success')
        if self.sponsorblock_notice:
            try:
                self.sponsorblock_notice(message)
            except Exception:
                logger.warning('Не удалось показать уведомление SponsorBlock', exc_info=True)

    def _prepare_sponsorblock(self, url):
        self._bypass_sponsorblock = False
        if not (is_youtube_url(url) and self.config.get('SPONSORBLOCK_REMOVE_LIST', [])):
            return True
        if self.sponsorblock_state.unavailable:
            recovered = self.sponsorblock_state.probe()
            if self._cancelled:
                return False
            if recovered:
                self._notify_sponsorblock_recovered()
            else:
                self._sponsorblock_reason = 'Не удалось связаться с API SponsorBlock'
                if not self._allow_sponsorblock_bypass():
                    self._log('SponsorBlock недоступен. Загрузка остановлена.', 'warning')
                    return False
                self._bypass_sponsorblock = self.sponsorblock_state.unavailable
        if self._bypass_sponsorblock:
            self._log('SponsorBlock недоступен — скачиваем без вырезания вставок.', 'warning')
        return not self._cancelled

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
        self._verbose_log = None
        self.already_downloaded = False
        self.result_message = ''
        download_result = 'error'

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

        logger.debug("download: Запуск subprocess.Popen")

        try:
            if is_verbose_download_log_enabled(self.config):
                self._verbose_log = VerboseDownloadLog.create(
                    self.config.get('UTILITIES_PATH', '')
                )
                if self._verbose_log:
                    self._log(f"Подробный журнал: {self._verbose_log.relative_path}")
                else:
                    self._log("Не удалось создать подробный журнал загрузки", 'warning')

            if hints.log_title:
                self._log(f"Плагин: {hints.log_title}")

            if self._verbose_log:
                self._log("Запуск загрузки")
            else:
                self._log(f"Запуск загрузки: {url}")
            self._log(f"Путь сохранения: {normalize_path_for_display(download_path)}")

            if not self._prepare_sponsorblock(url):
                return False
            range_retried = False
            sponsorblock_retried = False
            for attempt in range(3):
                if self._cancelled:
                    return False
                cmd = self._build_command(url, download_path, hints, resume=not range_retried)
                logger.debug(f"download: Команда (попытка {attempt + 1}): {cmd}")
                if self._verbose_log:
                    self._verbose_log.handle_ytdlp_line(
                        f'yt-dlp attempt {attempt + 1}: ' + ' '.join(cmd)
                    )

                return_code = self._run_process(cmd)

                if return_code is None:
                    download_result = 'cancelled'
                    return False

                if return_code == 0:
                    logger.debug("download: Загрузка успешна")
                    cleanup_download_temp_directory(download_path)
                    self.result_message = (
                        'Файл уже существует' if self.already_downloaded else
                        'Скачано без вырезания вставок' if self._bypass_sponsorblock else
                        'Файл скачан'
                    )
                    self._log(self.result_message, 'success')
                    self._progress(100.0, "Завершено")
                    download_result = 'success'
                    return True

                if self._sponsorblock_error and not self._cancelled:
                    self.sponsorblock_state.failed()
                    self._log(f'Не удалось связаться с SponsorBlock: {self._sponsorblock_reason}', 'warning')
                    if sponsorblock_retried or self._bypass_sponsorblock:
                        break
                    sponsorblock_retried = True
                    if self._allow_sponsorblock_bypass():
                        self._bypass_sponsorblock = self.sponsorblock_state.unavailable
                        if self._bypass_sponsorblock:
                            self._log('SponsorBlock недоступен — скачиваем без вырезания вставок.', 'warning')
                        self._logs_buffer = []
                        continue
                    break

                if self._range_error and not range_retried and not self._cancelled:
                    range_retried = True
                    self._log(
                        "HTTP 416: сервер не принимает продолжение. "
                        "Перезапуск загрузки с нуля (без --continue).",
                        'warning',
                    )
                    self._logs_buffer = []
                    continue

                break

            # Подробное логирование ошибок
            if self._cancelled:
                return False
            logger.error(f"download: Ошибка, return code = {return_code}")
            self._log(f"yt-dlp завершил с кодом {return_code}", 'error')
            error_lines = [
                line for line in self._logs_buffer
                if 'ERROR' in line or 'Error' in line or 'failed' in line.lower() or 'unable' in line.lower()
            ]
            if error_lines:
                logger.error(f"download: Ошибки в выводе: {error_lines[:5]}")
                for err_line in error_lines[-3:]:
                    self._log(f"Ошибка: {err_line}", 'error')

            if any('requested format is not available' in line.lower() for line in error_lines):
                self._log(
                    'Нет дорожек для выбранного формата и качества. '
                    'Попробуйте контейнер «Авто» или MKV и другое качество в настройках.',
                    'error',
                )

            return False

        except KeyboardInterrupt:
            logger.warning("download: Прервано пользователем (KeyboardInterrupt)")
            self._log("Прервано пользователем", 'warning')
            if self._process:
                _terminate_process_tree(self._process)
            download_result = 'cancelled'
            return False
        except Exception as e:
            logger.error(f"download: Исключение: {e}", exc_info=True)
            self._log(f"Ошибка загрузки: {e}", 'error')
            download_result = 'error'
            return False
        finally:
            logger.debug("download: Очистка process")
            if self._cancelled:
                download_result = 'cancelled'
            if self._verbose_log:
                self._verbose_log.close(download_result)
                self._verbose_log = None
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
