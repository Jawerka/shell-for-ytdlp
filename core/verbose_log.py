# -*- coding: utf-8 -*-
"""Обезличенный подробный журнал загрузки.

Нужен, чтобы сравнить серверы, формат и скорость двух загрузок
без данных пользователя: cookies, URL, названия, идентификаторов.
"""

from __future__ import annotations

import logging
import os
import re
import time
from collections import Counter, defaultdict
from datetime import datetime
from typing import Callable, Dict, List, Optional, Tuple

logger = logging.getLogger('UI-for-ytdlp.verbose_log')

VERBOSE_YTDLP_OPTIONS = [
    '--verbose',
    '--print-traffic',
    '--progress-delta', '1',
]

# Сырой HTTP-дамп --print-traffic: путь, query и заголовки не пишем.
# Без \b: в repr байтов заголовок идёт сразу после "\n", и граница слова не срабатывает.
_RAW_HTTP_DUMP_RE = re.compile(r'^(send:|header:|reply:)', re.I)
_SENSITIVE_HEADER_RE = re.compile(
    r'(?i)(set-cookie|cookie|authorization|proxy-authorization|user-agent|referer)\s*:'
)
_TRAFFIC_SUMMARY_RE = re.compile(
    r'https?://(?P<host>[^/:]+)(?::(?P<port>\d+))?\s+'
    r'"(?P<method>[A-Z]+)\s+\S+\s+[^"]*"\s+'
    r'(?P<status>\d{3})(?:\s+(?P<size>\d+|None))?',
    re.I,
)
_CONNECT_RE = re.compile(
    r'Starting new (?P<proto>HTTPS|HTTP) connection\s*\(\d+\):\s*'
    r'(?P<host>[^:\s]+)(?::(?P<port>\d+))?',
    re.I,
)
_URL_RE = re.compile(r'https?://[^\s\'"<>]+', re.I)
_COOKIES_ARG_RE = re.compile(
    r'(--cookies(?:-from-browser)?)\s+\S+',
    re.I,
)
_COOKIES_LIST_RE = re.compile(
    r"(--cookies(?:-from-browser)?)(['\"]?\s*,\s*['\"])[^'\"]+",
    re.I,
)
_COOKIES_FILE_RE = re.compile(r'(?i)cookies[^\\/\'"\s]*\.txt')
# Обычный путь и python-repr с удвоенными слэшами: C:\Users\Name и C:\\Users\\Name.
_WIN_USER_RE = re.compile(r'(?i)([A-Z]:(?:\\+)Users(?:\\+))([^\\]+)')
_UNIX_USER_RE = re.compile(r'(/Users/|/home/)([^/]+)')
_EXTRACTOR_ID_RE = re.compile(
    r'(\[(?:youtube(?::[^\]]+)?|info|generic|vk|goodgame[^\]]*)\]\s+)'
    r'([A-Za-z0-9_-]{4,64}):',
    re.I,
)
_DESTINATION_RE = re.compile(r'(Destination:\s*)(.+)$')
_MERGING_INTO_RE = re.compile(
    r'(Merging formats into\s+)["\']([^"\']+)["\']',
    re.I,
)
_QUOTED_PATH_RE = re.compile(r'"([^"]+)"')
_FILE_SCHEME_RE = re.compile(
    r'file:(?:[A-Z]:)?[\\/].+?\.(?:mp4|mkv|webm|m4a|m4v|mov|opus|ogg|mp3|part|ytdl)(?:\.\w+)?',
    re.I,
)
_UNQUOTED_MEDIA_PATH_RE = re.compile(
    r'[A-Z]:[\\/].+?\.(?:mp4|mkv|webm|m4a|m4v|mov|opus|ogg|mp3|part|ytdl)(?:\.\w+)?',
    re.I,
)
_FORMATS_RE = re.compile(r'Downloading 1 format\(s\):\s*(\S+)')
_FRAGMENT_RE = re.compile(r'Downloading fragment\s+(\d+)/(\d+)', re.I)
_RETRY_RE = re.compile(r'(?i)\bretrying\b')
_MEDIA_EXT_RE = re.compile(
    r'\.(mp4|mkv|webm|m4a|m4v|mov|opus|ogg|mp3|part|ytdl|info\.json)$',
    re.I,
)
_HTTP_HEADER_LINE_RE = re.compile(
    r'^(Accept|Accept-Language|Accept-Encoding|Accept-Charset|Sec-Fetch-\w+|'
    r'Connection|Host|Content-Type|Content-Length|Range|Origin|TE|Pragma|'
    r'Cache-Control)\s*:',
    re.I,
)
_TCP_CONNECT_RE = re.compile(
    r'(?:Starting connection attempt to|Successfully connected to)\s+'
    r'(\S+)\s+port\s+(\d+)',
    re.I,
)
_GUI_STAGE_RE = re.compile(
    r'^\[(youtube|youtube:[^\]]+|info|download|Merger|VideoRemuxer|'
    r'FixupM3u8|SponsorBlock|MoveFiles|ExtractAudio|generic)\]',
    re.I,
)
_FFMPEG_BANNER_RE = re.compile(
    r'^(ffmpeg version|built with|configuration:|libav\w+|libsw\w+)',
    re.I,
)
_FFMPEG_THREAD_RE = re.compile(
    r'(Starting thread|Terminating thread|Press \[q\] to stop|'
    r'returned EOF|Encoder thread received EOF|Decoder returned EOF|'
    r'Filtergraph returned EOF|All consumers returned EOF)',
    re.I,
)
_FFMPEG_FRAME_PROGRESS_RE = re.compile(r'^frame=\s*\d+', re.I)
_LIBX264_NOISE_RE = re.compile(
    r'\[libx264 @|'
    r'\bmb [IPB]\s|'
    r'\bi16 |\bi8 |\bi4 |\bi8c |'
    r'8x8 transform|coded y,|Weighted P-Frames|'
    r'ref P |ref B |consecutive B-frames|'
    r'frame [IPB]:',
    re.I,
)
_FFMPEG_MISC_NOISE_RE = re.compile(
    r'Reinit context|advanced_editlist|using cpu capabilities|'
    r'using SAR=|kb/s:\s*\d',
    re.I,
)
_STATS_BYTES_RE = re.compile(r'Statistics:\s+(\d+)\s+bytes read', re.I)
_VIDEO_STREAM_RE = re.compile(
    r'Stream\s+#\d+:\d+(?!.*->)[^:]*:\s+Video:\s+([A-Za-z0-9]+)'
    r'.*?(\d{2,5})x(\d{2,5})',
    re.I,
)
_AUDIO_STREAM_RE = re.compile(
    r'Stream\s+#\d+:\d+(?!.*->)[^:]*:\s+Audio:\s+([A-Za-z0-9]+)',
    re.I,
)
_STREAM_ENCODER_RE = re.compile(
    r'Stream\s+#\d+:\d+\s+->\s+#\d+:\d+\s+\(.+?->\s*\w+\s+\((\w+)\)\)',
    re.I,
)
_COMPLETED_DOWNLOAD_RE = re.compile(
    r'\[download\].*\b100(?:\.0+)?%.*\sin\s+\d',
    re.I,
)
_DRIVE_OR_BACKSLASH_RE = re.compile(r'[A-Z]:[\\/]|\\', re.I)

