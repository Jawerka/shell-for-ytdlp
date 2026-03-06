# План внедрения функционала сворачивания в трей

## Описание задачи

Реализовать сворачивание приложения в системный трей (область уведомлений Windows) с контекстным меню для быстрого управления приложением.

---

## Требования к функционалу

### 1. Сворачивание в трей

При нажатии на кнопку сворачивания (или при закрытии окна) приложение должно не закрываться, а сворачиваться в системный трей.

### 2. Контекстное меню в трее (ПКМ)

При нажатии правой кнопкой мыши на иконку в трее должно отображаться меню:

```
┌─────────────────────────────────────────────────────┐
│ ● Перехват ссылок из буфера      [Вкл/Выкл]        │
│ ● Проигрывание звуков              [Вкл/Выкл]        │
├─────────────────────────────────────────────────────┤
│ 📋 Вставить ссылку и скачать                        │
├─────────────────────────────────────────────────────┤
│ ⚙ Настройки                                         │
│ ❌ Выход                                              │
└─────────────────────────────────────────────────────┘
```

### 3. Быстрые переключатели

- **Перехват ссылок из буфера** — включает/отключает `ClipboardMonitor`
- **Проигрывание звуков** — включает/отключает `SoundManager`

Состояние должно синхронизироваться с основными настройками приложения.

### 4. Действия меню

- **Вставить ссылку и скачать** — получить URL из буфера и начать загрузку
- **Настройки** — открыть диалог настроек (`SettingsDialog`)
- **Выход** — корректно закрыть приложение с очисткой ресурсов

---

## Анализ существующей архитектуры

### Точки интеграции

#### 1. MainWindow (`ui/main_window.py`)

**Существующие атрибуты:**
```python
self.config_manager = ConfigManager()
self.clipboard_monitor = ClipboardMonitor(...)
self.sound_manager = SoundManager(enabled=True)
```

**Существующие методы:**
- `_on_closing()` — обработка закрытия окна (строка ~816)
- `_initialize_clipboard_monitoring()` — инициализация мониторинга (строка ~133)
- `_on_clipboard_url_detected()` — callback при обнаружении URL
- `_start_download()` — начало загрузки
- `_open_settings()` — открытие настроек

**Что нужно изменить:**
- Модифицировать `_on_closing()` для сворачивания в трей вместо закрытия
- Добавить `TrayManager` как атрибут
- Добавить методы для callback из трея

#### 2. ConfigManager (`core/config.py`)

**Существующие ключи:**
```python
'CLIPBOARD_MONITORING': False,
'ENABLE_NOTIFICATIONS': True,  # Можно переиспользовать или создать новый
```

**Что нужно изменить:**
- Добавить `'ENABLE_SOUND_NOTIFICATIONS': True`
- Обновить `_merge_with_defaults()` для новых полей

#### 3. SoundManager (`core/sound_manager.py`)

**Существующие методы:**
- `set_enabled(enabled: bool)`
- `is_enabled() -> bool`
- `shutdown()`

**Изменения:** минимальные — только синхронизация с конфигом

#### 4. SettingsDialog (`ui/components/settings_dialog.py`)

**Существующие секции:**
1. Cookies.txt
2. SponsorBlock
3. Автозагрузка из буфера обмена

**Что нужно изменить:**
- Добавить секцию "Звуковые уведомления"
- Обновить signature `on_save_callback`

### Зависимости

**Текущие (requirements.txt):**
```
customtkinter>=5.2.0
pyperclip>=1.9.0
packaging>=24.0
Pillow>=10.0.0
darkdetect>=0.8.0
pygame>=2.5.0
plyer>=2.1.0
pyinstaller>=6.0.0
pytest>=7.0.0
```

**Новые:**
```
pystray>=0.19.0
```

---

## Детальный план интеграции

### Этап 1: Зависимости

**Файл**: `requirements.txt`

Добавить:
```text
# Системный трей
pystray>=0.19.0
```

**Файл**: `UI-for-ytdlp.spec`

Обновить `hiddenimports`:
```python
hiddenimports = [
    # ... существующие ...
    'pystray',
    'pystray._icon',
]
```

---

### Этап 2: TrayManager

**Файл**: `core/tray_manager.py` (новый)

**Ключевые аспекты:**

1. **Поток безопасности**: pystray работает в отдельном потоке, все callback'ы должны вызываться через `self.after(0, callback)` в главном потоке tkinter.

2. **Иконка**: Использовать существующий `icon.ico` (нужно проверить размер 256×256).

