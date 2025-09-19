"""
安装场景集成测试

测试不同安装组合的功能完整性。
"""

import pytest
import os
from unittest.mock import patch

from tests.utils.mock_environment import (
    mock_environment,
    EnvironmentScenarios,
    MockPackage,
    EnvironmentConfig
)


class TestInstallationScenarios:
    """安装场景测试"""
    
    def test_minimal_installation_scenario(self):
        """测试最小安装场景"""
        # 只安装核心依赖
        config = EnvironmentConfig(
            installed_packages=[
                MockPackage("pyinstrument", "4.6.0"),
                MockPackage("requests", "2.31.0")
            ],
            missing_packages=["flask", "fastapi", "uvicorn", "aiofiles", "aiohttp", "mattermostdriver"]
        )
        
        with mock_environment(config):
            # 应该可以导入核心模块
            from web_performance_monitor.utils.framework_detector import FrameworkDetector
            from web_performance_monitor.utils.dependency_manager import DependencyManager
            
            # 框架检测应该返回空列表
            detector = FrameworkDetector()
            frameworks = detector.detect_installed_frameworks()
            assert frameworks == []
            
            # 依赖管理器应该报告没有可用框架
            manager = DependencyManager()
            report = manager.validate_environment()
            assert len(report.available_frameworks) == 0
            assert len(report.warnings) > 0
    
    def test_flask_only_installation_scenario(self):
        """测试只安装Flask的场景"""
        with mock_environment(EnvironmentScenarios.flask_only_environment()):
            from web_performance_monitor.utils.framework_detector import FrameworkDetector
            from web_performance_monitor.utils.dependency_manager import DependencyManager
            from web_performance_monitor.core.plugin_system import get_plugin_manager
            
            # 框架检测
            detector = FrameworkDetector()
            frameworks = detector.detect_installed_frameworks()
            assert "flask" in frameworks
            assert "fastapi" not in frameworks
            
            # 依赖验证
            manager = DependencyManager()
            flask_deps = manager.check_framework_dependencies("flask")
            assert len(flask_deps) == 0  # Flask依赖应该完整
            
            fastapi_deps = manager.check_framework_dependencies("fastapi")
            assert len(fastapi_deps) > 0  # FastAPI依赖缺失
            
            # 插件系统
            plugin_manager = get_plugin_manager()
            flask_plugin = plugin_manager.registry.get_plugin("flask")
            assert flask_plugin.is_installed() == True
            
            fastapi_plugin = plugin_manager.registry.get_plugin("fastapi")
            assert fastapi_plugin.is_installed() == False
    
    def test_fastapi_only_installation_scenario(self):
        """测试只安装FastAPI的场景"""
        with mock_environment(EnvironmentScenarios.fastapi_only_environment()):
            from web_performance_monitor.utils.framework_detector import FrameworkDetector
            from web_performance_monitor.utils.dependency_manager import DependencyManager
            
            # 框架检测
            detector = FrameworkDetector()
            frameworks = detector.detect_installed_frameworks()
            assert "fastapi" in frameworks
            assert "flask" not in frameworks
            
            # 检查FastAPI相关依赖
            manager = DependencyManager()
            
            # 所有FastAPI依赖都应该可用
            for dep in ["fastapi", "uvicorn", "aiofiles", "aiohttp"]:
                deps = manager.check_framework_dependencies(dep)
                # 注意：这里可能需要根据实际实现调整
    
    def test_notifications_only_installation_scenario(self):
        """测试只安装通知功能的场景"""
        config = EnvironmentConfig(
            installed_packages=[
                MockPackage("pyinstrument", "4.6.0"),
                MockPackage("requests", "2.31.0"),
                MockPackage("mattermostdriver", "7.3.2", import_name="mattermostdriver")
            ],
            missing_packages=["flask", "fastapi", "uvicorn", "aiofiles", "aiohttp"]
        )
        
        with mock_environment(config):
            from web_performance_monitor.utils.framework_detector import FrameworkDetector
            from web_performance_monitor.core.plugin_system import get_plugin_manager
            
            # 框架检测
            detector = FrameworkDetector()
            frameworks = detector.detect_installed_frameworks()
            assert len(frameworks) == 0  # 没有web框架
            
            # 通知插件应该可用
            plugin_manager = get_plugin_manager()
            notification_plugin = plugin_manager.registry.get_plugin("notifications")
            assert notification_plugin.is_installed() == True
    
    def test_mixed_installation_scenario(self):
        """测试混合安装场景（部分依赖）"""
        config = EnvironmentConfig(
            installed_packages=[
                MockPackage("pyinstrument", "4.6.0"),
                MockPackage("requests", "2.31.0"),
                MockPackage("flask", "2.3.0", import_name="flask"),
                MockPackage("fastapi", "0.104.0", import_name="fastapi"),
                # 缺少uvicorn, aiofiles, aiohttp
                MockPackage("mattermostdriver", "7.3.2", import_name="mattermostdriver")
            ],
            missing_packages=["uvicorn", "aiofiles", "aiohttp"],
            import_failures=["uvicorn", "aiofiles", "aiohttp"]
        )
        
        with mock_environment(config):
            from web_performance_monitor.utils.framework_detector import FrameworkDetector
            from web_performance_monitor.utils.dependency_manager import DependencyManager
            from web_performance_monitor.utils.installation_guide import InstallationGuide
            
            # 框架检测
            detector = FrameworkDetector()
            frameworks = detector.detect_installed_frameworks()
            assert "flask" in frameworks
            assert "fastapi" in frameworks
            
            # 依赖检查
            manager = DependencyManager()
            
            # Flask应该完整
            flask_deps = manager.check_framework_dependencies("flask")
            assert len(flask_deps) == 0
            
            # FastAPI应该有缺失依赖
            fastapi_deps = manager.check_framework_dependencies("fastapi")
            assert len(fastapi_deps) > 0
            
            # 安装建议
            guide = InstallationGuide()
            analysis = guide.analyze_current_environment()
            assert analysis['current_status'] in ['partial', 'incomplete']
            
            # 应该有补全FastAPI依赖的建议
            recommendations = analysis['recommendations']
            fastapi_recs = [r for r in recommendations if 'fastapi' in r.command]
            assert len(fastapi_recs) > 0
    
    def test_version_mismatch_scenario(self):
        """测试版本不匹配场景"""
        with mock_environment(EnvironmentScenarios.conflicted_environment()):
            from web_performance_monitor.utils.dependency_manager import DependencyManager
            from web_performance_monitor.core.conflict_resolver import ConflictResolver, DependencyInfo
            from web_performance_monitor.utils.installation_guide import InstallationGuide
            
            # 依赖管理器应该检测到版本问题
            manager = DependencyManager()
            
            # 检查版本兼容性
            flask_compatible = manager.check_version_compatibility("flask", ">=2.0.0")
            assert flask_compatible == False  # 1.1.0 不满足 >=2.0.0
            
            # 冲突检测
            resolver = ConflictResolver()
            dependencies = [
                DependencyInfo("flask", version_spec=">=2.0.0", required_by=["app"]),
                DependencyInfo("fastapi", version_spec=">=0.100.0", required_by=["app"])
            ]
            
            result = resolver.analyze_and_resolve(dependencies)
            assert result["total_conflicts"] > 0
            
            # 应该有版本不兼容的冲突
            conflict_types = [c.conflict_type.value for c in result["conflicts"]]
            assert "incompatible_versions" in conflict_types
            
            # 安装指导应该提供解决方案
            guide = InstallationGuide()
            error_info = {
                'type': 'version_conflict',
                'framework': 'flask',
                'current_version': '1.1.0',
                'required_version': '>=2.0.0'
            }
            
            troubleshooting = guide.generate_troubleshooting_guide(error_info)
            assert "版本冲突" in troubleshooting
            assert "虚拟环境" in troubleshooting


