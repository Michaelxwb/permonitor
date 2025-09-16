"""
核心抽象层模块

定义所有web框架监控器的统一接口和公共逻辑
"""

import time
import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Callable, Any, Dict, Optional
from datetime import datetime

from ..config.unified_config import UnifiedConfig
from ..models.models import PerformanceMetrics
from ..exceptions.exceptions import PerformanceMonitorError
from .overhead_monitor import PerformanceOverheadMonitor


class ExecutionContext(ABC):
    """执行上下文抽象类，封装不同类型的执行环境"""
    
    @abstractmethod
    def execute(self) -> Any:
        """执行具体操作"""
        pass
    
    @abstractmethod
    def get_request_info(self) -> Dict[str, Any]:
        """获取请求信息"""
        pass


class RequestExecutionContext(ExecutionContext):
    """HTTP请求执行上下文"""
    
    def __init__(self, app: Any, request_data: Any, monitor: 'BaseWebMonitor'):
        self.app = app
        self.request_data = request_data
        self.monitor = monitor
    
    def execute(self) -> Any:
        """执行请求处理 - 由具体框架实现"""
        raise NotImplementedError("子类必须实现execute方法")
    
    def get_request_info(self) -> Dict[str, Any]:
        """获取请求信息"""
        return self.monitor._extract_request_info(self.request_data)


class FunctionExecutionContext(ExecutionContext):
    """函数执行上下文"""
    
    def __init__(self, func: Callable, args: tuple, kwargs: dict):
        self.func = func
        self.args = args
        self.kwargs = kwargs
    
    def execute(self) -> Any:
        """执行函数"""
        return self.func(*self.args, **self.kwargs)
    
    def get_request_info(self) -> Dict[str, Any]:
        """从函数调用创建请求信息"""
        return {
            'endpoint': f"{self.func.__module__}.{self.func.__name__}",
            'request_url': f"function://{self.func.__name__}",
            'request_params': {
                'args_count': len(self.args),
                'kwargs_keys': list(self.kwargs.keys()),
                'function_module': self.func.__module__,
                'function_name': self.func.__name__
            },
            'request_method': 'FUNCTION'
        }


class AsyncFunctionExecutionContext(FunctionExecutionContext):
    """异步函数执行上下文"""
    
    async def execute_async(self) -> Any:
        """异步执行函数"""
        return await self.func(*self.args, **self.kwargs)
    
    def execute(self) -> Any:
        """同步执行（不推荐在异步环境中使用）"""
        # 为了兼容性提供，但不推荐使用
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # 如果没有事件循环，创建一个新的
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.execute_async())


class MonitoringStats:
    """监控统计信息"""
    
    def __init__(self):
        self.total_requests = 0
        self.slow_requests = 0
        self.alerts_sent = 0
        self.async_requests = 0
        self.sync_requests = 0
    
    def update(self, execution_time: float, exception_occurred: bool, is_async: bool = False):
        """更新统计信息"""
        self.total_requests += 1
        if is_async:
            self.async_requests += 1
        else:
            self.sync_requests += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'total_requests': self.total_requests,
            'slow_requests': self.slow_requests,
            'alerts_sent': self.alerts_sent,
            'async_requests': self.async_requests,
            'sync_requests': self.sync_requests,
            'slow_request_rate': (self.slow_requests / max(self.total_requests, 1)) * 100,
            'async_request_rate': (self.async_requests / max(self.total_requests, 1)) * 100,
        }


