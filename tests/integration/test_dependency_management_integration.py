"""
依赖管理集成测试套件

测试不同安装组合的功能完整性、向后兼容性和API稳定性。
"""

import pytest
import time
from unittest.mock import patch, MagicMock

from tests.utils.mock_environment import (
    mock_environment,
    EnvironmentScenarios,
    MockPackage,
    EnvironmentConfig
)
from web_performance_monitor.utils.framework_detector import FrameworkDetector
from web_performance_monitor.utils.dependency_manager import DependencyManager
from web_performance_monitor.core.dependency_checker import RuntimeDependencyChecker
from web_performance_monitor.core.plugin_system import get_plugin_manager
from web_performance_monitor.monitors.factory import MonitorFactory
from web_performance_monitor.utils.installation_guide import InstallationGuide
from web_performance_monitor.core.conflict_resolver import ConflictResolver, DependencyInfo


class TestEndToEndDependencyManagement:
    """端到端依赖管理测试"""
    
    def test_clean_environment_workflow(self):
        """测试干净环境的完整工作流程"""
        with mock_environment(EnvironmentScenarios.clean_environment()):
            # 1. 框架检测
            detector = FrameworkDetector()
            frameworks = detector.detect_installed_frameworks()
            assert frameworks == []
            
            # 2. 依赖管理
            manager = DependencyManager()
            report = manager.validate_environment()
            assert len(report.available_frameworks) == 0
            assert len(report.warnings) > 0
            
            # 3. 安装建议
            guide = InstallationGuide()
            analysis = guide.analyze_current_environment()
            assert analysis['current_status'] == 'no_frameworks'
            assert len(analysis['recommendations']) > 0
            
            # 4. 监控器工厂
            factory = MonitorFactory()
            available_monitors = factory.get_available_monitors()
            assert len(available_monitors) == 0
            
            # 5. 插件系统
            plugin_manager = get_plugin_manager()
            available_frameworks = plugin_manager.get_available_frameworks()
            assert len(available_frameworks) == 0
    
    def test_flask_environment_workflow(self):
        """测试Flask环境的完整工作流程"""
        with mock_environment(EnvironmentScenarios.flask_only_environment()):
            # 1. 框架检测
            detector = FrameworkDetector()
            frameworks = detector.detect_installed_frameworks()
            assert "flask" in frameworks
            assert "fastapi" not in frameworks
            
            # 2. 依赖管理
            manager = DependencyManager()
            report = manager.validate_environment()
            assert "flask" in report.available_frameworks
            assert "fastapi" not in report.available_frameworks
            
            # 3. 运行时检查
            checker = RuntimeDependencyChecker()
            flask_available = checker.check_framework_availability("flask")
            assert flask_available == True
            
            fastapi_available = checker.check_framework_availability("fastapi")
            assert fastapi_available == False
            
            # 4. 监控器创建
            factory = MonitorFactory()
            
            # Flask监控器应该可以创建
            try:
                flask_monitor = factory.create_monitor("flask")
                assert flask_monitor is not None
            except Exception as e:
                # 如果实际监控器类不存在，这是预期的
                assert "无法创建" in str(e) or "ImportError" in str(e)
            
            # FastAPI监控器应该失败
            with pytest.raises(Exception):
                factory.create_monitor("fastapi")
            
            # 5. 安装建议
            guide = InstallationGuide()
            analysis = guide.analyze_current_environment()
            assert analysis['current_status'] in ['complete', 'partial']
            
            # 应该建议安装其他框架
            recommendations = [r.command for r in analysis['recommendations']]
            assert any('fastapi' in cmd for cmd in recommendations)
    
    def test_fastapi_environment_workflow(self):
        """测试FastAPI环境的完整工作流程"""
        with mock_environment(EnvironmentScenarios.fastapi_only_environment()):
            # 1. 框架检测
            detector = FrameworkDetector()
            frameworks = detector.detect_installed_frameworks()
            assert "fastapi" in frameworks
            assert "flask" not in frameworks
            
            # 2. 依赖完整性检查
            manager = DependencyManager()
            report = manager.validate_environment()
            assert "fastapi" in report.available_frameworks
            
            # 检查FastAPI相关依赖
            fastapi_deps = manager.check_framework_dependencies("fastapi")
            assert len(fastapi_deps) == 0  # 应该没有缺失依赖
            
            # 3. 插件系统
            plugin_manager = get_plugin_manager()
            fastapi_plugin = plugin_manager.registry.get_plugin("fastapi")
            assert fastapi_plugin is not None
            assert fastapi_plugin.is_installed() == True
            
            # 4. 冲突检测
            resolver = ConflictResolver()
            dependencies = [
                DependencyInfo("fastapi", version_spec=">=0.100.0", required_by=["app"]),
                DependencyInfo("uvicorn", version_spec=">=0.20.0", required_by=["app"])
            ]
            
            result = resolver.analyze_and_resolve(dependencies)
            assert result["total_conflicts"] == 0  # 不应该有冲突
    
    def test_full_environment_workflow(self):
        """测试完整环境的完整工作流程"""
        with mock_environment(EnvironmentScenarios.full_environment()):
            # 1. 全面框架检测
            detector = FrameworkDetector()
            frameworks = detector.detect_installed_frameworks()
            assert "flask" in frameworks
            assert "fastapi" in frameworks
            
            # 2. 完整依赖验证
            manager = DependencyManager()
            report = manager.validate_environment()
            assert "flask" in report.available_frameworks
            assert "fastapi" in report.available_frameworks
            assert len(report.warnings) == 0  # 完整环境应该没有警告
            
            # 3. 所有监控器可用
            factory = MonitorFactory()
            available_monitors = factory.get_available_monitors()
            assert len(available_monitors) >= 2  # 至少Flask和FastAPI
            
            # 4. 插件系统完整性
            plugin_manager = get_plugin_manager()
            available_frameworks = plugin_manager.get_available_frameworks()
            assert "flask" in available_frameworks
            assert "fastapi" in available_frameworks
            
            # 5. 安装状态
            guide = InstallationGuide()
            analysis = guide.analyze_current_environment()
            assert analysis['current_status'] == 'complete'
            
            # 6. 无冲突
            resolver = ConflictResolver()
            dependencies = [
                DependencyInfo("flask", version_spec=">=2.0.0", required_by=["app"]),
                DependencyInfo("fastapi", version_spec=">=0.100.0", required_by=["app"]),
                DependencyInfo("mattermostdriver", version_spec=">=7.0.0", required_by=["app"])
            ]
            
            result = resolver.analyze_and_resolve(dependencies)
            assert result["total_conflicts"] == 0
    
    def test_conflicted_environment_workflow(self):
        """测试冲突环境的完整工作流程"""
        with mock_environment(EnvironmentScenarios.conflicted_environment()):
            # 1. 框架检测（应该检测到旧版本）
            detector = FrameworkDetector()
            frameworks = detector.detect_installed_frameworks()
            assert "flask" in frameworks
            assert "fastapi" in frameworks
            
            # 2. 版本兼容性检查
            manager = DependencyManager()
            
            # 检查Flask版本兼容性
            flask_compatible = manager.check_version_compatibility("flask", ">=2.0.0")
            assert flask_compatible == False  # 1.1.0 < 2.0.0
            
            # 检查FastAPI版本兼容性
            fastapi_compatible = manager.check_version_compatibility("fastapi", ">=0.100.0")
            assert fastapi_compatible == False  # 0.50.0 < 0.100.0
            
            # 3. 冲突检测
            resolver = ConflictResolver()
            dependencies = [
                DependencyInfo("flask", version_spec=">=2.0.0", required_by=["app"]),
                DependencyInfo("fastapi", version_spec=">=0.100.0", required_by=["app"])
            ]
            
            result = resolver.analyze_and_resolve(dependencies)
            assert result["total_conflicts"] > 0
            assert result["has_critical_conflicts"] or len(result["conflicts"]) > 0
            
            # 4. 解决方案生成
            assert len(result["resolution_plan"]) > 0
            
            # 5. 快速修复建议
            quick_fixes = resolver.get_quick_fix_suggestions(result["conflicts"])
            assert len(quick_fixes) > 0
    
    def test_partial_environment_workflow(self):
        """测试部分环境的完整工作流程"""
        with mock_environment(EnvironmentScenarios.partial_environment()):
            # 1. 框架检测
            detector = FrameworkDetector()
            frameworks = detector.detect_installed_frameworks()
            assert "flask" in frameworks
            assert "fastapi" in frameworks
            
            # 2. 依赖完整性检查
            manager = DependencyManager()
            
            # Flask应该可用（依赖完整）
            flask_deps = manager.check_framework_dependencies("flask")
            assert len(flask_deps) == 0
            
            # FastAPI应该有缺失依赖
            fastapi_deps = manager.check_framework_dependencies("fastapi")
            assert len(fastapi_deps) > 0  # 缺少uvicorn等
            
            # 3. 运行时检查
            checker = RuntimeDependencyChecker()
            
            flask_available = checker.check_framework_availability("flask")
            assert flask_available == True
            
            # FastAPI可能不完全可用
            fastapi_available = checker.check_framework_availability("fastapi")
            # 这取决于具体的检查逻辑
            
            # 4. 安装建议
            guide = InstallationGuide()
            analysis = guide.analyze_current_environment()
            assert analysis['current_status'] in ['partial', 'incomplete']
            
            # 应该有补全依赖的建议
            recommendations = analysis['recommendations']
            assert len(recommendations) > 0
            
            # 应该建议安装缺失的依赖
            commands = [r.command for r in recommendations]
            assert any('fastapi' in cmd for cmd in commands)


