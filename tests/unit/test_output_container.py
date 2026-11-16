"""Выбор контейнера: совместимость кодеков, настройки и команды без сети."""

from unittest.mock import Mock, patch

import pytest

from core.config import ConfigManager, DEFAULT_CONFIG
from core.download_handlers import DownloadHints
from core.downloader import YouTubeDownloader
from core.pipeline import (
    OUTPUT_CONTAINER_CHOICES,
    OUTPUT_CONTAINER_DESCRIPTIONS,
    normalize_output_container,
    ytdlp_container_options,
    ytdlp_format_selector_for_container,
    ytdlp_format_selector_for_quality,
)
from ui.components.settings_dialog import SettingsDialog


@pytest.mark.parametrize('value', [None, '', 'avi', [], 123])
def test_invalid_container_uses_auto(value):
    assert normalize_output_container(value) == 'auto'
    assert ytdlp_container_options(value) == []


def test_container_normalizes_case_and_spaces():
    assert normalize_output_container(' MP4 ') == 'mp4'


@pytest.mark.parametrize('container', ['auto', 'mkv'])
def test_best_quality_keeps_existing_selection(container):
    assert ytdlp_format_selector_for_container('720', container) == (
        ytdlp_format_selector_for_quality('720')
    )


@pytest.mark.parametrize('container', ['mp4', 'webm'])
@pytest.mark.parametrize('quality', ['max', '480', '720', '1080'])
def test_strict_codecs_apply_to_every_fallback(container, quality):
    selector = ytdlp_format_selector_for_container(quality, container)
    for alternative in selector.split('/'):
        assert '[vcodec' in alternative
        assert '[acodec' in alternative
        if quality != 'max':
            assert f'[height<={quality}]' in alternative
    assert not selector.endswith('/best')


@pytest.mark.parametrize('container', ['mp4', 'webm', 'mkv'])
def test_container_also_remuxes_single_file(container):
    options = ytdlp_container_options(container)
    assert options[options.index('--merge-output-format') + 1] == container
    assert options[options.index('--remux-video') + 1] == container
    assert '--recode-video' not in options
    assert ('Merger+ffmpeg_o:-movflags +faststart' in options) == (container == 'mp4')
    assert ('VideoRemuxer+ffmpeg_o:-movflags +faststart' in options) == (container == 'mp4')


@pytest.mark.parametrize('container', ['auto', 'mp4', 'webm', 'mkv'])
def test_explicit_container_overrides_handler_container(container):
    config = Mock()
    config.get.side_effect = lambda key, default=None: {
        'OUTPUT_CONTAINER': container, 'YTDLP_PATH': 'yt-dlp.exe',
        'UTILITIES_PATH': '', 'VIDEO_QUALITY': '720',
    }.get(key, default)
    downloader = YouTubeDownloader(config, Mock(), Mock())
    hints = DownloadHints(
        url='https://example.com/video.m3u8', format_selector='0',
        merge_output_format='mp4', referer='https://goodgame.ru/',
    )
    with patch('core.downloader.find_cookies_txt', return_value=None):
        command = downloader._build_command('https://goodgame.ru/vods/test', '/out', hints)
    assert command.count('--merge-output-format') == 1
    expected = 'mp4' if container == 'auto' else container
    assert command[command.index('--merge-output-format') + 1] == expected
    selector = command[command.index('-f') + 1]
    if container in ('mp4', 'webm'):
        assert selector.startswith('(0)[vcodec')
        assert '[acodec' in selector
    else:
        assert selector == '0'
    assert '--referer' in command
    assert command[-1] == hints.url


@pytest.mark.parametrize('saved,expected', [({}, 'auto'), ({'OUTPUT_CONTAINER': 'webm'}, 'webm')])
def test_config_merges_old_and_new_settings(saved, expected):
    config = ConfigManager.__new__(ConfigManager)
    assert config._merge_with_defaults(saved)['OUTPUT_CONTAINER'] == expected


def test_settings_save_passes_container_and_quality():
    dialog = SettingsDialog.__new__(SettingsDialog)
    dialog.cookies_entry = Mock()
    dialog.cookies_entry.get.return_value = ''
    dialog.checkbox_vars = {}
    dialog.clipboard_monitor_var = Mock()
    dialog.clipboard_monitor_var.get.return_value = False
    dialog.sound_enabled_var = Mock()
    dialog.sound_enabled_var.get.return_value = True
    dialog.quality_var = Mock()
    dialog.quality_var.get.return_value = '720p'
    dialog._quality_values = {'720p': '720'}
    dialog.container_var = Mock()
    dialog.container_var.get.return_value = 'WebM'
    dialog._container_values = {'WebM': 'webm'}
    dialog.on_save_callback = Mock()
    dialog.destroy = Mock()

    dialog._save_and_close()

    dialog.on_save_callback.assert_called_once_with(None, [], False, True, '720', 'webm')
    dialog.destroy.assert_called_once()


