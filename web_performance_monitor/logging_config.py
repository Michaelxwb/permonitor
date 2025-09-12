"""
日志配置模块

提供结构化日志记录和性能开销报告
"""

import logging
import logging.handlers
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from .formatters import MetricsFormatter


class PerformanceLogFormatter(logging.Formatter):
    """性能监控专用日志格式化器"""
    
    def __init__(self, include_performance_info: bool = True):
        """初始化格式化器
        
        Args:
            include_performance_info: 是否包含性能信息
        """
        self.include_performance_info = include_performance_info
        
        # 基础格式
        base_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        super().__init__(base_format)
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录
        
        Args:
            record: 日志记录
            
        Returns:
            str: 格式化后的日志字符串
        """
        # 添加性能监控相关信息
        if self.include_performance_info:
            # 添加组件标识
            if hasattr(record, 'component'):
                record.name = f"{record.name}.{record.component}"
            
            # 添加执行时间信息
            if hasattr(record, 'execution_time'):
                record.msg = f"{record.msg} (执行时间: {record.execution_time:.3f}s)"
            
            # 添加性能开销信息
            if hasattr(record, 'overhead_percent'):
                record.msg = f"{record.msg} (开销: {record.overhead_percent:.2f}%)"
        
        return super().format(record)


class JSONLogFormatter(logging.Formatter):
    """JSON格式日志格式化器"""
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化为JSON格式
        
        Args:
            record: 日志记录
            
        Returns:
            str: JSON格式的日志字符串
        """
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # 添加异常信息
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # 添加自定义字段
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'getMessage', 'exc_info', 'exc_text', 'stack_info']:
                log_data[key] = value
        
        return json.dumps(log_data, ensure_ascii=False, default=str)