3. **Состояние переключателей**: Синхронизировать с `ConfigManager` при инициализации.

4. **Методы:**
   - `show()` — показать иконку
   - `hide()` — скрыть иконку
   - `is_visible()` — проверка видимости
   - `stop()` — очистка ресурсов

---

### Этап 3: Интеграция в MainWindow

**Файл**: `ui/main_window.py`

#### 3.1. Импорт (строка ~50)

```python
from core.tray_manager import TrayManager
```

#### 3.2. Создание TrayManager (после sound_manager, строка ~85)

```python
# Инициализация менеджера звуковых эффектов
self.sound_manager = SoundManager(enabled=True)

# Инициализация менеджера трея
self.tray_manager = None  # Будет создан после создания окна
```

#### 3.3. Модификация _on_closing (строка ~816)

**Текущий код:**
```python
def _on_closing(self) -> None:
    """Обработчик закрытия окна."""
    # Остановка мониторинга буфера обмена
    if self.clipboard_monitor.is_running():
        self.clipboard_monitor.stop()

    # Остановка звукового менеджера
    self.sound_manager.shutdown()

    # Сохранение конфигурации при закрытии
    self.config_manager.save()
    logger.debug("_on_closing: Конфигурация сохранена")

    if self.is_downloading:
        # ... диалог подтверждения ...
```

**Новый код:**
```python
def _on_closing(self) -> None:
    """Обработчик закрытия окна — сворачивание в трей."""
    # Скрыть окно вместо закрытия
    self.withdraw()
    
    # Создать и показать иконку в трее если ещё не создана
    if self.tray_manager is None:
        self.tray_manager = TrayManager(
            clipboard_monitor=self.clipboard_monitor,
            sound_manager=self.sound_manager,
            config_manager=self.config_manager,
            on_restore=self._restore_from_tray,
            on_paste_and_download=self._paste_and_download_from_tray,
            on_open_settings=self._open_settings_from_tray,
            on_exit=self._exit_application
        )
    
    if not self.tray_manager.is_visible():
        self.tray_manager.show()
    
    logger.debug("_on_closing: Окно свёрнуто в трей")
```

#### 3.4. Новые методы (после _on_closing)

```python
def _restore_from_tray(self) -> None:
    """Восстановить окно из трея (вызывается из главного потока)."""
    self.deiconify()
    self.focus_force()
    self.tray_manager.hide()

def _paste_and_download_from_tray(self) -> None:
    """Вставить URL из буфера и начать загрузку (из трея)."""
    from core.utils import get_clipboard_url
    
    def _download():
        url = get_clipboard_url()
        if url:
            self.url_input.set_url(url)
            self.log_viewer.info(f"📋 URL из буфера: {url[:80]}...")
            self._start_download()
        else:
            self.log_viewer.warning("📋 Буфер обмена не содержит URL")
    
    # Выполнить в главном потоке
    self.after(0, _download)

def _open_settings_from_tray(self) -> None:
    """Открыть настройки из трея."""
    def _open():
        self._open_settings()
        self._restore_from_tray()
    
    self.after(0, _open)

def _exit_application(self) -> None:
    """Полный выход из приложения."""
    logger.debug("_exit_application: Выход из приложения")
    
    # Остановить трей
    if self.tray_manager:
        self.tray_manager.stop()
    
    # Остановить мониторинг
    if self.clipboard_monitor.is_running():
        self.clipboard_monitor.stop()
    
    # Остановить звук
    self.sound_manager.shutdown()
    
    # Сохранить конфиг
    self.config_manager.save()
    
    # Закрыть окно
    self.destroy()
```

---

### Этап 4: Обновление SettingsDialog

**Файл**: `ui/components/settings_dialog.py`

#### 4.1. Добавить чекбокс звуков (после clipboard_section)

