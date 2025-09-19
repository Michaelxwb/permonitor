"""
增强的监控器工厂测试模块
"""

import pytest
from unittest.mock import patch, MagicMock

from web_performance_monitor.monitors.factory import MonitorFactory, create_web_monitor
from web_performance_monitor.config.unified_config import UnifiedConfig
from web_performance_monitor.exceptions.exceptions import (
    MissingDependencyError, 
    FrameworkNotSupportedError
)


class TestEnhancedMonitorFactory:
    """增强的监控器工厂测试类"""
    
    def setup_method(self):
        """测试方法设置"""
        # 清除注册表以确保测试独立性
        MonitorFactory._monitor_registry.clear()
    
    def test_create_monitor_with_dependency_check_success(self):
        """测试依赖检查成功时创建监控器"""
        config = UnifiedConfig()
        
        with patch.object(MonitorFactory, 'detect_framework_with_dependency_check', return_value='flask'):
            with patch.object(MonitorFactory, 'create_monitor') as mock_create:
                with patch('web_performance_monitor.monitors.factory.RuntimeDependencyChecker') as mock_checker_class:
                    mock_checker = MagicMock()
                    mock_checker.validate_framework_usage.return_value = True
                    mock_checker_class.return_value = mock_checker
                    
                    mock_monitor = MagicMock()
                    mock_create.return_value = mock_monitor
                    
                    result = MonitorFactory.create_monitor_with_dependency_check(config)
                    
                    assert result == mock_monitor
                    mock_checker.validate_framework_usage.assert_called_once()
                    mock_create.assert_called_once_with(config, 'flask')
    
    def test_create_monitor_with_dependency_check_strict_mode_failure(self):
        """测试严格模式下依赖检查失败"""
        config = UnifiedConfig()
        
        with patch.object(MonitorFactory, 'detect_framework_with_dependency_check', return_value='flask'):
            with patch('web_performance_monitor.monitors.factory.RuntimeDependencyChecker') as mock_checker_class:
                mock_checker = MagicMock()
                mock_checker.validate_framework_usage.side_effect = MissingDependencyError('flask', ['flask'])
                mock_checker_class.return_value = mock_checker
                
                with pytest.raises(MissingDependencyError):
                    MonitorFactory.create_monitor_with_dependency_check(config, strict_dependencies=True)
    
    def test_create_monitor_with_dependency_check_non_strict_fallback(self):
        """测试非严格模式下的回退机制"""
        config = UnifiedConfig()
        
        with patch.object(MonitorFactory, 'detect_framework_with_dependency_check', return_value='flask'):
            with patch.object(MonitorFactory, '_create_fallback_monitor') as mock_fallback:
                with patch('web_performance_monitor.monitors.factory.RuntimeDependencyChecker') as mock_checker_class:
                    mock_checker = MagicMock()
                    mock_checker.validate_framework_usage.return_value = False
                    mock_checker_class.return_value = mock_checker
                    
                    mock_fallback_monitor = MagicMock()
                    mock_fallback.return_value = mock_fallback_monitor
                    
                    result = MonitorFactory.create_monitor_with_dependency_check(config, strict_dependencies=False)
                    
                    assert result == mock_fallback_monitor
                    mock_fallback.assert_called_once_with(config)
    
    def test_create_monitor_with_dependency_check_framework_detection_failure(self):
        """测试框架检测失败时的处理"""
        config = UnifiedConfig()
        
        with patch.object(MonitorFactory, 'detect_framework_with_dependency_check', side_effect=RuntimeError("No framework")):
            with patch.object(MonitorFactory, '_create_fallback_monitor') as mock_fallback:
                with patch('web_performance_monitor.monitors.factory.RuntimeDependencyChecker'):
                    mock_fallback_monitor = MagicMock()
                    mock_fallback.return_value = mock_fallback_monitor
                    
                    # 非严格模式应该使用回退监控器
                    result = MonitorFactory.create_monitor_with_dependency_check(config, strict_dependencies=False)
                    assert result == mock_fallback_monitor
                    
                    # 严格模式应该抛出异常
                    with pytest.raises(RuntimeError):
                        MonitorFactory.create_monitor_with_dependency_check(config, strict_dependencies=True)
    
    def test_get_available_monitors(self):
        """测试获取可用监控器"""
        # 模拟注册监控器
        MonitorFactory._monitor_registry = {'flask': MagicMock, 'fastapi': MagicMock}
        
        with patch('web_performance_monitor.monitors.factory.RuntimeDependencyChecker') as mock_checker_class:
            mock_checker = MagicMock()
            mock_checker.check_and_warn.side_effect = lambda framework: framework == 'flask'
            mock_checker_class.return_value = mock_checker
            
            available = MonitorFactory.get_available_monitors()
            
            assert available['flask'] is True
            assert available['fastapi'] is False
    
    def test_get_available_monitors_with_exception(self):
        """测试获取可用监控器时发生异常"""
        MonitorFactory._monitor_registry = {'flask': MagicMock}
        
        with patch('web_performance_monitor.monitors.factory.RuntimeDependencyChecker') as mock_checker_class:
            mock_checker = MagicMock()
            mock_checker.check_and_warn.side_effect = Exception("Test error")
            mock_checker_class.return_value = mock_checker
            
            available = MonitorFactory.get_available_monitors()
            
            assert available['flask'] is False
    
    def test_detect_framework_with_dependency_check_success(self):
        """测试带依赖检查的框架检测成功"""
        mock_checker = MagicMock()
        mock_checker.check_and_warn.return_value = True
        
        with patch('web_performance_monitor.monitors.factory.FrameworkDetector') as mock_detector_class:
            mock_detector_class.detect_framework_from_environment.return_value = 'flask'
            
            result = MonitorFactory.detect_framework_with_dependency_check(mock_checker)
            
            assert result == 'flask'
            mock_checker.check_and_warn.assert_called_once_with('flask')
    
    def test_detect_framework_with_dependency_check_incomplete_deps(self):
        """测试检测到框架但依赖不完整"""
        mock_checker = MagicMock()
        mock_checker.check_and_warn.return_value = False
        
        with patch('web_performance_monitor.monitors.factory.FrameworkDetector') as mock_detector_class:
            with patch.object(MonitorFactory, 'detect_framework', return_value='flask') as mock_detect:
                mock_detector_class.detect_framework_from_environment.return_value = 'flask'
                
                result = MonitorFactory.detect_framework_with_dependency_check(mock_checker)
                
                assert result == 'flask'
                mock_detect.assert_called_once()
    
    def test_detect_framework_with_dependency_check_no_framework(self):
        """测试未检测到框架时的回退"""
        mock_checker = MagicMock()
        
        with patch('web_performance_monitor.monitors.factory.FrameworkDetector') as mock_detector_class:
            with patch.object(MonitorFactory, 'detect_framework', return_value='flask') as mock_detect:
                mock_detector_class.detect_framework_from_environment.return_value = None
                
                result = MonitorFactory.detect_framework_with_dependency_check(mock_checker)
                
                assert result == 'flask'
                mock_detect.assert_called_once()
    
    def test_create_fallback_monitor(self):
        """测试创建回退监控器"""
        config = UnifiedConfig()
        
        with patch('web_performance_monitor.monitors.factory.GracefulDegradation') as mock_degradation:
            with patch('web_performance_monitor.monitors.factory.BaseWebMonitor') as mock_base_monitor:
                mock_degradation.get_degraded_config.return_value = {'test': 'config'}
                mock_monitor_instance = MagicMock()
                mock_base_monitor.return_value = mock_monitor_instance
                
                result = MonitorFactory._create_fallback_monitor(config)
                
                assert result == mock_monitor_instance
                mock_degradation.get_degraded_config.assert_called_once()
                mock_base_monitor.assert_called_once()
    
    def test_get_dependency_status_report(self):
        """测试获取依赖状态报告"""
        with patch('web_performance_monitor.monitors.factory.DependencyManager') as mock_manager_class:
            with patch.object(MonitorFactory, 'get_available_monitors') as mock_available:
                # 模拟依赖管理器
                mock_manager = MagicMock()
                mock_report = MagicMock()
                mock_report.dependency_statuses = {'flask': 'status'}
                mock_report.supported_frameworks = ['flask', 'fastapi']
                mock_report.available_frameworks = ['flask']
                mock_report.recommendations = ['recommendation']
                mock_report.warnings = ['warning']
                mock_report.get_summary.return_value = {'summary': 'data'}
                
                mock_manager.validate_environment.return_value = mock_report
                mock_manager_class.return_value = mock_manager
                
                # 模拟可用监控器
                mock_available.return_value = {'flask': True, 'fastapi': False}
                
                result = MonitorFactory.get_dependency_status_report()
                
                assert 'framework_dependencies' in result
                assert 'available_monitors' in result
                assert 'supported_frameworks' in result
                assert 'available_frameworks' in result
                assert 'recommendations' in result
                assert 'warnings' in result
                assert 'summary' in result
                
                assert result['available_monitors'] == {'flask': True, 'fastapi': False}
    
    def test_suggest_optimal_setup(self):
        """测试建议最优设置"""
        with patch('web_performance_monitor.monitors.factory.DependencyManager') as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.suggest_optimal_installation.return_value = "Install flask support"
            mock_manager_class.return_value = mock_manager
            
            result = MonitorFactory.suggest_optimal_setup()
            
            assert result == "Install flask support"
            mock_manager.suggest_optimal_installation.assert_called_once()
    
    def test_create_monitor_unsupported_framework(self):
        """测试创建不支持的框架监控器"""
        config = UnifiedConfig()
        
        with patch.object(MonitorFactory, 'get_supported_frameworks', return_value=['flask', 'fastapi']):
            with pytest.raises(FrameworkNotSupportedError) as exc_info:
                MonitorFactory.create_monitor(config, 'django')
            
            assert exc_info.value.unsupported_framework == 'django'
            assert exc_info.value.supported_frameworks == ['flask', 'fastapi']


