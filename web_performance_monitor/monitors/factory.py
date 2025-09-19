"""
监控器工厂和自动检测

提供监控器创建和框架自动检测功能，支持依赖检查和优雅降级
"""

import sys
import inspect
import logging
from typing import Optional, Type, List, Dict

from ..core.base import BaseWebMonitor
from ..config.unified_config import UnifiedConfig
from ..core.dependency_checker import RuntimeDependencyChecker
from ..utils.dependency_manager import DependencyManager
from ..utils.graceful_degradation import GracefulDegradation
from ..exceptions.exceptions import MissingDependencyError, FrameworkNotSupportedError


class MonitorFactory:
    """监控器工厂类"""
    
    _monitor_registry = {}
    _logger = logging.getLogger(__name__)
    
    @classmethod
    def create_monitor(cls, config: UnifiedConfig, 
                      framework: Optional[str] = None) -> BaseWebMonitor:
        """创建监控器实例"""
        if framework is None:
            framework = cls.detect_framework()
        
        if framework not in cls._monitor_registry:
            # 延迟导入以避免循环依赖
            cls._register_default_monitors()
        
        if framework not in cls._monitor_registry:
            supported_frameworks = cls.get_supported_frameworks()
            raise FrameworkNotSupportedError(framework, supported_frameworks)
        
        monitor_class = cls._monitor_registry[framework]
        return monitor_class(config)
    
    @classmethod
    def create_monitor_with_dependency_check(
        cls, 
        config: UnifiedConfig, 
        framework: Optional[str] = None,
        strict_dependencies: bool = False
    ) -> BaseWebMonitor:
        """
        创建监控器并进行依赖检查
        
        Args:
            config (UnifiedConfig): 统一配置
            framework (Optional[str]): 框架名称，None时自动检测
            strict_dependencies (bool): 是否使用严格依赖模式
            
        Returns:
            BaseWebMonitor: 监控器实例
            
        Raises:
            MissingDependencyError: 严格模式下缺少依赖时抛出
            FrameworkNotSupportedError: 不支持的框架时抛出
        """
        # 创建依赖检查器
        dependency_checker = RuntimeDependencyChecker(strict_mode=strict_dependencies)
        
        # 如果没有指定框架，尝试自动检测
        if framework is None:
            try:
                framework = cls.detect_framework_with_dependency_check(dependency_checker)
            except RuntimeError as e:
                cls._logger.warning(f"框架自动检测失败: {e}")
                # 在非严格模式下，尝试提供降级功能
                if not strict_dependencies:
                    return cls._create_fallback_monitor(config)
                raise
        
        # 检查框架依赖
        if not dependency_checker.validate_framework_usage(framework, "monitor creation"):
            # 依赖检查失败，在非严格模式下尝试降级
            if not strict_dependencies:
                cls._logger.warning(f"框架 {framework} 依赖不完整，尝试降级模式")
                return cls._create_fallback_monitor(config)
            # 严格模式下，异常已在validate_framework_usage中抛出
        
        # 创建监控器
        return cls.create_monitor(config, framework)
    
    @classmethod
    def get_available_monitors(cls) -> Dict[str, bool]:
        """
        获取可用的监控器及其依赖状态
        
        Returns:
            Dict[str, bool]: 监控器名称到可用性的映射
        """
        cls._register_default_monitors()
        dependency_checker = RuntimeDependencyChecker()
        
        available_monitors = {}
        for framework in cls._monitor_registry.keys():
            try:
                is_available = dependency_checker.check_and_warn(framework)
                available_monitors[framework] = is_available
            except MissingDependencyError:
                available_monitors[framework] = False
            except Exception as e:
                cls._logger.warning(f"检查 {framework} 监控器可用性时出错: {e}")
                available_monitors[framework] = False
        
        return available_monitors
    
    @classmethod
    def detect_framework(cls) -> str:
        """自动检测web框架类型 - 满足Requirement 10的自动检测要求"""
        # 检测FastAPI
        if cls._is_fastapi_available():
            cls._logger.info("检测到FastAPI框架")
            return 'fastapi'
        
        # 检测Flask
        if cls._is_flask_available():
            cls._logger.info("检测到Flask框架")
            return 'flask'
        
        raise RuntimeError("无法检测到支持的web框架")
    
    @classmethod
    def detect_framework_with_dependency_check(cls, dependency_checker: RuntimeDependencyChecker) -> str:
        """
        带依赖检查的框架自动检测
        
        Args:
            dependency_checker (RuntimeDependencyChecker): 依赖检查器
            
        Returns:
            str: 检测到的框架名称
            
        Raises:
            RuntimeError: 无法检测到支持的框架时抛出
        """
        # 使用增强的框架检测器
        from ..utils.framework_detector import FrameworkDetector
        
        detected_framework = FrameworkDetector.detect_framework_from_environment()
        
        if detected_framework:
            # 验证检测到的框架的依赖完整性
            if dependency_checker.check_and_warn(detected_framework):
                cls._logger.info(f"检测到可用框架: {detected_framework}")
                return detected_framework
            else:
                cls._logger.warning(f"检测到框架 {detected_framework} 但依赖不完整")
        
        # 回退到原有的检测逻辑
        return cls.detect_framework()
    
    @classmethod
    def _is_fastapi_available(cls) -> bool:
        """检测FastAPI是否可用 - 满足Requirement 10的自动检测要求"""
        try:
            import fastapi
            
            # 检查是否有FastAPI应用实例在运行
            # 创建副本以避免在迭代时修改字典
            modules_copy = dict(sys.modules)
            for name, obj in modules_copy.items():
                if hasattr(obj, 'FastAPI'):
                    return True
                # 检查模块中是否有FastAPI应用实例
                for attr_name in dir(obj):
                    try:
                        attr = getattr(obj, attr_name, None)
                        if attr is not None and attr is not NotImplemented and hasattr(attr, '__class__') and 'FastAPI' in str(attr.__class__):
                            return True
                    except:
                        continue
            
            # 检查调用栈中是否有FastAPI相关代码
            frame = inspect.currentframe()
            try:
                while frame:
                    if 'fastapi' in str(frame.f_code.co_filename).lower():
                        return True
                    frame = frame.f_back
            finally:
                del frame
            
            return 'fastapi' in sys.modules
        except ImportError:
            return False
    
    @classmethod
    def _is_flask_available(cls) -> bool:
        """检测Flask是否可用 - 满足Requirement 10的自动检测要求"""
        try:
            import flask
            
            # 检查是否有Flask应用实例
            # 创建副本以避免在迭代时修改字典
            modules_copy = dict(sys.modules)
            for name, obj in modules_copy.items():
                if hasattr(obj, 'Flask'):
                    return True
                # 检查模块中是否有Flask应用实例
                for attr_name in dir(obj):
                    try:
                        attr = getattr(obj, attr_name, None)
                        if attr is not None and attr is not NotImplemented and hasattr(attr, '__class__') and 'Flask' in str(attr.__class__):
                            return True
                    except:
                        continue
            
            # 检查调用栈中是否有Flask相关代码
            frame = inspect.currentframe()
            try:
                while frame:
                    if 'flask' in str(frame.f_code.co_filename).lower():
                        return True
                    frame = frame.f_back
            finally:
                del frame
            
            return 'flask' in sys.modules
        except ImportError:
            return False
    
    @classmethod
    def register_monitor(cls, framework: str, monitor_class: Type[BaseWebMonitor]):
        """注册新的监控器类型"""
        cls._monitor_registry[framework] = monitor_class
        cls._logger.info(f"注册监控器: {framework} -> {monitor_class.__name__}")
    
    @classmethod
    def get_supported_frameworks(cls) -> List[str]:
        """获取支持的框架列表"""
        cls._register_default_monitors()
        return list(cls._monitor_registry.keys())
    
    @classmethod
    def _register_default_monitors(cls):
        """注册默认监控器"""
        if not cls._monitor_registry:
            try:
                from .flask_monitor import FlaskMonitor
                cls._monitor_registry['flask'] = FlaskMonitor
            except ImportError:
                cls._logger.warning("Flask监控器导入失败")
            
            try:
                from .fastapi_monitor import FastAPIMonitor
                cls._monitor_registry['fastapi'] = FastAPIMonitor
            except ImportError:
                cls._logger.warning("FastAPI监控器导入失败")
    
    @classmethod
    def _create_fallback_monitor(cls, config: UnifiedConfig) -> BaseWebMonitor:
        """
        创建回退监控器（基础功能）
        
        Args:
            config (UnifiedConfig): 配置
            
        Returns:
            BaseWebMonitor: 基础监控器实例
        """
        cls._logger.info("创建回退监控器，提供基础性能监控功能")
        
        # 使用基础监控器类
        from ..core.base import BaseWebMonitor
        
        # 创建降级配置
        degraded_config_dict = GracefulDegradation.get_degraded_config(config.to_dict())
        degraded_config = UnifiedConfig.from_dict(degraded_config_dict)
        
        return BaseWebMonitor(degraded_config)
    
    @classmethod
    def get_dependency_status_report(cls) -> Dict[str, any]:
        """
        获取依赖状态报告
        
        Returns:
            Dict[str, any]: 依赖状态报告
        """
        dependency_manager = DependencyManager()
        report = dependency_manager.validate_environment()
        
        # 添加监控器特定信息
        available_monitors = cls.get_available_monitors()
        
        return {
            "framework_dependencies": report.dependency_statuses,
            "available_monitors": available_monitors,
            "supported_frameworks": report.supported_frameworks,
            "available_frameworks": report.available_frameworks,
            "recommendations": report.recommendations,
            "warnings": report.warnings,
            "summary": report.get_summary()
        }
    
    @classmethod
    def suggest_optimal_setup(cls) -> str:
        """
        建议最优的设置方案
        
        Returns:
            str: 设置建议
        """
        dependency_manager = DependencyManager()
        return dependency_manager.suggest_optimal_installation()


def create_web_monitor(framework: str = None, config: dict = None, 
                      check_dependencies: bool = True, strict_dependencies: bool = False) -> BaseWebMonitor:
    """
    创建web监控器的统一入口
    
    Args:
        framework (str, optional): 框架名称，None时自动检测
        config (dict, optional): 配置字典
        check_dependencies (bool): 是否检查依赖
        strict_dependencies (bool): 是否使用严格依赖模式
        
    Returns:
        BaseWebMonitor: 监控器实例
    """
    if config is None:
        # 使用默认配置
        unified_config = UnifiedConfig()
    else:
        unified_config = UnifiedConfig.from_dict(config)
    
    if check_dependencies:
        return MonitorFactory.create_monitor_with_dependency_check(
            unified_config, framework, strict_dependencies
        )
    else:
        return MonitorFactory.create_monitor(unified_config, framework)