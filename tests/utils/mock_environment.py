"""
模拟测试环境模块

提供模拟不同依赖安装场景的测试环境。
"""

import os
import sys
import tempfile
import shutil
from typing import Dict, List, Optional, Any, Set
from unittest.mock import patch, MagicMock
from contextlib import contextmanager
from dataclasses import dataclass, field

import pytest


@dataclass
class MockPackage:
    """模拟包信息"""
    name: str
    version: str
    dependencies: List[str] = field(default_factory=list)
    installed: bool = True
    import_name: Optional[str] = None
    
    def __post_init__(self):
        if self.import_name is None:
            self.import_name = self.name.replace('-', '_').lower()


@dataclass
class EnvironmentConfig:
    """环境配置"""
    python_version: str = "3.8.0"
    installed_packages: List[MockPackage] = field(default_factory=list)
    missing_packages: List[str] = field(default_factory=list)
    import_failures: List[str] = field(default_factory=list)
    environment_variables: Dict[str, str] = field(default_factory=dict)
    project_files: Dict[str, str] = field(default_factory=dict)
    config_files: Dict[str, str] = field(default_factory=dict)


class MockEnvironment:
    """模拟测试环境"""
    
    def __init__(self, config: EnvironmentConfig):
        self.config = config
        self._temp_dir = None
        self._original_cwd = None
        self._patches = []
        self._mock_modules = {}
        
    def __enter__(self):
        """进入环境上下文"""
        self.setup()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出环境上下文"""
        self.cleanup()
    
    def setup(self):
        """设置模拟环境"""
        # 创建临时目录
        self._temp_dir = tempfile.mkdtemp(prefix="wpm_test_")
        self._original_cwd = os.getcwd()
        os.chdir(self._temp_dir)
        
        # 设置环境变量
        for key, value in self.config.environment_variables.items():
            os.environ[key] = value
        
        # 创建项目文件
        self._create_project_files()
        
        # 创建配置文件
        self._create_config_files()
        
        # 模拟包安装状态
        self._setup_package_mocks()
        
        # 模拟导入失败
        self._setup_import_mocks()
    
    def cleanup(self):
        """清理模拟环境"""
        # 停止所有补丁
        for patch_obj in self._patches:
            try:
                patch_obj.stop()
            except RuntimeError:
                pass  # 补丁可能已经停止
        
        self._patches.clear()
        
        # 清理环境变量
        for key in self.config.environment_variables:
            os.environ.pop(key, None)
        
        # 恢复工作目录
        if self._original_cwd:
            os.chdir(self._original_cwd)
        
        # 删除临时目录
        if self._temp_dir and os.path.exists(self._temp_dir):
            shutil.rmtree(self._temp_dir, ignore_errors=True)
        
        # 清理模拟模块
        for module_name in self._mock_modules:
            if module_name in sys.modules:
                del sys.modules[module_name]
    
    def _create_project_files(self):
        """创建项目文件"""
        for file_path, content in self.config.project_files.items():
            full_path = os.path.join(self._temp_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
    
    def _create_config_files(self):
        """创建配置文件"""
        for file_path, content in self.config.config_files.items():
            full_path = os.path.join(self._temp_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
    
    def _setup_package_mocks(self):
        """设置包模拟"""
        # 模拟pkg_resources
        mock_working_set = []
        
        for package in self.config.installed_packages:
            if package.installed:
                mock_pkg = MagicMock()
                mock_pkg.project_name = package.name
                mock_pkg.version = package.version
                mock_working_set.append(mock_pkg)
        
        # 补丁pkg_resources.working_set
        try:
            import pkg_resources
            pkg_resources_patch = patch('pkg_resources.working_set', mock_working_set)
            self._patches.append(pkg_resources_patch)
            pkg_resources_patch.start()
        except ImportError:
            # 如果pkg_resources不可用，创建模拟模块
            mock_pkg_resources = MagicMock()
            mock_pkg_resources.working_set = mock_working_set
            sys.modules['pkg_resources'] = mock_pkg_resources
            self._mock_modules['pkg_resources'] = mock_pkg_resources
    
    def _setup_import_mocks(self):
        """设置导入模拟"""
        original_import = __builtins__.__import__
        
        def mock_import(name, *args, **kwargs):
            # 检查是否应该失败
            if name in self.config.import_failures:
                raise ImportError(f"No module named '{name}'")
            
            # 检查是否有已安装的包
            for package in self.config.installed_packages:
                if package.import_name == name and package.installed:
                    # 创建模拟模块
                    if name not in sys.modules:
                        mock_module = MagicMock()
                        mock_module.__name__ = name
                        mock_module.__version__ = package.version
                        sys.modules[name] = mock_module
                        self._mock_modules[name] = mock_module
                    return sys.modules[name]
            
            # 检查是否在缺失包列表中
            if name in self.config.missing_packages:
                raise ImportError(f"No module named '{name}'")
            
            # 否则使用原始导入
            return original_import(name, *args, **kwargs)
        
        import_patch = patch('builtins.__import__', side_effect=mock_import)
        self._patches.append(import_patch)
        import_patch.start()
    
    def add_package(self, package: MockPackage):
        """添加包到环境"""
        self.config.installed_packages.append(package)
        
        # 如果环境已经设置，立即应用更改
        if self._temp_dir:
            self._setup_package_mocks()
    
    def remove_package(self, package_name: str):
        """从环境中移除包"""
        self.config.installed_packages = [
            pkg for pkg in self.config.installed_packages 
            if pkg.name != package_name
        ]
        
        # 添加到缺失包列表
        if package_name not in self.config.missing_packages:
            self.config.missing_packages.append(package_name)
        
        # 如果环境已经设置，立即应用更改
        if self._temp_dir:
            self._setup_package_mocks()
    
    def set_import_failure(self, module_name: str, should_fail: bool = True):
        """设置模块导入失败"""
        if should_fail:
            if module_name not in self.config.import_failures:
                self.config.import_failures.append(module_name)
        else:
            if module_name in self.config.import_failures:
                self.config.import_failures.remove(module_name)
    
    def create_file(self, file_path: str, content: str):
        """在环境中创建文件"""
        if self._temp_dir:
            full_path = os.path.join(self._temp_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
    
    def get_temp_dir(self) -> str:
        """获取临时目录路径"""
        return self._temp_dir


class EnvironmentScenarios:
    """预定义的环境场景"""
    
    @staticmethod
    def clean_environment() -> EnvironmentConfig:
        """干净的环境（没有安装任何框架）"""
        return EnvironmentConfig(
            installed_packages=[
                MockPackage("pyinstrument", "4.6.0"),
                MockPackage("requests", "2.31.0")
            ],
            missing_packages=["flask", "fastapi", "uvicorn", "aiofiles", "aiohttp", "mattermostdriver"]
        )
    
    @staticmethod
    def flask_only_environment() -> EnvironmentConfig:
        """只安装Flask的环境"""
        return EnvironmentConfig(
            installed_packages=[
                MockPackage("pyinstrument", "4.6.0"),
                MockPackage("requests", "2.31.0"),
                MockPackage("flask", "2.3.0", import_name="flask")
            ],
            missing_packages=["fastapi", "uvicorn", "aiofiles", "aiohttp", "mattermostdriver"],
            project_files={
                "app.py": """
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello, World!'
""",
                "requirements.txt": """
