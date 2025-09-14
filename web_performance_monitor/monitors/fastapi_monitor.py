"""
FastAPI监控器实现

提供FastAPI框架特定的异步监控功能
"""

import asyncio
import functools
import time
from typing import Callable, Dict, Any

from ..core.base import BaseWebMonitor, RequestExecutionContext, FunctionExecutionContext, AsyncFunctionExecutionContext
from ..utils.performance_analyzer import AsyncPerformanceAnalyzer
from ..alerts.manager import AsyncAlertManager
from ..config.unified_config import UnifiedConfig


class FastAPIMonitor(BaseWebMonitor):
    """FastAPI框架监控器实现"""
    
    def create_middleware(self) -> Callable:
        """创建FastAPI中间件类"""
        monitor = self
        
        try:
            from fastapi import Request, Response
            from starlette.middleware.base import BaseHTTPMiddleware
            
            class PerformanceMiddleware(BaseHTTPMiddleware):
                async def dispatch(self, request: Request, call_next):
                    context = FastAPIRequestContext(request, call_next, monitor)
                    return await monitor._monitor_execution_async(context)
            
            return PerformanceMiddleware
        except ImportError:
            self.logger.error("FastAPI或Starlette未安装，无法创建中间件")
            raise ImportError("FastAPI监控需要安装fastapi和starlette")
    
    def create_decorator(self) -> Callable:
        """创建FastAPI异步装饰器"""
        def decorator(func: Callable) -> Callable:
            if asyncio.iscoroutinefunction(func):
                @functools.wraps(func)
                async def async_wrapper(*args, **kwargs):
                    context = AsyncFunctionExecutionContext(func, args, kwargs)
                    return await self._monitor_execution_async(context)
                return async_wrapper
            else:
                @functools.wraps(func)
                def sync_wrapper(*args, **kwargs):
                    context = FunctionExecutionContext(func, args, kwargs)
                    return self._monitor_execution(context)
                return sync_wrapper
        return decorator
    
    async def _monitor_execution_async(self, execution_context) -> Any:
        """异步监控执行流程"""
        if not self._monitoring_enabled:
            if hasattr(execution_context, 'execute_async'):
                return await execution_context.execute_async()
            else:
                return execution_context.execute()
        
        start_time = time.perf_counter()
        profiler = None
        result = None
        exception_occurred = False
        
        try:
            try:
                profiler = await self.analyzer.start_profiling_async()
            except Exception as e:
                self.logger.warning(f"启动性能分析器失败: {e}")
                profiler = None
            
            if hasattr(execution_context, 'execute_async'):
                result = await execution_context.execute_async()
            else:
                result = execution_context.execute()
        except Exception as e:
            exception_occurred = True
            raise
        finally:
            await self._finalize_monitoring_async(
                profiler, start_time, execution_context, exception_occurred
            )
        
        return result
    
    async def _finalize_monitoring_async(self, profiler, start_time: float,
                                       context, exception_occurred: bool):
        """异步完成监控处理"""
        try:
            end_time = time.perf_counter()
            total_time = end_time - start_time
            
            if profiler:
                execution_time = await self.analyzer.get_execution_time_async(profiler)
                html_report = await self.analyzer.stop_profiling_async(profiler)
                
                # 更新统计
                self._stats.update(execution_time, exception_occurred, is_async=True)
                
                # 异步处理告警
                if execution_time > self.config.threshold_seconds:
                    await self._process_alert_async(context, execution_time, html_report)
                    
        except Exception as e:
            self.logger.error(f"异步监控处理失败: {e}")
    
    async def _process_alert_async(self, context, execution_time: float, html_report: str):
        """异步处理告警"""
        try:
            request_info = context.get_request_info()
            from .models import PerformanceMetrics
            from datetime import datetime
            
            metrics = PerformanceMetrics(
                endpoint=request_info['endpoint'],
                request_url=request_info['request_url'],
                request_params=request_info['request_params'],
                execution_time=execution_time,
                timestamp=datetime.now(),
                request_method=request_info['request_method'],
                status_code=200,
                profiler_data=html_report
            )
            await self.alert_manager.process_alert_async(metrics, html_report)
        except Exception as e:
            self.logger.error(f"异步处理告警失败: {e}")
    
    def _extract_request_info(self, request) -> Dict[str, Any]:
        """从FastAPI请求中提取信息"""
        try:
            # 提取路径参数
            path_params = dict(request.path_params) if hasattr(request, 'path_params') else {}
            
            # 提取查询参数
            query_params = dict(request.query_params) if hasattr(request, 'query_params') else {}
            
            # 提取请求头
            headers = dict(request.headers) if hasattr(request, 'headers') else {}
            
            # 提取路由信息
            route_info = {}
            if hasattr(request, 'scope') and 'route' in request.scope:
                route = request.scope['route']
                route_info = {
                    'route_name': getattr(route, 'name', None),
                    'route_path': getattr(route, 'path', None),
                    'route_methods': getattr(route, 'methods', [])
                }
            
            # 异步提取请求体（如果需要）
            request_body_info = {}
            if request.method in ['POST', 'PUT', 'PATCH']:
                content_type = headers.get('content-type', '')
                if 'application/json' in content_type:
                    request_body_info['content_type'] = 'json'
                elif 'application/x-www-form-urlencoded' in content_type:
                    request_body_info['content_type'] = 'form'
                elif 'multipart/form-data' in content_type:
                    request_body_info['content_type'] = 'multipart'
                else:
                    request_body_info['content_type'] = 'other'
            
            return {
                'endpoint': request.url.path,
                'request_url': str(request.url),
                'request_params': {
                    'path_params': path_params,
                    'query_params': query_params,
                    'route_info': route_info,
                    'request_body_info': request_body_info,
                },
                'request_method': request.method
            }
            
        except Exception as e:
            self.logger.warning(f"提取FastAPI请求信息失败: {e}")
            return {
                'endpoint': '/',
                'request_url': 'http://localhost/',
                'request_params': {},
                'request_method': 'GET'
            }
    
    def _create_analyzer(self) -> AsyncPerformanceAnalyzer:
        """创建异步性能分析器"""
        return AsyncPerformanceAnalyzer()
    
    def _create_alert_manager(self) -> AsyncAlertManager:
        """创建异步告警管理器"""
        return AsyncAlertManager(self.config)


class FastAPIRequestContext(RequestExecutionContext):
    """FastAPI请求执行上下文"""
    
    def __init__(self, request, call_next: Callable, monitor: FastAPIMonitor):
        super().__init__(None, request, monitor)
        self.call_next = call_next
    
    async def execute_async(self):
        """异步执行FastAPI请求处理"""
        return await self.call_next(self.request_data)
    
    def execute(self) -> Any:
        """同步执行（不推荐在FastAPI中使用）"""
        # 为了兼容性提供，但不推荐使用
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.execute_async())