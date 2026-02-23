# TODO-final — План развития UI-for-ytdlp

**Дата создания:** 2026-02-23  
**Версия приложения:** 2.0  
**Статус:** UI модуль существует и работает ✓  
**Основано на:** TODO.md, TODO-2.md, TODO-3.md

---

## 📊 Актуальное состояние проекта

### ✅ Что реализовано и работает

#### Core модули (`core/`)
| Модуль | Статус | Описание |
|--------|--------|----------|
| `config.py` | ✅ Готов | ConfigManager с backup, merge с defaults |
| `logger.py` | ✅ Готов | GUILogger с 5 уровнями, цветной вывод |
| `downloader.py` | ✅ Готов | YouTubeDownloader с subprocess, SponsorBlock |
| `updater.py` | ✅ Готов | update_loop, проверка размеров файлов |
| `utils.py` | ✅ Готов | URL валидация, clipboard, cookies.txt |
| `theme.py` | ✅ Готов | COLOR_THEME, Spacing, дизайн-система |
| `icons.py` | ✅ Готов | Unicode-иконки, IconManager с кэшем |

#### UI модули (`ui/`)
| Компонент | Статус | Возможности |
|-----------|--------|-------------|
| `MainWindow` | ✅ Готов | 900x700, тёмная тема, все функции |
| `UrlInput` | ✅ Готов | Поле ввода + кнопка paste (Ctrl+V) |
| `LogViewer` | ✅ Готов | Цветные логи, кнопка очистки |
| `ProgressBarWithText` | ✅ Готов | Прогресс + процент + info |
| `SponsorBlockDialog` | ✅ Готов | 8 категорий, выбор/сохранение |

### 🔴 Критические проблемы (требуют исправления)

| Проблема | Приоритет | Файл | Описание |
|----------|-----------|------|----------|
| **Пробелы в путях** | 🔴 Критический | `downloader.py` | Нет экранирования путей с пробелами |
| **Отмена загрузки** | 🔴 Критический | `main_window.py` | Terminate процесса некорректный |
| **Отсутствие таймаутов** | 🟡 Высокий | `utils.py`, `main_window.py` | `urlopen` может зависнуть навсегда |

### ⚠️ Технические долги

1. **MainWindow монолитный** — смешана логика и UI (~500 строк)
2. **Нет тестов** — покрытие тестами = 0%
3. **Жёстко закодированные пути** — частично используются прямые пути
4. **Unicode-иконки** — могут отображаться некорректно на старых системах
5. **Неиспользуемые ресурсы** — PNG файлы в `resources/icons/` не используются

---

## 🎯 Этапы разработки

### Этап 1: Критические исправления (Приоритет: Макс)

#### 1.1 Исправление пробелов в путях
```python
# Проблема в downloader.py _build_command()
# Решение: использовать shlex.quote() для всех путей
```
- [ ] Использовать `shlex.quote()` для всех путей в `downloader.py`
- [ ] Тестирование с путями содержащими пробелы и спецсимволы
- [ ] Проверка работы на Windows с путями типа `C:\Users\User Name\Downloads`

#### 1.2 Корректная отмена загрузки
```python
# Проблема: terminate() может не убить yt-dlp
# Решение: заменить на kill() для гарантированной остановки
```
- [ ] Заменить `terminate()` на `kill()` в `downloader.py`
- [ ] Добавить обработку zombie-процессов
- [ ] Проверять что процесс действительно завершился

#### 1.3 Таймауты для сетевых операций
- [ ] Добавить таймауты во все `urlopen` вызовы в `utils.py`
- [ ] Добавить таймауты в `main_window.py` при проверке URL
- [ ] Обработка `socket.timeout` отдельно от других ошибок

#### 1.4 Очистка неиспользуемых файлов
- [ ] Удалить `resources/icons/*.png` (clear.png, download.png, folder.png, paste.png)
- [ ] Проверить что `resources/` не содержит неиспользуемых файлов

---