def test_main_window_persists_container():
    from ui.main_window import MainWindow

    window = MainWindow.__new__(MainWindow)
    window.config_manager = Mock()
    window.log_viewer = Mock()
    window.clipboard_monitor = Mock()
    window.sound_manager = Mock()
    with patch('ui.main_window.SettingsDialog') as dialog_class:
        window._open_settings()
        on_save = dialog_class.call_args.args[4]
        on_save(None, [], False, True, '720', 'webm')
    window.config_manager.set.assert_any_call('OUTPUT_CONTAINER', 'webm')
    window.config_manager.set.assert_any_call('VIDEO_QUALITY', '720')
    window.config_manager.save.assert_called()


def test_unavailable_format_explains_how_to_recover(tmp_path):
    config = Mock()
    config.get.side_effect = lambda key, default=None: {
        'DOWNLOAD_PATH': str(tmp_path), 'YTDLP_PATH': 'yt-dlp.exe',
        'OUTPUT_CONTAINER': 'webm',
    }.get(key, default)
    downloader = YouTubeDownloader(config, Mock(), Mock())

    def fail_download(command):
        downloader._log('ERROR: Requested format is not available')
        return 1

    with patch('core.downloader.os.path.exists', return_value=True), \
            patch('core.downloader.resolve_download_hints', return_value=DownloadHints(url='https://example.com')), \
            patch.object(downloader, '_build_command', return_value=['yt-dlp.exe']), \
            patch.object(downloader, '_run_process', side_effect=fail_download), \
            patch('core.downloader.cleanup_download_temp_directory') as cleanup:
        assert downloader.download('https://example.com') is False

    cleanup.assert_not_called()
    assert any('«Авто» или MKV' in call.args[0] for call in downloader.log_callback.call_args_list)


@pytest.mark.parametrize('container', ['mp4', 'webm'])
@pytest.mark.parametrize('quality', [None, 720, '', 'invalid', ' MAX '])
def test_invalid_quality_does_not_weaken_codec_constraints(container, quality):
    selector = ytdlp_format_selector_for_container(quality, container)
    assert 'height' not in selector
    assert selector == ytdlp_format_selector_for_container('max', container)


@pytest.mark.parametrize('label,value', [(label, value) for value, label in OUTPUT_CONTAINER_CHOICES])
def test_container_description_explains_selected_mode(label, value):
    dialog = SettingsDialog.__new__(SettingsDialog)
    dialog._container_values = {label: value}
    dialog.container_description = Mock()
    dialog._on_container_changed(label)
    text = dialog.container_description.configure.call_args.kwargs['text']
    assert OUTPUT_CONTAINER_DESCRIPTIONS[value] in text
    assert 'Без перекодирования' in text


def test_unknown_container_label_uses_auto_description():
    dialog = SettingsDialog.__new__(SettingsDialog)
    dialog._container_values = {}
    dialog.container_description = Mock()
    dialog._on_container_changed('obsolete')
    text = dialog.container_description.configure.call_args.kwargs['text']
    assert OUTPUT_CONTAINER_DESCRIPTIONS['auto'] in text


@pytest.mark.parametrize('saved,expected', [('mp4', 'mp4'), ('webm', 'webm'),
                                         ('mkv', 'mkv'), ('auto', 'auto'), ([], 'auto')])
def test_dialog_restores_container_without_saving(monkeypatch, saved, expected):
    import ui.components.settings_dialog as module

    def variable(value):
        var = Mock()
        var.get.return_value = value
        return var

    for name in ('CTkFrame', 'CTkScrollableFrame', 'CTkLabel', 'CTkEntry',
                 'CTkButton', 'CTkSegmentedButton', 'CTkOptionMenu', 'CTkCheckBox', 'CTkFont'):
        monkeypatch.setattr(module.ctk, name, Mock())
    monkeypatch.setattr(module.ctk, 'StringVar', variable)
    monkeypatch.setattr(module.ctk, 'BooleanVar', variable)
    monkeypatch.setattr(module, 'create_tooltip', Mock())
    monkeypatch.setattr(module.IconManager, 'get', Mock(return_value=''))
    dialog = SettingsDialog.__new__(SettingsDialog)
    dialog.config_manager = Mock()
    dialog.config_manager.get.side_effect = lambda key, default=None: {
        'OUTPUT_CONTAINER': saved, 'VIDEO_QUALITY': '720',
    }.get(key, default)
    dialog.cookies_path = ''
    dialog.sponsorblock_categories = set()
    dialog.clipboard_monitoring = False
    dialog.destroy = Mock()

    dialog._create_ui()

    assert dialog.container_var.get() == dict(OUTPUT_CONTAINER_CHOICES)[expected]
    assert dialog.quality_var.get() == '720p'
    dialog.config_manager.save.assert_not_called()
    dialog.config_manager.set.assert_not_called()
    option = module.ctk.CTkSegmentedButton.call_args.kwargs
    assert option['command'] == dialog._on_container_changed


def test_container_round_trip_on_disk(tmp_path):
    config = ConfigManager.__new__(ConfigManager)
    config.config_path = str(tmp_path/'config.json')
    config.bkp_path = str(tmp_path/'config.bkp')
    config.config = dict(DEFAULT_CONFIG, OUTPUT_CONTAINER='mkv', VIDEO_QUALITY='720')
    config.save()
    restored = config._load_or_create()
    assert restored['OUTPUT_CONTAINER'] == 'mkv'
    assert restored['VIDEO_QUALITY'] == '720'