Kind = str  # drop | traffic | progress | stage | error | debug


def is_verbose_download_log_enabled(config) -> bool:
    """Прочитать флаг из конфигурации."""
    if config is None:
        return False
    getter = getattr(config, 'get', None)
    if callable(getter):
        return bool(getter('VERBOSE_DOWNLOAD_LOG', False))
    return bool(config.get('VERBOSE_DOWNLOAD_LOG', False))


def summarize_traffic(line: str) -> Optional[str]:
    """Сжать HTTP-строку до метода, хоста, кода и размера. Путь и query отбрасываются."""
    match = _TRAFFIC_SUMMARY_RE.search(line)
    if match:
        host = match.group('host')
        method = match.group('method').upper()
        status = match.group('status')
        size = match.group('size')
        if size and size != 'None':
            return f'{method} {host} {status} {size}'
        return f'{method} {host} {status}'

    match = _CONNECT_RE.search(line)
    if match:
        host = match.group('host')
        port = match.group('port')
        proto = match.group('proto').upper()
        if port:
            return f'{proto} connect {host}:{port}'
        return f'{proto} connect {host}'

    match = _TCP_CONNECT_RE.search(line)
    if match:
        return f'TCP connect {match.group(1)}:{match.group(2)}'
    return None


def _redact_extractor_ids(line: str) -> str:
    def _replace(match: re.Match) -> str:
        return f'{match.group(1)}<id>:'

    return _EXTRACTOR_ID_RE.sub(_replace, line)