```python
# === Разделитель ===
separator3 = ctk.CTkFrame(content_frame, height=2, fg_color=COLOR_THEME["border"])
separator3.pack(fill="x", pady=Spacing.LG)

# === Секция 4: Звуковые уведомления ===
sound_section = ctk.CTkFrame(content_frame, fg_color="transparent")
sound_section.pack(fill="x", pady=(0, Spacing.LG))

sound_title = ctk.CTkLabel(
    sound_section,
    text="Звуковые уведомления",
    font=ctk.CTkFont(size=13, weight="bold"),
    text_color=COLOR_THEME["text_primary"],
    anchor="w"
)
sound_title.pack(fill="x", pady=(0, Spacing.SM))

sound_desc = ctk.CTkLabel(
    sound_section,
    text="Воспроизводить звуковые сигналы при событиях (начало/окончание загрузки)",
    font=ctk.CTkFont(size=12),
    text_color=COLOR_THEME["text_muted"],
    wraplength=560,
    justify="left",
    anchor="w"
)
sound_desc.pack(fill="x", pady=(0, Spacing.SM))

# Чекбокс включения звуков
self.sound_enabled_var = ctk.BooleanVar(
    value=self.config_manager.get('ENABLE_SOUND_NOTIFICATIONS', True)
)

sound_checkbox = ctk.CTkCheckBox(
    sound_section,
    text="Включить звуковые уведомления",
    variable=self.sound_enabled_var,
    width=20,
    height=20,
    checkbox_width=20,
    checkbox_height=20,
    font=ctk.CTkFont(size=12),
    text_color=COLOR_THEME["text_primary"],
    fg_color=COLOR_THEME["bg_card"],
    border_color=COLOR_THEME["text_muted"],
    hover_color=COLOR_THEME["primary"],
    corner_radius=4,
)
sound_checkbox.pack(side="left", pady=Spacing.SM)
```

#### 4.2. Обновить _save_and_close

**Текущий signature:**
```python
def _save_and_close(self) -> None:
    """Сохранить настройки и закрыть диалог."""
    cookies_path = self.cookies_entry.get().strip()
    selected_categories = [...]
    clipboard_monitoring = self.clipboard_monitor_var.get()
    
    if self.on_save_callback:
        self.on_save_callback(cookies_path, selected_categories, clipboard_monitoring)
```

**Новый signature:**
```python
def _save_and_close(self) -> None:
    """Сохранить настройки и закрыть диалог."""
    cookies_path = self.cookies_entry.get().strip()
    selected_categories = [...]
    clipboard_monitoring = self.clipboard_monitor_var.get()
    sound_enabled = self.sound_enabled_var.get()
    
    if self.on_save_callback:
        self.on_save_callback(
            cookies_path, 
            selected_categories, 
            clipboard_monitoring,
            sound_enabled
        )
```

---

### Этап 5: Обновление ConfigManager

**Файл**: `core/config.py`

#### 5.1. DEFAULT_CONFIG

```python
DEFAULT_CONFIG = {
    # ... существующие ...
    'CLIPBOARD_MONITORING': False,
    'ENABLE_SOUND_NOTIFICATIONS': True,  # НОВЫЙ ключ
    'LAST_DOWNLOADED_URL': '',
}
```

#### 5.2. _merge_with_defaults

```python
def _merge_with_defaults(self, config: dict) -> dict:
    """Объединить пользовательскую конфигурацию с настройками по умолчанию."""
    result = DEFAULT_CONFIG.copy()
    result.update(config)
    
    # ... существующий код ...
    
    # Добавление новых полей если их нет
    if 'QUESTION_BYPASS' not in result:
        result['QUESTION_BYPASS'] = False
    if 'ENABLE_NOTIFICATIONS' not in result:
        result['ENABLE_NOTIFICATIONS'] = True
    if 'ENABLE_SOUND_NOTIFICATIONS' not in result:
        result['ENABLE_SOUND_NOTIFICATIONS'] = True  # НОВОЕ
    
    return result
```

---

### Этап 6: Обновление SoundManager

**Файл**: `core/sound_manager.py`

#### 6.1. Синхронизация при инициализации

**Текущий __init__:**
```python
def __init__(self, enabled: bool = True):
    self.enabled = enabled
    # ...
```

**Новый __init__:**
```python
def __init__(self, enabled: bool = True, config_manager=None):
    """
    Инициализировать менеджер звуковых эффектов.

    Args:
        enabled: Включены ли звуковые эффекты (по умолчанию True)
        config_manager: Менеджер конфигурации для синхронизации (опционально)
    """
    # Если передан config_manager, используем настройку из конфига
    if config_manager:
        self.enabled = config_manager.get('ENABLE_SOUND_NOTIFICATIONS', enabled)
    else:
        self.enabled = enabled
    
    # ... остальной код ...
```

---

### Этап 7: Сборка

**Файл**: `UI-for-ytdlp.spec`

#### 7.1. hiddenimports

```python
hiddenimports = [
    # ... существующие ...
    'pystray',
    'pystray._icon',
    'core.tray_manager',
]
```

---

### Этап 8: Тестирование

#### Чек-лист тестирования

