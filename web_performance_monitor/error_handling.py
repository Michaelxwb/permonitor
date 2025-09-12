"""
错误处理模块

提供全面的错误处理和恢复机制
"""

import logging
import traceback
import functools
from typing import Callable, Any, Optional, Dict, List
from datetime import datetime
from .exceptions import PerformanceMonitorError


class ErrorHandler:
    """错误处理器
    
    提供统一的错误处理和恢复机制
    """
    
    def __init__(self, logger_name: str = None):
        """初始化错误处理器
        
        Args:
            logger_name: 日志器名称
        """
        self.logger = logging.getLogger(logger_name or __name__)
        self.error_counts: Dict[str, int] = {}
        self.error_history: List[Dict[str, Any]] = []
        self.max_history_size = 100
    
    def handle_error(self, error: Exception, context: str = "", suppress: bool = True) -> bool:
        """处理错误
        
        Args:
            error: 异常对象
            context: 错误上下文信息
            suppress: 是否抑制异常
            
        Returns:
            bool: 是否成功处理错误
        """
        try:
            error_type = type(error).__name__
            error_message = str(error)
            
            # 记录错误统计
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
            
            # 记录错误历史
            error_record = {
                'timestamp': datetime.now(),
                'error_type': error_type,
                'error_message': error_message,
                'context': context,
                'traceback': traceback.format_exc()
            }
            
            self.error_history.append(error_record)
            
            # 限制历史记录大小
            if len(self.error_history) > self.max_history_size:
                self.error_history.pop(0)
            
            # 记录日志
            log_message = f"Error in {context}: {error_message}" if context else f"Error: {error_message}"
            self.logger.error(log_message, exc_info=True)
            
            return True
            
        except Exception as e:
            # 错误处理器本身出错
            self.logger.critical(f"Error handler failed: {e}")
            return False
    
    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计信息
        
        Returns:
            Dict[str, Any]: 错误统计信息
        """
        total_errors = sum(self.error_counts.values())
        
        return {
            'total_errors': total_errors,
            'error_counts': self.error_counts.copy(),
            'recent_errors': self.error_history[-10:],  # 最近10个错误
            'error_types': list(self.error_counts.keys())
        }
    
    def clear_history(self) -> None:
        """清空错误历史"""
        self.error_history.clear()
        self.error_counts.clear()
        self.logger.info("Error history cleared")


# 全局错误处理器实例
_global_error_handler = ErrorHandler("web_performance_monitor.global")


def get_global_error_handler() -> ErrorHandler:
    """获取全局错误处理器
    
    Returns:
        ErrorHandler: 全局错误处理器实例
    """
    return _global_error_handler


def handle_monitoring_error(func: Callable) -> Callable:
    """监控错误处理装饰器
    
    确保监控相关的错误不会影响主应用
    
    Args:
        func: 要装饰的函数
        
    Returns:
        Callable: 装饰后的函数
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            _global_error_handler.handle_error(e, f"monitoring.{func.__name__}")
            return None
    
    return wrapper


def handle_notification_error(func: Callable) -> Callable:
    """通知错误处理装饰器
    
    确保通知发送错误不会影响主应用
    
    Args:
        func: 要装饰的函数
        
    Returns:
        Callable: 装饰后的函数
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            _global_error_handler.handle_error(e, f"notification.{func.__name__}")
            return False  # 通知失败返回False
    
    return wrapper


def handle_profiling_error(func: Callable) -> Callable:
    """性能分析错误处理装饰器
    
    确保性能分析错误不会影响主应用
    
    Args:
        func: 要装饰的函数
        
    Returns:
        Callable: 装饰后的函数
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            _global_error_handler.handle_error(e, f"profiling.{func.__name__}")
            return None
    
    return wrapper


class CircuitBreaker:
    """断路器模式实现
    
    当错误率过高时暂时停止执行，避免系统过载
    """
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        """初始化断路器
        
        Args:
            failure_threshold: 失败阈值
            recovery_timeout: 恢复超时时间（秒）
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        self.logger = logging.getLogger(__name__)
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """通过断路器调用函数
        
        Args:
            func: 要调用的函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            Any: 函数执行结果
            
        Raises:
            PerformanceMonitorError: 断路器开启时抛出
        """
        if self.state == 'OPEN':
            if self._should_attempt_reset():
                self.state = 'HALF_OPEN'
                self.logger.info("Circuit breaker entering HALF_OPEN state")
            else:
                raise PerformanceMonitorError("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """检查是否应该尝试重置断路器"""
        if self.last_failure_time is None:
            return True
        
        import time
        return time.time() - self.last_failure_time >= self.recovery_timeout
    
    def _on_success(self) -> None:
        """成功时的处理"""
        if self.state == 'HALF_OPEN':
            self.state = 'CLOSED'
            self.logger.info("Circuit breaker reset to CLOSED state")
        
        self.failure_count = 0
    
    def _on_failure(self) -> None:
        """失败时的处理"""
        import time
        
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'
            self.logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def get_state(self) -> Dict[str, Any]:
        """获取断路器状态
        
        Returns:
            Dict[str, Any]: 断路器状态信息
        """
        return {
            'state': self.state,
            'failure_count': self.failure_count,
            'failure_threshold': self.failure_threshold,
            'last_failure_time': self.last_failure_time,
            'recovery_timeout': self.recovery_timeout
        }


class RetryManager:
    """重试管理器"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        """初始化重试管理器
        
        Args:
            max_retries: 最大重试次数
            base_delay: 基础延迟时间
            max_delay: 最大延迟时间
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.logger = logging.getLogger(__name__)
    
    def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """执行函数并在失败时重试
        
        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            Any: 函数执行结果
            
        Raises:
            Exception: 所有重试都失败时抛出最后一个异常
        """
        import time
        import random
        
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    # 计算延迟时间（指数退避 + 随机抖动）
                    delay = min(
                        self.base_delay * (2 ** attempt) + random.uniform(0, 1),
                        self.max_delay
                    )
                    
                    self.logger.warning(
                        f"Attempt {attempt + 1} failed for {func.__name__}: {e}, "
                        f"retrying in {delay:.2f}s"
                    )
                    
                    time.sleep(delay)
                else:
                    self.logger.error(
                        f"All {self.max_retries + 1} attempts failed for {func.__name__}: {e}"
                    )
        
        raise last_exception


# 全局断路器和重试管理器实例
_monitoring_circuit_breaker = CircuitBreaker(failure_threshold=10, recovery_timeout=300)
_notification_retry_manager = RetryManager(max_retries=3, base_delay=1.0)


def get_monitoring_circuit_breaker() -> CircuitBreaker:
    """获取监控断路器
    
    Returns:
        CircuitBreaker: 监控断路器实例
    """
    return _monitoring_circuit_breaker


def get_notification_retry_manager() -> RetryManager:
    """获取通知重试管理器
    
    Returns:
        RetryManager: 通知重试管理器实例
    """
    return _notification_retry_manager