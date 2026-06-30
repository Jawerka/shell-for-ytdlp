# AGENTS.md — UI-for-ytdlp

Руководство для AI-агентов и разработчиков, работающих с этим репозиторием.

## Назначение

**UI-for-ytdlp** — Windows desktop GUI для [yt-dlp](https://github.com/yt-dlp/yt-dlp) на CustomTkinter. Главный приоритет — **надёжность пайплайна загрузки**. Вторичные функции (трей, звуки, настройки) не должны ломать основной поток.

## Быстрый старт

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Отладка:

```bash
set UI_FOR_YTDLP_DEBUG=1
python main.py
```

При первом запуске `yt-dlp.exe` и `ffmpeg` скачиваются в `utilities/` (не коммитить).

## Архитектура

```
main.py
  └── ui/main_window.py      # GUI, оркестрация потоков
        ├── core/pipeline.py # Проверки URL, папки, yt-dlp (без UI)
        ├── core/downloader.py   # subprocess → yt-dlp
        ├── core/updater.py      # обновление бинарников
        ├── core/config.py       # utilities/config.json
        └── ui/components/*      # виджеты
```

Бинарники и пользовательские данные живут в `utilities/`:
- `yt-dlp.exe`, `ffmpeg.exe`, `deno.exe` — скачиваются автоматически
- `config.json`, `config.bkp`, `*cookies*.txt` — **не коммитить**

## Главный пайплайн

```
URL / clipboard / tray
  → validate_url_for_download()     [core/pipeline.py]
  → _start_download()               [ui/main_window.py]
  → Thread: _update_and_download()
      → _update_utilities()         (deno, yt-dlp, ffmpeg — ошибки = warning)
      → check_ytdlp_ready()         (critical если нет yt-dlp)
      → _retry_ytdlp_download()       (одна повторная попытка)
      → YouTubeDownloader.download()
  → finally: _on_download_complete()  (всегда сбрасывает UI)
```

### Critical vs non-critical

| Сбой | Поведение |
|------|-----------|
| Нет `yt-dlp.exe` после retry | Стоп, ошибка в лог |
| Нет папки загрузки (PermissionError) | Стоп |
| Отмена пользователем (Esc) | Стоп, UI восстанавливается |
| Сбой обновления deno | Warning, загрузка продолжается |
| Сбой проверки версии ffmpeg | Warning, загрузка продолжается |
| Таймаут pre-check URL (YouTube и др.) | Warning, yt-dlp попробует |
| Нет cookies.txt | Загрузка без cookies |

## Тесты

```bash
# Unit-тесты (без сети и yt-dlp)
pytest tests/ -m "not integration"

# С покрытием core (порог 70%)
pytest tests/ -m "not integration" --cov=core --cov-fail-under=70

# Integration (нужен utilities/yt-dlp.exe)
pytest tests/ -m integration
```

**Что мокать:** `subprocess.Popen`, `urlopen`, `urlretrieve`, `pyperclip`, Tk/CTk виджеты.

**Паттерн для MainWindow:** `MainWindow.__new__(MainWindow)` + mock атрибутов (см. `tests/unit/test_tray_minimize.py`).

## Сборка

```bash
python build.py
# или
python -m PyInstaller --clean --noconfirm UI-for-ytdlp.spec
```

CI: `.github/workflows/build-ui-for-ytdlp.yml` — тесты + PyInstaller на Windows.

## Правила для агента

1. **Минимальный diff** — не рефакторить `main_window.py` без необходимости.
2. **Не коммитить** `utilities/*` (кроме `.gitkeep`), cookies, config, `venv/`, `build/`, `dist/`.
3. **UI-строки на русском** — сохранять язык существующих сообщений.
4. **Thread safety** — обновление UI только через `self.after(0, ...)`.
5. **subprocess** — `shell=False`, пути **без** ручных кавычек в списке аргументов.
6. **PyInstaller** — пути через `get_app_base_path()` / `sys._MEIPASS`, не hardcode.
7. Новую логику пайплайна добавлять в `core/pipeline.py` с unit-тестами.

## Частые ловушки

- `quote_path()` + `Popen(cmd, shell=False)` — кавычки попадают в аргумент буквально, ломая пути с пробелами.
- `_update_and_download` без `finally` — UI остаётся заблокированным при исключении.
- `NotificationManager()` создавал свой `ConfigManager` — передавать config явно при DI.
- `DEBUG`-print в `main.py` — только при `UI_FOR_YTDLP_DEBUG=1`.
- Backup конфига: `utilities/config.bkp` (не `config.json.bkp`).

## Структура тестов

```
tests/
  conftest.py          # sys.path, marker integration
  unit/
    test_pipeline.py           # core/pipeline.py
    test_downloader*.py        # downloader + subprocess
    test_main_window_download.py
    test_config.py, test_utils.py, ...
```

## Версия и лицензия

- Python 3.10+
- MIT License — см. `LICENSE`
- Версия приложения: README / git tags `v*`
