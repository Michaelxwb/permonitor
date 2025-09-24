"""
Web Performance Monitor

基于pyinstrument的多框架Web应用性能监控和告警工具
支持WSGI/ASGI框架，包括Flask、Django、FastAPI、Tornado、Pyramid等
"""

from .monitor import PerformanceMonitor
from .config import Config
from .exceptions import PerformanceMonitorError, ConfigurationError, NotificationError, ProfilingError

__version__ = "1.1.4"
__all__ = [
    "PerformanceMonitor", 
    "Config", 
    "PerformanceMonitorError", 
    "ConfigurationError",
    "NotificationError",
    "ProfilingError"
]

from .monitor import PerformanceMonitor
from .config import Config
from .exceptions import PerformanceMonitorError, ConfigurationError, NotificationError, ProfilingError

__version__ = "1.0.0"
__all__ = [
    "PerformanceMonitor", 
    "Config", 
    "PerformanceMonitorError", 
    "ConfigurationError",
    "NotificationError",
    "ProfilingError"
]


def quick_setup(threshold_seconds=1.0, enable_local_file=True, local_output_dir="/tmp"):
    """快速设置性能监控，使用默认配置
    
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