class PerformanceLogger:
    """性能监控专用日志器"""
    
    def __init__(self, name: str = "web_performance_monitor", level: str = "INFO"):
        """初始化性能日志器
        
        Args:
            name: 日志器名称
            level: 日志级别
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        
        # 避免重复添加处理器
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self) -> None:
        """设置日志处理器"""
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = PerformanceLogFormatter(include_performance_info=True)
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # 文件处理器（如果配置了日志目录）
        log_dir = os.getenv('WPM_LOG_DIR')
        if log_dir and os.path.exists(log_dir):
            self._setup_file_handler(log_dir)
    
    def _setup_file_handler(self, log_dir: str) -> None:
        """设置文件处理器
        
        Args:
            log_dir: 日志目录
        """
        try:
            # 创建轮转文件处理器
            log_file = os.path.join(log_dir, 'performance_monitor.log')
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            
            # 使用JSON格式用于文件日志
            json_formatter = JSONLogFormatter()
            file_handler.setFormatter(json_formatter)
            
            self.logger.addHandler(file_handler)
            
        except Exception as e:
            self.logger.warning(f"Failed to setup file handler: {e}")
    
    def log_request_start(self, endpoint: str, method: str, url: str) -> None:
        """记录请求开始
        
        Args:
            endpoint: 端点
            method: HTTP方法
            url: 请求URL
        """
        self.logger.debug(
            f"Request started: {method} {endpoint}",
            extra={
                'component': 'monitor',
                'event_type': 'request_start',
                'endpoint': endpoint,
                'method': method,
                'url': url
            }
        )
    
    def log_request_end(self, endpoint: str, method: str, execution_time: float, 
                       status_code: int, will_alert: bool = False) -> None:
        """记录请求结束
        
        Args:
            endpoint: 端点
            method: HTTP方法
            execution_time: 执行时间
            status_code: 状态码
            will_alert: 是否会触发告警
        """
        level = logging.WARNING if will_alert else logging.INFO
        
        self.logger.log(
            level,
            f"Request completed: {method} {endpoint} - {execution_time:.3f}s",
            extra={
                'component': 'monitor',
                'event_type': 'request_end',
                'endpoint': endpoint,
                'method': method,
                'execution_time': execution_time,
                'status_code': status_code,
                'will_alert': will_alert
            }
        )
    
    def log_performance_overhead(self, component: str, overhead_percent: float, 
                               sample_count: int) -> None:
        """记录性能开销
        
        Args:
            component: 组件名称
            overhead_percent: 开销百分比
            sample_count: 样本数量
        """
        level = logging.WARNING if overhead_percent > 5.0 else logging.INFO
        
        self.logger.log(
            level,
            f"Performance overhead: {component} - {overhead_percent:.2f}% (samples: {sample_count})",
            extra={
                'component': 'overhead_tracker',
                'event_type': 'overhead_report',
                'overhead_percent': overhead_percent,
                'sample_count': sample_count,
                'component_name': component
            }
        )
    
    def log_alert_sent(self, endpoint: str, execution_time: float, 
                      notifiers: Dict[str, bool], file_path: str = None) -> None:
        """记录告警发送
        
        Args:
            endpoint: 端点
            execution_time: 执行时间
            notifiers: 通知器发送结果
            file_path: 报告文件路径
        """
        successful_notifiers = [name for name, success in notifiers.items() if success]
        failed_notifiers = [name for name, success in notifiers.items() if not success]
        
        self.logger.info(
            f"Alert sent for {endpoint} ({execution_time:.3f}s) - "
            f"Success: {len(successful_notifiers)}, Failed: {len(failed_notifiers)}",
            extra={
                'component': 'alert_manager',
                'event_type': 'alert_sent',
                'endpoint': endpoint,
                'execution_time': execution_time,
                'successful_notifiers': successful_notifiers,
                'failed_notifiers': failed_notifiers,
                'file_path': file_path
            }
        )
    
    def log_notification_error(self, notifier_type: str, error: str, 
                             retry_count: int = 0) -> None:
        """记录通知发送错误
        
        Args:
            notifier_type: 通知器类型
            error: 错误信息
            retry_count: 重试次数
        """
        self.logger.error(
            f"Notification failed: {notifier_type} - {error} (retry: {retry_count})",
            extra={
                'component': 'notifier',
                'event_type': 'notification_error',
                'notifier_type': notifier_type,
                'error_message': error,
                'retry_count': retry_count
            }
        )
    
    def log_profiling_error(self, operation: str, error: str) -> None:
        """记录性能分析错误
        
        Args:
            operation: 操作名称
            error: 错误信息
        """
        self.logger.error(
            f"Profiling error in {operation}: {error}",
            extra={
                'component': 'analyzer',
                'event_type': 'profiling_error',
                'operation': operation,
                'error_message': error
            }
        )
    
    def log_cache_operation(self, operation: str, key: str, hit: bool = None) -> None:
        """记录缓存操作
        
        Args:
            operation: 操作类型
            key: 缓存键
            hit: 是否命中（仅查询操作）
        """
        message = f"Cache {operation}: {key[:32]}..."
        if hit is not None:
            message += f" ({'HIT' if hit else 'MISS'})"
        
        self.logger.debug(
            message,
            extra={
                'component': 'cache_manager',
                'event_type': 'cache_operation',
                'operation': operation,
                'cache_key': key,
                'cache_hit': hit
            }
        )
    
    def log_config_loaded(self, config_source: str, config_summary: Dict[str, Any]) -> None:
        """记录配置加载
        
        Args:
            config_source: 配置来源
            config_summary: 配置摘要
        """
        self.logger.info(
            f"Configuration loaded from {config_source}",
            extra={
                'component': 'config',
                'event_type': 'config_loaded',
                'config_source': config_source,
                'config_summary': config_summary
            }
        )
    
    def log_stats_summary(self, stats: Dict[str, Any]) -> None:
        """记录统计摘要
        
        Args:
            stats: 统计信息
        """
        self.logger.info(
            f"Stats summary - Requests: {stats.get('total_requests', 0)}, "
            f"Slow: {stats.get('slow_requests', 0)}, "
            f"Alerts: {stats.get('alerts_sent', 0)}",
            extra={
                'component': 'monitor',
                'event_type': 'stats_summary',
                'stats': stats
            }
        )
    
    def get_logger(self) -> logging.Logger:
        """获取底层日志器
        
        Returns:
            logging.Logger: 日志器实例
        """
        return self.logger


# 全局性能日志器实例
_performance_logger = None


def get_performance_logger(name: str = "web_performance_monitor", level: str = "INFO") -> PerformanceLogger:
    """获取性能日志器实例
    
    Args:
        name: 日志器名称
        level: 日志级别
        
    Returns:
        PerformanceLogger: 性能日志器实例
    """
    global _performance_logger
    
    if _performance_logger is None:
        _performance_logger = PerformanceLogger(name, level)
    
    return _performance_logger


def setup_logging_from_config(config) -> PerformanceLogger:
    """根据配置设置日志
    
    Args:
        config: 配置对象
        
    Returns:
        PerformanceLogger: 配置好的性能日志器
    """
    logger = get_performance_logger(level=config.log_level)
    
    # 记录配置加载信息
    logger.log_config_loaded("config_object", config.get_effective_config())
    
    return logger