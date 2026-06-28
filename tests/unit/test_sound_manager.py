# -*- coding: utf-8 -*-
"""
Тесты для модуля sound_manager.py.

Проверяют:
- Инициализацию менеджера
- Воспроизведение звуков
- Обработку ошибок
- Включение/отключение
"""

import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock

# Добавляем корень проекта в path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.sound_manager import (
    SoundManager,
    get_sound_manager,
    play_start_sound,
    play_end_sound,
    play_error_sound
)


class TestSoundManagerInit:
    """Тесты инициализации SoundManager."""

    def test_init_default_enabled(self):
        """Тест что по умолчанию звуки включены."""
        manager = SoundManager()
        
        assert manager.enabled is True

    def test_init_disabled(self):
        """Тест инициализации с отключенными звуками."""
        manager = SoundManager(enabled=False)
        
        assert manager.enabled is False

    def test_init_sets_project_root(self):
        """Тест что устанавливается корень проекта."""
        manager = SoundManager()
        
        assert hasattr(manager, '_project_root')
        assert manager._project_root is not None

    def test_init_pygame_not_initialized(self):
        """Тест что pygame не инициализирован при создании."""
        manager = SoundManager()
        
        assert manager._pygame_initialized is False


class TestGetSoundPath:
    """Тесты получения пути к звуковым файлам."""

    @pytest.fixture
    def manager(self):
        """Фикстура для создания менеджера."""
        return SoundManager()

    def test_get_sound_path_exists(self, manager):
        """Тест что путь к несуществующему файлу возвращает None."""
        # Проверяем что метод возвращает None для несуществующего файла
        result = manager._get_sound_path('nonexistent.wav')
        
        assert result is None

    def test_get_sound_path_logs_warning(self, manager):
        """Тест что предупреждение логируется."""
        with patch('core.sound_manager.logger.warning') as mock_warning:
            with patch('core.sound_manager.os.path.exists', return_value=False):
                manager._get_sound_path('nonexistent.wav')
                
                mock_warning.assert_called_once()


class TestPlay:
    """Тесты воспроизведения звуков."""

    @pytest.fixture
    def manager(self):
        """Фикстура для создания менеджера."""
        return SoundManager(enabled=False)  # Отключаем для тестов

    def test_play_disabled(self, manager):
        """Тест что play не работает когда отключено."""
        manager.enabled = False
        
        with patch('core.sound_manager.threading.Thread') as mock_thread:
            manager.play('START_DOWNLOAD')
            
            mock_thread.assert_not_called()

    def test_play_unknown_key(self, manager):
        """Тест что неизвестный ключ логируется."""
        manager.enabled = True
        
        with patch('core.sound_manager.logger.warning') as mock_warning:
            manager.play('UNKNOWN_KEY')
            
            mock_warning.assert_called_once()

    def test_play_starts_thread(self, manager):
        """Тест что play запускает поток."""
        manager.enabled = True
        
        with patch('core.sound_manager.threading.Thread') as mock_thread:
            manager.play('START_DOWNLOAD')
            
            mock_thread.assert_called_once()

    def test_play_valid_keys(self, manager):
        """Тест воспроизведения валидных ключей."""
        manager.enabled = True
        
        valid_keys = ['START_DOWNLOAD', 'END_DOWNLOAD', 'ERROR_DOWNLOAD']
        
        for key in valid_keys:
            with patch('core.sound_manager.threading.Thread'):
                # Не должно выбрасывать исключений
                manager.play(key)


class TestPlaySound:
    """Тесты метода _play_sound."""

    @pytest.fixture
    def manager(self):
        """Фикстура для создания менеджера."""
        manager = SoundManager()
        manager._project_root = '/test/path'
        return manager

    def test_play_sound_file_not_found(self, manager):
        """Тест что несуществующий файл не воспроизводится."""
        with patch('core.sound_manager.os.path.exists', return_value=False):
            # Не должно выбрасывать исключений
            manager._play_sound('nonexistent.wav')

    def test_play_sound_pygame_not_initialized(self, manager):
        """Тест что звук не воспроизводится без pygame."""
        with patch('core.sound_manager.os.path.exists', return_value=True):
            with patch('core.sound_manager.SoundManager._init_pygame', return_value=False):
                manager._play_sound('test.wav')

    def test_play_sound_loads_and_plays(self, manager):
        """Тест что звук загружается и воспроизводится."""
        mock_pygame = MagicMock()
        mock_sound = MagicMock()
        mock_pygame.mixer.Sound.return_value = mock_sound
        mock_pygame.mixer.get_busy.return_value = False
        
        with patch('core.sound_manager.os.path.exists', return_value=True):
            with patch('core.sound_manager.SoundManager._init_pygame', return_value=True):
                with patch.dict('sys.modules', {'pygame': mock_pygame}):
                    manager._play_sound('test.wav')
                    
                    mock_pygame.mixer.Sound.assert_called_once()
                    mock_sound.play.assert_called_once()

    def test_play_sound_handles_exception(self, manager):
        """Тест что исключения при воспроизведении обрабатываются."""
        mock_pygame = MagicMock()
        mock_pygame.mixer.Sound.side_effect = Exception("Sound error")
        
        with patch('core.sound_manager.os.path.exists', return_value=True):
            with patch('core.sound_manager.SoundManager._init_pygame', return_value=True):
                with patch.dict('sys.modules', {'pygame': mock_pygame}):
                    with patch('core.sound_manager.logger.error') as mock_error:
                        manager._play_sound('test.wav')
                        
                        mock_error.assert_called_once()


