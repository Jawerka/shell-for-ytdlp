# -*- coding: utf-8 -*-
"""Тесты обезличенного подробного журнала загрузки."""

from datetime import datetime
from io import StringIO
from pathlib import Path

from core.verbose_log import (
    VERBOSE_YTDLP_OPTIONS,
    VerboseDownloadLog,
    process_line,
    sanitize_text,
    should_show_in_gui,
    summarize_traffic,
)


COOKIE_LINE = (
    "send: b'GET /videoplayback?ip=1.2.3.4&sig=secret HTTP/1.1\\r\\n"
    "Host: rr1.googlevideo.com\\r\\n"
    "Cookie: SID=secret-cookie-value\\r\\n"
    "Authorization: Bearer super-secret\\r\\n"
    "User-Agent: Mozilla/5.0\\r\\n\\r\\n'"
)

TRAFFIC_SUMMARY = (
    'requests: https://rr1---sn-abc.googlevideo.com:443 '
    '"GET /videoplayback?ip=1.2.3.4&sig=xyz HTTP/1.1" 200 12345'
)


class TestProcessLineRedaction:
    def test_drops_cookie_and_authorization_headers(self):
        kind, payload = process_line(COOKIE_LINE)
        assert kind == 'drop'
        assert payload is None

    def test_drops_set_cookie_header(self):
        kind, payload = process_line('header: Set-Cookie: SID=abc; Path=/')
        assert kind == 'drop'
        assert payload is None

    def test_drops_user_agent_header(self):
        kind, payload = process_line('header: User-Agent: Mozilla/5.0 (Windows NT 10.0)')
        assert kind == 'drop'

    def test_traffic_keeps_host_drops_query(self):
        kind, payload = process_line(TRAFFIC_SUMMARY)
        assert kind == 'traffic'
        assert payload == 'GET rr1---sn-abc.googlevideo.com 200 12345'
        assert 'ip=' not in payload
        assert 'sig=' not in payload
        assert 'videoplayback' not in payload
        assert 'Cookie' not in payload

    def test_connect_line_keeps_host(self):
        kind, payload = process_line(
            'requests: Starting new HTTPS connection (1): www.youtube.com:443'
        )
        assert kind == 'traffic'
        assert payload == 'HTTPS connect www.youtube.com:443'

    def test_redacts_url_title_id_and_windows_user(self):
        raw = (
            '[youtube] dQw4w9WgXcQ: Downloading webpage from '
            'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        )
        kind, payload = process_line(raw)
        assert kind == 'stage'
        assert payload is not None
        assert 'dQw4w9WgXcQ' not in payload
        assert 'youtube.com' not in payload
        assert '<id>' in payload
        assert '<url>' in payload

        dest = process_line(
            r'[download] Destination: C:\Users\Masny\Downloads\Secret Title [dQw4w9WgXcQ].mp4'
        )
        assert dest[0] == 'stage'
        assert 'Secret Title' not in dest[1]
        assert 'Masny' not in dest[1]
        assert dest[1].endswith('<title>.mp4')

        path_line = sanitize_text(r'Путь сохранения: C:\Users\Masny\Downloads')
        assert 'Masny' not in path_line
        assert r'C:\Users\<user>\Downloads' in path_line

    def test_redacts_cookies_argument(self):
        raw = r'yt-dlp --cookies C:\Users\Masny\utilities\youtube_cookies.txt <url>'
        _, payload = process_line(raw)
        assert payload is not None
        assert 'Masny' not in payload
        assert 'youtube_cookies' not in payload
        assert '<cookies>' in payload

    def test_sensitive_words_not_left_as_header_prefix(self):
        for raw in (
            COOKIE_LINE,
            'header: Cookie: SID=abc',
            'header: Authorization: Bearer secret',
            'header: Proxy-Authorization: Basic abc',
        ):
            _, payload = process_line(raw)
            text = payload or ''
            assert 'Cookie:' not in text
            assert 'Authorization:' not in text
            assert 'SID=abc' not in text
            assert 'Bearer secret' not in text

    def test_progress_not_shown_in_gui_stage_is(self):
        progress_kind, _ = process_line(
            '[download]  12.3% of  50.00MiB at  2.50MiB/s ETA 00:17'
        )
        stage_kind, _ = process_line('[youtube] abcdefghijk: Downloading webpage')
        assert progress_kind == 'progress'
        assert not should_show_in_gui(progress_kind)
        assert stage_kind == 'stage'
        assert should_show_in_gui(stage_kind, '[youtube] <id>: Downloading webpage')
        assert not should_show_in_gui('traffic')
        assert not should_show_in_gui('stage', 'director: Sending request via "requests"')
        assert not should_show_in_gui('stage', 'Accept: text/html')

    def test_debug_not_shown_in_gui(self):
        kind, payload = process_line('[debug] yt-dlp version 2026.11.01')
        assert kind == 'debug'
        assert payload is not None
        assert not should_show_in_gui(kind)

    def test_encodings_error_locale_is_not_an_error(self):
        kind, payload = process_line(
            '[debug] Encodings: locale cp1251, fs utf-8, out cp1251, error cp1251 (dumb,No ANSI)'
        )
        assert kind == 'debug'
        assert not should_show_in_gui(kind, payload)

    def test_redacts_escaped_windows_user_and_ffmpeg_title(self):
        cmdline = (
            "[debug] Command-line config: ['-P', "
            r"'home:C:\\Users\\Masny\\Downloads', '--cookies', "
            r"'C:\\Users\\Masny\\utilities\\www.youtube.com_cookies.txt', '<url>']"
        )
        kind, payload = process_line(cmdline)
        assert kind == 'debug'
        assert payload is not None
        assert 'Masny' not in payload
        assert 'www.youtube.com_cookies' not in payload
        assert r'C:\\Users\\<user>\\' in payload or r'C:\Users\<user>' in payload

        ffmpeg = (
            r"Output #0, mp4, to 'file:C:\Users\Masny\Temp\Почему НЕ НУЖНО "
            r"использовать Linux [btQ_SCNZEgo].mp4.part':"
        )
        _, payload = process_line(ffmpeg)
        assert payload is not None
        assert 'Linux' not in payload
        assert 'btQ_SCNZEgo' not in payload
        assert 'Masny' not in payload
        assert 'file:<path>.part' in payload or 'file:<path>' in payload

    def test_drops_plain_http_headers_and_keeps_ffmpeg_tcp_host(self):
        kind, payload = process_line('Accept: text/html,application/xhtml+xml')
        assert kind == 'drop'
        assert payload is None

        kind, payload = process_line(
            '[tcp @ 000001] Successfully connected to 74.125.97.65 port 443'
        )
        assert kind == 'traffic'
        assert payload == 'TCP connect 74.125.97.65:443'

    def test_jsc_tag_is_not_treated_as_video_id(self):
        kind, payload = process_line(
            '[youtube] [jsc:deno] Solving JS challenges using deno'
        )
        assert kind == 'stage'
        assert payload is not None
        assert '[jsc:deno]' in payload
        assert '<id>' not in payload

    def test_verbose_flags(self):
        assert '--verbose' in VERBOSE_YTDLP_OPTIONS
        assert '--print-traffic' in VERBOSE_YTDLP_OPTIONS
        assert '--progress-delta' in VERBOSE_YTDLP_OPTIONS
        assert VERBOSE_YTDLP_OPTIONS[VERBOSE_YTDLP_OPTIONS.index('--progress-delta') + 1] == '1'
        assert '--dump-pages' not in VERBOSE_YTDLP_OPTIONS

    def test_format_selector_is_not_a_path(self):
        raw = (
            "[debug] Command-line config: ['-f', "
            "\"bestvideo[height<=480][vcodec~='^(avc|h264)']/"
            "best[height<=480]\", '<url>']"
        )
        kind, payload = process_line(raw)
        assert kind == 'debug'
        assert payload is not None
        assert '<path>' not in payload
        assert 'bestvideo[height<=480]' in payload
        assert '/best[height<=480]' in payload

    def test_ffmpeg_banner_and_libx264_stats_are_dropped(self):
        for raw in (
            'ffmpeg version N-125478 Copyright (c) 2000-2026',
            'built with gcc 15.2.0',
            'configuration: --prefix=/ffbuild/prefix --enable-libx264',
            'libavcodec     63.  3.100 / 63.  3.100',
            '[libx264 @ 0001] mb I  I16..4: 29.0% 58.8% 12.2%',
            '[libx264 @ 0001] frame I:7     Avg QP:19.72  size: 11197',
            'frame=    8 fps=0.0 q=29.0 size=       0KiB time=00:00:00.34',
            'Press [q] to stop, [?] for help',
            '[vost#0:0/libx264 @ 0001] Starting thread...',
        ):
            kind, payload = process_line(raw)
            assert kind == 'drop', raw
            assert payload is None

        kind, payload = process_line(
            'frame=  360 fps= 48 q=-1.0 Lsize=     875KiB time=00:00:12.00'
        )
        assert kind == 'stage'
        assert payload is not None
        assert 'Lsize=' in payload


class TestVerboseDownloadLogSession:
    def test_writes_file_and_summary(self, tmp_path):
        clock = {'t': 0.0}

        def monotonic():
            return clock['t']

        session = VerboseDownloadLog.create(
            str(tmp_path),
            now=lambda: datetime(2026, 11, 18, 18, 17, 5),
            monotonic=monotonic,
        )
        assert session is not None
        expected = tmp_path / 'logs' / 'download-20261118-181705.log'
        assert Path(session.path) == expected

        session.handle_ytdlp_line('[youtube] dQw4w9WgXcQ: Downloading webpage')
        clock['t'] = 1.0
        gui = session.handle_ytdlp_line(TRAFFIC_SUMMARY)
        assert gui is None
        clock['t'] = 2.0
        session.handle_ytdlp_line('[download]  50.0% of  10.00MiB at  5.00MiB/s ETA 00:01')
        clock['t'] = 4.0
        session.handle_ytdlp_line('[info] dQw4w9WgXcQ: Downloading 1 format(s): 137+251')
        session.handle_ytdlp_line('[Merger] Merging formats into "Secret.mp4"')
        session.close('success')

        text = expected.read_text(encoding='utf-8')
        assert 'dQw4w9WgXcQ' not in text
        assert 'Secret' not in text
        assert 'ip=1.2.3.4' not in text
        assert 'Cookie' not in text
        assert 'GET rr1---sn-abc.googlevideo.com 200 12345' in text
        assert '--- summary ---' in text
        assert 'result: success' in text
        assert '137+251' in text
        assert 'rr1---sn-abc.googlevideo.com' in text
        assert session.relative_path.replace('\\', '/').endswith(
            'logs/download-20261118-181705.log'
        )

    def test_ffmpeg_download_summary_uses_tcp_bytes_and_codecs(self, tmp_path):
        clock = {'t': 0.0}

        def monotonic():
            return clock['t']

        session = VerboseDownloadLog.create(
            str(tmp_path),
            now=lambda: datetime(2026, 11, 18, 18, 36, 10),
            monotonic=monotonic,
        )
        assert session is not None

        session.handle_ytdlp_line('[youtube] btQ_SCNZEgo: Downloading webpage')
        clock['t'] = 3.4
        session.handle_ytdlp_line('[info] btQ_SCNZEgo: Downloading 1 format(s): 135+140')
        clock['t'] = 3.5
        session.handle_ytdlp_line(
            '[debug] Invoking ffmpeg downloader on "https://example.invalid/v"'
        )
        session.handle_ytdlp_line('[download] Destination: Secret Title.mp4')
        clock['t'] = 3.54
        session.handle_ytdlp_line(
            '[tcp @ 0001] Successfully connected to 74.125.97.65 port 443'
        )
        clock['t'] = 5.3
        session.handle_ytdlp_line(
            'Stream #0:0[0x1](und): Video: h264 (Main), yuv420p, 854x480, 344 kb/s'
        )
        clock['t'] = 6.27
        session.handle_ytdlp_line(
            'Stream #1:0[0x1](und): Audio: aac (LC), 44100 Hz, stereo, 128 kb/s'
        )
        session.handle_ytdlp_line(
            'Stream #0:0 -> #0:0 (h264 (native) -> h264 (libx264))'
        )
        session.handle_ytdlp_line(
            '[libx264 @ 0001] mb I  I16..4: 29.0% 58.8% 12.2%'
        )
        session.handle_ytdlp_line('configuration: --prefix=/ffbuild --enable-libx264')
        session.handle_ytdlp_line(COOKIE_LINE)
        clock['t'] = 13.84
        session.handle_ytdlp_line('[AVIOContext @ 0001] Statistics: 425984 bytes read, 0 seeks')
        session.handle_ytdlp_line('[AVIOContext @ 0002] Statistics: 229376 bytes read, 0 seeks')
        session.handle_ytdlp_line('Exiting with exit code 0')
        clock['t'] = 13.85
        session.handle_ytdlp_line('[download] 100% of  874.95KiB in 00:00:10 at 84.69KiB/s')
        clock['t'] = 13.86
        session.handle_ytdlp_line(
            '[VideoRemuxer] Not remuxing media file "Secret.mp4"; already is in target format mp4'
        )
        clock['t'] = 14.32
        session.close('success')

        text = Path(session.path).read_text(encoding='utf-8')
        assert 'btQ_SCNZEgo' not in text
        assert 'Secret' not in text
        assert 'mb I' not in text
        assert 'configuration:' not in text
        assert 'Cookie' not in text
        assert 'SID=' not in text
        assert 'page parse: 3.5s' in text
        assert 'download: 10.3s' in text
        assert 'encode: 7.6s' in text
        assert 'merge: 0.5s' in text
        assert 'format: 135+140, 480p, h264+aac, mp4, 874.95KiB' in text
        assert '74.125.97.65  CONNECT  1 conn  -  640.0 KiB' in text
        assert 'avg speed: 0.06 MiB/s' in text

    def test_create_without_path_returns_none(self):
        assert VerboseDownloadLog.create('') is None

    def test_write_app_line_redacts_url(self):
        buffer = StringIO()
        session = VerboseDownloadLog(
            'memory.log',
            buffer,
            now=lambda: datetime(2026, 11, 18, 18, 0, 0),
            monotonic=lambda: 0.0,
        )
        message = 'Запуск загрузки: https://youtube.com/watch?v=secretid11'
        text = session.write_app_line(message)
        assert text == message
        assert '<url>' in buffer.getvalue()
        assert 'youtube.com' not in buffer.getvalue()

    def test_gui_keeps_titles_while_file_is_anonymized(self):
        buffer = StringIO()
        session = VerboseDownloadLog('memory.log', buffer)
        for message in (
            '[download] Destination: Secret Title.mp4',
            '[Merger] Merging formats into "Secret Title.mp4"',
            '[MoveFiles] Moving file "Secret Title.mp4" to "Secret Title.mp4"',
        ):
            assert session.handle_ytdlp_line(message) == message
        assert session.write_app_line('Плагин: Secret Title') == 'Плагин: Secret Title'
        assert 'Secret Title' not in buffer.getvalue()
        assert '<title>' in buffer.getvalue()


class TestSummarizeTraffic:
    def test_none_size(self):
        line = 'https://example.com:443 "GET /x HTTP/1.1" 204 None'
        assert summarize_traffic(line) == 'GET example.com 204'
