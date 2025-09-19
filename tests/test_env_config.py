"""
环境变量控制机制测试模块
"""

import pytest
import os
import tempfile
from unittest.mock import patch

from web_performance_monitor.config.env_config import (
    EnvironmentConfigManager,
    EnvVarDefinition,
    ConfigPriority,
    get_env_manager,
    get_env_config,
    validate_env_config,
    get_env_config_summary,
    export_env_template
)


class TestEnvVarDefinition:
    """环境变量定义测试类"""
    
    def test_env_var_definition_creation(self):
        """测试创建环境变量定义"""
        definition = EnvVarDefinition(
            name='TEST_VAR',
            default_value=True,
            value_type=bool,
            description='Test variable',
            required=True
        )
        
        assert definition.name == 'TEST_VAR'
        assert definition.default_value is True
        assert definition.value_type == bool
        assert definition.description == 'Test variable'
        assert definition.required is True
        assert definition.validator is None
        assert definition.transformer is None
        assert definition.choices is None


class TestEnvironmentConfigManager:
    """环境变量配置管理器测试类"""
    
    def setup_method(self):
        """测试方法设置"""
        self.manager = EnvironmentConfigManager()
        # 清除缓存
        self.manager.clear_cache()
    
    def test_register_env_var(self):
        """测试注册环境变量"""
        definition = EnvVarDefinition(
            name='TEST_CUSTOM_VAR',
            default_value='test',
            value_type=str,
            description='Custom test variable'
        )
        
        self.manager.register_env_var(definition)
        
        assert 'TEST_CUSTOM_VAR' in self.manager.env_var_definitions
        assert self.manager.env_var_definitions['TEST_CUSTOM_VAR'] == definition
    
    def test_get_env_value_default(self):
        """测试获取环境变量默认值"""
        # 使用已注册的环境变量
        value = self.manager.get_env_value('WPM_SKIP_DEPENDENCY_CHECK')
        
        assert value is False  # 默认值
    
    @patch.dict(os.environ, {'WPM_SKIP_DEPENDENCY_CHECK': 'true'})
    def test_get_env_value_from_env(self):
        """测试从环境变量获取值"""
        value = self.manager.get_env_value('WPM_SKIP_DEPENDENCY_CHECK', use_cache=False)
        
        assert value is True
    
    @patch.dict(os.environ, {'WPM_SKIP_DEPENDENCY_CHECK': 'invalid'})
    def test_get_env_value_invalid_conversion(self):
        """测试无效值转换时使用默认值"""
        value = self.manager.get_env_value('WPM_SKIP_DEPENDENCY_CHECK', use_cache=False)
        
        assert value is False  # 应该回退到默认值
    
    def test_get_env_value_unregistered(self):
        """测试获取未注册的环境变量"""
        with pytest.raises(ValueError, match="未注册的环境变量"):
            self.manager.get_env_value('UNREGISTERED_VAR')
    
    def test_get_env_value_with_cache(self):
        """测试缓存机制"""
        # 第一次调用
        value1 = self.manager.get_env_value('WPM_SKIP_DEPENDENCY_CHECK')
        
        # 检查缓存
        assert 'WPM_SKIP_DEPENDENCY_CHECK' in self.manager.config_cache
        
        # 第二次调用应该使用缓存
        value2 = self.manager.get_env_value('WPM_SKIP_DEPENDENCY_CHECK')
        
        assert value1 == value2
    
    @patch.dict(os.environ, {
        'WPM_SKIP_DEPENDENCY_CHECK': 'true',
        'WPM_STRICT_DEPENDENCIES': 'false',
        'WPM_PREFERRED_FRAMEWORKS': 'flask,fastapi'
    })
    def test_get_all_env_values(self):
        """测试获取所有环境变量值"""
        values = self.manager.get_all_env_values(use_cache=False)
        
        assert 'WPM_SKIP_DEPENDENCY_CHECK' in values
        assert values['WPM_SKIP_DEPENDENCY_CHECK'] is True
        assert values['WPM_STRICT_DEPENDENCIES'] is False
        assert values['WPM_PREFERRED_FRAMEWORKS'] == ['flask', 'fastapi']
    
    def test_validate_all_env_vars_valid(self):
        """测试验证所有环境变量 - 有效情况"""
        result = self.manager.validate_all_env_vars()
        
        assert result is True
        assert len(self.manager.get_validation_errors()) == 0
    
    @patch.dict(os.environ, {'WPM_AUTO_DETECTION_INTERVAL': '0'})
    def test_validate_all_env_vars_invalid(self):
        """测试验证所有环境变量 - 无效情况"""
        result = self.manager.validate_all_env_vars()
        
        assert result is False
        errors = self.manager.get_validation_errors()
        assert len(errors) > 0
        assert any('WPM_AUTO_DETECTION_INTERVAL' in error for error in errors)
    
    @patch.dict(os.environ, {'WPM_PREFERRED_FRAMEWORKS': 'django'})
    def test_validate_frameworks_invalid(self):
        """测试验证无效框架"""
        result = self.manager.validate_all_env_vars()
        
        assert result is False
        errors = self.manager.get_validation_errors()
        assert any('WPM_PREFERRED_FRAMEWORKS' in error for error in errors)
    
    @patch.dict(os.environ, {'WPM_NOTIFICATION_CHANNELS': 'slack'})
    def test_validate_notification_channels_invalid(self):
        """测试验证无效通知渠道"""
        result = self.manager.validate_all_env_vars()
        
        assert result is False
        errors = self.manager.get_validation_errors()
        assert any('WPM_NOTIFICATION_CHANNELS' in error for error in errors)
    
    @patch.dict(os.environ, {'WPM_LOG_LEVEL': 'INVALID'})
    def test_validate_choices_invalid(self):
        """测试验证无效选择"""
        result = self.manager.validate_all_env_vars()
        
        assert result is False
        errors = self.manager.get_validation_errors()
        assert any('WPM_LOG_LEVEL' in error for error in errors)
    
    def test_clear_cache(self):
        """测试清除缓存"""
        # 先获取一个值以填充缓存
        self.manager.get_env_value('WPM_SKIP_DEPENDENCY_CHECK')
        
        assert len(self.manager.config_cache) > 0
        
        self.manager.clear_cache()
        
        assert len(self.manager.config_cache) == 0
    
    @patch.dict(os.environ, {
        'WPM_SKIP_DEPENDENCY_CHECK': 'true',
        'WPM_PREFERRED_FRAMEWORKS': 'flask'
    })
    def test_get_config_summary(self):
        """测试获取配置摘要"""
        summary = self.manager.get_config_summary()
        
        assert 'total_env_vars' in summary
        assert 'cached_values' in summary
        assert 'validation_errors' in summary
        assert 'env_var_status' in summary
        
        # 检查特定环境变量状态
        skip_check_status = summary['env_var_status']['WPM_SKIP_DEPENDENCY_CHECK']
        assert skip_check_status['set'] is True
        assert skip_check_status['value'] == 'true'
        assert skip_check_status['using_default'] is False
        
        frameworks_status = summary['env_var_status']['WPM_PREFERRED_FRAMEWORKS']
        assert frameworks_status['set'] is True
        assert frameworks_status['value'] == 'flask'
    
    def test_export_env_template(self):
        """测试导出环境变量模板"""
        template = self.manager.export_env_template(include_descriptions=True)
        
        assert 'WPM_SKIP_DEPENDENCY_CHECK' in template
        assert 'WPM_STRICT_DEPENDENCIES' in template
        assert '# 跳过运行时依赖检查' in template
        assert 'WPM_SKIP_DEPENDENCY_CHECK=false' in template
    
    def test_export_env_template_no_descriptions(self):
        """测试导出环境变量模板（不包含描述）"""
        template = self.manager.export_env_template(include_descriptions=False)
        
        assert 'WPM_SKIP_DEPENDENCY_CHECK=false' in template
        assert '# 跳过运行时依赖检查' not in template
    
    def test_str_to_bool_transformer(self):
        """测试字符串到布尔值转换器"""
        assert self.manager._str_to_bool('true') is True
        assert self.manager._str_to_bool('True') is True
        assert self.manager._str_to_bool('1') is True
        assert self.manager._str_to_bool('yes') is True
        assert self.manager._str_to_bool('on') is True
        assert self.manager._str_to_bool('enabled') is True
        
        assert self.manager._str_to_bool('false') is False
        assert self.manager._str_to_bool('False') is False
        assert self.manager._str_to_bool('0') is False
        assert self.manager._str_to_bool('no') is False
        assert self.manager._str_to_bool('off') is False
        assert self.manager._str_to_bool('disabled') is False
    
    def test_str_to_list_transformer(self):
        """测试字符串到列表转换器"""
        assert self.manager._str_to_list('') == []
        assert self.manager._str_to_list('  ') == []
        assert self.manager._str_to_list('flask') == ['flask']
        assert self.manager._str_to_list('flask,fastapi') == ['flask', 'fastapi']
        assert self.manager._str_to_list('flask, fastapi, django') == ['flask', 'fastapi', 'django']
        assert self.manager._str_to_list('flask,,fastapi') == ['flask', 'fastapi']  # 空项被过滤
    
    def test_str_to_json_transformer(self):
        """测试字符串到JSON转换器"""
        assert self.manager._str_to_json('{}') == {}
        assert self.manager._str_to_json('{"key": "value"}') == {"key": "value"}
        assert self.manager._str_to_json('[1, 2, 3]') == [1, 2, 3]
        
        with pytest.raises(ValueError, match="JSON解析失败"):
            self.manager._str_to_json('invalid json')
    
    def test_validate_frameworks(self):
        """测试框架验证器"""
        assert self.manager._validate_frameworks(['flask']) is True
        assert self.manager._validate_frameworks(['fastapi']) is True
        assert self.manager._validate_frameworks(['flask', 'fastapi']) is True
        assert self.manager._validate_frameworks([]) is True
        
        assert self.manager._validate_frameworks(['django']) is False
        assert self.manager._validate_frameworks(['flask', 'django']) is False
    
    def test_validate_notification_channels(self):
        """测试通知渠道验证器"""
        assert self.manager._validate_notification_channels(['mattermost']) is True
        assert self.manager._validate_notification_channels(['file']) is True
        assert self.manager._validate_notification_channels(['console']) is True
        assert self.manager._validate_notification_channels(['mattermost', 'file']) is True
        assert self.manager._validate_notification_channels([]) is True
        
        assert self.manager._validate_notification_channels(['slack']) is False
        assert self.manager._validate_notification_channels(['mattermost', 'slack']) is False