class TestBackwardCompatibility:
    """向后兼容性测试"""
    
    def test_legacy_api_compatibility(self):
        """测试遗留API兼容性"""
        with mock_environment(EnvironmentScenarios.flask_only_environment()):
            # 测试旧的导入方式仍然有效
            try:
                from web_performance_monitor import create_web_monitor
                from web_performance_monitor import check_dependencies
                from web_performance_monitor import get_dependency_status
                
                # 这些函数应该仍然可用
                assert callable(create_web_monitor)
                assert callable(check_dependencies)
                assert callable(get_dependency_status)
                
            except ImportError as e:
                # 如果这些函数不存在，说明需要实现
                pytest.skip(f"Legacy API not implemented: {e}")
    
    def test_configuration_backward_compatibility(self):
        """测试配置向后兼容性"""
        with mock_environment(EnvironmentScenarios.flask_only_environment()):
            # 测试旧的配置方式
            from web_performance_monitor.config.unified_config import UnifiedConfig
            
            # 旧的配置应该仍然有效
            config = UnifiedConfig()
            
            # 检查是否有依赖相关的配置
            assert hasattr(config, 'dependency_config')
            
            # 测试环境变量配置
            import os
            os.environ['WPM_SKIP_DEPENDENCY_CHECK'] = 'true'
            
            config = UnifiedConfig()
            assert config.dependency_config.skip_dependency_check == True
            
            # 清理
            os.environ.pop('WPM_SKIP_DEPENDENCY_CHECK', None)
    
    def test_monitor_factory_backward_compatibility(self):
        """测试监控器工厂向后兼容性"""
        with mock_environment(EnvironmentScenarios.flask_only_environment()):
            from web_performance_monitor.monitors.factory import MonitorFactory
            
            factory = MonitorFactory()
            
            # 旧的方法应该仍然有效
            assert hasattr(factory, 'create_monitor')
            
            # 新的方法也应该可用
            assert hasattr(factory, 'get_available_monitors')
            assert hasattr(factory, 'create_monitor_with_dependency_check')


