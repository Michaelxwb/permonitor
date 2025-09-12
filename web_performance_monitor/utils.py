"""
工具函数模块

提供通用的工具函数
"""

import logging
import json
from typing import Callable, Any, Optional
from datetime import datetime
from .exceptions import PerformanceMonitorError
from .models import PerformanceMetrics


def safe_execute(func: Callable, *args, **kwargs) -> Any:
    """安全执行函数，捕获所有异常
    
    Args:
        func: 要执行的函数
        *args: 位置参数
        **kwargs: 关键字参数
        
    Returns:
        Any: 函数执行结果，异常时返回None
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
        return None


def safe_execute_with_fallback(func: Callable, fallback_value: Any = None, *args, **kwargs) -> Any:
    """安全执行函数，支持自定义回退值
    
    Args:
        func: 要执行的函数
        fallback_value: 异常时返回的回退值
        *args: 位置参数
        **kwargs: 关键字参数
        
    Returns:
        Any: 函数执行结果或回退值
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error in {func.__name__}: {e}, using fallback value: {fallback_value}")
        return fallback_value


def safe_execute_with_retry(func: Callable, max_retries: int = 3, delay: float = 1.0, *args, **kwargs) -> Any:
    """安全执行函数，支持重试机制
    
    Args:
        func: 要执行的函数
        max_retries: 最大重试次数
        delay: 重试间隔（秒）
        *args: 位置参数
        **kwargs: 关键字参数
        
    Returns:
        Any: 函数执行结果，失败时返回None
    """
    import time
    
    logger = logging.getLogger(__name__)
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}, retrying in {delay}s")
                time.sleep(delay)
            else:
                logger.error(f"All {max_retries + 1} attempts failed for {func.__name__}: {e}")
    
    return None


class SafeExecutionContext:
    """安全执行上下文管理器"""
    
    def __init__(self, operation_name: str, suppress_exceptions: bool = True, log_errors: bool = True):
        """初始化安全执行上下文
        
        Args:
            operation_name: 操作名称，用于日志记录
            suppress_exceptions: 是否抑制异常
            log_errors: 是否记录错误日志
        """
        self.operation_name = operation_name
        self.suppress_exceptions = suppress_exceptions
        self.log_errors = log_errors
        self.logger = logging.getLogger(__name__)
        self.exception_occurred = False
        self.exception = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.exception_occurred = True
            self.exception = exc_val
            
            if self.log_errors:
                self.logger.error(f"Error in {self.operation_name}: {exc_val}", exc_info=True)
            
            # 返回True表示抑制异常，False表示重新抛出
            return self.suppress_exceptions
        
        return False
    
    def has_exception(self) -> bool:
        """检查是否发生了异常"""
        return self.exception_occurred
    
    def get_exception(self) -> Optional[Exception]:
        """获取发生的异常"""
        return self.exception


def graceful_degradation(func: Callable, error_message: str = None) -> Callable:
    """优雅降级装饰器
    
    当函数执行失败时，记录错误但不影响程序继续运行
    
    Args:
        func: 要装饰的函数
        error_message: 自定义错误消息
        
    Returns:
        Callable: 装饰后的函数
    """
    def decorator(original_func):
        def wrapper(*args, **kwargs):
            try:
                return original_func(*args, **kwargs)
            except Exception as e:
                logger = logging.getLogger(__name__)
                msg = error_message or f"Graceful degradation in {original_func.__name__}"
                logger.error(f"{msg}: {e}", exc_info=True)
                return None
        return wrapper
    
    if func is None:
        return decorator
    else:
        return decorator(func)


def format_alert_message(metrics: PerformanceMetrics) -> str:
    """格式化告警消息
    
    Args:
        metrics: 性能指标数据
        
    Returns:
        str: 格式化的告警消息
    """
    return f"""性能告警报告
接口: {metrics.endpoint}
请求URL: {metrics.request_url}
请求参数: {json.dumps(metrics.request_params, ensure_ascii=False, indent=2)}
响应时间: {metrics.execution_time:.2f}秒
告警时间: {metrics.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
请求方法: {metrics.request_method}
状态码: {metrics.status_code}
"""


def generate_filename(metrics: PerformanceMetrics) -> str:
    """生成包含时间戳和接口信息的唯一文件名
    
    Args:
        metrics: 性能指标数据
        
    Returns:
        str: 生成的文件名
    """
    timestamp = metrics.timestamp.strftime('%Y%m%d_%H%M%S_%f')[:-3]  # 包含毫秒
    # 清理端点名称，移除特殊字符
    safe_endpoint = (metrics.endpoint
                    .replace('/', '_')
                    .replace('<', '')
                    .replace('>', '')
                    .replace(':', '')
                    .replace('?', '')
                    .replace('&', '_')
                    .replace('=', '_'))
    
    return f"performance_alert_{safe_endpoint}_{timestamp}.html"


def setup_logging(level: str = "INFO") -> logging.Logger:
    """设置日志配置
    
    Args:
        level: 日志级别
        
    Returns:
        logging.Logger: 配置好的日志器
    """
    logger = logging.getLogger("web_performance_monitor")
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    logger.setLevel(getattr(logging, level.upper()))
    return logger


def validate_threshold(threshold: float) -> float:
    """验证阈值配置
    
    Args:
        threshold: 阈值
        
    Returns:
        float: 验证后的阈值
        
    Raises:
        ValueError: 阈值无效时抛出
    """
    if not isinstance(threshold, (int, float)) or threshold <= 0:
        raise ValueError(f"阈值必须是正数，当前值: {threshold}")
    return float(threshold)


def validate_window_days(days: int) -> int:
    """验证时间窗口配置
    
    Args:
        days: 天数
        
    Returns:
        int: 验证后的天数
        
    Raises:
        ValueError: 天数无效时抛出
    """
    if not isinstance(days, int) or days <= 0:
        raise ValueError(f"时间窗口必须是正整数，当前值: {days}")
    return days