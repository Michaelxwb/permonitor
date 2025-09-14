"""
异常定义模块

定义性能监控工具的异常层次结构
"""


class PerformanceMonitorError(Exception):
    """性能监控工具基础异常类"""
    pass


class ConfigurationError(PerformanceMonitorError):
    """配置相关错误"""
    pass


class NotificationError(PerformanceMonitorError):
    """通知发送相关错误"""
    pass


class ProfilingError(PerformanceMonitorError):
    """性能分析相关错误"""
    pass


class CacheError(PerformanceMonitorError):
    """缓存操作相关错误"""
    pass