| № | Тест | Ожидаемый результат |
|---|------|---------------------|
| 1 | Закрытие окна (крестик) | Окно скрывается, иконка в трее |
| 2 | ПКМ по иконке | Контекстное меню отображается |
| 3 | Переключатель "Перехват ссылок" | Состояние меняется, сохраняется в конфиг |
| 4 | Переключатель "Проигрывание звуков" | Состояние меняется, сохраняется в конфиг |
| 5 | "Вставить ссылку и скачать" | URL из буфера вставляется, начинается загрузка |
| 6 | "Настройки" | Открывается SettingsDialog |
| 7 | "Выход" | Приложение закрывается полностью |
| 8 | Двойной клик по иконке | Окно восстанавливается |
| 9 | Синхронизация настроек | Изменения в SettingsDialog отражаются в трее |
| 10 | Долгая работа (>1 час) | Нет утечек памяти |

---

## Потенциальные проблемы и решения

| Проблема | Решение |
|----------|---------|
| `pystray` не работает в PyInstaller | Добавить `hiddenimports`, проверить версию |
| Иконка не отображается | Проверить формат ICO (256×256, 32-bit) |
| Callback из трея не работает | Использовать `self.after(0, callback)` |
| Окно не восстанавливается | Проверить `deiconify()` + `focus_force()` |
| Утечка памяти | Вызывать `tray_manager.stop()` при выходе |
| Конфликт с антивирусом | Добавить подпись в exe, тестировать на чистых системах |

---

## Структура файлов (итог)

```.
d:\Documents\Projects\python\UI-for-ytdlp\
├── core/
│   ├── tray_manager.py          # НОВЫЙ: Менеджер трея
│   ├── clipboard_monitor.py     # Без изменений
│   ├── sound_manager.py         # Обновить __init__
│   └── config.py                # Добавить ENABLE_SOUND_NOTIFICATIONS
├── ui/
│   ├── main_window.py           # Интеграция TrayManager
│   └── components/
│       └── settings_dialog.py   # Секция звуков
├── icon.ico                     # Для окна и трея
├── requirements.txt             # Добавить pystray
└── UI-for-ytdlp.spec            # Добавить hiddenimports
```

---

## Оценка времени

| Этап | Задача | Время (часы) |
|------|--------|--------------|
| 1 | Зависимости + spec | 0.5 |
| 2 | TrayManager (базовый) | 2.5 |
| 3 | TrayManager (меню + callback) | 1.5 |
| 4 | Интеграция в MainWindow | 2.0 |
| 5 | SettingsDialog | 1.0 |
| 6 | ConfigManager + SoundManager | 0.5 |
| 7 | Сборка + отладка | 1.5 |
| 8 | Тестирование | 2.0 |
| **Итого** | | **11.5 часов** |

---

## Приоритеты реализации

### Критичные (MVP)
1. Базовый `TrayManager` с иконкой
2. Сворачивание окна в трей
3. Выход из приложения через трей

### Важные
4. Переключатель мониторинга буфера
5. Переключатель звуков
6. "Вставить и скачать"

### Дополнительные
7. Двойной клик для восстановления
8. Синхронизация состояний
9. Секция звуков в SettingsDialog

---

## Следующие шаги

1. ✅ Утвердить план (прочитан)
2. ✅ Этап 1: Добавление зависимости `pystray`
3. ✅ Этап 2: Создать `core/tray_manager.py`
4. ✅ Этап 3: Интегрировать в `MainWindow`
5. ✅ Этап 4: Обновить `SettingsDialog`
6. ✅ Этап 5: Обновить конфигурацию
7. ✅ Этап 6: Обновить `SoundManager`
8. ✅ Этап 7: Обновить `UI-for-ytdlp.spec`
9. ✅ Этап 8: Тестирование
10. ✅ Закоммитить изменения

---

## Статус реализации

**Все этапы завершены!** ✅

Реализованный функционал:
- ✅ Сворачивание в трей при закрытии окна
- ✅ Иконка в трее с контекстным меню
- ✅ Переключатель мониторинга буфера обмена
- ✅ Переключатель звуковых уведомлений
- ✅ Быстрая команда "Вставить и скачать"
- ✅ Открытие настроек из трея
- ✅ Выход из приложения через трей
- ✅ Двойной клик для восстановления окна
- ✅ Синхронизация состояний с конфигом
- ✅ Секция звуков в SettingsDialog

Коммит: `3571eae` — "feat: сворачивание приложения в системный трей"