### Этап 2: Функциональные улучшения (Приоритет: Высокий)

#### 2.1 Выбор формата и качества ⭐ ВАЖНО
```
Новый диалог: ui/components/format_dialog.py

┌─────────────────────────────────────┐
│  Выбор формата и качества           │
├─────────────────────────────────────┤
│  Формат:                            │
│  ○ MP4 (видео + аудио)             │
│  ○ WebM (видео + аудио)            │
│  ● MP3 (только аудио)              │
│  ○ M4A (только аудио)              │
├─────────────────────────────────────┤
│  Качество видео:                    │
│  ○ 4K (2160p)                      │
│  ○ 1080p                           │
│  ● 720p                            │
│  ○ 480p                            │
│  ○ Аудио только                    │
├─────────────────────────────────────┤
│  [Отмена]        [Сохранить]       │
└─────────────────────────────────────┘
```
- [ ] Создать `FormatDialog` компонент (`ui/components/format_dialog.py`)
- [ ] Добавить в `config.py`: `DEFAULT_FORMAT`, `DEFAULT_QUALITY`
- [ ] Модифицировать `downloader.py` для поддержки опций yt-dlp:
  - `-f 'bestvideo[height<=1080]+bestaudio/best'`
  - `--extract-audio --audio-format mp3`
  - `--merge-output-format mp4`

#### 2.2 Улучшенный прогресс-бар
```
Текущий:    [████████████████████░░░░] 65%
                    0%

Целевой:    Загрузка: 65% of 150 MiB
            [████████████████████░░░░]
            Скорость: 2.5 MB/s | Осталось: 00:42
```
- [ ] Добавить парсинг скорости из вывода yt-dlp (regex)
- [ ] Добавить парсинг ETA (оставшееся время)
- [ ] Добавить индикатор текущего файла (для плейлистов)

**Паттерны для парсинга:**
```python
speed_pattern = r'at\s+(\d+\.?\d*)\s*(KiB|MiB|GiB)/s'
eta_pattern = r'ETA\s+(\d+:\d+)'
playlist_pattern = r'Downloading item (\d+) of (\d+)'
```

#### 2.3 История загрузок
```python
# utilities/download_history.json
{
  "history": [
    {
      "url": "https://...",
      "title": "Video Title",
      "date": "2026-02-23T14:30:00",
      "status": "completed",
      "path": "C:/.../Downloads/"
    }
  ]
}
```
- [ ] Создать `HistoryManager` в `core/history.py`
- [ ] Добавить меню "История" в UI
- [ ] Возможность повторить загрузку из истории
- [ ] Очистка истории (вся/выборочно)

#### 2.4 Системные уведомления
- [ ] Добавить зависимость `plyer` или `win10toast` в `requirements.txt`
- [ ] Уведомление о завершении загрузки
- [ ] Уведомление об ошибках
- [ ] Настройка в config: `ENABLE_NOTIFICATIONS`

---

### Этап 3: UX улучшения (Приоритет: Средний)

#### 3.1 Горячие клавиши
| Комбинация | Действие | Файл |
|------------|----------|------|
| `Ctrl+V` | Вставить URL | ✅ Уже работает |
| `Ctrl+Enter` | Начать загрузку | `main_window.py` |
| `Ctrl+O` | Выбрать папку | `main_window.py` |
| `Ctrl+L` | Очистить логи | `log_viewer.py` |
| `Ctrl+S` | Настройки SponsorBlock | `main_window.py` |
| `Ctrl+F` | Формат/качество | `main_window.py` |
| `Esc` | Отмена загрузки | `main_window.py` |

```python
# Реализация в main_window.py
def _setup_hotkeys(self):
    self.bind('<Control-Return>', lambda e: self._start_download())
    self.bind('<Control-o>', lambda e: self._select_folder())
    self.bind('<Escape>', lambda e: self._cancel_download())
```

