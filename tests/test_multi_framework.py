"""
多框架支持测试

测试Flask和FastAPI监控器的创建和使用
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys

from web_performance_monitor import (
    MonitorFactory, UnifiedConfig, FlaskMonitor, FastAPIMonitor,
    create_web_monitor
)
from web_performance_monitor.core.base import BaseWebMonitor


class TestMultiFrameworkSupport:
    """多框架支持测试"""
    
    def test_flask_monitor_creation(self):
        """测试Flask监控器创建"""
        config = UnifiedConfig()
        monitor = MonitorFactory.create_monitor(config, 'flask')
        assert isinstance(monitor, FlaskMonitor)
        assert isinstance(monitor, BaseWebMonitor)
    
    def test_fastapi_monitor_creation(self):
        """测试FastAPI监控器创建"""
        config = UnifiedConfig()
        monitor = MonitorFactory.create_monitor(config, 'fastapi')
        assert isinstance(monitor, FastAPIMonitor)
        assert isinstance(monitor, BaseWebMonitor)
    
    def test_flask_middleware_creation(self):
        """测试Flask中间件创建"""
        config = UnifiedConfig()
        monitor = FlaskMonitor(config)
        middleware = monitor.create_middleware()
        assert callable(middleware)
    
    def test_fastapi_middleware_creation(self):
        """测试FastAPI中间件创建"""
        config = UnifiedConfig()
        monitor = FastAPIMonitor(config)
        
        # Mock FastAPI imports
        mock_base_middleware = MagicMock()
        with patch.dict('sys.modules', {
            'fastapi': MagicMock(),
            'starlette.middleware.base': MagicMock(BaseHTTPMiddleware=mock_base_middleware)
        }):
            middleware_class = monitor.create_middleware()
            assert middleware_class is not None
    
    def test_framework_detection_flask(self):
        """测试Flask框架检测"""
        with patch.dict('sys.modules', {'flask': Mock()}):
            with patch.object(MonitorFactory, '_is_flask_available', return_value=True):
                with patch.object(MonitorFactory, '_is_fastapi_available', return_value=False):
                    framework = MonitorFactory.detect_framework()
                    assert framework == 'flask'
    
    def test_framework_detection_fastapi(self):
        """测试FastAPI框架检测"""
        with patch.dict('sys.modules', {'fastapi': Mock()}):
            with patch.object(MonitorFactory, '_is_fastapi_available', return_value=True):
                with patch.object(MonitorFactory, '_is_flask_available', return_value=False):
                    framework = MonitorFactory.detect_framework()
                    assert framework == 'fastapi'
    
    def test_framework_detection_failure(self):
        """测试框架检测失败"""
        with patch.object(MonitorFactory, '_is_flask_available', return_value=False):
            with patch.object(MonitorFactory, '_is_fastapi_available', return_value=False):
                with pytest.raises(RuntimeError, match="无法检测到支持的web框架"):
                    MonitorFactory.detect_framework()
    
    def test_monitor_factory_unsupported_framework(self):
        """测试不支持的框架"""
        config = UnifiedConfig()
        with pytest.raises(ValueError, match="不支持的框架"):
            MonitorFactory.create_monitor(config, 'django')
    
    def test_create_web_monitor_auto_detect(self):
        """测试统一创建函数的自动检测"""
        with patch.object(MonitorFactory, 'detect_framework', return_value='flask'):
            monitor = create_web_monitor()
            assert isinstance(monitor, FlaskMonitor)
    
    def test_create_web_monitor_explicit_framework(self):
        """测试统一创建函数的显式框架指定"""
        monitor = create_web_monitor(framework='flask')
        assert isinstance(monitor, FlaskMonitor)
    
    def test_create_web_monitor_with_config(self):
        """测试统一创建函数的配置传递"""
        config_dict = {
            'threshold_seconds': 2.0,
            'enable_local_file': False,
            'enable_mattermost': True,  # 需要启用至少一种通知方式
            'mattermost_server_url': 'http://test.com',
            'mattermost_token': 'test_token',
            'mattermost_channel_id': 'test_channel'
        }
        monitor = create_web_monitor(framework='flask', config=config_dict)
        assert monitor.config.threshold_seconds == 2.0
        assert monitor.config.enable_local_file == False
    
    def test_get_supported_frameworks(self):
        """测试获取支持的框架列表"""
        frameworks = MonitorFactory.get_supported_frameworks()
        assert 'flask' in frameworks
        assert 'fastapi' in frameworks
    
    def test_register_custom_monitor(self):
        """测试注册自定义监控器"""
        class CustomMonitor(BaseWebMonitor):
            def create_middleware(self):
                return lambda: None
            
            def create_decorator(self):
                return lambda f: f
            
            def _extract_request_info(self, request_context):
                return {}
            
            def _create_analyzer(self):
                return Mock()
            
            def _create_alert_manager(self):
                return Mock()
        
        MonitorFactory.register_monitor('custom', CustomMonitor)
        
        config = UnifiedConfig()
        monitor = MonitorFactory.create_monitor(config, 'custom')
        assert isinstance(monitor, CustomMonitor)


class TestFrameworkDetection:
    """框架检测测试"""
    
    def test_flask_detection_with_module(self):
        """测试通过模块检测Flask"""
        mock_flask = Mock()
        mock_flask.Flask = Mock()
        
        with patch.dict('sys.modules', {'flask': mock_flask}):
            assert MonitorFactory._is_flask_available() == True
    
    def test_fastapi_detection_with_module(self):
        """测试通过模块检测FastAPI"""
        mock_fastapi = Mock()
        mock_fastapi.FastAPI = Mock()
        
        with patch.dict('sys.modules', {'fastapi': mock_fastapi}):
            assert MonitorFactory._is_fastapi_available() == True
    
    def test_flask_detection_without_module(self):
        """测试Flask模块不存在时的检测"""
        # 确保flask模块不在sys.modules中
        modules_backup = sys.modules.copy()
        if 'flask' in sys.modules:
            del sys.modules['flask']
        
        try:
            # 模拟ImportError
            with patch('builtins.__import__', side_effect=ImportError):
                assert MonitorFactory._is_flask_available() == False
        finally:
            sys.modules.update(modules_backup)
    
    def test_fastapi_detection_without_module(self):
        """测试FastAPI模块不存在时的检测"""
        # 确保fastapi模块不在sys.modules中
        modules_backup = sys.modules.copy()
        if 'fastapi' in sys.modules:
            del sys.modules['fastapi']
        
        try:
            # 模拟ImportError
            with patch('builtins.__import__', side_effect=ImportError):
                assert MonitorFactory._is_fastapi_available() == False
        finally:
            sys.modules.update(modules_backup)