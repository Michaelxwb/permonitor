"""
虚拟环境管理工具

提供创建、管理和清理测试用虚拟环境的功能。
"""

import os
import sys
import subprocess
import tempfile
import shutil
from typing import List, Dict, Optional, Any
from pathlib import Path
from dataclasses import dataclass
from contextlib import contextmanager

import pytest


@dataclass
class VenvConfig:
    """虚拟环境配置"""
    python_version: str = sys.version.split()[0]  # 使用当前Python版本
    packages: List[str] = None
    requirements_file: Optional[str] = None
    environment_variables: Dict[str, str] = None
    
    def __post_init__(self):
        if self.packages is None:
            self.packages = []
        if self.environment_variables is None:
            self.environment_variables = {}


class VirtualEnvironmentManager:
    """虚拟环境管理器"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir) if base_dir else Path(tempfile.gettempdir()) / "wpm_test_venvs"
        self.base_dir.mkdir(exist_ok=True)
        self._created_venvs = []
    
    def create_venv(self, name: str, config: VenvConfig) -> Path:
        """
        创建虚拟环境
        
        Args:
            name (str): 环境名称
            config (VenvConfig): 环境配置
            
        Returns:
            Path: 虚拟环境路径
        """
        venv_path = self.base_dir / name
        
        # 如果环境已存在，先删除
        if venv_path.exists():
            shutil.rmtree(venv_path)
        
        # 创建虚拟环境
        try:
            subprocess.run([
                sys.executable, "-m", "venv", str(venv_path)
            ], check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"创建虚拟环境失败: {e.stderr}")
        
        # 获取pip路径
        pip_path = self._get_pip_path(venv_path)
        
        # 升级pip
        try:
            subprocess.run([
                str(pip_path), "install", "--upgrade", "pip"
            ], check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            print(f"警告: 升级pip失败: {e.stderr}")
        
        # 安装包
        if config.packages:
            self._install_packages(venv_path, config.packages)
        
        # 从requirements文件安装
        if config.requirements_file and os.path.exists(config.requirements_file):
            self._install_from_requirements(venv_path, config.requirements_file)
        
        self._created_venvs.append(venv_path)
        return venv_path
    
    def _get_pip_path(self, venv_path: Path) -> Path:
        """获取虚拟环境中的pip路径"""
        if sys.platform == "win32":
            return venv_path / "Scripts" / "pip.exe"
        else:
            return venv_path / "bin" / "pip"
    
    def _get_python_path(self, venv_path: Path) -> Path:
        """获取虚拟环境中的Python路径"""
        if sys.platform == "win32":
            return venv_path / "Scripts" / "python.exe"
        else:
            return venv_path / "bin" / "python"
    
    def _install_packages(self, venv_path: Path, packages: List[str]):
        """在虚拟环境中安装包"""
        pip_path = self._get_pip_path(venv_path)
        
        for package in packages:
            try:
                subprocess.run([
                    str(pip_path), "install", package
                ], check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"安装包 {package} 失败: {e.stderr}")
    
    def _install_from_requirements(self, venv_path: Path, requirements_file: str):
        """从requirements文件安装包"""
        pip_path = self._get_pip_path(venv_path)
        
        try:
            subprocess.run([
                str(pip_path), "install", "-r", requirements_file
            ], check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"从requirements文件安装失败: {e.stderr}")
    
    def run_in_venv(self, venv_path: Path, command: List[str], 
                   env_vars: Optional[Dict[str, str]] = None) -> subprocess.CompletedProcess:
        """
        在虚拟环境中运行命令
        
        Args:
            venv_path (Path): 虚拟环境路径
            command (List[str]): 要运行的命令
            env_vars (Optional[Dict[str, str]]): 环境变量
            
        Returns:
            subprocess.CompletedProcess: 命令执行结果
        """
        python_path = self._get_python_path(venv_path)
        
        # 准备环境变量
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)
        
        # 设置虚拟环境路径
        env["VIRTUAL_ENV"] = str(venv_path)
        env["PATH"] = f"{venv_path / 'bin' if sys.platform != 'win32' else venv_path / 'Scripts'}{os.pathsep}{env['PATH']}"
        
        # 运行命令
        full_command = [str(python_path)] + command
        
        return subprocess.run(
            full_command,
            env=env,
            capture_output=True,
            text=True
        )
    
    def get_installed_packages(self, venv_path: Path) -> Dict[str, str]:
        """
        获取虚拟环境中已安装的包
        
        Args:
            venv_path (Path): 虚拟环境路径
            
        Returns:
            Dict[str, str]: 包名到版本的映射
        """
        pip_path = self._get_pip_path(venv_path)
        
        try:
            result = subprocess.run([
                str(pip_path), "list", "--format=json"
            ], check=True, capture_output=True, text=True)
            
            import json
            packages_info = json.loads(result.stdout)
            
            return {pkg["name"]: pkg["version"] for pkg in packages_info}
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            raise RuntimeError(f"获取已安装包列表失败: {e}")
    
    def test_import_in_venv(self, venv_path: Path, module_name: str) -> bool:
        """
        测试在虚拟环境中是否可以导入模块
        
        Args:
            venv_path (Path): 虚拟环境路径
            module_name (str): 模块名称
            
        Returns:
            bool: 是否可以导入
        """
        result = self.run_in_venv(venv_path, ["-c", f"import {module_name}"])
        return result.returncode == 0
    
    def cleanup_venv(self, venv_path: Path):
        """清理虚拟环境"""
        if venv_path.exists():
            shutil.rmtree(venv_path)
        
        if venv_path in self._created_venvs:
            self._created_venvs.remove(venv_path)
    
    def cleanup_all(self):
        """清理所有创建的虚拟环境"""
        for venv_path in self._created_venvs.copy():
            self.cleanup_venv(venv_path)
    
    def __del__(self):
        """析构函数，清理资源"""
        try:
            self.cleanup_all()
        except:
            pass  # 忽略清理时的错误


class TestVenvScenarios:
    """测试虚拟环境场景"""
    
    @staticmethod
    def minimal_scenario() -> VenvConfig:
        """最小安装场景"""
        return VenvConfig(
            packages=[
                "pyinstrument>=4.6.0",
                "requests>=2.25.0"
            ]
        )
    
    @staticmethod
    def flask_scenario() -> VenvConfig:
        """Flask场景"""
        return VenvConfig(
            packages=[
                "pyinstrument>=4.6.0",
                "requests>=2.25.0",
                "flask>=2.0.0"
            ]
        )
    
    @staticmethod
    def fastapi_scenario() -> VenvConfig:
        """FastAPI场景"""
        return VenvConfig(
            packages=[
                "pyinstrument>=4.6.0",
                "requests>=2.25.0",
                "fastapi>=0.100.0",
                "uvicorn>=0.20.0",
                "aiofiles>=24.1.0",
                "aiohttp>=3.12.0"
            ]
        )
    
    @staticmethod
    def full_scenario() -> VenvConfig:
        """完整安装场景"""
        return VenvConfig(
            packages=[
                "pyinstrument>=4.6.0",
                "requests>=2.25.0",
                "flask>=2.0.0",
                "fastapi>=0.100.0",
                "uvicorn>=0.20.0",
                "aiofiles>=24.1.0",
                "aiohttp>=3.12.0",
                "mattermostdriver>=7.0.0"
            ]
        )
    
    @staticmethod
    def conflicted_scenario() -> VenvConfig:
        """版本冲突场景"""
        return VenvConfig(
            packages=[
                "pyinstrument>=4.6.0",
                "requests>=2.25.0",
                "flask==1.1.4",  # 旧版本
                "fastapi==0.50.0"  # 旧版本
            ]
        )


@contextmanager
def temporary_venv(config: VenvConfig, name: Optional[str] = None):
    """临时虚拟环境上下文管理器"""
    manager = VirtualEnvironmentManager()
    venv_name = name or f"temp_venv_{id(config)}"
    
    try:
        venv_path = manager.create_venv(venv_name, config)
        yield venv_path, manager
    finally:
        manager.cleanup_all()


class VenvTestCase:
    """虚拟环境测试用例基类"""
    
    def setup_method(self):
        """测试方法设置"""
        self.venv_manager = VirtualEnvironmentManager()
        self.created_venvs = []
    
    def teardown_method(self):
        """测试方法清理"""
        self.venv_manager.cleanup_all()
    
    def create_test_venv(self, name: str, config: VenvConfig) -> Path:
        """创建测试虚拟环境"""
        venv_path = self.venv_manager.create_venv(name, config)
        self.created_venvs.append(venv_path)
        return venv_path
    
    def run_test_in_venv(self, venv_path: Path, test_code: str, 
                        env_vars: Optional[Dict[str, str]] = None) -> subprocess.CompletedProcess:
        """在虚拟环境中运行测试代码"""
        return self.venv_manager.run_in_venv(venv_path, ["-c", test_code], env_vars)
    
    def assert_package_installed(self, venv_path: Path, package_name: str):
        """断言包已安装"""
        installed_packages = self.venv_manager.get_installed_packages(venv_path)
        assert package_name.lower() in [pkg.lower() for pkg in installed_packages.keys()], \
            f"包 {package_name} 未安装"
    
    def assert_import_works(self, venv_path: Path, module_name: str):
        """断言模块可以导入"""
        assert self.venv_manager.test_import_in_venv(venv_path, module_name), \
            f"无法导入模块 {module_name}"
    
    def assert_import_fails(self, venv_path: Path, module_name: str):
        """断言模块导入失败"""
        assert not self.venv_manager.test_import_in_venv(venv_path, module_name), \
            f"模块 {module_name} 不应该可以导入"


# pytest fixtures
@pytest.fixture
def venv_manager():
    """虚拟环境管理器fixture"""
    manager = VirtualEnvironmentManager()
    yield manager
    manager.cleanup_all()


@pytest.fixture
def minimal_venv(venv_manager):
    """最小虚拟环境fixture"""
    config = TestVenvScenarios.minimal_scenario()
    venv_path = venv_manager.create_venv("minimal_test", config)
    yield venv_path


@pytest.fixture
def flask_venv(venv_manager):
    """Flask虚拟环境fixture"""
    config = TestVenvScenarios.flask_scenario()
    venv_path = venv_manager.create_venv("flask_test", config)
    yield venv_path


@pytest.fixture
def fastapi_venv(venv_manager):
    """FastAPI虚拟环境fixture"""
    config = TestVenvScenarios.fastapi_scenario()
    venv_path = venv_manager.create_venv("fastapi_test", config)
    yield venv_path


@pytest.fixture
def full_venv(venv_manager):
    """完整虚拟环境fixture"""
    config = TestVenvScenarios.full_scenario()
    venv_path = venv_manager.create_venv("full_test", config)
    yield venv_path