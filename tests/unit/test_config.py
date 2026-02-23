# -*- coding: utf-8 -*-
"""
Unit-тесты для модуля core/config.py.

Тестирование класса ConfigManager:
- Инициализация
- Загрузка конфигурации
- Слияние с настройками по умолчанию
- Сохранение конфигурации
- Получение и установка значений
"""

import pytest
import json
import os
from unittest.mock import patch, MagicMock, mock_open

from core.config import (
    ConfigManager,
    DEFAULT_CONFIG,
    get_app_base_path,
    get_utilities_path,
    get_config_path,
    get_config_backup_path,
)


class TestConfigManagerInit:
    """Тесты инициализации ConfigManager."""

    def test_init_creates_paths(self):
        """Проверка создания путей при инициализации."""
        with patch('core.config.get_config_path') as mock_config_path:
            with patch('core.config.get_config_backup_path') as mock_bkp_path:
                with patch('core.config.get_app_base_path') as mock_base:
                    mock_config_path.return_value = '/fake/config.json'
                    mock_bkp_path.return_value = '/fake/config.bkp'
                    mock_base.return_value = '/fake/app'
                    
                    with patch('core.config.os.path.exists') as mock_exists:
                        mock_exists.return_value = False  # Файл не существует
                        with patch.object(ConfigManager, '_load_or_create') as mock_load:
                            mock_load.return_value = DEFAULT_CONFIG.copy()
                            
                            config = ConfigManager()
                            
                            assert config.config_path == '/fake/config.json'
                            assert config.bkp_path == '/fake/config.bkp'


class TestConfigManagerLoadOrCreate:
    """Тесты загрузки конфигурации."""

    def test_load_existing_config(self):
        """Проверка загрузки существующей конфигурации."""
        config_data = {'DOWNLOAD_PATH': '/custom/path', 'KEY': 'value'}
        
        with patch('core.config.os.path.exists') as mock_exists:
            with patch('core.config.os.path.getsize') as mock_getsize:
                mock_exists.return_value = True
                mock_getsize.return_value = 1000  # Файл больше 100 байт
                
                mock_file = mock_open(read_data=json.dumps(config_data))
                with patch('builtins.open', mock_file):
                    with patch.object(ConfigManager, '_backup_config'):
                        with patch.object(ConfigManager, '_merge_with_defaults') as mock_merge:
                            mock_merge.return_value = config_data
                            
                            config = ConfigManager.__new__(ConfigManager)
                            config.config_path = '/fake/config.json'
                            config.bkp_path = '/fake/config.bkp'
                            
                            result = config._load_or_create()
                            
                            assert result == config_data
                            mock_file.assert_called_with('/fake/config.json', 'r', encoding='utf-8')

    def test_load_corrupted_config_fallback_to_backup(self):
        """Проверка загрузки при повреждённом config.json."""
        with patch('core.config.os.path.exists') as mock_exists:
            with patch('core.config.os.path.getsize') as mock_getsize:
                mock_exists.side_effect = [True, True, True]  # config, backup, config
                mock_getsize.return_value = 1000
                
                # Повреждённый JSON
                mock_file = mock_open(read_data='{invalid json}')
                with patch('builtins.open', mock_file):
                    with patch('core.config.shutil.copyfile'):
                        with patch.object(ConfigManager, '_merge_with_defaults') as mock_merge:
                            mock_merge.return_value = DEFAULT_CONFIG.copy()
                            
                            config = ConfigManager.__new__(ConfigManager)
                            config.config_path = '/fake/config.json'
                            config.bkp_path = '/fake/config.bkp'
                            
                            result = config._load_or_create()
                            
                            assert result == DEFAULT_CONFIG

    def test_load_backup_if_config_missing(self):
        """Проверка загрузки из backup если config.json отсутствует."""
        config_data = {'KEY': 'value'}
        
        with patch('core.config.os.path.exists') as mock_exists:
            with patch('core.config.os.path.getsize') as mock_getsize:
                # config.json не существует, backup существует
                mock_exists.side_effect = [False, True, True]
                mock_getsize.return_value = 1000
                
                mock_file = mock_open(read_data=json.dumps(config_data))
                with patch('builtins.open', mock_file):
                    with patch('core.config.shutil.copyfile'):
                        with patch.object(ConfigManager, '_merge_with_defaults') as mock_merge:
                            mock_merge.return_value = config_data
                            
                            config = ConfigManager.__new__(ConfigManager)
                            config.config_path = '/fake/config.json'
                            config.bkp_path = '/fake/config.bkp'
                            
                            result = config._load_or_create()
                            
                            assert result == config_data

    def test_create_new_config_if_none_exist(self):
        """Проверка создания новой конфигурации если файлы отсутствуют."""
        with patch('core.config.os.path.exists') as mock_exists:
            mock_exists.return_value = False
            
            config = ConfigManager.__new__(ConfigManager)
            config.config_path = '/fake/config.json'
            config.bkp_path = '/fake/config.bkp'
            
            result = config._load_or_create()
            
            assert result == DEFAULT_CONFIG


