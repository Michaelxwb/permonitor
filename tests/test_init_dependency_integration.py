"""
包初始化依赖集成测试模块
"""

import pytest
from unittest.mock import patch, MagicMock
import logging

import web_performance_monitor


class TestInitDependencyIntegration:
    """包初始化依赖集成测试"""
    
    def test_check_dependencies_success(self):
        """测试依赖检查成功"""
        with patch('web_performance_monitor.DependencyManager') as mock_manager_class:
            mock_manager = MagicMock()
            mock_report = MagicMock()
            mock_report.supported_frameworks = ['flask', 'fastapi']
            mock_report.available_frameworks = ['flask']
            mock_report.recommendations = ['Install FastAPI']
            mock_report.warnings = []
            mock_report.get_summary.return_value = {'status': 'partial'}
            
            mock_manager.check_dependencies.return_value = mock_report
            mock_manager_class.return_value = mock_manager
            
            result = web_performance_monitor.check_dependencies()
            
            assert 'supported_frameworks' in result
            assert 'available_frameworks' in result
            assert 'recommendations' in result
            assert 'warnings' in result
            assert 'summary' in result
            
            assert result['supported_frameworks'] == ['flask', 'fastapi']
            assert result['available_frameworks'] == ['flask']
    
    def test_check_dependencies_manager_unavailable(self):
        """测试依赖管理器不可用时的检查"""
        with patch('web_performance_monitor.DependencyManager', None):
            result = web_performance_monitor.check_dependencies()
            
            assert 'error' in result
            assert '依赖管理功能不可用' in result['error']
            assert 'suggestion' in result
    
    def test_check_dependencies_exception(self):
        """测试依赖检查时发生异常"""
        with patch('web_performance_monitor.DependencyManager') as mock_manager_class:
            mock_manager_class.side_effect = Exception("Test error")
            
            result = web_performance_monitor.check_dependencies()
            
            assert 'error' in result
            assert 'Test error' in result['error']
            assert 'suggestion' in result
    
    def test_get_supported_frameworks_success(self):
        """测试获取支持框架成功"""
        with patch('web_performance_monitor.DependencyManager') as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.get_supported_frameworks.return_value = ['flask', 'fastapi']
            mock_manager_class.return_value = mock_manager
            
            result = web_performance_monitor.get_supported_frameworks()
            
            assert result == ['flask', 'fastapi']
    
    def test_get_supported_frameworks_manager_unavailable(self):
        """测试依赖管理器不可用时获取支持框架"""
        with patch('web_performance_monitor.DependencyManager', None):
            result = web_performance_monitor.get_supported_frameworks()
            
            assert result == []
    
    def test_get_supported_frameworks_exception(self):
        """测试获取支持框架时发生异常"""
        with patch('web_performance_monitor.DependencyManager') as mock_manager_class:
            mock_manager_class.side_effect = Exception("Test error")
            
            result = web_performance_monitor.get_supported_frameworks()
            
            assert result == []
    
    def test_get_dependency_status_success(self):
        """测试获取依赖状态成功"""
        with patch('web_performance_monitor.MonitorFactory') as mock_factory:
            mock_report = {
                'framework_dependencies': {'flask': 'available'},
                'available_monitors': {'flask': True},
                'summary': {'status': 'complete'}
            }
            mock_factory.get_dependency_status_report.return_value = mock_report
            
            result = web_performance_monitor.get_dependency_status()
            
            assert result == mock_report
    
    def test_get_dependency_status_exception(self):
        """测试获取依赖状态时发生异常"""
        with patch('web_performance_monitor.MonitorFactory') as mock_factory:
            mock_factory.get_dependency_status_report.side_effect = Exception("Test error")
            
            result = web_performance_monitor.get_dependency_status()
            
            assert 'error' in result
            assert 'Test error' in result['error']
            assert 'suggestion' in result
    
    def test_initialize_dependency_status_success(self):
        """测试初始化依赖状态成功"""
        with patch('web_performance_monitor.DependencyManager') as mock_manager_class:
            with patch('web_performance_monitor.FrameworkDetector') as mock_detector_class:
                # 模拟依赖管理器
                mock_manager = MagicMock()
                mock_manager.get_supported_frameworks.return_value = ['flask', 'fastapi']
                mock_manager_class.return_value = mock_manager
                
                # 模拟框架检测器
                mock_detector = MagicMock()
                mock_detector.detect_installed_frameworks.return_value = ['flask']
                mock_detector_class.return_value = mock_detector
                
                # 重新导入模块以触发初始化
                import importlib
                importlib.reload(web_performance_monitor)
                
                # 验证调用
                mock_manager.get_supported_frameworks.assert_called()
                mock_detector.detect_installed_frameworks.assert_called()
    
    def test_initialize_dependency_status_no_manager(self):
        """测试依赖管理器不可用时的初始化"""
        with patch('web_performance_monitor.DependencyManager', None):
            with patch('logging.getLogger') as mock_logger:
                mock_log = MagicMock()
                mock_logger.return_value = mock_log
                
                # 调用初始化函数
                web_performance_monitor._initialize_dependency_status()
                
                # 验证警告日志
                mock_log.warning.assert_called_with("依赖管理功能不可用，某些高级功能可能无法使用")
    
    def test_initialize_dependency_status_exception(self):
        """测试初始化时发生异常"""
        with patch('web_performance_monitor.DependencyManager') as mock_manager_class:
            mock_manager_class.side_effect = Exception("Test error")
            
            with patch('logging.getLogger') as mock_logger:
                mock_log = MagicMock()
                mock_logger.return_value = mock_log
                
                # 调用初始化函数
                web_performance_monitor._initialize_dependency_status()
                
                # 验证调试日志
                mock_log.debug.assert_called()
                debug_call_args = mock_log.debug.call_args[0][0]
                assert "初始化依赖检查时出错" in debug_call_args
    
    def test_safe_imports_flask_monitor(self):
        """测试Flask监控器的安全导入"""
        # 这个测试验证即使导入失败，模块也能正常加载
        with patch('web_performance_monitor.monitors.flask_monitor', side_effect=ImportError("No Flask")):
            import importlib
            
            # 重新导入应该不会抛出异常
            try:
                importlib.reload(web_performance_monitor)
                # 验证FlaskMonitor被设置为None
                assert web_performance_monitor.FlaskMonitor is None
            except ImportError:
                pytest.fail("安全导入失败，不应该抛出ImportError")
    
    def test_safe_imports_fastapi_monitor(self):
        """测试FastAPI监控器的安全导入"""
        with patch('web_performance_monitor.monitors.fastapi_monitor', side_effect=ImportError("No FastAPI")):
            import importlib
            
            try:
                importlib.reload(web_performance_monitor)
                assert web_performance_monitor.FastAPIMonitor is None
            except ImportError:
                pytest.fail("安全导入失败，不应该抛出ImportError")
    
    def test_safe_imports_dependency_management(self):
        """测试依赖管理模块的安全导入"""
        with patch('web_performance_monitor.utils.dependency_manager', side_effect=ImportError("No dependency manager")):
            import importlib
            
            try:
                importlib.reload(web_performance_monitor)
                assert web_performance_monitor.DependencyManager is None
                assert web_performance_monitor.RuntimeDependencyChecker is None
                assert web_performance_monitor.GracefulDegradation is None
            except ImportError:
                pytest.fail("安全导入失败，不应该抛出ImportError")
    
    def test_all_exports_available(self):
        """测试所有导出的符号都可用"""
        # 获取__all__中定义的所有符号
        all_symbols = web_performance_monitor.__all__
        
        for symbol in all_symbols:
            # 验证符号存在于模块中
            assert hasattr(web_performance_monitor, symbol), f"Symbol {symbol} not found in module"
            
            # 获取符号值
            value = getattr(web_performance_monitor, symbol)
            
            # 验证符号不是None（除非是可选的依赖管理功能）
            dependency_symbols = [
                'DependencyManager', 'RuntimeDependencyChecker', 'GracefulDegradation',
                'FeatureGate', 'DependencyStatus', 'EnvironmentReport', 'DependencyConfig'
            ]
            
            if symbol in dependency_symbols:
                # 依赖管理符号可能为None
                pass
            else:
                assert value is not None, f"Symbol {symbol} is None"