class TestGlobalFunctions:
    """全局函数测试类"""
    
    def test_get_env_manager_singleton(self):
        """测试全局环境管理器单例"""
        manager1 = get_env_manager()
        manager2 = get_env_manager()
        
        assert manager1 is manager2
    
    def test_get_env_config(self):
        """测试获取环境变量配置"""
        value = get_env_config('WPM_SKIP_DEPENDENCY_CHECK')
        
        assert isinstance(value, bool)
        assert value is False  # 默认值
    
    @patch.dict(os.environ, {'WPM_SKIP_DEPENDENCY_CHECK': 'true'})
    def test_get_env_config_from_env(self):
        """测试从环境变量获取配置"""
        # 清除缓存以确保从环境变量读取
        get_env_manager().clear_cache()
        
        value = get_env_config('WPM_SKIP_DEPENDENCY_CHECK', use_cache=False)
        
        assert value is True
    
    def test_validate_env_config(self):
        """测试验证环境变量配置"""
        result = validate_env_config()
        
        assert isinstance(result, bool)
    
    def test_get_env_config_summary(self):
        """测试获取环境变量配置摘要"""
        summary = get_env_config_summary()
        
        assert isinstance(summary, dict)
        assert 'total_env_vars' in summary
        assert 'env_var_status' in summary
    
    def test_export_env_template_to_file(self):
        """测试导出环境变量模板到文件"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as f:
            temp_file = f.name
        
        try:
            template = export_env_template(temp_file)
            
            # 检查文件是否创建
            assert os.path.exists(temp_file)
            
            # 检查文件内容
            with open(temp_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            assert content == template
            assert 'WPM_SKIP_DEPENDENCY_CHECK' in content
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_export_env_template_no_file(self):
        """测试导出环境变量模板（不保存到文件）"""
        template = export_env_template()
        
        assert isinstance(template, str)
        assert 'WPM_SKIP_DEPENDENCY_CHECK' in template
        assert len(template) > 0


class TestConfigPriority:
    """配置优先级测试类"""
    
    def test_config_priority_enum(self):
        """测试配置优先级枚举"""
        assert ConfigPriority.ENVIRONMENT.value == 1
        assert ConfigPriority.CONFIG_FILE.value == 2
        assert ConfigPriority.DEFAULT.value == 3
        
        # 环境变量应该有最高优先级
        assert ConfigPriority.ENVIRONMENT.value < ConfigPriority.CONFIG_FILE.value
        assert ConfigPriority.CONFIG_FILE.value < ConfigPriority.DEFAULT.value