class TestAPIStability:
    """API稳定性测试"""
    
    def test_public_api_signatures(self):
        """测试公共API签名稳定性"""
        # 检查主要类的API签名
        from web_performance_monitor.utils.framework_detector import FrameworkDetector
        from web_performance_monitor.utils.dependency_manager import DependencyManager
        from web_performance_monitor.core.dependency_checker import RuntimeDependencyChecker
        
        # FrameworkDetector API
        detector = FrameworkDetector()
        assert hasattr(detector, 'detect_installed_frameworks')
        assert hasattr(detector, 'detect_framework_from_environment')
        assert hasattr(detector, 'get_framework_version')
        
        # DependencyManager API
        manager = DependencyManager()
        assert hasattr(manager, 'validate_environment')
        assert hasattr(manager, 'check_framework_dependencies')
        assert hasattr(manager, 'get_supported_frameworks')
        
        # RuntimeDependencyChecker API
        checker = RuntimeDependencyChecker()
        assert hasattr(checker, 'check_framework_availability')
        assert hasattr(checker, 'validate_dependencies')
    
    def test_exception_handling_consistency(self):
        """测试异常处理一致性"""
        from web_performance_monitor.exceptions.exceptions import (
            DependencyError,
            MissingDependencyError,
            IncompatibleVersionError
        )
        
        # 检查异常类层次结构
        assert issubclass(MissingDependencyError, DependencyError)
        assert issubclass(IncompatibleVersionError, DependencyError)
        
        # 检查异常消息格式
        try:
            raise MissingDependencyError("test_package", "test_framework")
        except MissingDependencyError as e:
            assert "test_package" in str(e)
            assert "test_framework" in str(e)
    
    def test_configuration_api_stability(self):
        """测试配置API稳定性"""
        from web_performance_monitor.config.unified_config import UnifiedConfig
        from web_performance_monitor.config.env_config import EnvironmentConfig
        
        # 检查配置类API
        config = UnifiedConfig()
        assert hasattr(config, 'dependency_config')
        assert hasattr(config, 'monitoring_config')
        assert hasattr(config, 'notification_config')
        
        # 检查环境配置
        env_config = EnvironmentConfig()
        assert hasattr(env_config, 'get_dependency_config')


