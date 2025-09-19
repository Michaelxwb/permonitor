"""
框架检测器模块

用于检测当前环境中已安装的web框架，提供版本信息和安装建议。
"""

import importlib
import logging
from typing import List, Optional, Dict, Tuple
from packaging import version

logger = logging.getLogger(__name__)


class FrameworkDetector:
    """框架检测器，用于检测已安装的web框架"""
    
    # 支持的框架及其最低版本要求
    SUPPORTED_FRAMEWORKS = {
        'flask': {
            'module': 'flask',
            'min_version': '2.0.0',
            'version_attr': '__version__'
        },
        'fastapi': {
            'module': 'fastapi',
            'min_version': '0.100.0',
            'version_attr': '__version__'
        }
    }
    
    # FastAPI相关的异步依赖
    FASTAPI_ASYNC_DEPS = {
        'uvicorn': {
            'module': 'uvicorn',
            'min_version': '0.20.0',
            'version_attr': '__version__'
        },
        'aiofiles': {
            'module': 'aiofiles',
            'min_version': '24.1.0',
            'version_attr': '__version__'
        },
        'aiohttp': {
            'module': 'aiohttp',
            'min_version': '3.12.0',
            'version_attr': '__version__'
        }
    }
    
    @staticmethod
    def detect_installed_frameworks() -> List[str]:
        """
        检测当前环境中已安装的框架
        
        Returns:
            List[str]: 已安装的框架名称列表
        """
        installed_frameworks = []
        
        for framework_name, framework_info in FrameworkDetector.SUPPORTED_FRAMEWORKS.items():
            if FrameworkDetector.is_framework_available(framework_name):
                installed_frameworks.append(framework_name)
                logger.debug(f"检测到已安装框架: {framework_name}")
        
        return installed_frameworks
    
    @staticmethod
    def is_framework_available(framework: str) -> bool:
        """
        检查特定框架是否可用
        
        Args:
            framework (str): 框架名称
            
        Returns:
            bool: 框架是否可用
        """
        if framework not in FrameworkDetector.SUPPORTED_FRAMEWORKS:
            return False
            
        framework_info = FrameworkDetector.SUPPORTED_FRAMEWORKS[framework]
        
        try:
            module = importlib.import_module(framework_info['module'])
            
            # 检查版本兼容性
            framework_version = FrameworkDetector.get_framework_version(framework)
            if framework_version:
                min_version = framework_info['min_version']
                if version.parse(framework_version) >= version.parse(min_version):
                    return True
                else:
                    logger.warning(f"{framework} 版本 {framework_version} 低于最低要求 {min_version}")
                    return False
            
            # 如果无法获取版本信息，但模块存在，则认为可用
            return True
            
        except ImportError:
            logger.debug(f"框架 {framework} 未安装")
            return False
        except Exception as e:
            logger.warning(f"检测框架 {framework} 时出错: {e}")
            return False
    
    @staticmethod
    def get_framework_version(framework: str) -> Optional[str]:
        """
        获取框架版本信息
        
        Args:
            framework (str): 框架名称
            
        Returns:
            Optional[str]: 框架版本，如果无法获取则返回None
        """
        if framework not in FrameworkDetector.SUPPORTED_FRAMEWORKS:
            return None
            
        framework_info = FrameworkDetector.SUPPORTED_FRAMEWORKS[framework]
        
        try:
            module = importlib.import_module(framework_info['module'])
            version_attr = framework_info['version_attr']
            
            if hasattr(module, version_attr):
                return getattr(module, version_attr)
            
            return None
            
        except ImportError:
            return None
        except Exception as e:
            logger.warning(f"获取 {framework} 版本时出错: {e}")
            return None
    
    @staticmethod
    def check_fastapi_async_dependencies() -> Dict[str, bool]:
        """
        检查FastAPI异步依赖的可用性
        
        Returns:
            Dict[str, bool]: 依赖名称到可用性的映射
        """
        async_deps_status = {}
        
        for dep_name, dep_info in FrameworkDetector.FASTAPI_ASYNC_DEPS.items():
            try:
                module = importlib.import_module(dep_info['module'])
                
                # 检查版本
                if hasattr(module, dep_info['version_attr']):
                    dep_version = getattr(module, dep_info['version_attr'])
                    min_version = dep_info['min_version']
                    
                    if version.parse(dep_version) >= version.parse(min_version):
                        async_deps_status[dep_name] = True
                    else:
                        logger.warning(f"{dep_name} 版本 {dep_version} 低于最低要求 {min_version}")
                        async_deps_status[dep_name] = False
                else:
                    # 无法获取版本但模块存在
                    async_deps_status[dep_name] = True
                    
            except ImportError:
                async_deps_status[dep_name] = False
            except Exception as e:
                logger.warning(f"检查 {dep_name} 时出错: {e}")
                async_deps_status[dep_name] = False
        
        return async_deps_status
    
    @staticmethod
    def suggest_installation(missing_frameworks: List[str]) -> Dict[str, str]:
        """
        为缺失的框架提供安装建议
        
        Args:
            missing_frameworks (List[str]): 缺失的框架列表
            
        Returns:
            Dict[str, str]: 框架名称到安装命令的映射
        """
        suggestions = {}
        
        for framework in missing_frameworks:
            if framework == 'flask':
                suggestions[framework] = "pip install web-performance-monitor[flask]"
            elif framework == 'fastapi':
                suggestions[framework] = "pip install web-performance-monitor[fastapi]"
            else:
                suggestions[framework] = f"pip install web-performance-monitor[{framework}]"
        
        return suggestions
    
    @staticmethod
    def get_framework_status_report() -> Dict[str, Dict]:
        """
        获取所有框架的详细状态报告
        
        Returns:
            Dict[str, Dict]: 框架状态报告
        """
        report = {}
        
        for framework_name in FrameworkDetector.SUPPORTED_FRAMEWORKS.keys():
            is_available = FrameworkDetector.is_framework_available(framework_name)
            framework_version = FrameworkDetector.get_framework_version(framework_name)
            min_version = FrameworkDetector.SUPPORTED_FRAMEWORKS[framework_name]['min_version']
            
            report[framework_name] = {
                'available': is_available,
                'version': framework_version,
                'min_version': min_version,
                'installation_command': f"pip install web-performance-monitor[{framework_name}]"
            }
            
            # 为FastAPI添加异步依赖状态
            if framework_name == 'fastapi':
                report[framework_name]['async_dependencies'] = FrameworkDetector.check_fastapi_async_dependencies()
        
        return report
    
    @staticmethod
    def detect_framework_from_environment() -> Optional[str]:
        """
        从当前环境自动检测最可能使用的框架
        
        Returns:
            Optional[str]: 检测到的框架名称，如果无法确定则返回None
        """
        installed_frameworks = FrameworkDetector.detect_installed_frameworks()
        
        if not installed_frameworks:
            return None
        
        # 如果只有一个框架，直接返回
        if len(installed_frameworks) == 1:
            return installed_frameworks[0]
        
        # 如果有多个框架，优先选择FastAPI（因为它通常用于更现代的项目）
        if 'fastapi' in installed_frameworks:
            return 'fastapi'
        
        # 否则返回第一个检测到的框架
        return installed_frameworks[0]