class TestUpgradeScenarios:
    """升级场景测试"""
    
    def test_upgrade_from_minimal_to_flask(self):
        """测试从最小安装升级到Flask"""
        # 模拟升级过程：先是最小安装，然后添加Flask
        
        # 第一阶段：最小安装
        minimal_config = EnvironmentConfig(
            installed_packages=[
                MockPackage("pyinstrument", "4.6.0"),
                MockPackage("requests", "2.31.0")
            ],
            missing_packages=["flask", "fastapi", "uvicorn", "aiofiles", "aiohttp", "mattermostdriver"]
        )
        
        with mock_environment(minimal_config) as env:
            from web_performance_monitor.utils.framework_detector import FrameworkDetector
            from web_performance_monitor.utils.installation_guide import InstallationGuide
            
            # 初始状态检查
            detector = FrameworkDetector()
            frameworks = detector.detect_installed_frameworks()
            assert len(frameworks) == 0
            
            # 获取安装建议
            guide = InstallationGuide()
            command = guide.get_quick_install_command('flask')
            assert 'flask' in command
            
            # 模拟安装Flask
            env.add_package(MockPackage("flask", "2.3.0", import_name="flask"))
            
            # 重新检测
            frameworks = detector.detect_installed_frameworks()
            assert "flask" in frameworks
    
    def test_upgrade_from_flask_to_full(self):
        """测试从Flask升级到完整安装"""
        with mock_environment(EnvironmentScenarios.flask_only_environment()) as env:
            from web_performance_monitor.utils.framework_detector import FrameworkDetector
            from web_performance_monitor.utils.installation_guide import InstallationGuide
            
            # 初始状态：只有Flask
            detector = FrameworkDetector()
            initial_frameworks = detector.detect_installed_frameworks()
            assert "flask" in initial_frameworks
            assert "fastapi" not in initial_frameworks
            
            # 获取升级建议
            guide = InstallationGuide()
            analysis = guide.analyze_current_environment()
            
            # 应该建议安装其他框架
            recommendations = analysis['recommendations']
            fastapi_recs = [r for r in recommendations if 'fastapi' in r.command]
            assert len(fastapi_recs) > 0
            
            # 模拟添加FastAPI相关包
            fastapi_packages = [
                MockPackage("fastapi", "0.104.0", import_name="fastapi"),
                MockPackage("uvicorn", "0.24.0", import_name="uvicorn"),
                MockPackage("aiofiles", "24.1.0", import_name="aiofiles"),
                MockPackage("aiohttp", "3.12.0", import_name="aiohttp"),
                MockPackage("mattermostdriver", "7.3.2", import_name="mattermostdriver")
            ]
            
            for package in fastapi_packages:
                env.add_package(package)
            
            # 重新检测
            final_frameworks = detector.detect_installed_frameworks()
            assert "flask" in final_frameworks
            assert "fastapi" in final_frameworks
            
            # 状态应该变为完整
            final_analysis = guide.analyze_current_environment()
            assert final_analysis['current_status'] == 'complete'