def _extension_of(name: str) -> str:
    match = _MEDIA_EXT_RE.search(name.split('?')[0].rstrip('"\''))
    return match.group(0) if match else ''


def _redact_destination(line: str) -> str:
    def _replace(match: re.Match) -> str:
        ext = _extension_of(match.group(2))
        return f'{match.group(1)}<title>{ext}'

    line = _DESTINATION_RE.sub(_replace, line)

    def _merge(match: re.Match) -> str:
        ext = _extension_of(match.group(2))
        return f'{match.group(1)}"<title>{ext}"'

    return _MERGING_INTO_RE.sub(_merge, line)


def _redact_quoted_paths(line: str) -> str:
    def _replace(match: re.Match) -> str:
        text = match.group(1)
        if text.startswith('http://') or text.startswith('https://'):
            return '"<url>"'
        # Путь: буква диска, обратный слэш или медиа-расширение.
        # Обычный / в селекторе -f "bestvideo.../best" путём не считается.
        if _DRIVE_OR_BACKSLASH_RE.search(text) or _MEDIA_EXT_RE.search(text):
            ext = _extension_of(text)
            return f'"<file>{ext}"' if ext else '"<path>"'
        return match.group(0)

    return _QUOTED_PATH_RE.sub(_replace, line)


def _redact_filesystem_paths(line: str) -> str:
    def _file_scheme(_match: re.Match) -> str:
        ext = _extension_of(_match.group(0))
        return f'file:<path>{ext}' if ext else 'file:<path>'

    def _media_path(match: re.Match) -> str:
        ext = _extension_of(match.group(0))
        return f'<file>{ext}' if ext else '<path>'

    line = _FILE_SCHEME_RE.sub(_file_scheme, line)
    return _UNQUOTED_MEDIA_PATH_RE.sub(_media_path, line)


def sanitize_text(line: str) -> str:
    """Убрать из строки данные, по которым можно узнать пользователя или ролик."""
    if line.startswith('Плагин: '):
        return 'Плагин: <title>'
    line = _COOKIES_ARG_RE.sub(r'\1 <cookies>', line)
    line = _COOKIES_LIST_RE.sub(r'\1\2<cookies>', line)
    line = _COOKIES_FILE_RE.sub('<cookies>', line)
    line = _URL_RE.sub('<url>', line)
    line = _redact_extractor_ids(line)
    line = _redact_destination(line)
    line = _redact_quoted_paths(line)
    line = _redact_filesystem_paths(line)
    line = _WIN_USER_RE.sub(r'\1<user>', line)
    line = _UNIX_USER_RE.sub(r'\1<user>', line)
    if 'Proxy map' in line:
        return '[debug] Proxy map: <redacted>'
    return line.rstrip()


def is_raw_http_dump(line: str) -> bool:
    return bool(_RAW_HTTP_DUMP_RE.match(line.strip()))


