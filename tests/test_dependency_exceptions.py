"""
依赖相关异常测试模块
"""

import pytest

from web_performance_monitor.exceptions.exceptions import (
    DependencyError,
    MissingDependencyError,
    FrameworkNotSupportedError,
    DependencyConflictError,
    DependencyVersionError,
    EnvironmentValidationError,
    PerformanceMonitorError
)


class TestDependencyError:
    """依赖错误基类测试"""
    
    def test_basic_dependency_error(self):
        """测试基本依赖错误"""
        error = DependencyError("Test error message")
        
        assert str(error) == "Test error message"
        assert error.framework is None
        assert error.suggestions == []
        assert isinstance(error, PerformanceMonitorError)
    
    def test_dependency_error_with_framework(self):
        """测试带框架信息的依赖错误"""
        error = DependencyError("Test error", framework="flask")
        
        assert error.framework == "flask"
        assert str(error) == "Test error"
    
    def test_dependency_error_with_suggestions(self):
        """测试带建议的依赖错误"""
        suggestions = ["suggestion 1", "suggestion 2"]
        error = DependencyError("Test error", suggestions=suggestions)
        
        assert error.suggestions == suggestions


class TestMissingDependencyError:
    """缺失依赖错误测试"""
    
    def test_missing_dependency_error_basic(self):
        """测试基本缺失依赖错误"""
        error = MissingDependencyError("flask", ["flask"])
        
        assert error.framework == "flask"
        assert error.missing_packages == ["flask"]
        assert error.installation_command == "pip install web-performance-monitor[flask]"
        assert "Missing dependencies for flask: flask" in str(error)
    
    def test_missing_dependency_error_multiple_packages(self):
        """测试多个缺失包的错误"""
        error = MissingDependencyError("fastapi", ["uvicorn", "aiofiles"])
        
        assert error.missing_packages == ["uvicorn", "aiofiles"]
        assert "uvicorn, aiofiles" in str(error)
    
    def test_missing_dependency_error_custom_command(self):
        """测试自定义安装命令"""
        custom_command = "pip install custom-package"
        error = MissingDependencyError("custom", ["package"], custom_command)
        
        assert error.installation_command == custom_command
    
    def test_missing_dependency_error_suggestions(self):
        """测试错误建议"""
        error = MissingDependencyError("flask", ["flask"])
        
        assert len(error.suggestions) >= 2
        assert any("pip install web-performance-monitor[flask]" in s for s in error.suggestions)
        assert any("pip install web-performance-monitor[all]" in s for s in error.suggestions)
    
    def test_get_installation_guide(self):
        """测试获取安装指导"""
        error = MissingDependencyError("flask", ["flask"])
        guide = error.get_installation_guide()
        
        assert "缺少 flask 依赖" in guide
        assert "解决方案" in guide
        assert "pip install web-performance-monitor[flask]" in guide


class TestFrameworkNotSupportedError:
    """不支持框架错误测试"""
    
    def test_framework_not_supported_basic(self):
        """测试基本不支持框架错误"""
        error = FrameworkNotSupportedError("django")
        
        assert error.unsupported_framework == "django"
        assert error.framework == "django"
        assert "Framework 'django' is not supported" in str(error)
    
    def test_framework_not_supported_with_supported_list(self):
        """测试带支持框架列表的错误"""
        supported = ["flask", "fastapi"]
        error = FrameworkNotSupportedError("django", supported)
        
        assert error.supported_frameworks == supported
        assert len(error.suggestions) >= 2
        assert any("flask, fastapi" in s for s in error.suggestions)


class TestDependencyConflictError:
    """依赖冲突错误测试"""
    
    def test_dependency_conflict_basic(self):
        """测试基本依赖冲突错误"""
        conflicts = {"package1": "version info"}
        error = DependencyConflictError(conflicts)
        
        assert error.conflicting_packages == conflicts
        assert "Dependency conflicts detected" in str(error)
        assert len(error.suggestions) >= 3
    
    def test_dependency_conflict_detailed(self):
        """测试详细依赖冲突错误"""
        conflicts = {
            "flask": {
                "required": ">=2.0.0",
                "installed": "1.9.0"
            }
        }
        error = DependencyConflictError(conflicts)
        
        error_str = str(error)
        assert "flask" in error_str
        assert "required: >=2.0.0" in error_str
        assert "installed: 1.9.0" in error_str
    
    def test_dependency_conflict_custom_suggestions(self):
        """测试自定义解决建议"""
        conflicts = {"package1": "info"}
        suggestions = ["custom suggestion 1", "custom suggestion 2"]
        error = DependencyConflictError(conflicts, suggestions)
        
        assert error.suggestions == suggestions


class TestDependencyVersionError:
    """依赖版本错误测试"""
    
    def test_dependency_version_error_with_installed(self):
        """测试有已安装版本的版本错误"""
        error = DependencyVersionError("flask", "2.0.0", "1.9.0")
        
        assert error.package == "flask"
        assert error.required_version == "2.0.0"
        assert error.installed_version == "1.9.0"
        
        error_str = str(error)
        assert "version mismatch" in error_str
        assert "required 2.0.0" in error_str
        assert "installed 1.9.0" in error_str
    
    def test_dependency_version_error_not_installed(self):
        """测试未安装的版本错误"""
        error = DependencyVersionError("flask", "2.0.0")
        
        assert error.installed_version is None
        
        error_str = str(error)
        assert "version 2.0.0 is required but not installed" in error_str
    
    def test_dependency_version_error_suggestions(self):
        """测试版本错误建议"""
        error = DependencyVersionError("flask", "2.0.0", "1.9.0")
        
        assert len(error.suggestions) >= 2
        assert any("pip install 'flask>=2.0.0'" in s for s in error.suggestions)
        assert any("pip install 'flask==2.0.0'" in s for s in error.suggestions)


class TestEnvironmentValidationError:
    """环境验证错误测试"""
    
    def test_environment_validation_error_basic(self):
        """测试基本环境验证错误"""
        failures = ["failure 1", "failure 2"]
        error = EnvironmentValidationError(failures)
        
        assert error.validation_failures == failures
        assert error.environment_info == {}
        
        error_str = str(error)
        assert "Environment validation failed" in error_str
        assert "failure 1; failure 2" in error_str
    
    def test_environment_validation_error_with_info(self):
        """测试带环境信息的验证错误"""
        failures = ["failure 1"]
        env_info = {"python_version": "3.9.0", "platform": "linux"}
        error = EnvironmentValidationError(failures, env_info)
        
        assert error.environment_info == env_info
    
    def test_environment_validation_error_suggestions(self):
        """测试环境验证错误建议"""
        error = EnvironmentValidationError(["failure"])
        
        assert len(error.suggestions) >= 3
        assert any("Python environment" in s for s in error.suggestions)
        assert any("virtual environment" in s for s in error.suggestions)


class TestExceptionHierarchy:
    """异常层次结构测试"""
    
    def test_all_dependency_errors_inherit_from_dependency_error(self):
        """测试所有依赖错误都继承自DependencyError"""
        exceptions = [
            MissingDependencyError("test", ["test"]),
            FrameworkNotSupportedError("test"),
            DependencyConflictError({}),
            DependencyVersionError("test", "1.0.0"),
            EnvironmentValidationError([])
        ]
        
        for exc in exceptions:
            assert isinstance(exc, DependencyError)
            assert isinstance(exc, PerformanceMonitorError)
    
    def test_dependency_error_inherits_from_performance_monitor_error(self):
        """测试DependencyError继承自PerformanceMonitorError"""
        error = DependencyError("test")
        assert isinstance(error, PerformanceMonitorError)