```python
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
from typing import Optional, Callable
from dataclasses import dataclass

try:
    import pystray
    from pystray import Icon, MenuItem, Menu
    PYSTRAY_AVAILABLE = True
except ImportError:
    PYSTRAY_AVAILABLE = False

from core.clipboard_monitor import ClipboardMonitor
from core.sound_manager import SoundManager
from core.config import ConfigManager

logger = logging.getLogger('UI-for-ytdlp.tray_manager')


@dataclass
class TrayState:
    """Состояние элементов трея."""
    clipboard_monitoring: bool = False
    sound_enabled: bool = True


class TrayManager:
    """
    Менеджер системного трея приложения.

    Создаёт иконку в трее с контекстным меню для быстрого управления.
    """

    def __init__(
        self,
        clipboard_monitor: ClipboardMonitor,
        sound_manager: SoundManager,
        config_manager: ConfigManager,
        on_paste_and_download: Callable[[], None],
        on_open_settings: Callable[[], None],
        on_exit: Callable[[], None]
    ):
        """
        Инициализировать менеджер трея.

        Args:
            clipboard_monitor: Менеджер буфера обмена
            sound_manager: Менеджер звуков
            config_manager: Менеджер конфигурации
            on_paste_and_download: Callback для вставки и загрузки
            on_open_settings: Callback для открытия настроек
            on_exit: Callback для выхода из приложения
        """
        self.clipboard_monitor = clipboard_monitor
        self.sound_manager = sound_manager
        self.config_manager = config_manager
        self.on_paste_and_download = on_paste_and_download
        self.on_open_settings = on_open_settings
        self.on_exit = on_exit

        self._icon: Optional[Icon] = None
        self._state = TrayState()

    def create_icon(self) -> Optional[Icon]:
        """Создать иконку трея."""
        pass

    def _build_menu(self) -> Menu:
        """Построить контекстное меню."""
        pass

    def _update_menu_state(self) -> None:
        """Обновить состояние пунктов меню."""
        pass

    def _toggle_clipboard_monitoring(self) -> None:
        """Переключить мониторинг буфера обмена."""
        pass

    def _toggle_sound_enabled(self) -> None:
        """Переключить звуковые уведомления."""
        pass

    def show(self) -> None:
        """Показать иконку в трее."""
        pass

    def hide(self) -> None:
        """Скрыть иконку из трея."""
        pass

    def run_detached(self) -> None:
        """Запустить иконку в отдельном потоке."""
        pass

    def stop(self) -> None:
        """Остановить иконку трея."""
        pass
```

---

### Этап 3: Интеграция в MainWindow

**Файл**: `ui/main_window.py`

#### 3.1. Добавить импорт

```python
from core.tray_manager import TrayManager
```

#### 3.2. Создать атрибут tray_manager

В `__init__` после создания `clipboard_monitor` и `sound_manager`:

```python
# Создание менеджера трея
self.tray_manager = TrayManager(
    clipboard_monitor=self.clipboard_monitor,
    sound_manager=self.sound_manager,
    config_manager=self.config_manager,
    on_paste_and_download=self._paste_and_download_from_tray,
    on_open_settings=self._open_settings_from_tray,
    on_exit=self._on_tray_exit
)
```

#### 3.3. Реализовать callback методы

```python
def _paste_and_download_from_tray(self) -> None:
    """Вставить URL из буфера и начать загрузку (из трея)."""
    pass

def _open_settings_from_tray(self) -> None:
    """Открыть настройки из трея."""
    pass

def _on_tray_exit(self) -> None:
    """Обработать выход из трея."""
    pass
```

#### 3.4. Обработка сворачивания

Переопределить обработчик `WM_DELETE_WINDOW`:

```python
def _on_closing(self) -> None:
    """Обработать закрытие окна (сворачивание в трей)."""
    # Скрыть окно
    self.withdraw()
    # Показать иконку в трее если ещё не показана
    if not self.tray_manager.is_visible():
        self.tray_manager.show()
```

#### 3.5. Восстановление из трея

Двойной клик по иконке трея должен разворачивать окно:

```python
def _restore_from_tray(self) -> None:
    """Восстановить окно из трея."""
    self.after(0, lambda: self._restore_window())

def _restore_window(self) -> None:
    """Восстановить окно (внутренний метод)."""
    self.deiconify()
    self.focus_force()
```

---

### Этап 4: Обновление SettingsDialog

**Файл**: `ui/components/settings_dialog.py`

#### 4.1. Добавить секцию звуковых уведомлений