def contains_sensitive_header(line: str) -> bool:
    return bool(_SENSITIVE_HEADER_RE.search(line))


def _is_completed_download_line(line: str) -> bool:
    return bool(_COMPLETED_DOWNLOAD_RE.search(line))


def is_ffmpeg_noise(line: str) -> bool:
    """Баннер ffmpeg, прогресс кадра и статистика libx264 в журнал не пишем."""
    stripped = line.strip()
    if not stripped:
        return False
    # Склеенные через \r кадры: если нет Lsize, это промежуточный прогресс.
    head = stripped.split('\r')[0].strip()
    if _FFMPEG_FRAME_PROGRESS_RE.match(head) and 'Lsize=' not in stripped:
        return True
    if _FFMPEG_BANNER_RE.match(stripped):
        return True
    if _FFMPEG_THREAD_RE.search(stripped):
        return True
    if _LIBX264_NOISE_RE.search(stripped):
        return True
    if _FFMPEG_MISC_NOISE_RE.search(stripped):
        return True
    return False


def classify_sanitized(line: str) -> Kind:
    # Только метки yt-dlp. Иначе «error cp1251» из [debug] Encodings попадает в GUI.
    if re.search(r'(?i)(?:^ERROR:|\]\s*ERROR:|\bERROR:\s)', line):
        return 'error'
    if re.search(r'(?i)(?:^WARNING:|\]\s*WARNING:|\bWARNING:\s)', line):
        return 'error'
    if '[download]' in line and '%' in line and 'Destination' not in line:
        return 'progress'
    if (
        line.startswith('[debug]')
        or line.startswith('director:')
        or line.startswith('requests:')
        or line.startswith('urllib')
    ):
        return 'debug'
    return 'stage'


def process_line(raw: str) -> Tuple[Kind, Optional[str]]:
    """Классифицировать сырую строку yt-dlp и вернуть обезличенный текст."""
    stripped = raw.strip()
    if not stripped:
        return 'drop', None
    if (
        is_raw_http_dump(stripped)
        or contains_sensitive_header(stripped)
        or _HTTP_HEADER_LINE_RE.match(stripped)
        or is_ffmpeg_noise(stripped)
    ):
        return 'drop', None
    traffic = summarize_traffic(stripped)
    if traffic:
        return 'traffic', traffic
    sanitized = sanitize_text(stripped)
    if not sanitized or contains_sensitive_header(sanitized):
        return 'drop', None
    return classify_sanitized(sanitized), sanitized


def should_show_in_gui(kind: Kind, line: str = '') -> bool:
    if kind == 'error':
        return True
    if kind != 'stage':
        return False
    if not line:
        return True
    return bool(_GUI_STAGE_RE.match(line))


def _parse_speed_kib(line: str) -> Optional[float]:
    match = re.search(r'at\s+(\d+\.?\d*)\s*(KiB|MiB|GiB)/s', line)
    if not match:
        return None
    value = float(match.group(1))
    unit = match.group(2)
    if unit == 'GiB':
        return value * 1024 * 1024
    if unit == 'MiB':
        return value * 1024
    return value


