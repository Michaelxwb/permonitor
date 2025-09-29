"""
Sanic适配器

为Sanic框架提供性能监控适配，支持异步请求处理
"""
import time
from datetime import datetime
from typing import Callable, Dict, Any, Optional

from .base import BaseFrameworkAdapter


class SanicAdapter(BaseFrameworkAdapter):
    """Sanic框架适配器

    支持Sanic异步Web框架的性能监控
    """

    def get_adapter_name(self) -> str:
        """获取适配器名称"""
        return "Sanic"

    def create_middleware(self) -> Callable:
        """创建Sanic中间件

        Returns:
            Callable: Sanic中间件函数
        """

        def sanic_middleware(request) -> Optional[Dict[str, Any]]:
            """Sanic中间件实现

            Args:
                request: Sanic请求对象

            Returns:
                Optional[Dict[str, Any]]: 响应数据（如果有错误）
            """
            return self._monitor_sanic_request(request)

        self.logger.info("Sanic中间件已创建")
        return sanic_middleware

    def _monitor_sanic_request(self, request) -> Optional[Dict[str, Any]]:
        """监控Sanic请求

        Args:
            request: Sanic请求对象

        Returns:
            Optional[Dict[str, Any]]: 错误响应（如果有）
        """
        # 提取请求信息
        request_data = self._extract_sanic_request(request)
        request_context = self.create_request_context(request_data)

        # 开始监控
        start_time = time.time()

        try:
            # 存储监控数据到请求对象，供响应处理使用
            request.ctx.perf_monitor_data = {
                'start_time': start_time,
                'request_context': request_context,
                'profiler': None
            }

            # 启动性能分析
            profiler = self.monitor.analyzer.start_profiling()
            if profiler:
                request.ctx.perf_monitor_data['profiler'] = profiler

        except Exception as e:
            self.logger.error(f"Sanic请求监控启动失败: {e}")
            # 不影响原应用，继续处理请求

        return None  # 继续正常处理请求

    def process_response(self, request, response) -> None:
        """处理Sanic响应

        Args:
            request: Sanic请求对象
            response: Sanic响应对象
        """
        # 检查是否有监控数据
        if not hasattr(request.ctx, 'perf_monitor_data'):
            return

        monitor_data = request.ctx.perf_monitor_data

        try:
            start_time = monitor_data.get('start_time', time.time())
            request_context = monitor_data.get('request_context', {})
            profiler = monitor_data.get('profiler')

            # 计算执行时间
            execution_time = time.time() - start_time

            # 提取响应信息
            status_code = getattr(response, 'status', 200)

            # 停止性能分析
            html_report = None
            if profiler:
                html_report = self.monitor.analyzer.stop_profiling(profiler)

            # 创建性能指标
            metrics_data = {
                'endpoint': request_context.get('endpoint', '/'),
                'request_url': request_context.get('request_url', ''),
                'request_method': request_context.get('request_method', 'GET'),
                'execution_time': execution_time,
                'status_code': status_code,
                'timestamp': datetime.now(),
                'request_params': request_context.get('request_params', {})
            }

            # 创建性能指标对象
            from ..models import PerformanceMetrics
            metrics = PerformanceMetrics(
                endpoint=metrics_data['endpoint'],
                request_url=metrics_data['request_url'],
                request_params=request_context.get('request_params', {}),
                execution_time=execution_time,
                timestamp=datetime.now(),
                request_method=metrics_data['request_method'],
                status_code=status_code,
                profiler_data=html_report
            )

            # 使用监控器的内部处理逻辑
            if hasattr(self.monitor, 'alert_manager'):
                if metrics.is_slow(self.monitor.config.threshold_seconds):
                    self.monitor.alert_manager.process_metrics(metrics, html_report)

            # 记录请求完成
            if hasattr(self.monitor, 'perf_logger'):
                self.monitor.perf_logger.log_request_end(
                    request_context.get('endpoint', '/'),
                    request_context.get('request_method', 'GET'),
                    execution_time,
                    status_code,
                    execution_time > self.monitor.config.threshold_seconds
                )

        except Exception as e:
            self.logger.error(f"Sanic响应处理错误: {e}")

    def _extract_sanic_request(self, request) -> Dict[str, Any]:
        """提取Sanic请求信息

        Args:
            request: Sanic请求对象

        Returns:
            Dict[str, Any]: 标准化的请求数据
        """
        try:
            # 构建完整的URL
            scheme = request.scheme
            host = request.host
            path = request.path
            query_string = request.query_string

            url = f"{scheme}://{host}{path}"
            if query_string:
                url += f"?{query_string}"

            # 提取查询参数
            params = dict(request.args) if request.args else {}

            # 提取请求头
            headers = dict(request.headers) if request.headers else {}

            # 提取路径参数
            path_params = dict(request.match_info) if hasattr(request,
                                                              'match_info') else {}

            # 合并所有参数
            all_params = {**params, **path_params}

            # 提取POST数据（如果是POST请求）
            if request.method in ['POST', 'PUT', 'PATCH']:
                try:
                    if request.json:
                        all_params['json_body'] = request.json
                    elif request.form:
                        all_params['form_data'] = dict(request.form)
                    elif request.body:
                        body_size = len(request.body)
                        if body_size < 10240:  # 限制大小10KB
                            all_params['request_body'] = {
                                'size': body_size,
                                'type': 'raw'
                            }
                except Exception as e:
                    self.logger.debug(f"解析请求体失败: {e}")

            return {
                'method': request.method,
                'path': path,
                'url': url,
                'params': all_params,
                'headers': headers,
                'query_string': query_string,
                'path_params': path_params,
            }

        except Exception as e:
            self.logger.warning(f"提取Sanic请求信息失败: {e}")
            return {
                'method': 'GET',
                'path': '/',
                'url': 'http://localhost/',
                'params': {},
                'headers': {},
                'query_string': '',
                'path_params': {},
            }

    def _process_metrics_sync(self, metrics_data: Dict[str, Any],
                              request_params: Dict[str, Any]):
        """同步处理性能指标

        Args:
            metrics_data: 性能指标数据
            request_params: 请求参数
        """
        # 使用监控器的内部处理逻辑
        if hasattr(self.monitor, '_process_performance_metrics'):
            self.monitor._process_performance_metrics(metrics_data, request_params)
        else:
            # 备用处理方法
            self._fallback_process_metrics(metrics_data, request_params)

    def _fallback_process_metrics(self, metrics_data: Dict[str, Any],
                                  request_params: Dict[str, Any]):
        """备用性能指标处理方法

        Args:
            metrics_data: 性能指标数据
            request_params: 请求参数
        """
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
        if metrics.is_slow(self.monitor.config.threshold_seconds):
            if hasattr(self.monitor, 'alert_manager'):
                self.monitor.alert_manager.handle_alert(metrics)