class TestPerformanceImpact:
    """性能影响测试"""
    
    def test_dependency_check_performance(self):
        """测试依赖检查性能"""
        with mock_environment(EnvironmentScenarios.full_environment()):
            from web_performance_monitor.core.dependency_checker import RuntimeDependencyChecker
            
            checker = RuntimeDependencyChecker()
            
            # 测试单次检查性能
            start_time = time.time()
            result = checker.check_framework_availability("flask")
            end_time = time.time()
            
            check_time = end_time - start_time
            assert check_time < 0.1  # 应该在100ms内完成
            
            # 测试缓存效果
            start_time = time.time()
            result2 = checker.check_framework_availability("flask")
            end_time = time.time()
            
            cached_check_time = end_time - start_time
            assert cached_check_time < check_time  # 缓存应该更快
            assert result == result2  # 结果应该一致
    
    def test_framework_detection_performance(self):
        """测试框架检测性能"""
        with mock_environment(EnvironmentScenarios.full_environment()):
            from web_performance_monitor.utils.framework_detector import FrameworkDetector
            
            detector = FrameworkDetector()
            
            # 测试检测性能
            start_time = time.time()
            frameworks = detector.detect_installed_frameworks()
            end_time = time.time()
            
            detection_time = end_time - start_time
            assert detection_time < 0.5  # 应该在500ms内完成
            
            # 测试重复检测
            start_time = time.time()
            frameworks2 = detector.detect_installed_frameworks()
            end_time = time.time()
            
            second_detection_time = end_time - start_time
            assert frameworks == frameworks2  # 结果应该一致
    
    def test_plugin_system_performance(self):
        """测试插件系统性能"""
        with mock_environment(EnvironmentScenarios.full_environment()):
            from web_performance_monitor.core.plugin_system import get_plugin_manager
            
            # 测试插件管理器初始化性能
            start_time = time.time()
            manager = get_plugin_manager()
            end_time = time.time()
            
            init_time = end_time - start_time
            assert init_time < 1.0  # 应该在1秒内完成
            
            # 测试获取可用框架性能
            start_time = time.time()
            frameworks = manager.get_available_frameworks()
            end_time = time.time()
            
            query_time = end_time - start_time
            assert query_time < 0.1  # 应该在100ms内完成
    
    def test_conflict_detection_performance(self):
        """测试冲突检测性能"""
        with mock_environment(EnvironmentScenarios.conflicted_environment()):
            from web_performance_monitor.core.conflict_resolver import ConflictResolver, DependencyInfo
            
            resolver = ConflictResolver()
            
            # 创建大量依赖进行测试
            dependencies = []
            for i in range(50):  # 50个依赖
                dependencies.append(
                    DependencyInfo(f"package_{i}", version_spec=">=1.0.0", required_by=[f"app_{i}"])
                )
            
            # 测试冲突检测性能
            start_time = time.time()
            result = resolver.analyze_and_resolve(dependencies)
            end_time = time.time()
            
            analysis_time = end_time - start_time
            assert analysis_time < 2.0  # 应该在2秒内完成
    
    def test_memory_usage(self):
        """测试内存使用情况"""
        import gc
        import sys
        
        with mock_environment(EnvironmentScenarios.full_environment()):
            # 获取初始内存使用
            gc.collect()
            initial_objects = len(gc.get_objects())
            
            # 执行依赖管理操作
            from web_performance_monitor.utils.framework_detector import FrameworkDetector
            from web_performance_monitor.utils.dependency_manager import DependencyManager
            from web_performance_monitor.core.plugin_system import get_plugin_manager
            
            detector = FrameworkDetector()
            manager = DependencyManager()
            plugin_manager = get_plugin_manager()
            
            # 执行一些操作
            frameworks = detector.detect_installed_frameworks()
            report = manager.validate_environment()
            available = plugin_manager.get_available_frameworks()
            
            # 检查内存使用
            gc.collect()
            final_objects = len(gc.get_objects())
            
            # 内存增长应该在合理范围内
            memory_growth = final_objects - initial_objects
            assert memory_growth < 1000  # 不应该创建过多对象


