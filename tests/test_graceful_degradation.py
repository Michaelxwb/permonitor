"""
优雅降级机制测试模块
"""

import pytest
import warnings
from unittest.mock import patch, MagicMock

from web_performance_monitor.utils.graceful_degradation import (
    GracefulDegradation,
    require_framework,
    require_feature,
    FeatureGate
)
from web_performance_monitor.exceptions.exceptions import MissingDependencyError


class TestGracefulDegradation:
    """优雅降级测试类"""
    
    def setup_method(self):
        """测试方法设置"""
        # 清除缓存
        GracefulDegradation.clear_feature_cache()
    
    def test_handle_missing_framework_warn(self):
        """测试警告模式处理缺失框架"""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            result = GracefulDegradation.handle_missing_framework("flask", "warn")
            
            assert result is True
            assert len(w) > 0
            assert "Framework flask is not available" in str(w[0].message)
    
    def test_handle_missing_framework_error(self):
        """测试错误模式处理缺失框架"""
        result = GracefulDegradation.handle_missing_framework("flask", "error")
        assert result is False
    
    def test_handle_missing_framework_silent(self):
        """测试静默模式处理缺失框架"""
        result = GracefulDegradation.handle_missing_framework("flask", "silent")
        assert result is True
    
    def test_provide_limited_functionality_full(self):
        """测试提供完整功能时的状态"""
        all_features = [
            "flask_middleware", "flask_decorator", "fastapi_middleware",
            "async_monitoring", "mattermost_notifications", 
            "file_notifications", "performance_analysis"
        ]
        
        status = GracefulDegradation.provide_limited_functionality(all_features)
        
        assert status["functionality_level"] == 1.0
        assert len(status["unavailable_features"]) == 0
        assert len(status["recommendations"]) == 0
    
    def test_provide_limited_functionality_partial(self):
        """测试提供部分功能时的状态"""
        available_features = ["file_notifications", "performance_analysis"]
        
        status = GracefulDegradation.provide_limited_functionality(available_features)
        
        assert status["functionality_level"] < 1.0
        assert len(status["unavailable_features"]) > 0
        assert len(status["recommendations"]) > 0
        
        # 检查是否有Flask和FastAPI的安装建议
        recommendations_text = " ".join(status["recommendations"])
        assert "Flask" in recommendations_text or "flask" in recommendations_text
        assert "FastAPI" in recommendations_text or "fastapi" in recommendations_text
    
    @patch('web_performance_monitor.utils.graceful_degradation.importlib.import_module')
    def test_handle_missing_notification_deps_available(self, mock_import):
        """测试通知依赖可用时的处理"""
        mock_import.return_value = MagicMock()  # 模拟成功导入
        
        status = GracefulDegradation.handle_missing_notification_deps()
        
        assert status["mattermost"] is True
        assert status["file"] is True
        assert status["console"] is True
    
    @patch('web_performance_monitor.utils.graceful_degradation.importlib.import_module')
    def test_handle_missing_notification_deps_missing(self, mock_import):
        """测试通知依赖缺失时的处理"""
        mock_import.side_effect = ImportError("No module named 'mattermostdriver'")
        
        status = GracefulDegradation.handle_missing_notification_deps()
        
        assert status["mattermost"] is False
        assert status["file"] is True
        assert status["console"] is True
    
    @patch.object(GracefulDegradation, '_feature_availability_cache', {})
    @patch('web_performance_monitor.utils.graceful_degradation.FrameworkDetector')
    def test_check_feature_availability_flask(self, mock_detector_class):
        """测试检查Flask功能可用性"""
        mock_detector = MagicMock()
        mock_detector.is_framework_available.return_value = True
        mock_detector_class.return_value = mock_detector
        
        result = GracefulDegradation.check_feature_availability("flask_middleware")
        
        assert result is True
        mock_detector.is_framework_available.assert_called_with("flask")
    
    @patch.object(GracefulDegradation, '_feature_availability_cache', {})
    @patch('web_performance_monitor.utils.graceful_degradation.FrameworkDetector')
    def test_check_feature_availability_fastapi_with_async_deps(self, mock_detector_class):
        """测试检查FastAPI异步功能可用性"""
        mock_detector = MagicMock()
        mock_detector.is_framework_available.return_value = True
        mock_detector.check_fastapi_async_dependencies.return_value = {
            'uvicorn': True,
            'aiofiles': True,
            'aiohttp': True
        }
        mock_detector_class.return_value = mock_detector
        
        result = GracefulDegradation.check_feature_availability("async_monitoring")
        
        assert result is True
        mock_detector.check_fastapi_async_dependencies.assert_called_once()
    
    @patch.object(GracefulDegradation, '_feature_availability_cache', {})
    @patch('web_performance_monitor.utils.graceful_degradation.FrameworkDetector')
    def test_check_feature_availability_fastapi_missing_async_deps(self, mock_detector_class):
        """测试FastAPI异步依赖缺失时的功能可用性"""
        mock_detector = MagicMock()
        mock_detector.is_framework_available.return_value = True
        mock_detector.check_fastapi_async_dependencies.return_value = {
            'uvicorn': True,
            'aiofiles': False,  # 缺失
            'aiohttp': True
        }
        mock_detector_class.return_value = mock_detector
        
        result = GracefulDegradation.check_feature_availability("async_monitoring")
        
        assert result is False
    
    def test_check_feature_availability_always_available(self):
        """测试总是可用的功能"""
        always_available = ["file_notifications", "console_notifications", "performance_analysis"]
        
        for feature in always_available:
            result = GracefulDegradation.check_feature_availability(feature)
            assert result is True
    
    def test_check_feature_availability_cache(self):
        """测试功能可用性缓存"""
        # 设置缓存
        GracefulDegradation._feature_availability_cache["test_feature"] = True
        
        result = GracefulDegradation.check_feature_availability("test_feature")
        assert result is True
        
        # 清除缓存
        GracefulDegradation.clear_feature_cache()
        assert len(GracefulDegradation._feature_availability_cache) == 0
    
    def test_get_degraded_config_with_notifications(self):
        """测试获取降级配置（包含通知）"""
        original_config = {
            "notifications": [
                {"type": "mattermost", "webhook": "url"},
                {"type": "file", "path": "/tmp/log"},
                {"type": "console"}
            ]
        }
        
        with patch.object(GracefulDegradation, 'handle_missing_notification_deps') as mock_handle:
            mock_handle.return_value = {
                "mattermost": False,  # 不可用
                "file": True,
                "console": True
            }
            
            degraded_config = GracefulDegradation.get_degraded_config(original_config)
            
            # 应该只保留可用的通知类型
            assert len(degraded_config["notifications"]) == 2
            notification_types = [n.get("type") for n in degraded_config["notifications"]]
            assert "file" in notification_types
            assert "console" in notification_types
            assert "mattermost" not in notification_types