После секции "Мониторинг буфера обмена":

```python
# === Разделитель ===
separator3 = ctk.CTkFrame(content_frame, height=2, fg_color=COLOR_THEME["border"])
separator3.pack(fill="x", pady=Spacing.LG)

# === Секция 4: Звуковые уведомления ===
sound_section = ctk.CTkFrame(content_frame, fg_color="transparent")
sound_section.pack(fill="x", pady=(0, Spacing.LG))
```

#### 4.2. Обновить on_save

Добавить параметр `sound_enabled` в callback.

---

### Этап 5: Обновление ConfigManager

**Файл**: `core/config.py`

#### 5.1. Добавить ключ конфигурации

В `DEFAULT_CONFIG`:

```python
# Настройки звуковых уведомлений
'ENABLE_SOUND_NOTIFICATIONS': True,
```

---

### Этап 6: Обновление SoundManager

**Файл**: `core/sound_manager.py`

#### 6.1. Добавить метод для чтения состояния из конфига

Синхронизация при запуске приложения.

---

### Этап 7: Сборка и иконка

**Файл**: `build.py` или `UI-for-ytdlp.spec`

#### 7.1. Добавить иконку для трея

Создать файл `icon_tray.ico` (можно использовать существующий `icon.ico`).

#### 7.2. Обновить spec-файл

Добавить иконку в данные приложения.

---

### Этап 8: Тестирование

#### Чек-лист тестирования

- [ ] Иконка появляется в трее при сворачивании
- [ ] ПКМ по иконке показывает контекстное меню
- [ ] Переключатель "Перехват ссылок" работает
- [ ] Переключатель "Проигрывание звуков" работает
- [ ] "Вставить ссылку и скачать" работает
- [ ] "Настройки" открывает диалог
- [ ] "Выход" корректно закрывает приложение
- [ ] Двойной клик по иконке восстанавливает окно
- [ ] Состояния синхронизируются между треем и настройками
- [ ] При закрытии окна данные не теряются

---

## Структура файлов (итог)

```
d:\Documents\Projects\python\UI-for-ytdlp\
├── core/
│   ├── tray_manager.py          # НОВЫЙ: Менеджер трея
│   ├── clipboard_monitor.py     # Существующий
│   ├── sound_manager.py         # Обновить
│   └── config.py                # Обновить
├── ui/
│   ├── main_window.py           # Обновить (интеграция TrayManager)
│   └── components/
│       └── settings_dialog.py   # Обновить (секция звуков)
├── icon.ico                     # Использовать для трея
└── requirements.txt             # Добавить pystray
```

---

## Лучшие практики (PEP)

1. **Документирование**: Все новые методы и классы должны иметь docstring на русском языке.
2. **Типизация**: Использовать type hints для всех параметров и возвращаемых значений.
3. **Логирование**: Логировать все важные события (создание, уничтожение, переключения).
4. **Потокобезопасность**: Callback из трея должны выполняться в главном потоке (через `after()`).
5. **Очистка ресурсов**: При выходе корректно останавливать `TrayManager`, `ClipboardMonitor`, `SoundManager`.

---

## Потенциальные проблемы и решения

| Проблема | Решение |
|----------|---------|
| `pystray` не работает в PyInstaller | Добавить hidden imports в spec-файл |
| Иконка не отображается в трее | Проверить формат ICO (должен быть 256×256) |
| Callback из трея не работает | Использовать `self.after(0, callback)` для главного потока |
| Утечка памяти при долгой работе | Следить за очисткой `_icon.stop()` при выходе |

---

## Приоритеты реализации

1. **Высокий**: Базовая функциональность (сворачивание, контекстное меню, выход)
2. **Средний**: Переключатели (буфер, звуки)
3. **Низкий**: Двойной клик для восстановления, синхронизация состояний

---

## Оценка времени

| Этап | Время (часы) |
|------|--------------|
| 1. Зависимости | 0.5 |
| 2. TrayManager | 3.0 |
| 3. Интеграция | 2.0 |
| 4. SettingsDialog | 1.0 |
| 5-6. Config/Sound | 0.5 |
| 7. Сборка | 1.0 |
| 8. Тестирование | 1.5 |
| **Итого** | **9.5 часов** |

---

## Следующие шаги

1. Утвердить план
2. Начать с Этапа 1 (добавление зависимости)
3. Последовательно реализовывать этапы
4. После каждого этапа запускать приложение для проверки
5. По завершении — полное тестирование и коммит