class BaseWebMonitor(ABC):
    """Web框架监控器抽象基类
    
    定义所有web框架监控器的统一接口和公共逻辑
    """
    
    def __init__(self, config: UnifiedConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.analyzer = self._create_analyzer()
        self.alert_manager = self._create_alert_manager()
        self.overhead_monitor = PerformanceOverheadMonitor(config.max_performance_overhead)
        self._monitoring_enabled = True
        self._stats = MonitoringStats()
    
    @abstractmethod
    def create_middleware(self) -> Callable:
        """创建框架特定的中间件"""
        pass
    
    @abstractmethod
    def create_decorator(self) -> Callable:
        """创建框架特定的装饰器"""
        pass
    
    @abstractmethod
    def _extract_request_info(self, request_context: Any) -> Dict[str, Any]:
        """从框架特定的请求上下文中提取信息"""
        pass
    
    @abstractmethod
    def _create_analyzer(self) -> Any:
        """创建框架特定的性能分析器"""
        pass
    
    @abstractmethod
    def _create_alert_manager(self) -> Any:
        """创建框架特定的告警管理器"""
        pass
    
    # 公共方法 - 模板方法模式
    def _monitor_execution(self, execution_context: ExecutionContext) -> Any:
        """监控执行的通用流程"""
        if not self._monitoring_enabled:
            return execution_context.execute()
        
        start_time = time.perf_counter()
        profiler = None
        result = None
        exception_occurred = False
        
        try:
            profiler = self.analyzer.start_profiling()
            result = execution_context.execute()
        except Exception as e:
            exception_occurred = True
            raise
        finally:
            self._finalize_monitoring(
                profiler, start_time, execution_context, 
                exception_occurred
            )
        
        return result
    
    def _finalize_monitoring(self, profiler, start_time: float, 
                           context: ExecutionContext, exception_occurred: bool):
        """完成监控处理的通用逻辑"""
        try:
            end_time = time.perf_counter()
            total_time = end_time - start_time
            
            if profiler:
                execution_time = self.analyzer.get_execution_time(profiler)
                html_report = self.analyzer.stop_profiling(profiler)
                
                # 记录性能开销
                self.overhead_monitor.record_overhead(execution_time, total_time)
                
                # 检查开销是否可接受
                if not self.overhead_monitor.is_overhead_acceptable():
                    self.logger.warning("监控开销超过阈值，考虑调整配置或禁用监控")
                
                # 更新统计
                self._stats.update(execution_time, exception_occurred)
                
                # 处理告警
                if execution_time > self.config.threshold_seconds:
                    self._process_alert(context, execution_time, html_report)
                    
        except Exception as e:
            self.logger.error(f"监控处理失败: {e}")
    
    def _process_alert(self, context: ExecutionContext, 
                      execution_time: float, html_report: str):
        """处理告警的通用逻辑"""
        try:
            request_info = context.get_request_info()
            metrics = PerformanceMetrics(
                endpoint=request_info['endpoint'],
                request_url=request_info['request_url'],
                request_params=request_info['request_params'],
                execution_time=execution_time,
                timestamp=datetime.now(),
                request_method=request_info['request_method'],
                status_code=200,  # 默认状态码，具体实现可以覆盖
                profiler_data=html_report
            )
            self.alert_manager.process_metrics(metrics, html_report)
        except Exception as e:
            self.logger.error(f"处理告警失败: {e}")
    
    # 公共接口方法
    def get_stats(self) -> Dict[str, Any]:
        """获取监控统计信息"""
        stats = self._stats.to_dict()
        stats['overhead_stats'] = self.overhead_monitor.get_overhead_stats()
        return stats
    
    def enable_monitoring(self) -> None:
        """启用监控"""
        self._monitoring_enabled = True
        self.logger.info("监控已启用")
    
    def disable_monitoring(self) -> None:
        """禁用监控"""
        self._monitoring_enabled = False
        self.logger.info("监控已禁用")
    
    def is_monitoring_enabled(self) -> bool:
        """检查监控是否启用"""
        return self._monitoring_enabled
    
    def cleanup(self) -> None:
        """清理资源"""
        try:
            if hasattr(self.alert_manager, 'cleanup'):
                self.alert_manager.cleanup()
        except Exception as e:
            self.logger.error(f"清理资源失败: {e}")