class TestRequireFrameworkDecorator:
    """require_framework装饰器测试"""
    
    @patch('web_performance_monitor.utils.graceful_degradation.FrameworkDetector')
    def test_require_framework_available(self, mock_detector_class):
        """测试框架可用时的装饰器行为"""
        mock_detector = MagicMock()
        mock_detector.is_framework_available.return_value = True
        mock_detector_class.return_value = mock_detector
        
        @require_framework("flask")
        def test_function():
            return "success"
        
        result = test_function()
        assert result == "success"
    
    @patch('web_performance_monitor.utils.graceful_degradation.FrameworkDetector')
    @patch.object(GracefulDegradation, 'handle_missing_framework')
    def test_require_framework_missing_warn(self, mock_handle, mock_detector_class):
        """测试框架缺失时的警告模式"""
        mock_detector = MagicMock()
        mock_detector.is_framework_available.return_value = False
        mock_detector_class.return_value = mock_detector
        mock_handle.return_value = True  # 可以继续执行
        
        @require_framework("flask", "warn")
        def test_function():
            return "success"
        
        result = test_function()
        assert result is None  # 降级模式返回None
        mock_handle.assert_called_with("flask", "warn")
    
    @patch('web_performance_monitor.utils.graceful_degradation.FrameworkDetector')
    @patch.object(GracefulDegradation, 'handle_missing_framework')
    def test_require_framework_missing_error(self, mock_handle, mock_detector_class):
        """测试框架缺失时的错误模式"""
        mock_detector = MagicMock()
        mock_detector.is_framework_available.return_value = False
        mock_detector_class.return_value = mock_detector
        mock_handle.return_value = False  # 不能继续执行
        
        @require_framework("flask", "error")
        def test_function():
            return "success"
        
        with pytest.raises(MissingDependencyError):
            test_function()


