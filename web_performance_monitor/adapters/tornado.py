"""
Tornado专用适配器

为Tornado框架提供深度集成的监控适配器
"""

import asyncio
from typing import Callable, Dict, Any, Optional
from .base import BaseFrameworkAdapter


class TornadoAdapter(BaseFrameworkAdapter):
    """Tornado框架适配器
    
    为Tornado框架提供专门的监控集成功能
    """
    
    def get_adapter_name(self) -> str:
        """获取适配器名称"""
        return "Tornado"
    
    def create_middleware(self) -> Callable:
        """创建Tornado中间件（通过RequestHandler钩子）
        
        Returns:
            Callable: Tornado处理器基类
        """
        
        class MonitoredRequestHandler:
            """带监控的Tornado RequestHandler基类"""
            
            def prepare(self):
                """请求预处理"""
                import time
                self._monitor_start_time = time.time()
                
                # 提取请求信息
                self._request_info = self._extract_tornado_request()
            
            def on_finish(self):
                """请求后处理"""
                if hasattr(self, '_monitor_start_time'):
                    import time
                    execution_time = time.time() - self._monitor_start_time
                    
                    # 创建性能指标
                    if hasattr(self, '_request_info'):
                        metrics_data = self.monitor.adapter.extract_performance_metrics(
                            self._request_info,
                            {
                                'status_code': self.get_status(),
                                'headers': dict(self._headers)
                            },
                            execution_time
                        )
                        
                        # 处理性能指标
                        self._process_tornado_metrics(metrics_data)
            
            def _extract_tornado_request(self) -> Dict[str, Any]:
                """提取Tornado请求信息"""
                return {
                    'method': self.request.method,
                    'path': self.request.path,
                    'url': self.request.full_url(),
                    'params': {**self.request.query_arguments, **self.request.body_arguments},
                    'headers': dict(self.request.headers),
                    'remote_ip': self.request.remote_ip,
                    'user_agent': self.request.headers.get('User-Agent', ''),
                    'content_type': self.request.headers.get('Content-Type', ''),
                    'content_length': self.request.headers.get('Content-Length', ''),
                }
            
            def _process_tornado_metrics(self, metrics_data: Dict[str, Any]):
                """处理Tornado性能指标"""
                # 使用监控器的内部处理逻辑
                if hasattr(self.monitor, '_process_performance_metrics'):
                    self.monitor._process_performance_metrics(
                        metrics_data, 
                        self._request_info.get('params', {})
                    )
            
            @property
            def monitor(self):
                """获取监控器实例"""
                if hasattr(self.application, 'monitor'):
                    return self.application.monitor
                return None
        
        self.logger.info("Tornado RequestHandler基类已创建")
        return MonitoredRequestHandler
    
    def create_async_decorator(self, name: Optional[str] = None) -> Callable:
        """创建异步性能监控装饰器
        
        Args:
            name: 可选的监控名称
            
        Returns:
            Callable: 异步装饰器函数
        """
        def decorator(func: Callable) -> Callable:
            """装饰器实现"""
            if asyncio.iscoroutinefunction(func):
                # 异步函数装饰器
                @functools.wraps(func)
                async def async_wrapper(*args, **kwargs):
                    """异步函数包装器"""
                    monitor_name = name or func.__name__
                    return await self._monitor_async_function(func, monitor_name, *args, **kwargs)
                
                return async_wrapper
            else:
                # 同步函数装饰器
                return self.monitor.create_decorator(name)(func)
        
        return decorator
    
    async def _monitor_async_function(self, func: Callable, monitor_name: str, *args, **kwargs):
        """监控异步函数执行
        
        Args:
            func: 被监控的异步函数
            monitor_name: 监控名称
            *args: 函数位置参数
            **kwargs: 函数关键字参数
            
        Returns:
            Any: 函数执行结果
        """
        import time
        from ..models import PerformanceMetrics
        from datetime import datetime
        
        if not self.monitor._monitoring_enabled:
            return await func(*args, **kwargs)
        
        # 创建函数信息
        func_info = {
            'endpoint': monitor_name or f"{func.__module__}.{func.__name__}",
            'request_url': f"async_function://{monitor_name or func.__name__}",
            'request_params': {
                'args_count': len(args),
                'kwargs_keys': list(kwargs.keys()) if kwargs else [],
                'function_module': func.__module__,
                'function_name': func.__name__,
                'monitor_name': monitor_name,
                'is_async': True
            },
            'request_method': 'ASYNC_FUNCTION'
        }
        
        # 开始性能分析
        start_time = time.time()
        profiler = None
        profiler_data = None
        
        try:
            # 启动性能分析（如果可用）
            if hasattr(self.monitor, 'analyzer') and hasattr(self.monitor.analyzer, 'start_profiling'):
                profiler = self.monitor.analyzer.start_profiling()
            
            # 执行异步函数
            result = await func(*args, **kwargs)
            
            # 停止性能分析
            if profiler:
                profiler_data = self.monitor.analyzer.stop_profiling(profiler)
            
            # 计算执行时间
            execution_time = time.time() - start_time
            
            # 创建性能指标
            metrics = PerformanceMetrics(
                endpoint=func_info['endpoint'],
                request_url=func_info['request_url'],
                request_params=func_info['request_params'],
                execution_time=execution_time,
                timestamp=datetime.now(),
                request_method=func_info['request_method'],
                status_code=200,
                profiler_data=profiler_data
            )
            
            # 分析性能
            self._finalize_function_monitoring(
                profiler, start_time, func_info, 200, metrics
            )
            
            return result
            
        except Exception as e:
            # 停止性能分析
            if profiler:
                profiler_data = self.monitor.analyzer.stop_profiling(profiler)
            
            execution_time = time.time() - start_time
            
            # 创建错误性能指标
            metrics = PerformanceMetrics(
                endpoint=func_info['endpoint'],
                request_url=func_info['request_url'],
                request_params=func_info['request_params'],
                execution_time=execution_time,
                timestamp=datetime.now(),
                request_method=func_info['request_method'],
                status_code=500,
                profiler_data=profiler_data
            )
            
            # 分析错误性能
            self._finalize_function_monitoring(
                profiler, start_time, func_info, 500, metrics
            )
            
            # 重新抛出异常
            raise
    
    def _finalize_function_monitoring(self, profiler, start_time: float, 
                                    func_info: Dict[str, Any], status_code: int,
                                    metrics: 'PerformanceMetrics'):
        """完成函数监控
        
        Args:
            profiler: 性能分析器
            start_time: 开始时间
            func_info: 函数信息
            status_code: 状态码
            metrics: 性能指标
        """
        # 分析性能
        if hasattr(self.monitor, 'analyzer'):
            if asyncio.iscoroutinefunction(self.monitor.analyzer.analyze_request):
                # 异步分析器
                asyncio.create_task(
                    self.monitor.analyzer.analyze_request(
                        metrics.endpoint,
                        metrics.execution_time,
                        metrics.to_dict()
                    )
                )
            else:
                # 同步分析器，在线程池中执行
                import asyncio
                loop = asyncio.get_event_loop()
                asyncio.create_task(
                    loop.run_in_executor(
                        None,
                        self.monitor.analyzer.analyze_request,
                        metrics.endpoint,
                        metrics.execution_time,
                        metrics.to_dict()
                    )
                )
        
        # 检查是否需要告警
        if hasattr(self.monitor, 'alert_manager'):
            if metrics.is_slow(self.monitor.config.threshold_seconds):
                if asyncio.iscoroutinefunction(self.monitor.alert_manager.handle_alert):
                    # 异步告警管理器
                    asyncio.create_task(self.monitor.alert_manager.handle_alert(metrics))
                else:
                    # 同步告警管理器，在线程池中执行
                    import asyncio
                    loop = asyncio.get_event_loop()
                    asyncio.create_task(
                        loop.run_in_executor(
                            None,
                            self.monitor.alert_manager.handle_alert,
                            metrics
                        )
                    )
    
    def create_coroutine_monitor(self, coro_name: str) -> Callable:
        """创建协程监控上下文管理器
        
        Args:
            coro_name: 协程名称
            
        Returns:
            Callable: 异步上下文管理器
        """
        class CoroutineMonitor:
            """协程监控上下文管理器"""
            
            def __init__(self, monitor, name: str):
                self.monitor = monitor
                self.name = name
                self.start_time = None
            
            async def __aenter__(self):
                """进入上下文"""
                import time
                self.start_time = time.time()
                return self
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                """退出上下文"""
                import time
                from datetime import datetime
                from ..models import PerformanceMetrics
                
                if self.start_time:
                    execution_time = time.time() - self.start_time
                    
                    # 创建性能指标
                    metrics = PerformanceMetrics(
                        endpoint=f"coroutine.{self.name}",
                        request_url=f"coroutine://{self.name}",
                        request_params={'coroutine_name': self.name},
                        execution_time=execution_time,
                        timestamp=datetime.now(),
                        request_method='COROUTINE',
                        status_code=500 if exc_type else 200
                    )
                    
                    # 处理性能指标
                    if hasattr(self.monitor, 'analyzer'):
                        self.monitor.analyzer.analyze_request(
                            metrics.endpoint,
                            metrics.execution_time,
                            metrics.to_dict()
                        )
                    
                    # 检查是否需要告警
                    if hasattr(self.monitor, 'alert_manager'):
                        if metrics.is_slow(self.monitor.config.threshold_seconds):
                            self.monitor.alert_manager.handle_alert(metrics)
        
        return CoroutineMonitor(self.monitor, coro_name)