#### 3.2 Улучшение логгера
- [ ] **Фильтрация логов**: Кнопки фильтрации по уровням (Info ✅/Success ✅/Warning ⚠/Error ✕)
- [ ] **Экспорт логов**: Сохранение логов в файл (Ctrl+S в log viewer)
- [ ] **Автоскролл**: Опция включения/отключения автоскролла
- [ ] **Счётчики**: Отображение количества сообщений по уровням

#### 3.3 Drag & Drop
- [ ] Поддержка drag & drop URL в окно
- [ ] Использование `tkinterdnd2` или встроенных событий Windows

#### 3.4 Улучшение SponsorBlock
- [ ] Диалог с описанием категорий (что означает каждая)
- [ ] Возможность выбора нескольких категорий
- [ ] Сохранение выбора в конфиг

---

### Этап 4: Архитектурные улучшения (Приоритет: Средний)

#### 4.1 Рефакторинг MainWindow
**Текущее состояние:** ~500 строк, смешана логика и UI

**Целевая структура:**
```
ui/
├── main_window.py          # UI только (~250 строк)
├── controllers/
│   ├── __init__.py
│   ├── download_controller.py   # Логика загрузки
│   └── settings_controller.py   # Логика настроек
└── services/
    ├── __init__.py
    └── download_service.py      # Обёртка над downloader
```

**Пример контроллера:**
```python
# ui/controllers/download_controller.py
class DownloadController:
    def __init__(self, config, logger, progress_callback):
        self.config = config
        self.logger = logger
        self.progress = progress_callback
        self._downloader = None
        self._is_downloading = False

    def start(self, url: str) -> bool:
        ...

    def cancel(self) -> None:
        ...

    @property
    def is_downloading(self) -> bool:
        ...
```

#### 4.2 Событийная модель (Observer)
```python
# core/events.py
class EventBus:
    def subscribe(self, event: str, callback: Callable):
        ...

    def emit(self, event: str, data: Any = None):
        ...

# Использование
event_bus = EventBus()
event_bus.subscribe('download.complete', on_download_complete)
event_bus.emit('download.complete', {'url': url, 'success': True})
```

#### 4.3 Валидация конфигурации
- [ ] Использовать `pydantic` для валидации схемы конфигурации
- [ ] Система миграций при изменении схемы
- [ ] Автоматическое восстановление при повреждении

#### 4.4 Асинхронность (asyncio) — на будущее
```python
# Вместо threading.Thread
import asyncio

async def download_async(self, url: str):
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT
    )
    ...
```

---

### Этап 5: Тестирование (Приоритет: Высокий)

#### 5.1 Структура тестов
```
tests/
├── __init__.py
├── conftest.py               # Фикстуры pytest
├── unit/
│   ├── test_config.py
│   ├── test_utils.py
│   ├── test_theme.py
│   └── test_logger.py
├── integration/
│   ├── test_downloader.py
│   └── test_updater.py
└── ui/
    └── test_components.py
```

#### 5.2 Unit-тесты (приоритетные)
```python
# tests/unit/test_utils.py
class TestUrlValidation:
    def test_valid_youtube_url(self):
        assert is_valid_url('https://youtube.com/watch?v=abc123')

    def test_invalid_no_protocol(self):
        assert not is_valid_url('youtube.com/watch')

    def test_empty_string(self):
        assert not is_valid_url('')

# tests/unit/test_config.py
class TestConfigManager:
    def test_config_manager_load(self):
        ...

    def test_config_manager_merge_defaults(self):
        ...
```

#### 5.3 Интеграционные тесты
- [ ] Тест загрузки тестового видео
- [ ] Тест обновления утилит
- [ ] Тест диалога SponsorBlock

#### 5.4 CI/CD
```yaml
# .github/workflows/tests.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-cov
      - run: pytest --cov=core --cov=ui
```

---

### Этап 6: Дополнительные возможности (Приоритет: Низкий)

#### 6.1 Поддержка плейлистов и каналов
- [ ] Выбор диапазона видео из плейлиста
- [ ] Пропуск уже загруженных видео
- [ ] Загрузка целых каналов
- [ ] Фильтрация по дате
- [ ] Ограничение количества видео