class TestRequireFeatureDecorator:
    """require_feature装饰器测试"""
    
    @patch.object(GracefulDegradation, 'check_feature_availability')
    def test_require_feature_available(self, mock_check):
        """测试功能可用时的装饰器行为"""
        mock_check.return_value = True
        
        @require_feature("flask_middleware")
        def test_function():
            return "success"
        
        result = test_function()
        assert result == "success"
    
    @patch.object(GracefulDegradation, 'check_feature_availability')
    def test_require_feature_unavailable(self, mock_check):
        """测试功能不可用时的装饰器行为"""
        mock_check.return_value = False
        
        @require_feature("flask_middleware", "fallback_value")
        def test_function():
            return "success"
        
        result = test_function()
        assert result == "fallback_value"


class TestFeatureGate:
    """功能门控测试"""
    
    def setup_method(self):
        """测试方法设置"""
        self.gate = FeatureGate()
    
    @patch.object(GracefulDegradation, 'check_feature_availability')
    def test_is_enabled_auto_detect(self, mock_check):
        """测试自动检测功能状态"""
        mock_check.return_value = True
        
        result = self.gate.is_enabled("flask_middleware")
        assert result is True
        mock_check.assert_called_with("flask_middleware")
    
    def test_enable_disable_feature(self):
        """测试手动启用/禁用功能"""
        # 启用功能
        self.gate.enable_feature("test_feature")
        assert self.gate.is_enabled("test_feature") is True
        
        # 禁用功能
        self.gate.disable_feature("test_feature")
        assert self.gate.is_enabled("test_feature") is False
    
    @patch.object(GracefulDegradation, 'check_feature_availability')
    def test_reset_feature(self, mock_check):
        """测试重置功能状态"""
        mock_check.return_value = True
        
        # 手动设置功能状态
        self.gate.disable_feature("test_feature")
        assert self.gate.is_enabled("test_feature") is False
        
        # 重置为自动检测
        self.gate.reset_feature("test_feature")
        assert self.gate.is_enabled("test_feature") is True
        mock_check.assert_called_with("test_feature")
    
    @patch.object(FeatureGate, 'is_enabled')
    def test_get_available_features(self, mock_is_enabled):
        """测试获取可用功能列表"""
        # 模拟部分功能可用
        def mock_enabled_side_effect(feature):
            return feature in ["flask_middleware", "file_notifications"]
        
        mock_is_enabled.side_effect = mock_enabled_side_effect
        
        available = self.gate.get_available_features()
        
        assert "flask_middleware" in available
        assert "file_notifications" in available
        assert len(available) == 2
    
    @patch.object(FeatureGate, 'is_enabled')
    @patch.object(FeatureGate, '_get_unavailability_reason')
    def test_get_feature_report(self, mock_reason, mock_is_enabled):
        """测试获取功能报告"""
        # 模拟功能状态
        def mock_enabled_side_effect(feature):
            return feature == "flask_middleware"
        
        mock_is_enabled.side_effect = mock_enabled_side_effect
        mock_reason.return_value = "Flask framework not installed"
        
        report = self.gate.get_feature_report()
        
        assert "available_features" in report
        assert "unavailable_features" in report
        assert "feature_details" in report
        
        assert "flask_middleware" in report["available_features"]
        assert len(report["unavailable_features"]) > 0
        
        # 检查功能详情
        flask_detail = report["feature_details"]["flask_middleware"]
        assert flask_detail["available"] is True
        assert flask_detail["reason"] is None
    
    @patch('web_performance_monitor.utils.graceful_degradation.FrameworkDetector')
    def test_get_unavailability_reason_flask(self, mock_detector_class):
        """测试获取Flask功能不可用原因"""
        mock_detector = MagicMock()
        mock_detector.is_framework_available.return_value = False
        self.gate.detector = mock_detector
        
        reason = self.gate._get_unavailability_reason("flask_middleware")
        assert reason == "Flask framework not installed"
    
    @patch('web_performance_monitor.utils.graceful_degradation.FrameworkDetector')
    def test_get_unavailability_reason_fastapi_async_deps(self, mock_detector_class):
        """测试获取FastAPI异步依赖不可用原因"""
        mock_detector = MagicMock()
        mock_detector.is_framework_available.return_value = True
        mock_detector.check_fastapi_async_dependencies.return_value = {
            'uvicorn': True,
            'aiofiles': False,
            'aiohttp': False
        }
        self.gate.detector = mock_detector
        
        reason = self.gate._get_unavailability_reason("async_monitoring")
        assert "Missing async dependencies" in reason
        assert "aiofiles" in reason
        assert "aiohttp" in reason