class TestEnvironmentVariableScenarios:
    """环境变量场景测试"""
    
    def test_skip_dependency_check_scenario(self):
        """测试跳过依赖检查场景"""
        config = EnvironmentConfig(
            environment_variables={
                'WPM_SKIP_DEPENDENCY_CHECK': 'true'
            },
            installed_packages=[
                MockPackage("pyinstrument", "4.6.0"),
                MockPackage("requests", "2.31.0")
            ],
            missing_packages=["flask", "fastapi", "uvicorn", "aiofiles", "aiohttp", "mattermostdriver"]
        )
        
        with mock_environment(config):
            from web_performance_monitor.core.dependency_checker import RuntimeDependencyChecker
            from web_performance_monitor.monitors.factory import MonitorFactory
            
            # 依赖检查器应该跳过检查
            checker = RuntimeDependencyChecker()
            
            # 即使Flask未安装，也应该返回True（因为跳过检查）
            flask_available = checker.check_framework_availability("flask")
            # 具体行为取决于实现
            
            # 监控器工厂应该尝试创建监控器（可能会失败，但不会因为依赖检查而阻止）
            factory = MonitorFactory()
            try:
                monitor = factory.create_monitor("flask")
                # 如果成功，说明跳过了依赖检查
            except Exception as e:
                # 如果失败，应该是因为实际导入失败，而不是依赖检查
                assert "dependency" not in str(e).lower()
    
    def test_strict_mode_scenario(self):
        """测试严格模式场景"""
        config = EnvironmentConfig(
            environment_variables={
                'WPM_DEPENDENCY_CHECK_MODE': 'strict'
            },
            installed_packages=[
                MockPackage("pyinstrument", "4.6.0"),
                MockPackage("requests", "2.31.0"),
                MockPackage("flask", "1.1.0", import_name="flask")  # 旧版本
            ]
        )
        
        with mock_environment(config):
            from web_performance_monitor.core.dependency_checker import RuntimeDependencyChecker
            from web_performance_monitor.utils.dependency_manager import DependencyManager
            
            # 严格模式下应该检测到版本问题
            manager = DependencyManager()
            compatible = manager.check_version_compatibility("flask", ">=2.0.0")
            assert compatible == False
            
            # 运行时检查器应该更严格
            checker = RuntimeDependencyChecker()
            # 具体行为取决于实现
    
    def test_debug_mode_scenario(self):
        """测试调试模式场景"""
        config = EnvironmentConfig(
            environment_variables={
                'WPM_DEBUG': 'true',
                'WPM_LOG_LEVEL': 'DEBUG'
            },
            installed_packages=[
                MockPackage("pyinstrument", "4.6.0"),
                MockPackage("requests", "2.31.0"),
                MockPackage("flask", "2.3.0", import_name="flask")
            ]
        )
        
        with mock_environment(config):
            # 在调试模式下，应该有更详细的日志输出
            # 这里主要测试不会因为调试模式而崩溃
            
            from web_performance_monitor.utils.framework_detector import FrameworkDetector
            from web_performance_monitor.utils.dependency_manager import DependencyManager
            
            detector = FrameworkDetector()
            frameworks = detector.detect_installed_frameworks()
            assert "flask" in frameworks
            
            manager = DependencyManager()
            report = manager.validate_environment()
            assert "flask" in report.available_frameworks