class TestCreateWebMonitor:
    """create_web_monitor函数测试"""
    
    def test_create_web_monitor_with_dependency_check(self):
        """测试带依赖检查的监控器创建"""
        with patch.object(MonitorFactory, 'create_monitor_with_dependency_check') as mock_create:
            mock_monitor = MagicMock()
            mock_create.return_value = mock_monitor
            
            result = create_web_monitor(
                framework='flask',
                config={'test': 'config'},
                check_dependencies=True,
                strict_dependencies=True
            )
            
            assert result == mock_monitor
            mock_create.assert_called_once()
            
            # 检查调用参数
            args, kwargs = mock_create.call_args
            assert args[1] == 'flask'  # framework
            assert args[2] is True     # strict_dependencies
    
    def test_create_web_monitor_without_dependency_check(self):
        """测试不带依赖检查的监控器创建"""
        with patch.object(MonitorFactory, 'create_monitor') as mock_create:
            mock_monitor = MagicMock()
            mock_create.return_value = mock_monitor
            
            result = create_web_monitor(
                framework='flask',
                config={'test': 'config'},
                check_dependencies=False
            )
            
            assert result == mock_monitor
            mock_create.assert_called_once()
    
    def test_create_web_monitor_default_config(self):
        """测试使用默认配置创建监控器"""
        with patch.object(MonitorFactory, 'create_monitor_with_dependency_check') as mock_create:
            with patch('web_performance_monitor.monitors.factory.UnifiedConfig') as mock_config_class:
                mock_config = MagicMock()
                mock_config_class.return_value = mock_config
                mock_monitor = MagicMock()
                mock_create.return_value = mock_monitor
                
                result = create_web_monitor()
                
                assert result == mock_monitor
                mock_config_class.assert_called_once()  # 使用默认配置
                mock_create.assert_called_once()
    
    def test_create_web_monitor_with_dict_config(self):
        """测试使用字典配置创建监控器"""
        config_dict = {'threshold_seconds': 2.0}
        
        with patch.object(MonitorFactory, 'create_monitor_with_dependency_check') as mock_create:
            with patch('web_performance_monitor.monitors.factory.UnifiedConfig') as mock_config_class:
                mock_config = MagicMock()
                mock_config_class.from_dict.return_value = mock_config
                mock_monitor = MagicMock()
                mock_create.return_value = mock_monitor
                
                result = create_web_monitor(config=config_dict)
                
                assert result == mock_monitor
                mock_config_class.from_dict.assert_called_once_with(config_dict)
                mock_create.assert_called_once()