class TestInitPygame:
    """Тесты инициализации pygame."""

    @pytest.fixture
    def manager(self):
        """Фикстура для создания менеджера."""
        return SoundManager()

    def test_init_pygame_already_initialized(self, manager):
        """Тест что повторная инициализация не происходит."""
        manager._pygame_initialized = True
        
        result = manager._init_pygame()
        
        assert result is True

    def test_init_pygame_success(self, manager):
        """Тест успешной инициализации."""
        mock_pygame = MagicMock()
        
        with patch.dict('sys.modules', {'pygame': mock_pygame}):
            result = manager._init_pygame()
            
            assert result is True
            assert manager._pygame_initialized is True
            mock_pygame.mixer.init.assert_called_once()

    def test_init_pygame_error(self, manager):
        """Тест ошибки инициализации."""
        mock_pygame = MagicMock()
        mock_pygame.mixer.init.side_effect = Exception("Init error")
        
        with patch.dict('sys.modules', {'pygame': mock_pygame}):
            with patch('core.sound_manager.logger.error') as mock_error:
                result = manager._init_pygame()
                
                assert result is False
                mock_error.assert_called_once()


class TestSpecificPlayMethods:
    """Тесты специфичных методов play_*."""

    def test_play_start_download(self):
        """Тест play_start_download."""
        manager = SoundManager(enabled=False)
        
        with patch.object(manager, 'play') as mock_play:
            manager.play_start_download()
            
            mock_play.assert_called_once_with('START_DOWNLOAD')

    def test_play_end_download(self):
        """Тест play_end_download."""
        manager = SoundManager(enabled=False)
        
        with patch.object(manager, 'play') as mock_play:
            manager.play_end_download()
            
            mock_play.assert_called_once_with('END_DOWNLOAD')

    def test_play_error_download(self):
        """Тест play_error_download."""
        manager = SoundManager(enabled=False)
        
        with patch.object(manager, 'play') as mock_play:
            manager.play_error_download()
            
            mock_play.assert_called_once_with('ERROR_DOWNLOAD')


class TestEnableDisable:
    """Тесты включения/отключения."""

    def test_set_enabled_true(self):
        """Тест включения звуков."""
        manager = SoundManager(enabled=False)
        
        with patch('core.sound_manager.logger.info') as mock_info:
            manager.set_enabled(True)
            
            assert manager.enabled is True
            mock_info.assert_called()

    def test_set_enabled_false(self):
        """Тест отключения звуков."""
        manager = SoundManager(enabled=True)
        
        with patch('core.sound_manager.logger.info') as mock_info:
            manager.set_enabled(False)
            
            assert manager.enabled is False
            mock_info.assert_called()

    def test_is_enabled(self):
        """Тест проверки состояния."""
        manager = SoundManager(enabled=True)
        
        assert manager.is_enabled() is True
        
        manager.enabled = False
        assert manager.is_enabled() is False


class TestShutdown:
    """Тесты остановки."""

    def test_shutdown_success(self):
        """Тест успешной остановки."""
        manager = SoundManager()
        manager._pygame_initialized = True
        
        mock_pygame = MagicMock()
        mock_pygame.mixer.get_init.return_value = True
        
        with patch.dict('sys.modules', {'pygame': mock_pygame}):
            manager.shutdown()
            
            assert manager._pygame_initialized is False
            mock_pygame.mixer.quit.assert_called_once()

    def test_shutdown_handles_exception(self):
        """Тест что исключения при остановке обрабатываются."""
        manager = SoundManager()
        
        mock_pygame = MagicMock()
        mock_pygame.mixer.get_init.side_effect = Exception("Shutdown error")
        
        with patch.dict('sys.modules', {'pygame': mock_pygame}):
            with patch('core.sound_manager.logger.warning') as mock_warning:
                manager.shutdown()
                
                mock_warning.assert_called_once()


class TestGlobalFunctions:
    """Тесты глобальных функций."""

    def test_get_sound_manager_singleton(self):
        """Тест что get_sound_manager возвращает singleton."""
        manager1 = get_sound_manager()
        manager2 = get_sound_manager()
        
        assert manager1 is manager2

    def test_play_start_sound(self):
        """Тест play_start_sound."""
        with patch('core.sound_manager.get_sound_manager') as mock_get:
            mock_manager = Mock()
            mock_get.return_value = mock_manager
            
            play_start_sound()
            
            mock_manager.play_start_download.assert_called_once()

    def test_play_end_sound(self):
        """Тест play_end_sound."""
        with patch('core.sound_manager.get_sound_manager') as mock_get:
            mock_manager = Mock()
            mock_get.return_value = mock_manager
            
            play_end_sound()
            
            mock_manager.play_end_download.assert_called_once()

    def test_play_error_sound(self):
        """Тест play_error_sound."""
        with patch('core.sound_manager.get_sound_manager') as mock_get:
            mock_manager = Mock()
            mock_get.return_value = mock_manager
            
            play_error_sound()
            
            mock_manager.play_error_download.assert_called_once()
