"""
依赖管理器模块

提供依赖状态检查、安装指导和环境验证功能。
"""

import logging
import os
from typing import List, Dict, Optional

from .framework_detector import FrameworkDetector
from ..models.dependency_models import DependencyStatus, EnvironmentReport, DependencyConfig, DependencyType

logger = logging.getLogger(__name__)


class DependencyManager:
    """依赖管理器，提供依赖状态检查和管理功能"""
    
    def __init__(self, config: Optional[DependencyConfig] = None):
        """
        初始化依赖管理器
        
        Args:
            config (Optional[DependencyConfig]): 依赖配置，如果为None则从环境变量创建
        """
        self.config = config or DependencyConfig.from_env_vars(os.environ)
        self.framework_detector = FrameworkDetector()
        
        # 支持的框架列表
        self.supported_frameworks = list(FrameworkDetector.SUPPORTED_FRAMEWORKS.keys())
        
        # 通知依赖映射
        self.notification_dependencies = {
            'mattermost': {
                'packages': ['mattermostdriver'],
                'min_versions': {'mattermostdriver': '7.0.0'},
                'installation_command': 'pip install web-performance-monitor[notifications]'
            }
        }
    
    def check_framework_dependencies(self, framework: str) -> DependencyStatus:
        """
        检查特定框架的依赖状态
        
        Args:
            framework (str): 框架名称
            
        Returns:
            DependencyStatus: 依赖状态信息
        """
        if framework not in self.supported_frameworks:
            return DependencyStatus(
                framework=framework,
                is_available=False,
                missing_packages=[framework],
                installation_command=f"pip install web-performance-monitor[{framework}]"
            )
        
        is_available = self.framework_detector.is_framework_available(framework)
        installed_version = self.framework_detector.get_framework_version(framework)
        required_version = FrameworkDetector.SUPPORTED_FRAMEWORKS[framework]['min_version']
        
        missing_packages = []
        if not is_available:
            missing_packages.append(framework)
        
        # 对于FastAPI，还需要检查异步依赖
        if framework == 'fastapi' and is_available:
            async_deps = self.framework_detector.check_fastapi_async_dependencies()
            for dep_name, is_dep_available in async_deps.items():
                if not is_dep_available:
                    missing_packages.append(dep_name)
        
        return DependencyStatus(
            framework=framework,
            is_available=is_available and len(missing_packages) == 0,
            missing_packages=missing_packages,
            installed_version=installed_version,
            required_version=required_version,
            installation_command=f"pip install web-performance-monitor[{framework}]",
            dependency_type=DependencyType.FRAMEWORK
        )
    
    def get_supported_frameworks(self) -> List[str]:
        """
        获取当前支持的框架列表
        
        Returns:
            List[str]: 支持的框架名称列表
        """
        return self.supported_frameworks.copy()
    
    def get_installation_guide(self, framework: str) -> str:
        """
        获取框架依赖安装指导
        
        Args:
            framework (str): 框架名称
            
        Returns:
            str: 安装指导文本
        """
        if framework not in self.supported_frameworks:
            return f"不支持的框架: {framework}"
        
        base_command = f"pip install web-performance-monitor[{framework}]"
        
        if framework == 'flask':
            return f"""Flask 依赖安装指导:
1. 安装 Flask 支持: {base_command}
2. 这将安装 Flask >= 2.0.0
3. 安装完成后可以使用 Flask 中间件和装饰器功能"""
        
        elif framework == 'fastapi':
            return f"""FastAPI 依赖安装指导:
1. 安装 FastAPI 支持: {base_command}
2. 这将安装以下依赖:
   - FastAPI >= 0.100.0
   - uvicorn >= 0.20.0 (ASGI 服务器)
   - aiofiles >= 24.1.0 (异步文件操作)
   - aiohttp >= 3.12.0 (异步HTTP客户端)
3. 安装完成后可以使用 FastAPI 中间件和异步监控功能"""
        
        else:
            return f"安装 {framework} 支持: {base_command}"
    
    def validate_environment(self) -> EnvironmentReport:
        """
        验证当前环境的依赖完整性
        
        Returns:
            EnvironmentReport: 环境验证报告
        """
        report = EnvironmentReport(
            supported_frameworks=self.supported_frameworks.copy()
        )
        
        # 检查每个框架的状态
        for framework in self.supported_frameworks:
            status = self.check_framework_dependencies(framework)
            report.dependency_statuses[framework] = status
            
            if status.is_available:
                report.available_frameworks.append(framework)
            else:
                # 添加安装建议
                if status.missing_packages:
                    missing_str = ', '.join(status.missing_packages)
                    report.add_recommendation(
                        f"安装 {framework} 依赖: {status.installation_command} (缺失: {missing_str})"
                    )
        
        # 检查通知依赖
        self._check_notification_dependencies(report)
        
        # 生成智能建议
        self._generate_smart_recommendations(report)
        
        return report
    
    def _check_notification_dependencies(self, report: EnvironmentReport):
        """检查通知依赖状态"""
        for channel, dep_info in self.notification_dependencies.items():
            missing_packages = []
            
            for package in dep_info['packages']:
                try:
                    __import__(package)
                except ImportError:
                    missing_packages.append(package)
            
            if missing_packages:
                status = DependencyStatus(
                    framework=channel,
                    is_available=False,
                    missing_packages=missing_packages,
                    installation_command=dep_info['installation_command'],
                    dependency_type=DependencyType.NOTIFICATION
                )
                report.dependency_statuses[f"notification_{channel}"] = status
                report.add_warning(f"{channel} 通知功能不可用，缺失依赖: {', '.join(missing_packages)}")
    
    def _generate_smart_recommendations(self, report: EnvironmentReport):
        """生成智能建议"""
        available_count = len(report.available_frameworks)
        total_count = len(report.supported_frameworks)
        
        if available_count == 0:
            report.add_recommendation(
                "当前环境没有安装任何支持的web框架。建议安装: pip install web-performance-monitor[all]"
            )
        elif available_count == 1:
            available_framework = report.available_frameworks[0]
            report.add_recommendation(
                f"检测到 {available_framework} 框架。如需支持其他框架，可安装: pip install web-performance-monitor[all]"
            )
        elif available_count == total_count:
            report.add_recommendation("所有支持的框架都已安装，功能完整。")
        
        # 检查是否有部分可用的框架（有框架但缺少某些依赖）
        for framework, status in report.dependency_statuses.items():
            if (status.dependency_type == DependencyType.FRAMEWORK and 
                not status.is_available and 
                status.installed_version is not None):
                report.add_warning(
                    f"{framework} 已安装但依赖不完整，缺失: {', '.join(status.missing_packages)}"
                )
    
    def get_dependency_summary(self) -> Dict[str, any]:
        """
        获取依赖状态摘要
        
        Returns:
            Dict[str, any]: 依赖状态摘要
        """
        report = self.validate_environment()
        
        return {
            'supported_frameworks': report.supported_frameworks,
            'available_frameworks': report.available_frameworks,
            'missing_frameworks': [
                fw for fw in report.supported_frameworks 
                if fw not in report.available_frameworks
            ],
            'warnings_count': len(report.warnings),
            'recommendations_count': len(report.recommendations),
            'overall_status': 'complete' if len(report.available_frameworks) == len(report.supported_frameworks) else 'partial'
        }
    
    def check_dependencies(self) -> EnvironmentReport:
        """
        执行完整的依赖检查
        
        Returns:
            EnvironmentReport: 完整的环境报告
        """
        if self.config.skip_dependency_check:
            logger.info("跳过依赖检查 (WPM_SKIP_DEPENDENCY_CHECK=true)")
            return EnvironmentReport(
                supported_frameworks=self.supported_frameworks,
                available_frameworks=self.supported_frameworks,  # 假设所有都可用
                recommendations=["依赖检查已跳过"]
            )
        
        return self.validate_environment()
    
    def suggest_optimal_installation(self) -> str:
        """
        根据当前环境建议最优的安装方案
        
        Returns:
            str: 安装建议
        """
        detected_framework = self.framework_detector.detect_framework_from_environment()
        
        if detected_framework:
            return f"检测到 {detected_framework} 环境，建议安装: pip install web-performance-monitor[{detected_framework}]"
        
        installed_frameworks = self.framework_detector.detect_installed_frameworks()
        
        if len(installed_frameworks) > 1:
            frameworks_str = ','.join(installed_frameworks)
            return f"检测到多个框架，建议安装: pip install web-performance-monitor[{frameworks_str}]"
        elif len(installed_frameworks) == 1:
            framework = installed_frameworks[0]
            return f"检测到 {framework}，建议安装: pip install web-performance-monitor[{framework}]"
        else:
            return "未检测到支持的框架，建议安装完整版本: pip install web-performance-monitor[all]"