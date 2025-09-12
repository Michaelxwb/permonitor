"""
配置管理测试

测试Config类的各种配置场景
"""

import os
import json
import tempfile
import pytest
from unittest.mock import patch
from web_performance_monitor.config import Config
from web_performance_monitor.exceptions import ConfigurationError


class TestConfig:
    """Config类测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = Config()
        
        assert config.threshold_seconds == 1.0
        assert config.alert_window_days == 10
        assert config.max_performance_overhead == 0.05
        assert config.enable_local_file is True
        assert config.local_output_dir == "/tmp"
        assert config.enable_mattermost is False
        assert config.log_level == "INFO"
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = Config(
            threshold_seconds=2.0,
            alert_window_days=5,
            enable_mattermost=True,
            mattermost_server_url="https://test.com",
            mattermost_token="test-token",
            mattermost_channel_id="test-channel"
        )
        
        assert config.threshold_seconds == 2.0
        assert config.alert_window_days == 5
        assert config.enable_mattermost is True
        assert config.mattermost_server_url == "https://test.com"
    
    def test_from_env_valid(self):
        """测试从环境变量加载有效配置"""
        env_vars = {
            'WPM_THRESHOLD_SECONDS': '1.5',
            'WPM_ALERT_WINDOW_DAYS': '7',
            'WPM_ENABLE_LOCAL_FILE': 'true',
            'WPM_LOCAL_OUTPUT_DIR': '/custom/path',
            'WPM_ENABLE_MATTERMOST': 'false',
            'WPM_LOG_LEVEL': 'DEBUG'
        }
        
        with patch.dict(os.environ, env_vars):
            config = Config.from_env()
            
            assert config.threshold_seconds == 1.5
            assert config.alert_window_days == 7
            assert config.enable_local_file is True
            assert config.local_output_dir == '/custom/path'
            assert config.enable_mattermost is False
            assert config.log_level == 'DEBUG'
    
    def test_from_env_invalid_values(self):
        """测试从环境变量加载无效值"""
        env_vars = {
            'WPM_THRESHOLD_SECONDS': 'invalid',
            'WPM_ALERT_WINDOW_DAYS': 'not_a_number'
        }
        
        with patch.dict(os.environ, env_vars):
            with pytest.raises(ConfigurationError):
                Config.from_env()
    
    def test_from_dict_valid(self):
        """测试从字典加载有效配置"""
        config_dict = {
            'threshold_seconds': 2.5,
            'alert_window_days': 14,
            'enable_local_file': False,
            'enable_mattermost': True,
            'mattermost_server_url': 'https://example.com'
        }
        
        config = Config.from_dict(config_dict)
        
        assert config.threshold_seconds == 2.5
        assert config.alert_window_days == 14
        assert config.enable_local_file is False
        assert config.enable_mattermost is True
        assert config.mattermost_server_url == 'https://example.com'
    
    def test_from_dict_invalid_fields(self):
        """测试从字典加载包含无效字段"""
        config_dict = {
            'threshold_seconds': 1.0,
            'invalid_field': 'should_be_ignored',
            'another_invalid': 123
        }
        
        config = Config.from_dict(config_dict)
        
        assert config.threshold_seconds == 1.0
        assert not hasattr(config, 'invalid_field')
        assert not hasattr(config, 'another_invalid')
    
    def test_from_file_valid(self):
        """测试从文件加载有效配置"""
        config_data = {
            'threshold_seconds': 3.0,
            'alert_window_days': 21,
            'enable_local_file': True,
            'local_output_dir': '/test/path'
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_file = f.name
        
        try:
            config = Config.from_file(config_file)
            
            assert config.threshold_seconds == 3.0
            assert config.alert_window_days == 21
            assert config.enable_local_file is True
            assert config.local_output_dir == '/test/path'
        finally:
            os.unlink(config_file)
    
    def test_from_file_not_exists(self):
        """测试从不存在的文件加载配置"""
        with pytest.raises(ConfigurationError, match="配置文件不存在"):
            Config.from_file('/nonexistent/file.json')
    
    def test_from_file_invalid_json(self):
        """测试从无效JSON文件加载配置"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('invalid json content')
            config_file = f.name
        
        try:
            with pytest.raises(ConfigurationError, match="JSON格式错误"):
                Config.from_file(config_file)
        finally:
            os.unlink(config_file)
    
    def test_validate_invalid_threshold(self):
        """测试验证无效阈值"""
        with patch('web_performance_monitor.config.logging.getLogger') as mock_logger:
            config = Config(threshold_seconds=-1.0)
            
            # 应该被重置为默认值
            assert config.threshold_seconds == 1.0
            mock_logger.return_value.warning.assert_called()
    
    def test_validate_invalid_window_days(self):
        """测试验证无效时间窗口"""
        with patch('web_performance_monitor.config.logging.getLogger') as mock_logger:
            config = Config(alert_window_days=-5)
            
            # 应该被重置为默认值
            assert config.alert_window_days == 10
            mock_logger.return_value.warning.assert_called()
    
    def test_validate_invalid_overhead(self):
        """测试验证无效性能开销"""
        with patch('web_performance_monitor.config.logging.getLogger') as mock_logger:
            config = Config(max_performance_overhead=1.5)  # 150%
            
            # 应该被重置为默认值
            assert config.max_performance_overhead == 0.05
            mock_logger.return_value.warning.assert_called()
    
    def test_validate_mattermost_incomplete(self):
        """测试验证不完整的Mattermost配置"""
        with patch('web_performance_monitor.config.logging.getLogger') as mock_logger:
            config = Config(
                enable_mattermost=True,
                mattermost_server_url="https://test.com",
                # 缺少token和channel_id
            )
            
            # 应该被禁用
            assert config.enable_mattermost is False
            mock_logger.return_value.warning.assert_called()
    
    def test_validate_no_notifications(self):
        """测试验证没有启用任何通知方式"""
        with patch('web_performance_monitor.config.logging.getLogger') as mock_logger:
            config = Config(
                enable_local_file=False,
                enable_mattermost=False
            )
            
            # 应该自动启用本地文件通知
            assert config.enable_local_file is True
            mock_logger.return_value.warning.assert_called()
    
    def test_get_effective_config(self):
        """测试获取生效配置"""
        config = Config(
            threshold_seconds=2.0,
            mattermost_token="secret-token-12345"
        )
        
        effective_config = config.get_effective_config()
        
        assert effective_config['threshold_seconds'] == 2.0
        assert effective_config['mattermost_token'] == "secret-t***"  # 脱敏
    
    def test_to_dict(self):
        """测试转换为字典"""
        config = Config(
            threshold_seconds=1.5,
            enable_mattermost=True,
            mattermost_token="full-token"
        )
        
        config_dict = config.to_dict()
        
        assert config_dict['threshold_seconds'] == 1.5
        assert config_dict['enable_mattermost'] is True
        assert config_dict['mattermost_token'] == "full-token"  # 包含完整信息
    
    def test_boolean_env_parsing(self):
        """测试布尔值环境变量解析"""
        test_cases = [
            ('true', True),
            ('True', True),
            ('TRUE', True),
            ('false', False),
            ('False', False),
            ('FALSE', False),
            ('yes', False),  # 只有'true'被识别为True
            ('1', False),
        ]
        
        for env_value, expected in test_cases:
            with patch.dict(os.environ, {'WPM_ENABLE_LOCAL_FILE': env_value}):
                config = Config.from_env()
                assert config.enable_local_file == expected