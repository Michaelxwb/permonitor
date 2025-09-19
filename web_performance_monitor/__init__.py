"""
Web Performance Monitor

基于pyinstrument的多框架web应用性能监控和告警工具
支持Flask和FastAPI框架
"""

# 向后兼容性 - 保持原有API不变
from .core.monitor import PerformanceMonitor
from .config.config import Config
from .exceptions.exceptions import PerformanceMonitorError, ConfigurationError, NotificationError, ProfilingError

# 新的多框架支持
from .config.unified_config import UnifiedConfig
from .monitors.factory import MonitorFactory, create_web_monitor
from .core.base import BaseWebMonitor
from .core.overhead_monitor import PerformanceOverheadMonitor
from .utils.async_retry import AsyncRetryHandler

# 框架特定监控器 - 使用安全导入
try:
    from .monitors.flask_monitor import FlaskMonitor
except ImportError as e:
    FlaskMonitor = None
    import logging
    logging.getLogger(__name__).debug(f"Flask监控器不可用: {e}")

try:
    from .monitors.fastapi_monitor import FastAPIMonitor
except ImportError as e:
    FastAPIMonitor = None
    import logging
    logging.getLogger(__name__).debug(f"FastAPI监控器不可用: {e}")

# 依赖管理相关导入
try:
    from .utils.dependency_manager import DependencyManager
    from .core.dependency_checker import RuntimeDependencyChecker
    from .utils.graceful_degradation import GracefulDegradation, FeatureGate
    from .models.dependency_models import DependencyStatus, EnvironmentReport, DependencyConfig
except ImportError as e:
    import logging
    logging.getLogger(__name__).warning(f"依赖管理功能不完整: {e}")
    DependencyManager = None
    RuntimeDependencyChecker = None
    GracefulDegradation = None
    FeatureGate = None
    DependencyStatus = None
    EnvironmentReport = None
    DependencyConfig = None

__version__ = "2.0.0"
__all__ = [
    # 向后兼容API
    "PerformanceMonitor", 
    "Config", 
    "PerformanceMonitorError", 
    "ConfigurationError",
    "NotificationError",
    "ProfilingError",
    # 新的多框架API
    "UnifiedConfig",
    "MonitorFactory",
    "create_web_monitor",
    "BaseWebMonitor",
    "FlaskMonitor",
    "FastAPIMonitor",
    "PerformanceOverheadMonitor",
    # 依赖管理API
    "DependencyManager",
    "RuntimeDependencyChecker", 
    "GracefulDegradation",
    "FeatureGate",
    "DependencyStatus",
    "EnvironmentReport",
    "DependencyConfig",
    # 便捷函数
    "check_dependencies",
    "get_supported_frameworks",
    "get_dependency_status"
]


def quick_setup(threshold_seconds=1.0, enable_local_file=True, local_output_dir="/tmp"):
    """快速设置性能监控，使用默认配置（向后兼容）
    
    Args:
        threshold_seconds (float): 响应时间阈值，默认1.0秒
        enable_local_file (bool): 是否启用本地文件通知，默认True
        local_output_dir (str): 本地文件输出目录，默认/tmp
        
    Returns:
        PerformanceMonitor: 配置好的性能监控实例
    """
    config = Config(
        threshold_seconds=threshold_seconds,
        enable_local_file=enable_local_file,
        local_output_dir=local_output_dir
    )
    return PerformanceMonitor(config)


def quick_setup_multi_framework(framework=None, threshold_seconds=1.0, enable_local_file=True, local_output_dir="/tmp"):
    """快速设置多框架性能监控
    
    Args:
        framework (str, optional): 框架类型 ('flask' 或 'fastapi')，None时自动检测
        threshold_seconds (float): 响应时间阈值，默认1.0秒
        enable_local_file (bool): 是否启用本地文件通知，默认True
        local_output_dir (str): 本地文件输出目录，默认/tmp
        
    Returns:
        BaseWebMonitor: 配置好的性能监控实例
    """
    config = UnifiedConfig(
        threshold_seconds=threshold_seconds,
        enable_local_file=enable_local_file,
        local_output_dir=local_output_dir
    )
    return MonitorFactory.create_monitor(config, framework)


def check_dependencies() -> dict:
    """
    检查当前环境的依赖状态
    
    Returns:
        dict: 依赖检查报告
    """
    if DependencyManager is None:
        return {
            "error": "依赖管理功能不可用",
            "suggestion": "请确保正确安装了web-performance-monitor包"
        }
    
    try:
        manager = DependencyManager()
        report = manager.check_dependencies()
        return {
            "supported_frameworks": report.supported_frameworks,
            "available_frameworks": report.available_frameworks,
            "recommendations": report.recommendations,
            "warnings": report.warnings,
            "summary": report.get_summary()
        }
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"依赖检查失败: {e}")
        return {
            "error": f"依赖检查失败: {e}",
            "suggestion": "请检查您的Python环境和包安装"
        }


def get_supported_frameworks() -> list:
    """
    获取支持的框架列表
    
    Returns:
        list: 支持的框架名称列表
    """
    if DependencyManager is None:
        return []
    
    try:
        manager = DependencyManager()
        return manager.get_supported_frameworks()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取支持框架列表失败: {e}")
        return []


def get_dependency_status() -> dict:
    """
    获取详细的依赖状态信息
    
    Returns:
        dict: 详细的依赖状态报告
    """
    try:
        return MonitorFactory.get_dependency_status_report()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"获取依赖状态失败: {e}")
        return {
            "error": f"获取依赖状态失败: {e}",
            "suggestion": "请检查您的Python环境和包安装"
        }


# 在模块加载时进行基础的依赖检查和状态报告
def _initialize_dependency_status():
    """初始化时的依赖状态检查"""
    import logging
    logger = logging.getLogger(__name__)
    
    if DependencyManager is None:
        logger.warning("依赖管理功能不可用，某些高级功能可能无法使用")
        return
    
    try:
        # 执行快速的依赖检查
        manager = DependencyManager()
        available_frameworks = manager.get_supported_frameworks()
        
        if available_frameworks:
            logger.info(f"Web Performance Monitor 已加载，支持框架: {', '.join(available_frameworks)}")
            
            # 检查当前环境中可用的框架
            from .utils.framework_detector import FrameworkDetector
            detector = FrameworkDetector()
            installed_frameworks = detector.detect_installed_frameworks()
            
            if installed_frameworks:
                logger.info(f"检测到已安装框架: {', '.join(installed_frameworks)}")
            else:
                logger.info("未检测到已安装的web框架，可使用基础监控功能")
        else:
            logger.warning("未找到支持的框架")
            
    except Exception as e:
        logger.debug(f"初始化依赖检查时出错: {e}")


# 执行初始化检查
_initialize_dependency_status()