flask>=2.0.0
web-performance-monitor
"""
            }
        )
    
    @staticmethod
    def fastapi_only_environment() -> EnvironmentConfig:
        """只安装FastAPI的环境"""
        return EnvironmentConfig(
            installed_packages=[
                MockPackage("pyinstrument", "4.6.0"),
                MockPackage("requests", "2.31.0"),
                MockPackage("fastapi", "0.104.0", import_name="fastapi"),
                MockPackage("uvicorn", "0.24.0", import_name="uvicorn"),
                MockPackage("aiofiles", "24.1.0", import_name="aiofiles"),
                MockPackage("aiohttp", "3.12.0", import_name="aiohttp")
            ],
            missing_packages=["flask", "mattermostdriver"],
            project_files={
                "main.py": """
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def read_root():
    return {"Hello": "World"}
""",
                "requirements.txt": """
fastapi>=0.100.0
uvicorn>=0.20.0
aiofiles>=24.1.0
aiohttp>=3.12.0
web-performance-monitor
"""
            }
        )
    
    @staticmethod
    def full_environment() -> EnvironmentConfig:
        """完整安装的环境"""
        return EnvironmentConfig(
            installed_packages=[
                MockPackage("pyinstrument", "4.6.0"),
                MockPackage("requests", "2.31.0"),
                MockPackage("flask", "2.3.0", import_name="flask"),
                MockPackage("fastapi", "0.104.0", import_name="fastapi"),
                MockPackage("uvicorn", "0.24.0", import_name="uvicorn"),
                MockPackage("aiofiles", "24.1.0", import_name="aiofiles"),
                MockPackage("aiohttp", "3.12.0", import_name="aiohttp"),
                MockPackage("mattermostdriver", "7.3.2", import_name="mattermostdriver")
            ],
            project_files={
                "flask_app.py": """
from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello from Flask!'
""",
                "fastapi_app.py": """
from fastapi import FastAPI
app = FastAPI()

