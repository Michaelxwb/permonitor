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

# 框架特定监控器
try:
    from .monitors.flask_monitor import FlaskMonitor
except ImportError:
    FlaskMonitor = None

try:
    from .monitors.fastapi_monitor import FastAPIMonitor
except ImportError:
    FastAPIMonitor = None

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
    "PerformanceOverheadMonitor"
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