class TestConfigManagerMergeWithDefaults:
    """Тесты слияния с настройками по умолчанию."""

    def test_merge_adds_missing_keys(self):
        """Проверка добавления отсутствующих ключей."""
        user_config = {'CUSTOM_KEY': 'custom_value'}
        
        config = ConfigManager.__new__(ConfigManager)
        result = config._merge_with_defaults(user_config)
        
        # Проверяем что пользовательские ключи сохранены
        assert result['CUSTOM_KEY'] == 'custom_value'
        
        # Проверяем что ключи по умолчанию добавлены
        assert 'DOWNLOAD_PATH' in result
        assert 'YTDLP_PATH' in result

    def test_merge_preserves_user_values(self):
        """Проверка сохранения пользовательских значений."""
        user_config = {'DOWNLOAD_PATH': '/custom/path'}
        
        config = ConfigManager.__new__(ConfigManager)
        result = config._merge_with_defaults(user_config)
        
        assert result['DOWNLOAD_PATH'] == '/custom/path'

    def test_merge_updates_paths(self):
        """Проверка обновления путей."""
        import ntpath
        with patch('core.config.get_app_base_path') as mock_base:
            with patch('core.config.os.path.join', ntpath.join):
                mock_base.return_value = r'\app'
                
                config = ConfigManager.__new__(ConfigManager)
                result = config._merge_with_defaults({})
                
                assert 'app' in result['DAFAULT_PATH']
                assert 'utilities' in result['UTILITIES_PATH']
                assert 'yt-dlp.exe' in result['YTDLP_PATH']


class TestConfigManagerSave:
    """Тесты сохранения конфигурации."""

    def test_save_creates_backup(self):
        """Проверка создания backup при сохранении."""
        with patch('core.config.os.path.exists') as mock_exists:
            mock_exists.return_value = True
            
            mock_file = mock_open()
            with patch('builtins.open', mock_file):
                with patch.object(ConfigManager, '_backup_config') as mock_backup:
                    config = ConfigManager.__new__(ConfigManager)
                    config.config_path = '/fake/config.json'
                    config.config = {'KEY': 'value'}
                    
                    config.save()
                    
                    mock_backup.assert_called_once_with('/fake/config.json')

    def test_save_writes_json(self):
        """Проверка записи JSON файла."""
        mock_file = mock_open()
        with patch('builtins.open', mock_file):
            with patch('core.config.os.path.exists') as mock_exists:
                mock_exists.return_value = False
                
                config = ConfigManager.__new__(ConfigManager)
                config.config_path = '/fake/config.json'
                config.config = {'KEY': 'value'}
                
                config.save()
                
                mock_file.assert_called_with('/fake/config.json', 'w', encoding='utf-8')


class TestConfigManagerGetSet:
    """Тесты получения и установки значений."""

    def test_get_existing_key(self):
        """Проверка получения существующего ключа."""
        config = ConfigManager.__new__(ConfigManager)
        config.config = {'KEY': 'value'}
        
        result = config.get('KEY')
        assert result == 'value'

    def test_get_missing_key_with_default(self):
        """Проверка получения отсутствующего ключа с default."""
        config = ConfigManager.__new__(ConfigManager)
        config.config = {}
        
        result = config.get('MISSING_KEY', 'default_value')
        assert result == 'default_value'

    def test_get_missing_key_returns_none(self):
        """Проверка получения отсутствующего ключа без default."""
        config = ConfigManager.__new__(ConfigManager)
        config.config = {}
        
        result = config.get('MISSING_KEY')
        assert result is None

    def test_set_new_key(self):
        """Проверка установки нового ключа."""
        config = ConfigManager.__new__(ConfigManager)
        config.config = {}
        
        config.set('NEW_KEY', 'new_value')
        
        assert config.config['NEW_KEY'] == 'new_value'

    def test_set_existing_key(self):
        """Проверка обновления существующего ключа."""
        config = ConfigManager.__new__(ConfigManager)
        config.config = {'KEY': 'old_value'}
        
        config.set('KEY', 'new_value')
        
        assert config.config['KEY'] == 'new_value'

    def test_get_all_returns_copy(self):
        """Проверка что get_all возвращает копию."""
        config = ConfigManager.__new__(ConfigManager)
        config.config = {'KEY': 'value'}
        
        result = config.get_all()
        result['KEY'] = 'modified'
        
        assert config.config['KEY'] == 'value'  # Оригинал не изменён


class TestHelperFunctions:
    """Тесты вспомогательных функций."""

    def test_get_config_path(self):
        """Проверка get_config_path()."""
        with patch('core.config.get_utilities_path') as mock_utils:
            mock_utils.return_value = '/utilities'
            result = get_config_path()
            assert result.endswith('config.json')
            assert 'utilities' in result

    def test_get_config_backup_path(self):
        """Проверка get_config_backup_path()."""
        with patch('core.config.get_utilities_path') as mock_utils:
            mock_utils.return_value = '/utilities'
            result = get_config_backup_path()
            assert result.endswith('config.bkp')
            assert 'utilities' in result

    def test_get_utilities_path_creates_directory(self):
        """Проверка что get_utilities_path создаёт директорию."""
        with patch('core.config.get_app_base_path') as mock_base:
            with patch('core.config.os.path.join') as mock_join:
                with patch('core.config.os.makedirs') as mock_makedirs:
                    mock_base.return_value = '/app'
                    mock_join.return_value = '/app/utilities'
                    
                    result = get_utilities_path()
                    
                    mock_makedirs.assert_called_once_with('/app/utilities', exist_ok=True)