#### 6.2 Интеграции
- [ ] **Cookies из браузера**: Автоматическое извлечение cookies (browser-cookie3)
- [ ] **Поддержка Chrome, Firefox, Edge**

#### 6.3 Производительность
- [ ] Кэширование информации о видео
- [ ] Параллельная загрузка фрагментов
- [ ] Уменьшение потребления памяти

---

## 📈 Метрики и цели

| Метрика | Текущее | Цель | Приоритет |
|---------|---------|------|-----------|
| Размер exe | ~25 MB | <20 MB | Низкий |
| Время запуска | ~2 сек | <1 сек | Средний |
| Потребление памяти | ~100 MB | <80 MB | Низкий |
| Покрытие тестами | 0% | >70% | Высокий |
| Количество багов | 3 | 0 | Макс |

---

## 🗓️ План разработки по спринтам

### Спринт 1 (1 неделя) — Критические баги
1. Исправление пробелов в путях (`downloader.py`)
2. Корректная отмена загрузки (`kill()` вместо `terminate()`)
3. Таймауты для сетевых операций (`utils.py`, `main_window.py`)
4. Очистка неиспользуемых PNG файлов

### Спринт 2 (1 неделя) — Функциональность
1. Диалог выбора формата и качества (`format_dialog.py`)
2. Улучшенный прогресс-бар (скорость, ETA)
3. Горячие клавиши (Ctrl+Enter, Ctrl+O, Ctrl+L, Ctrl+S, Esc)

### Спринт 3 (1 неделя) — История и уведомления
1. История загрузок (`HistoryManager`, UI диалог)
2. Системные уведомления (`plyer`/`win10toast`)
3. Экспорт логов в файл

### Спринт 4 (1 неделя) — Улучшение UI
1. Фильтрация логов по уровням
2. Автоскролл логов (toggle)
3. Drag & Drop URL

### Спринт 5 (2 недели) — Архитектура и тесты
1. Рефакторинг MainWindow (разделение логики/UI)
2. Создание контроллеров (`download_controller.py`)
3. Событийная модель (`EventBus`)
4. Unit-тесты для core модулей

### Спринт 6 (1 неделя) — Документация и полировка
1. Обновление README.md (скриншоты, описание функций)
2. Docstring для публичных методов
3. Changelog (CHANGELOG.md)

---

## 📋 Чеклист релиза v2.1

- [ ] Все критические баги исправлены (пробелы, отмена, таймауты)
- [ ] Выбор формата и качества реализован
- [ ] История загрузок работает
- [ ] Покрытие тестами >50%
- [ ] Горячие клавиши работают
- [ ] Документация обновлена
- [ ] Сборка проходит без ошибок
- [ ] Протестировано на Windows 10/11

---

## 📝 Технические заметки

### Проблемы и решения

| Проблема | Решение | Файлы |
|----------|---------|-------|
| Пробелы в путях | `shlex.quote()` для всех путей | `downloader.py` |
| Отмена загрузки | `kill()` вместо `terminate()` | `downloader.py`, `main_window.py` |
| Зависание urlopen | Таймауты 10 сек везде | `utils.py`, `main_window.py` |
| Монолитный UI | Вынести логику в контроллеры | `main_window.py` → `controllers/` |

### Будущие исследования
1. **Tauri/Electron** — переход на веб-технологии для кроссплатформенности
2. **Asyncio** — переход на асинхронную модель для улучшения отзывчивости
3. **SQLite** — использование SQLite для хранения истории и настроек
4. **pydantic** — валидация конфигурации и миграции

---

## 🔄 История изменений документа

| Версия | Дата | Изменения |
|--------|------|-----------|
| 1.0 | 2026-02-23 | Initial — объединение TODO.md, TODO-2.md, TODO-3.md |

---

*Документ является основным планом развития проекта. Все изменения вносятся по мере выполнения задач.*
