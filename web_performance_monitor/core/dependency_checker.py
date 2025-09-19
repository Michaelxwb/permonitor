"""
运行时依赖检查器模块

提供运行时依赖验证、环境变量控制和智能错误处理功能。
"""

import logging
import os
import warnings
from typing import List, Optional, Dict

from ..utils.framework_detector import FrameworkDetector
from ..models.dependency_models import DependencyConfig
from ..exceptions.exceptions import MissingDependencyError, DependencyError

logger = logging.getLogger(__name__)


class RuntimeDependencyChecker:
    """运行时依赖检查器"""
    
    def __init__(self, strict_mode: Optional[bool] = None):
        """
        初始化运行时依赖检查器
        
        Args:
            strict_mode (Optional[bool]): 严格模式，如果为None则从环境变量读取
        """
        self.config = DependencyConfig.from_env_vars(os.environ)
        
        # 严格模式优先级：参数 > 环境变量 > 默认值
        if strict_mode is not None:
            self.strict_mode = strict_mode
        else:
            self.strict_mode = self.config.strict_dependencies
        
        self.framework_detector = FrameworkDetector()
        
        # 缓存检查结果，避免重复检查
        self._check_cache: Dict[str, bool] = {}
    
    def should_skip_check(self) -> bool:
        """
        检查是否应跳过依赖检查
        
        Returns:
            bool: 是否跳过检查
        """
        return self.config.skip_dependency_check
    
    def check_and_warn(self, required_framework: str) -> bool:
        """
        检查依赖并发出警告或异常
        
        Args:
            required_framework (str): 需要的框架名称
            
        Returns:
            bool: 依赖是否满足
            
        Raises:
            MissingDependencyError: 在严格模式下缺少依赖时抛出
        """
        if self.should_skip_check():
            logger.debug(f"跳过 {required_framework} 依赖检查")
            return True
        
        # 检查缓存
        cache_key = f"{required_framework}_{self.strict_mode}"
        if cache_key in self._check_cache:
            return self._check_cache[cache_key]
        
        # 执行依赖检查
        is_available = self.framework_detector.is_framework_available(required_framework)
        missing_deps = self.get_missing_dependencies(required_framework)
        
        if is_available and not missing_deps:
            self._check_cache[cache_key] = True
            logger.debug(f"{required_framework} 依赖检查通过")
            return True
        
        # 处理依赖缺失情况
        self._handle_missing_dependencies(required_framework, missing_deps)
        
        self._check_cache[cache_key] = False
        return False
    
    def get_missing_dependencies(self, framework: str) -> List[str]:
        """
        获取缺失的依赖列表
        
        Args:
            framework (str): 框架名称
            
        Returns:
            List[str]: 缺失的依赖包名称列表
        """
        missing_deps = []
        
        # 检查框架本身
        if not self.framework_detector.is_framework_available(framework):
            missing_deps.append(framework)
            return missing_deps  # 如果框架本身不可用，直接返回
        
        # 检查框架特定的依赖
        if framework == 'fastapi':
            async_deps = self.framework_detector.check_fastapi_async_dependencies()
            for dep_name, is_available in async_deps.items():
                if not is_available:
                    missing_deps.append(dep_name)
        
        return missing_deps
    
    def _handle_missing_dependencies(self, framework: str, missing_deps: List[str]):
        """
        处理缺失依赖的情况
        
        Args:
            framework (str): 框架名称
            missing_deps (List[str]): 缺失的依赖列表
        """
        if not missing_deps:
            missing_deps = [framework]  # 如果没有具体的缺失依赖，说明框架本身缺失
        
        installation_command = f"pip install web-performance-monitor[{framework}]"
        missing_str = ', '.join(missing_deps)
        
        error_message = (
            f"缺少 {framework} 依赖: {missing_str}。"
            f"请运行: {installation_command}"
        )
        
        if self.strict_mode:
            logger.error(error_message)
            raise MissingDependencyError(framework, missing_deps)
        else:
            logger.warning(error_message)
            warnings.warn(
                f"Missing {framework} dependencies: {missing_str}. "
                f"Install with: {installation_command}",
                UserWarning,
                stacklevel=3
            )
    
    def validate_framework_usage(self, framework: str, feature_name: str = "") -> bool:
        """
        验证框架使用的合法性
        
        Args:
            framework (str): 框架名称
            feature_name (str): 功能名称（用于错误消息）
            
        Returns:
            bool: 是否可以使用该框架
        """
        feature_desc = f" ({feature_name})" if feature_name else ""
        
        try:
            return self.check_and_warn(framework)
        except MissingDependencyError as e:
            logger.error(f"无法使用 {framework}{feature_desc}: {e}")
            raise
        except Exception as e:
            logger.error(f"验证 {framework}{feature_desc} 时出错: {e}")
            if self.strict_mode:
                raise DependencyError(f"Framework validation failed: {e}")
            return False
    
    def check_notification_dependencies(self, notification_type: str) -> bool:
        """
        检查通知依赖
        
        Args:
            notification_type (str): 通知类型 (如 'mattermost')
            
        Returns:
            bool: 通知依赖是否可用
        """
        if self.should_skip_check():
            return True
        
        notification_modules = {
            'mattermost': 'mattermostdriver'
        }
        
        if notification_type not in notification_modules:
            logger.warning(f"不支持的通知类型: {notification_type}")
            return False
        
        module_name = notification_modules[notification_type]
        
        try:
            __import__(module_name)
            logger.debug(f"{notification_type} 通知依赖可用")
            return True
        except ImportError:
            error_message = (
                f"缺少 {notification_type} 通知依赖: {module_name}。"
                f"请运行: pip install web-performance-monitor[notifications]"
            )
            
            if self.strict_mode:
                logger.error(error_message)
                raise MissingDependencyError(notification_type, [module_name])
            else:
                logger.warning(error_message)
                return False
    
    def get_environment_status(self) -> Dict[str, any]:
        """
        获取当前环境的依赖状态
        
        Returns:
            Dict[str, any]: 环境状态信息
        """
        status = {
            'skip_check': self.should_skip_check(),
            'strict_mode': self.strict_mode,
            'frameworks': {},
            'notifications': {},
            'config': {
                'WPM_SKIP_DEPENDENCY_CHECK': os.getenv('WPM_SKIP_DEPENDENCY_CHECK', 'false'),
                'WPM_STRICT_DEPENDENCIES': os.getenv('WPM_STRICT_DEPENDENCIES', 'false'),
                'WPM_AUTO_INSTALL_DEPS': os.getenv('WPM_AUTO_INSTALL_DEPS', 'false')
            }
        }
        
        # 检查框架状态
        for framework in FrameworkDetector.SUPPORTED_FRAMEWORKS.keys():
            try:
                is_available = self.framework_detector.is_framework_available(framework)
                missing_deps = self.get_missing_dependencies(framework)
                
                status['frameworks'][framework] = {
                    'available': is_available and not missing_deps,
                    'missing_dependencies': missing_deps,
                    'version': self.framework_detector.get_framework_version(framework)
                }
            except Exception as e:
                status['frameworks'][framework] = {
                    'available': False,
                    'error': str(e)
                }
        
        # 检查通知状态
        for notification_type in ['mattermost']:
            try:
                status['notifications'][notification_type] = {
                    'available': self.check_notification_dependencies(notification_type)
                }
            except Exception as e:
                status['notifications'][notification_type] = {
                    'available': False,
                    'error': str(e)
                }
        
        return status
    
    def clear_cache(self):
        """清除检查缓存"""
        self._check_cache.clear()
        logger.debug("依赖检查缓存已清除")
    
    def precheck_all_dependencies(self) -> Dict[str, bool]:
        """
        预检查所有依赖
        
        Returns:
            Dict[str, bool]: 框架名称到可用性的映射
        """
        results = {}
        
        for framework in FrameworkDetector.SUPPORTED_FRAMEWORKS.keys():
            try:
                results[framework] = self.check_and_warn(framework)
            except MissingDependencyError:
                results[framework] = False
            except Exception as e:
                logger.warning(f"预检查 {framework} 时出错: {e}")
                results[framework] = False
        
        return results