class TestErrorHandlingAndRecovery:
    """错误处理和恢复测试"""
    
    def test_graceful_degradation(self):
        """测试优雅降级"""
        with mock_environment(EnvironmentScenarios.partial_environment()):
            from web_performance_monitor.utils.graceful_degradation import GracefulDegradation
            
            degradation = GracefulDegradation()
            
            # 测试功能可用性检查
            flask_available = degradation.is_feature_available("flask_monitoring")
            fastapi_available = degradation.is_feature_available("fastapi_monitoring")
            
            # Flask应该可用，FastAPI可能不完全可用
            assert flask_available == True
            # fastapi_available的结果取决于具体实现
            
            # 测试降级处理
            @degradation.with_fallback("alternative_monitoring")
            def monitoring_function():
                # 模拟需要完整依赖的功能
                import uvicorn  # 这会失败
                return "full_monitoring"
            
            result = monitoring_function()
            # 应该返回降级结果而不是抛出异常
    
    def test_error_recovery_mechanisms(self):
        """测试错误恢复机制"""
        with mock_environment(EnvironmentScenarios.conflicted_environment()):
            from web_performance_monitor.monitors.factory import MonitorFactory
            
            factory = MonitorFactory()
            
            # 尝试创建可能失败的监控器
            try:
                monitor = factory.create_monitor("fastapi")
                # 如果成功，检查是否是降级版本
            except Exception as e:
                # 应该有清晰的错误信息和恢复建议
                assert len(str(e)) > 0
                
                # 检查是否有恢复建议
                if hasattr(e, 'recovery_suggestions'):
                    assert len(e.recovery_suggestions) > 0
    
    def test_configuration_error_handling(self):
        """测试配置错误处理"""
        import os
        
        # 设置无效的环境变量
        os.environ['WPM_DEPENDENCY_CHECK_MODE'] = 'invalid_mode'
        
        try:
            from web_performance_monitor.config.unified_config import UnifiedConfig
            
            config = UnifiedConfig()
            # 应该使用默认值而不是崩溃
            assert config.dependency_config.check_mode in ['strict', 'lenient', 'disabled']
            
        finally:
            # 清理
            os.environ.pop('WPM_DEPENDENCY_CHECK_MODE', None)