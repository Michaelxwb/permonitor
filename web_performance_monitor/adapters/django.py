"""
Django专用适配器

为Django框架提供深度集成的监控适配器
"""
import time
from datetime import datetime
from functools import wraps
from typing import Callable, Dict, Any

from .wsgi import WSGIAdapter


class DjangoAdapter(WSGIAdapter):
    """Django框架适配器

    继承自WSGIAdapter，提供Django特定的优化和功能
    """

    def get_adapter_name(self) -> str:
        """获取适配器名称"""
        return "Django"

    def create_middleware(self) -> Callable:
        """创建Django中间件

        Returns:
            Callable: Django中间件类
        """
        from django.utils.deprecation import MiddlewareMixin

        class PerformanceMonitoringMiddleware(MiddlewareMixin):
            """Django性能监控中间件"""

            def __init__(self, get_response):
                """初始化中间件"""
                self.get_response = get_response
                self.monitor = monitor
                self.logger = monitor.logger

            def __call__(self, request):
                """处理请求"""
                # 开始计时
                start_time = time.time()

                # 处理请求
                response = self.get_response(request)

                # 计算执行时间
                execution_time = time.time() - start_time

                # 提取请求信息
                request_data = self._extract_django_request(request)

                # 创建性能指标
                metrics_data = self.monitor.adapter.extract_performance_metrics(
                    self.monitor.adapter.create_request_context(request_data),
                    {
                        'status_code': response.status_code,
                        'headers': dict(response.items())
                    },
                    execution_time
                )

                # 处理性能指标
                self._process_django_metrics(metrics_data,
                                             request_data.get('params', {}))

                return response

            def _extract_django_request(self, request) -> Dict[str, Any]:
                """提取Django请求信息"""
                return {
                    'method': request.method,
                    'path': request.path,
                    'url': request.build_absolute_uri(),
                    'params': {**request.GET.dict(), **request.POST.dict()},
                    'headers': dict(request.headers),
                    'content_type': request.content_type,
                    'content_length': request.META.get('CONTENT_LENGTH', ''),
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'remote_addr': request.META.get('REMOTE_ADDR', ''),
                    'django_user': str(request.user) if hasattr(request,
                                                                'user') and request.user.is_authenticated else 'anonymous'
                }

            def _process_django_metrics(self, metrics_data: Dict[str, Any],
                                        request_params: Dict[str, Any]):
                """处理Django性能指标"""
                # 使用监控器的内部处理逻辑
                if hasattr(self.monitor, '_process_performance_metrics'):
                    self.monitor._process_performance_metrics(metrics_data,
                                                              request_params)
                else:
                    # 备用处理方法
                    self._fallback_process_metrics(metrics_data, request_params)

            def _fallback_process_metrics(self, metrics_data: Dict[str, Any],
                                          request_params: Dict[str, Any]):
                """备用性能指标处理方法"""
                from ..models import PerformanceMetrics
                metrics = PerformanceMetrics(
                    endpoint=metrics_data['endpoint'],
                    request_url=metrics_data['request_url'],
                    request_params=request_params,
                    execution_time=metrics_data['execution_time'],
                    timestamp=datetime.now(),
                    request_method=metrics_data['request_method'],
                    status_code=metrics_data['status_code'],
                )

                # 使用监控器的分析器处理
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

        # 设置monitor引用
        PerformanceMonitoringMiddleware.monitor = self.monitor

        self.logger.info("Django中间件已创建")
        return PerformanceMonitoringMiddleware

    def create_model_monitor(self, model_class):
        """创建Django模型监控装饰器

        Args:
            model_class: Django模型类

        Returns:
            Callable: 模型方法监控装饰器
        """

        def monitor_model_method(method_name: str):
            """监控模型方法"""

            def decorator(method):
                """装饰器实现"""

                @wraps(method)
                def wrapper(*args, **kwargs):
                    """包装器"""
                    monitor_name = f"{model_class.__name__}.{method_name}"
                    return self.monitor.create_decorator(name=monitor_name)(method)(
                        *args, **kwargs)

                return wrapper

            return decorator

        return monitor_model_method

    def create_query_monitor(self):
        """创建Django查询监控器

        Returns:
            Callable: 查询监控装饰器
        """

        def monitor_queryset(queryset, operation_name: str = "query"):
            """监控QuerySet操作"""
            from django.db import connection

            start_time = time.time()
            initial_queries = len(connection.queries)

            try:
                result = list(queryset)  # 强制执行查询
                execution_time = time.time() - start_time
                query_count = len(connection.queries) - initial_queries

                # 创建数据库查询性能指标
                db_metrics = {
                    'endpoint': f"db_query.{operation_name}",
                    'request_url': f"database://{queryset.model._meta.db_table}",
                    'request_params': {
                        'model': queryset.model.__name__,
                        'query_count': query_count,
                        'query_sql': [q['sql'] for q in
                                      connection.queries[initial_queries:]]
                    },
                    'execution_time': execution_time,
                    'request_method': 'DB_QUERY',
                    'status_code': 200,
                }

                # 处理数据库查询性能指标
                self._process_db_metrics(db_metrics)

                return result

            except Exception as e:
                execution_time = time.time() - start_time

                # 错误情况下的指标
                db_metrics = {
                    'endpoint': f"db_query.{operation_name}",
                    'request_url': f"database://{queryset.model._meta.db_table}",
                    'request_params': {'error': str(e)},
                    'execution_time': execution_time,
                    'request_method': 'DB_QUERY',
                    'status_code': 500,
                }

                self._process_db_metrics(db_metrics)
                raise

        return monitor_queryset

    def _process_db_metrics(self, db_metrics: Dict[str, Any]):
        """处理数据库查询性能指标"""
        # 使用监控器的内部处理逻辑
        if hasattr(self.monitor, '_process_performance_metrics'):
            self.monitor._process_performance_metrics(db_metrics,
                                                      db_metrics['request_params'])
        else:
            # 备用处理方法
            from ..models import PerformanceMetrics
            metrics = PerformanceMetrics(
                endpoint=db_metrics['endpoint'],
                request_url=db_metrics['request_url'],
                request_params=db_metrics['request_params'],
                execution_time=db_metrics['execution_time'],
                timestamp=datetime.now(),
                request_method=db_metrics['request_method'],
                status_code=db_metrics['status_code'],
            )

            # 使用监控器的分析器处理
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