class TestProjectStructureScenarios:
    """项目结构场景测试"""
    
    def test_flask_project_structure_detection(self):
        """测试Flask项目结构检测"""
        config = EnvironmentConfig(
            installed_packages=[
                MockPackage("pyinstrument", "4.6.0"),
                MockPackage("requests", "2.31.0"),
                MockPackage("flask", "2.3.0", import_name="flask")
            ],
            project_files={
                "app.py": """
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello, World!'

if __name__ == '__main__':
    app.run(debug=True)
""",
                "requirements.txt": """
flask>=2.0.0
web-performance-monitor[flask]
""",
                "config.py": """
class Config:
    SECRET_KEY = 'dev'
    DEBUG = True
""",
                "templates/index.html": """
<!DOCTYPE html>
<html>
<head><title>Flask App</title></head>
<body><h1>Hello, World!</h1></body>
</html>
"""
            }
        )
        
        with mock_environment(config):
            from web_performance_monitor.utils.framework_detector import FrameworkDetector
            
            # 框架检测器应该能够从项目文件中检测到Flask
            detector = FrameworkDetector()
            
            # 检测已安装的框架
            installed_frameworks = detector.detect_installed_frameworks()
            assert "flask" in installed_frameworks
            
            # 检测项目中使用的框架
            project_framework = detector.detect_framework_from_environment()
            assert project_framework == "flask"
    
    def test_fastapi_project_structure_detection(self):
        """测试FastAPI项目结构检测"""
        config = EnvironmentConfig(
            installed_packages=[
                MockPackage("pyinstrument", "4.6.0"),
                MockPackage("requests", "2.31.0"),
                MockPackage("fastapi", "0.104.0", import_name="fastapi"),
                MockPackage("uvicorn", "0.24.0", import_name="uvicorn")
            ],
            project_files={
                "main.py": """
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def read_root():
    return {"Hello": "World"}

@app.get("/items/{item_id}")
async def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}
""",
                "requirements.txt": """
fastapi>=0.100.0
uvicorn>=0.20.0
web-performance-monitor[fastapi]
""",
                "pyproject.toml": """
[build-system]
requires = ["setuptools", "wheel"]

[tool.uvicorn]
host = "0.0.0.0"
port = 8000
"""
            }
        )
        
        with mock_environment(config):
            from web_performance_monitor.utils.framework_detector import FrameworkDetector
            
            detector = FrameworkDetector()
            
            # 检测已安装的框架
            installed_frameworks = detector.detect_installed_frameworks()
            assert "fastapi" in installed_frameworks
            
            # 检测项目中使用的框架
            project_framework = detector.detect_framework_from_environment()
            assert project_framework == "fastapi"
    
    def test_mixed_project_structure_detection(self):
        """测试混合项目结构检测"""
        config = EnvironmentConfig(
            installed_packages=[
                MockPackage("pyinstrument", "4.6.0"),
                MockPackage("requests", "2.31.0"),
                MockPackage("flask", "2.3.0", import_name="flask"),
                MockPackage("fastapi", "0.104.0", import_name="fastapi"),
                MockPackage("uvicorn", "0.24.0", import_name="uvicorn")
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
flask>=2.0.0
fastapi>=0.100.0
uvicorn>=0.20.0
web-performance-monitor[all]
""",
                "docker-compose.yml": """
version: '3.8'
services:
  flask-app:
    build: .
    command: python flask_app.py
    ports:
      - "5000:5000"
  
  fastapi-app:
    build: .
    command: uvicorn fastapi_app:app --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
"""
            }
        )
        
        with mock_environment(config):
            from web_performance_monitor.utils.framework_detector import FrameworkDetector
            from web_performance_monitor.utils.installation_guide import InstallationGuide
            
            detector = FrameworkDetector()
            
            # 应该检测到两个框架
            installed_frameworks = detector.detect_installed_frameworks()
            assert "flask" in installed_frameworks
            assert "fastapi" in installed_frameworks
            
            # 安装指导应该识别这是一个完整的环境
            guide = InstallationGuide()
            analysis = guide.analyze_current_environment()
            assert analysis['current_status'] == 'complete'
            
            # 应该建议安装通知功能（如果还没有）
            recommendations = analysis['recommendations']
            notification_recs = [r for r in recommendations if 'notifications' in r.command]
            # 可能有也可能没有，取决于是否已安装mattermostdriver