def _format_duration(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0
    if seconds < 60:
        return f'{seconds:.1f}s'
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f'{int(minutes)}m {sec:.0f}s'
    hours, minutes = divmod(minutes, 60)
    return f'{int(hours)}h {int(minutes)}m'


def _format_bytes(size: int) -> str:
    if size >= 1024 * 1024 * 1024:
        return f'{size / (1024 * 1024 * 1024):.2f} GiB'
    if size >= 1024 * 1024:
        return f'{size / (1024 * 1024):.2f} MiB'
    if size >= 1024:
        return f'{size / 1024:.1f} KiB'
    return f'{size} B'


class VerboseDownloadLog:
    """Сессия журнала одной загрузки: файл, этапы, хосты, сводка."""

    def __init__(
        self,
        path: str,
        file_obj,
        now: Optional[Callable[[], datetime]] = None,
        monotonic: Optional[Callable[[], float]] = None,
    ):
        self.path = path
        self._file = file_obj
        self._now = now or datetime.now
        self._mono = monotonic or time.monotonic
        self._t0 = self._mono()
        self._download_start_at: Optional[float] = None
        self._first_progress_at: Optional[float] = None
        self._last_progress_at: Optional[float] = None
        self._first_byte_at: Optional[float] = None
        self._merge_at: Optional[float] = None
        self._encode_start_at: Optional[float] = None
        self._encode_end_at: Optional[float] = None
        self._transcoding = False
        self._hosts: Dict[str, Dict] = defaultdict(lambda: {
            'count': 0,
            'bytes': 0,
            'statuses': Counter(),
            'methods': Counter(),
        })
        self._last_tcp_host: Optional[str] = None
        self._ffmpeg_bytes = 0
        self._speeds_kib: List[float] = []
        self._format_ids: Optional[str] = None
        self._container: Optional[str] = None
        self._size_label: Optional[str] = None
        self._completed_sizes = {}
        self._current_destination = None
        self._height_label: Optional[str] = None
        self._video_codec: Optional[str] = None
        self._audio_codec: Optional[str] = None
        self._retries = 0
        self._fragments_total: Optional[int] = None
        self._closed = False

    @classmethod
    def create(
        cls,
        utilities_path: str,
        now: Optional[Callable[[], datetime]] = None,
        monotonic: Optional[Callable[[], float]] = None,
    ) -> Optional['VerboseDownloadLog']:
        """Создать файл utilities/logs/download-YYYYMMDD-HHMMSS.log."""
        if not utilities_path:
            return None
        now_fn = now or datetime.now
        log_dir = os.path.join(utilities_path, 'logs')
        try:
            os.makedirs(log_dir, exist_ok=True)
            stamp = now_fn()
            filename = f"download-{stamp.strftime('%Y%m%d-%H%M%S')}.log"
            path = os.path.join(log_dir, filename)
            file_obj = open(path, 'w', encoding='utf-8')
        except OSError as exc:
            logger.warning("verbose log: не удалось создать журнал: %s", exc)
            return None
        session = cls(path, file_obj, now=now_fn, monotonic=monotonic)
        session._write('# UI-for-ytdlp verbose download log')
        session._write('# Anonymized: hosts and timings only, no user data')
        return session

    @property
    def relative_path(self) -> str:
        return os.path.join('logs', os.path.basename(self.path))

    def handle_ytdlp_line(self, raw: str) -> Optional[str]:
        """Записать обезличенную строку yt-dlp. Вернуть текст для GUI или None."""
        kind, payload = process_line(raw)
        if kind == 'drop' or payload is None:
            return None
        self._observe(kind, payload, raw)
        self._write(payload)
        if should_show_in_gui(kind, payload):
            return raw.strip()
        return None

    def write_app_line(self, message: str) -> str:
        """Записать обезличенное сообщение и вернуть исходное для GUI."""
        kind, payload = process_line(message)
        text = payload if payload is not None else sanitize_text(message)
        if text:
            self._write(text)
        return message

    def close(self, result: str) -> None:
        """Дописать сводку и закрыть файл. result: success | error | cancelled."""
        if self._closed:
            return
        try:
            for line in self._summary_lines(result):
                self._write(line)
        finally:
            self._closed = True
            try:
                self._file.close()
            except OSError:
                pass

    def _write(self, text: str) -> None:
        stamp = self._now()
        if isinstance(stamp, datetime):
            rendered = stamp.strftime('%H:%M:%S.%f')[:-3]
        else:
            rendered = str(stamp)
        try:
            self._file.write(f'[{rendered}] {text}\n')
            self._file.flush()
        except OSError as exc:
            logger.warning("verbose log: ошибка записи: %s", exc)

    def _mark_download_start(self, now: float) -> None:
        if self._download_start_at is None:
            self._download_start_at = now

    def _observe(self, kind: Kind, payload: str, raw: str) -> None:
        now = self._mono()
        if kind == 'traffic':
            self._observe_traffic(payload, now)
        if 'Invoking ffmpeg downloader' in raw:
            self._mark_download_start(now)
        if '[download]' in raw and 'Destination:' in raw:
            self._mark_download_start(now)
            self._current_destination = raw.split('Destination:', 1)[1].strip()
        if 'Downloading fragment' in raw:
            self._mark_download_start(now)
        is_progress = kind == 'progress' or (
            kind == 'stage' and '[download]' in payload and '%' in payload
        )
        if is_progress:
            completed = _is_completed_download_line(raw)
            if not completed:
                self._mark_download_start(now)
                if self._first_progress_at is None:
                    self._first_progress_at = now
                speed = _parse_speed_kib(raw)
                if speed is not None:
                    self._speeds_kib.append(speed)
            elif self._current_destination is not None:
                size = re.search(r'of\s+(\d+\.?\d*)\s*(KiB|MiB|GiB)', raw)
                if size:
                    multiplier = {'KiB': 1024, 'MiB': 1024**2, 'GiB': 1024**3}[size[2]]
                    self._completed_sizes[self._current_destination] = float(size[1]) * multiplier
            self._last_progress_at = now
            size_match = re.search(r'of\s+(\d+\.?\d*\s*(?:KiB|MiB|GiB))', raw)
            if size_match:
                self._size_label = size_match.group(1)
        if '[Merger]' in raw or '[VideoRemuxer]' in raw:
            if self._merge_at is None:
                self._merge_at = now
        self._observe_format(payload, raw, now)
        fragments = _FRAGMENT_RE.search(raw)
        if fragments:
            self._fragments_total = int(fragments.group(2))
        if _RETRY_RE.search(raw):
            self._retries += 1
        stats = _STATS_BYTES_RE.search(raw)
        if stats and self._merge_at is None:
            nbytes = int(stats.group(1))
            self._ffmpeg_bytes += nbytes
            if self._last_tcp_host:
                self._hosts[self._last_tcp_host]['bytes'] += nbytes
        if 'Exiting with exit code' in raw and self._transcoding:
            self._encode_end_at = now

    def _observe_format(self, payload: str, raw: str, now: float) -> None:
        formats = _FORMATS_RE.search(payload) or _FORMATS_RE.search(raw)
        if formats:
            self._format_ids = formats.group(1)
        dest = _DESTINATION_RE.search(payload) or _MERGING_INTO_RE.search(payload)
        if dest:
            ext = _extension_of(dest.group(2) if dest.lastindex >= 2 else payload)
            if ext:
                self._container = ext.lstrip('.')
        if self._video_codec is None:
            video = _VIDEO_STREAM_RE.search(raw)
            if video:
                self._video_codec = video.group(1).lower()
                self._height_label = f'{int(video.group(3))}p'
        if self._audio_codec is None:
            audio = _AUDIO_STREAM_RE.search(raw)
            if audio:
                self._audio_codec = audio.group(1).lower()
        encoder = _STREAM_ENCODER_RE.search(raw)
        if encoder:
            name = encoder.group(1).lower()
            if name not in ('copy', 'native'):
                self._transcoding = True
                if self._encode_start_at is None:
                    self._encode_start_at = now

    def _observe_traffic(self, payload: str, now: float) -> None:
        parts = payload.split()
        if len(parts) >= 3 and parts[1] == 'connect':
            host = parts[2].split(':')[0]
            stats = self._hosts[host]
            stats['methods']['CONNECT'] += 1
            stats['count'] += 1
            self._last_tcp_host = host
            return
        if len(parts) >= 3:
            method, host, status = parts[0], parts[1], parts[2]
            stats = self._hosts[host]
            stats['count'] += 1
            stats['methods'][method] += 1
            stats['statuses'][status] += 1
            if len(parts) >= 4 and parts[3].isdigit():
                stats['bytes'] += int(parts[3])

    def _format_summary_label(self) -> Optional[str]:
        parts = []
        if self._format_ids:
            parts.append(self._format_ids)
        if self._height_label:
            parts.append(self._height_label)
        codecs = []
        if self._video_codec:
            codecs.append(self._video_codec)
        if self._audio_codec:
            codecs.append(self._audio_codec)
        if codecs:
            parts.append('+'.join(codecs))
        if self._container:
            parts.append(self._container)
        if len(self._completed_sizes) > 1:
            parts.append(_format_bytes(int(sum(self._completed_sizes.values()))) + ' (all streams)')
        elif self._size_label:
            parts.append(self._size_label)
        if not parts:
            return None
        return 'format: ' + ', '.join(parts)

    def _avg_speed_line(self, download_seconds: float) -> Optional[str]:
        if self._ffmpeg_bytes and download_seconds > 0:
            mib_s = (self._ffmpeg_bytes / download_seconds) / (1024 * 1024)
            return f'avg speed: {mib_s:.2f} MiB/s'
        if self._completed_sizes and download_seconds > 0:
            avg = sum(self._completed_sizes.values()) / download_seconds / (1024 * 1024)
            return f'avg speed: {avg:.2f} MiB/s (completed media bytes / download elapsed; includes waits, may include resumed data)'
        return None

    def _host_unit(self, stats: Dict) -> str:
        methods = set(stats['methods'])
        if methods and methods <= {'CONNECT'}:
            return 'conn'
        return 'req'

    def _summary_lines(self, result: str) -> List[str]:
        end = self._mono()
        total = end - self._t0
        download_start = self._download_start_at
        parse_until = download_start or self._merge_at or end
        download_end = self._last_progress_at or self._merge_at or end
        merge_start = self._merge_at or end
        first_progress = (f'{_format_duration(self._first_progress_at - self._t0)}'
                          if self._first_progress_at is not None else 'not observed')
        download_seconds = 0.0
        if download_start is not None:
            download_seconds = download_end - download_start
        elif self._first_progress_at is not None:
            download_seconds = download_end - self._first_progress_at

        lines = [
            '--- summary ---',
            f'result: {result}',
            f'total: {_format_duration(total)}',
            f'  preparation (includes waits/retries): {_format_duration(parse_until - self._t0)}',
            f'  first progress: {first_progress}',
            f'  download: {_format_duration(download_seconds)}',
        ]
        if self._transcoding and self._encode_start_at is not None:
            encode_end = self._encode_end_at or merge_start
            lines.append(
                f'  encode: {_format_duration(encode_end - self._encode_start_at)}'
            )
        lines.append(f'  merge: {_format_duration(end - merge_start)}')
        format_line = self._format_summary_label()
        if format_line:
            lines.append(format_line)
        speed_line = self._avg_speed_line(download_seconds)
        if speed_line:
            lines.append(speed_line)
        if self._fragments_total:
            lines.append(f'fragments: {self._fragments_total}')
        lines.append(f'retries: {self._retries}')
        if self._hosts:
            lines.append('hosts:')
            for host, stats in sorted(
                self._hosts.items(),
                key=lambda item: item[1]['bytes'],
                reverse=True,
            ):
                statuses = ', '.join(
                    f'{code}×{count}'
                    for code, count in sorted(stats['statuses'].items())
                ) or '-'
                methods = ','.join(sorted(stats['methods']))
                unit = self._host_unit(stats)
                lines.append(
                    f"  {host}  {methods}  {stats['count']} {unit}  "
                    f"{statuses}  {_format_bytes(stats['bytes'])}"
                )
        else:
            lines.append('hosts: (none recorded)')
        return lines
