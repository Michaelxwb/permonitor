"""
模拟环境测试模块
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

from tests.utils.mock_environment import (
    MockPackage,
    EnvironmentConfig,
    MockEnvironment,
    EnvironmentScenarios,
    mock_environment,
    with_clean_environment,
    with_flask_environment,
    with_fastapi_environment,
    with_full_environment
)


class TestMockPackage:
    """模拟包测试类"""
    
    def test_mock_package_creation(self):
        """测试模拟包创建"""
        package = MockPackage("flask", "2.0.0", ["werkzeug", "jinja2"])
        
        assert package.name == "flask"
        assert package.version == "2.0.0"
        assert package.dependencies == ["werkzeug", "jinja2"]
        assert package.installed == True
        assert package.import_name == "flask"
    
    def test_mock_package_import_name_conversion(self):
        """测试导入名称转换"""
        package = MockPackage("python-dateutil", "2.8.0")
        assert package.import_name == "python_dateutil"
        
        package = MockPackage("Flask-Login", "0.6.0")
        assert package.import_name == "flask_login"
    
    def test_mock_package_custom_import_name(self):
        """测试自定义导入名称"""
        package = MockPackage("PyYAML", "6.0", import_name="yaml")
        assert package.import_name == "yaml"


class TestEnvironmentConfig:
    """环境配置测试类"""
    
    def test_environment_config_defaults(self):
        """测试环境配置默认值"""
        config = EnvironmentConfig()
        
        assert config.python_version == "3.8.0"
        assert config.installed_packages == []
        assert config.missing_packages == []
        assert config.import_failures == []
        assert config.environment_variables == {}
        assert config.project_files == {}
        assert config.config_files == {}
    
    def test_environment_config_custom(self):
        """测试自定义环境配置"""
        packages = [MockPackage("flask", "2.0.0")]
        env_vars = {"DEBUG": "true"}
        
        config = EnvironmentConfig(
            python_version="3.9.0",
            installed_packages=packages,
            missing_packages=["fastapi"],
            environment_variables=env_vars
        )
        
        assert config.python_version == "3.9.0"
        assert config.installed_packages == packages
        assert config.missing_packages == ["fastapi"]
        assert config.environment_variables == env_vars


class TestMockEnvironment:
    """模拟环境测试类"""
    
    def test_mock_environment_context_manager(self):
        """测试模拟环境上下文管理器"""
        config = EnvironmentConfig(
            environment_variables={"TEST_VAR": "test_value"},
            project_files={"test.py": "print('hello')"}
        )
        
        original_cwd = os.getcwd()
        
        with MockEnvironment(config) as env:
            # 检查环境变量
            assert os.environ.get("TEST_VAR") == "test_value"
            
            # 检查工作目录变更
            assert os.getcwd() != original_cwd
            
            # 检查文件创建
            assert os.path.exists("test.py")
            
            # 检查临时目录
            temp_dir = env.get_temp_dir()
            assert temp_dir is not None
            assert os.path.exists(temp_dir)
        
        # 检查清理
        assert os.environ.get("TEST_VAR") is None
        assert os.getcwd() == original_cwd
    
    def test_package_mocking(self):
        """测试包模拟"""
        config = EnvironmentConfig(
            installed_packages=[
                MockPackage("flask", "2.0.0"),
                MockPackage("requests", "2.31.0")
            ],
            missing_packages=["fastapi"],
            import_failures=["uvicorn"]
        )
        
        with MockEnvironment(config):
            # 测试成功导入
            import flask
            assert flask.__version__ == "2.0.0"
            
            import requests
            assert requests.__version__ == "2.31.0"
            
            # 测试导入失败
            with pytest.raises(ImportError):
                import fastapi
            
            with pytest.raises(ImportError):
                import uvicorn
    
    def test_pkg_resources_mocking(self):
        """测试pkg_resources模拟"""
        config = EnvironmentConfig(
            installed_packages=[
                MockPackage("flask", "2.0.0"),
                MockPackage("requests", "2.31.0")
            ]
        )
        
        with MockEnvironment(config):
            import pkg_resources
            
            # 检查working_set
            package_names = [pkg.project_name for pkg in pkg_resources.working_set]
            assert "flask" in package_names
            assert "requests" in package_names
            
            # 检查版本
            flask_pkg = next(pkg for pkg in pkg_resources.working_set if pkg.project_name == "flask")
            assert flask_pkg.version == "2.0.0"
    
    def test_dynamic_package_management(self):
        """测试动态包管理"""
        config = EnvironmentConfig()
        
        with MockEnvironment(config) as env:
            # 添加包
            new_package = MockPackage("new_package", "1.0.0")
            env.add_package(new_package)
            
            # 测试导入
            import new_package
            assert new_package.__version__ == "1.0.0"
            
            # 移除包
            env.remove_package("new_package")
            
            # 测试导入失败
            with pytest.raises(ImportError):
                import another_new_package  # 这应该失败
    
    def test_file_creation(self):
        """测试文件创建"""
        config = EnvironmentConfig()
        
        with MockEnvironment(config) as env:
            # 创建文件
            env.create_file("subdir/test.py", "print('test')")
            
            # 检查文件存在
            assert os.path.exists("subdir/test.py")
            
            # 检查文件内容
            with open("subdir/test.py", "r") as f:
                content = f.read()
                assert content == "print('test')"


class TestEnvironmentScenarios:
    """环境场景测试类"""
    
    def test_clean_environment(self):
        """测试干净环境"""
        config = EnvironmentScenarios.clean_environment()
        
        assert len(config.installed_packages) == 2  # pyinstrument, requests
        assert "flask" in config.missing_packages
        assert "fastapi" in config.missing_packages
    
    def test_flask_only_environment(self):
        """测试Flask环境"""
        config = EnvironmentScenarios.flask_only_environment()
        
        # 检查已安装包
        package_names = [pkg.name for pkg in config.installed_packages]
        assert "flask" in package_names
        assert "pyinstrument" in package_names
        assert "requests" in package_names
        
        # 检查缺失包
        assert "fastapi" in config.missing_packages
        assert "uvicorn" in config.missing_packages
        
        # 检查项目文件
        assert "app.py" in config.project_files
        assert "requirements.txt" in config.project_files
    
    def test_fastapi_only_environment(self):
        """测试FastAPI环境"""
        config = EnvironmentScenarios.fastapi_only_environment()
        
        # 检查已安装包
        package_names = [pkg.name for pkg in config.installed_packages]
        assert "fastapi" in package_names
        assert "uvicorn" in package_names
        assert "aiofiles" in package_names
        assert "aiohttp" in package_names
        
        # 检查缺失包
        assert "flask" in config.missing_packages
        assert "mattermostdriver" in config.missing_packages
        
        # 检查项目文件
        assert "main.py" in config.project_files
    
    def test_full_environment(self):
        """测试完整环境"""
        config = EnvironmentScenarios.full_environment()
        
        # 检查所有包都已安装
        package_names = [pkg.name for pkg in config.installed_packages]
        assert "flask" in package_names
        assert "fastapi" in package_names
        assert "uvicorn" in package_names
        assert "aiofiles" in package_names
        assert "aiohttp" in package_names
        assert "mattermostdriver" in package_names
        
        # 检查项目文件
        assert "flask_app.py" in config.project_files
        assert "fastapi_app.py" in config.project_files
    
    def test_conflicted_environment(self):
        """测试冲突环境"""
        config = EnvironmentScenarios.conflicted_environment()
        
        # 检查旧版本包
        flask_pkg = next(pkg for pkg in config.installed_packages if pkg.name == "flask")
        assert flask_pkg.version == "1.1.0"
        
        fastapi_pkg = next(pkg for pkg in config.installed_packages if pkg.name == "fastapi")
        assert fastapi_pkg.version == "0.50.0"
        
        # 检查缺失包
        assert "aiofiles" in config.missing_packages
        assert "aiohttp" in config.missing_packages
    
    def test_partial_environment(self):
        """测试部分环境"""
        config = EnvironmentScenarios.partial_environment()
        
        # 检查已安装包
        package_names = [pkg.name for pkg in config.installed_packages]
        assert "flask" in package_names
        assert "fastapi" in package_names
        
        # 检查缺失包
        assert "uvicorn" in config.missing_packages
        assert "aiofiles" in config.missing_packages
        
        # 检查导入失败
        assert "uvicorn" in config.import_failures
        assert "aiofiles" in config.import_failures
    
    def test_development_environment(self):
        """测试开发环境"""
        config = EnvironmentScenarios.development_environment()
        
        # 检查开发工具
        package_names = [pkg.name for pkg in config.installed_packages]
        assert "pytest" in package_names
        assert "black" in package_names
        assert "flake8" in package_names
        
        # 检查环境变量
        assert config.environment_variables["WPM_DEBUG"] == "true"
        assert config.environment_variables["WPM_LOG_LEVEL"] == "DEBUG"
        
        # 检查配置文件
        assert "pyproject.toml" in config.project_files
        assert "setup.cfg" in config.project_files


class TestEnvironmentDecorators:
    """环境装饰器测试类"""
    
    @with_clean_environment
    def test_clean_environment_decorator(self):
        """测试干净环境装饰器"""
        # 应该无法导入框架
        with pytest.raises(ImportError):
            import flask
        
        with pytest.raises(ImportError):
            import fastapi
        
        # 但应该可以导入基础包
        import pyinstrument
        import requests
    
    @with_flask_environment
    def test_flask_environment_decorator(self):
        """测试Flask环境装饰器"""
        # 应该可以导入Flask
        import flask
        assert flask.__version__ == "2.3.0"
        
        # 应该无法导入FastAPI
        with pytest.raises(ImportError):
            import fastapi
        
        # 检查项目文件
        assert os.path.exists("app.py")
        assert os.path.exists("requirements.txt")
    
    @with_fastapi_environment
    def test_fastapi_environment_decorator(self):
        """测试FastAPI环境装饰器"""
        # 应该可以导入FastAPI相关包
        import fastapi
        import uvicorn
        import aiofiles
        import aiohttp
        
        assert fastapi.__version__ == "0.104.0"
        
        # 应该无法导入Flask
        with pytest.raises(ImportError):
            import flask
        
        # 检查项目文件
        assert os.path.exists("main.py")
    
    @with_full_environment
    def test_full_environment_decorator(self):
        """测试完整环境装饰器"""
        # 应该可以导入所有框架
        import flask
        import fastapi
        import uvicorn
        import aiofiles
        import aiohttp
        import mattermostdriver
        
        # 检查版本
        assert flask.__version__ == "2.3.0"
        assert fastapi.__version__ == "0.104.0"
        
        # 检查项目文件
        assert os.path.exists("flask_app.py")
        assert os.path.exists("fastapi_app.py")


class TestMockEnvironmentIntegration:
    """模拟环境集成测试类"""
    
    def test_dependency_detection_in_mock_environment(self):
        """测试在模拟环境中的依赖检测"""
        from web_performance_monitor.utils.framework_detector import FrameworkDetector
        
        config = EnvironmentScenarios.flask_only_environment()
        
        with mock_environment(config):
            detector = FrameworkDetector()
            frameworks = detector.detect_installed_frameworks()
            
            assert "flask" in frameworks
            assert "fastapi" not in frameworks
    
    def test_plugin_system_in_mock_environment(self):
        """测试在模拟环境中的插件系统"""
        from web_performance_monitor.core.plugin_system import get_plugin_manager
        
        config = EnvironmentScenarios.full_environment()
        
        with mock_environment(config):
            manager = get_plugin_manager()
            available_frameworks = manager.get_available_frameworks()
            
            # 在完整环境中，所有框架都应该可用
            assert "flask" in available_frameworks
            assert "fastapi" in available_frameworks
    
    def test_conflict_detection_in_mock_environment(self):
        """测试在模拟环境中的冲突检测"""
        from web_performance_monitor.core.conflict_resolver import ConflictResolver, DependencyInfo
        
        config = EnvironmentScenarios.conflicted_environment()
        
        with mock_environment(config):
            resolver = ConflictResolver()
            
            # 创建依赖信息（要求新版本）
            dependencies = [
                DependencyInfo("flask", version_spec=">=2.0.0", required_by=["app"]),
                DependencyInfo("fastapi", version_spec=">=0.100.0", required_by=["app"])
            ]
            
            result = resolver.analyze_and_resolve(dependencies)
            
            # 应该检测到版本冲突
            assert result["total_conflicts"] > 0
            assert result["has_critical_conflicts"] or any(
                "incompatible" in conflict.conflict_type.value.lower() 
                for conflict in result["conflicts"]
            )