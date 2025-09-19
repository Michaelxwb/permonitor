"""
统一配置依赖管理扩展测试模块
"""

import pytest
import os
from unittest.mock import patch

from web_performance_monitor.config.unified_config import UnifiedConfig
from web_performance_monitor.models.dependency_models import DependencyConfig


class TestUnifiedConfigDependencyExtension:
    """统一配置依赖管理扩展测试类"""
    
    def test_default_dependency_config(self):
        """测试默认依赖配置"""
        config = UnifiedConfig()
        
        assert isinstance(config.dependency_config, DependencyConfig)
        assert config.dependency_config.skip_dependency_check is False
        assert config.dependency_config.strict_dependencies is False
        assert config.dependency_config.auto_install_deps is False
        assert config.dependency_config.preferred_frameworks == []
        assert config.dependency_config.notification_channels == []
    
    def test_default_auto_detection_config(self):
        """测试默认自动检测配置"""
        config = UnifiedConfig()
        
        assert config.enable_auto_detection is True
        assert config.auto_detection_interval == 300
        assert config.enable_framework_monitoring is True
    
    def test_default_graceful_degradation_config(self):
        """测试默认优雅降级配置"""
        config = UnifiedConfig()
        
        assert config.enable_graceful_degradation is True
        assert config.fallback_to_basic_monitor is True
        assert config.show_dependency_warnings is True
    
    def test_default_installation_suggestion_config(self):
        """测试默认安装建议配置"""
        config = UnifiedConfig()
        
        assert config.show_installation_suggestions is True
        assert config.suggest_optimal_installation is True
        assert config.include_size_estimates is True
    
    @patch.dict(os.environ, {
        'WPM_SKIP_DEPENDENCY_CHECK': 'true',
        'WPM_STRICT_DEPENDENCIES': 'true',
        'WPM_AUTO_INSTALL_DEPS': 'true',
        'WPM_PREFERRED_FRAMEWORKS': 'flask,fastapi',
        'WPM_NOTIFICATION_CHANNELS': 'mattermost,file',
        'WPM_ENABLE_AUTO_DETECTION': 'false',
        'WPM_AUTO_DETECTION_INTERVAL': '600',
        'WPM_ENABLE_FRAMEWORK_MONITORING': 'false',
        'WPM_ENABLE_GRACEFUL_DEGRADATION': 'false',
        'WPM_FALLBACK_TO_BASIC_MONITOR': 'false',
        'WPM_SHOW_DEPENDENCY_WARNINGS': 'false',
        'WPM_SHOW_INSTALLATION_SUGGESTIONS': 'false',
        'WPM_SUGGEST_OPTIMAL_INSTALLATION': 'false',
        'WPM_INCLUDE_SIZE_ESTIMATES': 'false'
    })
    def test_from_env_dependency_config(self):
        """测试从环境变量加载依赖配置"""
        config = UnifiedConfig.from_env()
        
        # 检查依赖配置
        assert config.dependency_config.skip_dependency_check is True
        assert config.dependency_config.strict_dependencies is True
        assert config.dependency_config.auto_install_deps is True
        assert config.dependency_config.preferred_frameworks == ['flask', 'fastapi']
        assert config.dependency_config.notification_channels == ['mattermost', 'file']
        
        # 检查自动检测配置
        assert config.enable_auto_detection is False
        assert config.auto_detection_interval == 600
        assert config.enable_framework_monitoring is False
        
        # 检查优雅降级配置
        assert config.enable_graceful_degradation is False
        assert config.fallback_to_basic_monitor is False
        assert config.show_dependency_warnings is False
        
        # 检查安装建议配置
        assert config.show_installation_suggestions is False
        assert config.suggest_optimal_installation is False
        assert config.include_size_estimates is False
    
    def test_validate_for_framework_fastapi(self):
        """测试FastAPI框架配置验证"""
        config = UnifiedConfig()
        
        # 正常情况
        config.validate_for_framework('fastapi')
        
        # 异常情况 - 超时时间无效
        config.fastapi_async_timeout = 0
        with pytest.raises(ValueError, match="FastAPI异步超时时间必须大于0"):
            config.validate_for_framework('fastapi')
        
        # 异常情况 - 并发告警数无效
        config.fastapi_async_timeout = 30.0
        config.fastapi_max_concurrent_alerts = 0
        with pytest.raises(ValueError, match="FastAPI最大并发告警数必须大于0"):
            config.validate_for_framework('fastapi')
    
    def test_validate_for_framework_flask(self):
        """测试Flask框架配置验证"""
        config = UnifiedConfig()
        
        # 正常情况
        config.validate_for_framework('flask')
        
        # 异常情况 - 缓冲区大小无效
        config.flask_wsgi_buffer_size = 0
        with pytest.raises(ValueError, match="Flask WSGI缓冲区大小必须大于0"):
            config.validate_for_framework('flask')
        
        # 异常情况 - 请求体限制无效
        config.flask_wsgi_buffer_size = 8192
        config.flask_request_body_limit = 0
        with pytest.raises(ValueError, match="Flask请求体限制必须大于0"):
            config.validate_for_framework('flask')
    
    def test_validate_dependency_config_invalid_framework(self):
        """测试验证无效的首选框架"""
        config = UnifiedConfig()
        config.dependency_config.preferred_frameworks = ['django']  # 不支持的框架
        
        with pytest.raises(ValueError, match="不支持的首选框架: django"):
            config.validate_dependency_config()
    
    def test_validate_dependency_config_invalid_channel(self):
        """测试验证无效的通知渠道"""
        config = UnifiedConfig()
        config.dependency_config.notification_channels = ['slack']  # 不支持的渠道
        
        with pytest.raises(ValueError, match="不支持的通知渠道: slack"):
            config.validate_dependency_config()
    
    def test_validate_auto_detection_interval(self):
        """测试验证自动检测间隔"""
        config = UnifiedConfig()
        config.auto_detection_interval = 0
        
        with pytest.raises(ValueError, match="自动检测间隔必须大于0"):
            config.validate_for_framework('flask')
    
    def test_get_dependency_config_dict(self):
        """测试获取依赖配置字典"""
        config = UnifiedConfig()
        config.dependency_config.skip_dependency_check = True
        config.dependency_config.preferred_frameworks = ['flask']
        
        config_dict = config.get_dependency_config_dict()
        
        assert config_dict['skip_dependency_check'] is True
        assert config_dict['strict_dependencies'] is False
        assert config_dict['preferred_frameworks'] == ['flask']
        assert 'notification_channels' in config_dict
    
    def test_update_dependency_config(self):
        """测试更新依赖配置"""
        config = UnifiedConfig()
        
        config.update_dependency_config(
            skip_dependency_check=True,
            preferred_frameworks=['fastapi']
        )
        
        assert config.dependency_config.skip_dependency_check is True
        assert config.dependency_config.preferred_frameworks == ['fastapi']
    
    def test_update_dependency_config_invalid_key(self):
        """测试更新无效的依赖配置项"""
        config = UnifiedConfig()
        
        with pytest.raises(ValueError, match="未知的依赖配置项: invalid_key"):
            config.update_dependency_config(invalid_key='value')
    
    def test_is_framework_preferred_no_preferences(self):
        """测试框架偏好检查 - 无偏好设置"""
        config = UnifiedConfig()
        
        assert config.is_framework_preferred('flask') is True
        assert config.is_framework_preferred('fastapi') is True
        assert config.is_framework_preferred('django') is True
    
    def test_is_framework_preferred_with_preferences(self):
        """测试框架偏好检查 - 有偏好设置"""
        config = UnifiedConfig()
        config.dependency_config.preferred_frameworks = ['flask']
        
        assert config.is_framework_preferred('flask') is True
        assert config.is_framework_preferred('fastapi') is False
    
    def test_should_skip_dependency_check(self):
        """测试是否跳过依赖检查"""
        config = UnifiedConfig()
        
        assert config.should_skip_dependency_check() is False
        
        config.dependency_config.skip_dependency_check = True
        assert config.should_skip_dependency_check() is True
    
    def test_is_strict_dependencies_mode(self):
        """测试是否为严格依赖模式"""
        config = UnifiedConfig()
        
        assert config.is_strict_dependencies_mode() is False
        
        config.dependency_config.strict_dependencies = True
        assert config.is_strict_dependencies_mode() is True
    
    def test_get_auto_detection_config(self):
        """测试获取自动检测配置"""
        config = UnifiedConfig()
        config.enable_auto_detection = False
        config.auto_detection_interval = 600
        
        auto_config = config.get_auto_detection_config()
        
        assert auto_config['enable_auto_detection'] is False
        assert auto_config['auto_detection_interval'] == 600
        assert auto_config['enable_framework_monitoring'] is True
    
    def test_get_graceful_degradation_config(self):
        """测试获取优雅降级配置"""
        config = UnifiedConfig()
        config.enable_graceful_degradation = False
        
        degradation_config = config.get_graceful_degradation_config()
        
        assert degradation_config['enable_graceful_degradation'] is False
        assert degradation_config['fallback_to_basic_monitor'] is True
        assert degradation_config['show_dependency_warnings'] is True
    
    def test_get_installation_suggestion_config(self):
        """测试获取安装建议配置"""
        config = UnifiedConfig()
        config.show_installation_suggestions = False
        
        suggestion_config = config.get_installation_suggestion_config()
        
        assert suggestion_config['show_installation_suggestions'] is False
        assert suggestion_config['suggest_optimal_installation'] is True
        assert suggestion_config['include_size_estimates'] is True
    
    def test_get_effective_config_includes_dependency_config(self):
        """测试有效配置包含依赖管理配置"""
        config = UnifiedConfig()
        config.dependency_config.skip_dependency_check = True
        config.enable_auto_detection = False
        
        effective_config = config.get_effective_config()
        
        # 检查依赖配置
        assert 'dependency_config' in effective_config
        assert effective_config['dependency_config']['skip_dependency_check'] is True
        
        # 检查自动检测配置
        assert effective_config['enable_auto_detection'] is False
        assert effective_config['auto_detection_interval'] == 300
        
        # 检查优雅降级配置
        assert effective_config['enable_graceful_degradation'] is True
        
        # 检查安装建议配置
        assert effective_config['show_installation_suggestions'] is True
    
    def test_create_with_dependency_config(self):
        """测试使用依赖配置创建实例"""
        dependency_config = DependencyConfig(
            skip_dependency_check=True,
            preferred_frameworks=['flask']
        )
        
        config = UnifiedConfig.create_with_dependency_config(
            dependency_config=dependency_config,
            threshold_seconds=2.0
        )
        
        assert config.dependency_config.skip_dependency_check is True
        assert config.dependency_config.preferred_frameworks == ['flask']
        assert config.threshold_seconds == 2.0
    
    def test_create_with_dependency_config_from_env(self):
        """测试从环境变量创建依赖配置"""
        with patch.dict(os.environ, {'WPM_SKIP_DEPENDENCY_CHECK': 'true'}):
            config = UnifiedConfig.create_with_dependency_config(threshold_seconds=2.0)
            
            assert config.dependency_config.skip_dependency_check is True
            assert config.threshold_seconds == 2.0
    
    @patch.dict(os.environ, {
        'WPM_SKIP_DEPENDENCY_CHECK': 'true',
        'WPM_PREFERRED_FRAMEWORKS': 'fastapi'
    })
    def test_merge_with_env_dependency_config(self):
        """测试合并环境变量依赖配置"""
        config = UnifiedConfig()
        config.dependency_config.skip_dependency_check = False
        config.dependency_config.preferred_frameworks = ['flask']
        
        config.merge_with_env_dependency_config()
        
        # 环境变量应该覆盖现有配置
        assert config.dependency_config.skip_dependency_check is True
        assert config.dependency_config.preferred_frameworks == ['fastapi']
    
    def test_merge_with_env_dependency_config_no_env_vars(self):
        """测试没有环境变量时的合并"""
        config = UnifiedConfig()
        original_skip_check = config.dependency_config.skip_dependency_check
        original_frameworks = config.dependency_config.preferred_frameworks.copy()
        
        config.merge_with_env_dependency_config()
        
        # 配置应该保持不变
        assert config.dependency_config.skip_dependency_check == original_skip_check
        assert config.dependency_config.preferred_frameworks == original_frameworks