@app.get("/")
async def read_root():
    return {"message": "Hello from FastAPI!"}
""",
                "requirements.txt": """
web-performance-monitor[all]
"""
            }
        )
    
    @staticmethod
    def conflicted_environment() -> EnvironmentConfig:
        """有版本冲突的环境"""
        return EnvironmentConfig(
            installed_packages=[
                MockPackage("pyinstrument", "4.6.0"),
                MockPackage("requests", "2.31.0"),
                MockPackage("flask", "1.1.0", import_name="flask"),  # 旧版本
                MockPackage("fastapi", "0.50.0", import_name="fastapi"),  # 旧版本
                MockPackage("uvicorn", "0.10.0", import_name="uvicorn")  # 旧版本
            ],
            missing_packages=["aiofiles", "aiohttp", "mattermostdriver"],
            project_files={
                "requirements.txt": """
flask>=2.0.0
fastapi>=0.100.0
uvicorn>=0.20.0
web-performance-monitor[all]
"""
            }
        )
    
    @staticmethod
    def partial_environment() -> EnvironmentConfig:
        """部分安装的环境（有些依赖缺失）"""
        return EnvironmentConfig(
            installed_packages=[
                MockPackage("pyinstrument", "4.6.0"),
                MockPackage("requests", "2.31.0"),
                MockPackage("flask", "2.3.0", import_name="flask"),
                MockPackage("fastapi", "0.104.0", import_name="fastapi"),
                # 缺少uvicorn, aiofiles, aiohttp
            ],
            missing_packages=["uvicorn", "aiofiles", "aiohttp", "mattermostdriver"],
            import_failures=["uvicorn", "aiofiles", "aiohttp"],
            project_files={
                "app.py": """
from flask import Flask
from fastapi import FastAPI

flask_app = Flask(__name__)
fastapi_app = FastAPI()
"""
            }
        )
    
    @staticmethod
    def development_environment() -> EnvironmentConfig:
        """开发环境（包含开发工具）"""
        return EnvironmentConfig(
            installed_packages=[
                MockPackage("pyinstrument", "4.6.0"),
                MockPackage("requests", "2.31.0"),
                MockPackage("flask", "2.3.0", import_name="flask"),
                MockPackage("fastapi", "0.104.0", import_name="fastapi"),
                MockPackage("uvicorn", "0.24.0", import_name="uvicorn"),
                MockPackage("aiofiles", "24.1.0", import_name="aiofiles"),
                MockPackage("aiohttp", "3.12.0", import_name="aiohttp"),
                MockPackage("pytest", "7.4.0", import_name="pytest"),
                MockPackage("black", "23.0.0", import_name="black"),
                MockPackage("flake8", "6.0.0", import_name="flake8")
            ],
            environment_variables={
                "WPM_DEBUG": "true",
                "WPM_LOG_LEVEL": "DEBUG",
                "FLASK_ENV": "development",
                "FASTAPI_ENV": "development"
            },
            project_files={
                "pyproject.toml": """
[build-system]
requires = ["setuptools", "wheel"]

[tool.black]
line-length = 88

[tool.pytest.ini_options]
testpaths = ["tests"]
""",
                "setup.cfg": """
[flake8]
max-line-length = 88
exclude = .git,__pycache__,build,dist
"""
            }
        )


@contextmanager
def mock_environment(config: EnvironmentConfig):
    """环境上下文管理器"""
    env = MockEnvironment(config)
    try:
        env.setup()
        yield env
    finally:
        env.cleanup()


# 便捷的装饰器
def with_clean_environment(func):
    """使用干净环境的装饰器"""
    def wrapper(*args, **kwargs):
        with mock_environment(EnvironmentScenarios.clean_environment()):
            return func(*args, **kwargs)
    return wrapper


def with_flask_environment(func):
    """使用Flask环境的装饰器"""
    def wrapper(*args, **kwargs):
        with mock_environment(EnvironmentScenarios.flask_only_environment()):
            return func(*args, **kwargs)
    return wrapper


def with_fastapi_environment(func):
    """使用FastAPI环境的装饰器"""
    def wrapper(*args, **kwargs):
        with mock_environment(EnvironmentScenarios.fastapi_only_environment()):
            return func(*args, **kwargs)
    return wrapper


def with_full_environment(func):
    """使用完整环境的装饰器"""
    def wrapper(*args, **kwargs):
        with mock_environment(EnvironmentScenarios.full_environment()):
            return func(*args, **kwargs)
    return wrapper


def with_conflicted_environment(func):
    """使用冲突环境的装饰器"""
    def wrapper(*args, **kwargs):
        with mock_environment(EnvironmentScenarios.conflicted_environment()):
            return func(*args, **kwargs)
    return wrapper