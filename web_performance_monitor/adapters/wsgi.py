"""
WSGI适配器

为WSGI兼容框架提供监控适配
"""

from typing import Callable, Dict, Any, Optional
from .base import BaseFrameworkAdapter


class WSGIAdapter(BaseFrameworkAdapter):
    """WSGI框架适配器

    支持所有WSGI兼容的Web框架，包括Flask、Django、Pyramid等
    """

    def get_adapter_name(self) -> str:
        """获取适配器名称"""
        return "WSGI"

    def create_middleware(self) -> Callable:
        """创建WSGI中间件

        Returns:
            Callable: WSGI中间件函数
        """
        def middleware(app: Callable) -> Callable:
            """WSGI中间件包装器"""
            def wsgi_wrapper(environ: Dict[str, Any], start_response: Callable) -> Any:
                """WSGI应用包装器"""
                return self._monitor_wsgi_request(app, environ, start_response)
            return wsgi_wrapper

        self.logger.info("WSGI中间件已创建")
        return middleware

    def _monitor_wsgi_request(self, app: Callable, environ: Dict[str, Any],
                             start_response: Callable) -> Any:
        """监控ASGI请求（重构为使用pyinstrument）

        Args:
            app: ASGI应用
            environ: ASGI环境变量
            receive: 接收函数
            send: 发送函数
        """
        import time
        from ..models import PerformanceMetrics

        # 记录开始时间
        start_time = time.time()

        # 提取请求信息
        request_data = self._extract_wsgi_request(environ)
        request_context = self.create_request_context(request_data)

        # 开始pyinstrument性能分析
        profiler = None
        profiler_data = None
        status_code = 200
        response_headers = []

        # 包装start_response以捕获状态码
        def wrapped_start_response(status: str, headers: list, exc_info=None):
            nonlocal status_code, response_headers
            try:
                status_code = int(status.split(' ')[0])
            except (ValueError, IndexError):
                status_code = 200
            response_headers = headers
            return start_response(status, headers, exc_info)

        try:
            # 启动pyinstrument性能分析
            if hasattr(self.monitor, 'analyzer') and hasattr(self.monitor.analyzer, 'start_profiling'):
                profiler = self.monitor.analyzer.start_profiling()

            # 执行应用
            response = app(environ, wrapped_start_response)

            # 停止pyinstrument性能分析
            if profiler:
                profiler_data = self.monitor.analyzer.stop_profiling(profiler)

            # 计算执行时间
            execution_time = time.time() - start_time

            # 创建性能指标
            metrics_data = self.extract_performance_metrics(
                request_context,
                {'status_code': status_code, 'headers': response_headers},
                execution_time
            )

            # 使用真实的pyinstrument报告数据
            if profiler_data:
                metrics_data['profiler_data'] = profiler_data

            # 处理性能指标（包含真实的pyinstrument报告）
            self._process_metrics(metrics_data, request_data.get('params', {}))

            return response

        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"WSGI请求处理错误: {e}")

            # 停止pyinstrument性能分析（如果已启动）
            if profiler:
                profiler_data = self.monitor.analyzer.stop_profiling(profiler)

            # 错误情况下也要记录性能指标
            metrics_data = self.extract_performance_metrics(
                request_context,
                {'status_code': 500, 'headers': []},
                execution_time
            )

            # 使用真实的pyinstrument报告数据（如果有）
            if profiler_data:
                metrics_data['profiler_data'] = profiler_data

            self._process_metrics(metrics_data, request_data.get('params', {}))
            raise

    def _extract_wsgi_request(self, environ: Dict[str, Any]) -> Dict[str, Any]:
        """提取WSGI请求信息

        Args:
            environ: WSGI环境变量

        Returns:
            Dict[str, Any]: 标准化的请求数据
        """
        # 构建完整的URL
        url = self._build_wsgi_url(environ)

        # 提取查询参数
        query_string = environ.get('QUERY_STRING', '')
        params = self._parse_query_string(query_string)

        # 提取请求头
        headers = {}
        for key, value in environ.items():
            if key.startswith('HTTP_'):
                header_name = key[5:].replace('_', '-').title()
                headers[header_name] = value

        return {
            'method': environ.get('REQUEST_METHOD', 'GET'),
            'path': environ.get('PATH_INFO', '/'),
            'url': url,
            'params': params,
            'headers': headers,
            'query_string': query_string,
            'content_type': environ.get('CONTENT_TYPE', ''),
            'content_length': environ.get('CONTENT_LENGTH', ''),
        }

    def _build_wsgi_url(self, environ: Dict[str, Any]) -> str:
        """构建完整的WSGI URL

        Args:
            environ: WSGI环境变量

        Returns:
            str: 完整的URL
        """
        scheme = environ.get('wsgi.url_scheme', 'http')
        host = environ.get('HTTP_HOST')
        if not host:
            server_name = environ.get('SERVER_NAME', 'localhost')
            server_port = environ.get('SERVER_PORT', '80')
            if (scheme == 'https' and server_port == '443') or (scheme == 'http' and server_port == '80'):
                host = server_name
            else:
                host = f"{server_name}:{server_port}"

        path = environ.get('SCRIPT_NAME', '') + environ.get('PATH_INFO', '/')
        query_string = environ.get('QUERY_STRING', '')

        if query_string:
            return f"{scheme}://{host}{path}?{query_string}"
        else:
            return f"{scheme}://{host}{path}"

    def _parse_query_string(self, query_string: str) -> Dict[str, Any]:
        """解析查询字符串

        Args:
            query_string: 查询字符串

        Returns:
            Dict[str, Any]: 解析后的参数
        """
        from urllib.parse import parse_qs

        if not query_string:
            return {}

        try:
            parsed = parse_qs(query_string, keep_blank_values=True)
            # 转换单值列表为单个值
            return {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
        except Exception:
            return {}

    def _generate_basic_html_report(self, metrics_data: Dict[str, Any], profiler_data: Optional[str] = None) -> str:
        """生成基于pyinstrument的性能报告

        Args:
            metrics_data: 性能指标数据
            profiler_data: pyinstrument生成的HTML报告数据

        Returns:
            str: HTML报告内容，优先使用pyinstrument的真实数据
        """
        # 如果有pyinstrument的真实报告数据，直接使用
        if profiler_data and isinstance(profiler_data, str) and len(profiler_data.strip()) > 0:
            return profiler_data

        # 如果没有pyinstrument数据，生成基本报告
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        endpoint = metrics_data.get('endpoint', 'Unknown')
        execution_time = metrics_data.get('execution_time', 0)
        status_code = metrics_data.get('status_code', 200)
        request_method = metrics_data.get('request_method', 'GET')

        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>性能监控报告 - {endpoint}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ background: #007bff; color: white; padding: 20px; border-radius: 8px 8px 0 0; margin: -20px -20px 20px -20px; }}
        .metric {{ background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #007bff; }}
        .metric-label {{ font-weight: bold; color: #495057; }}
        .metric-value {{ font-size: 1.2em; color: #212529; }}
        .slow {{ border-left-color: #dc3545; }}
        .fast {{ border-left-color: #28a745; }}
        .timestamp {{ color: #6c757d; font-size: 0.9em; }}
        .warning {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; border-radius: 5px; margin: 10px 0; }}
        .no-profiler {{ color: #856404; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 性能监控报告</h1>
            <p>端点: {endpoint}</p>
            <p class="timestamp">生成时间: {timestamp}</p>
        </div>

        {f'<div class="warning no-profiler"><strong>⚠️ 注意:</strong> 当前报告未包含pyinstrument的详细性能分析数据。请确保pyinstrument已正确配置和启用。</div>' if not profiler_data else ''}

        <div class="metric {'slow' if execution_time > 0.1 else 'fast'}">
            <div class="metric-label">⏱️ 执行时间</div>
            <div class="metric-value">{execution_time:.3f} 秒</div>
        </div>

        <div class="metric">
            <div class="metric-label">📊 HTTP方法</div>
            <div class="metric-value">{request_method}</div>
        </div>

        <div class="metric">
            <div class="metric-label">📈 状态码</div>
            <div class="metric-value">{status_code}</div>
        </div>

        <div class="metric">
            <div class="metric-label">📍 端点</div>
            <div class="metric-value">{endpoint}</div>
        </div>

        <div class="metric">
            <div class="metric-label">🎯 性能评估</div>
            <div class="metric-value">{'⚠️ 需要优化' if execution_time > 0.1 else '✅ 性能良好'}</div>
        </div>

        {f'<div class="metric"><div class="metric-label">📊 pyinstrument报告</div><div class="metric-value">✅ 已包含详细性能分析数据</div></div>' if profiler_data else ''}
    </div>
</body>
</html>
"""
        return html_content.strip()

    def _process_metrics(self, metrics_data: Dict[str, Any], request_params: Dict[str, Any]):
        """处理性能指标

        Args:
            metrics_data: 性能指标数据
            request_params: 请求参数
        """
        # 更新统计信息（仅在WSGI适配器中更新，避免与装饰器重复）
        self.monitor._total_requests += 1

        # 使用监控器的内部处理逻辑
        if hasattr(self.monitor, '_process_performance_metrics'):
            # 修复参数传递 - 需要传递4个参数
            status_code = metrics_data.get('status_code', 200)

            # 生成基本的HTML报告
            html_report = self._generate_basic_html_report(
                metrics_data, metrics_data.get("profiler_data"))

            self.monitor._process_performance_metrics(
                metrics_data,
                metrics_data.get('execution_time', 0),
                status_code,
                html_report
            )
        else:
            # 如果没有专用方法，直接创建指标对象并处理
            from ..models import PerformanceMetrics
            from datetime import datetime

            metrics = PerformanceMetrics(
                endpoint=metrics_data['endpoint'],
                request_url=metrics_data['request_url'],
                request_params=request_params,
                execution_time=metrics_data['execution_time'],
                timestamp=datetime.now(),
                request_method=metrics_data['request_method'],
                status_code=metrics_data['status_code'],
            )

            # 检查是否需要告警
            if metrics.is_slow(self.monitor.config.threshold_seconds):
                self.monitor._slow_requests += 1

                # 使用监控器的分析器处理
                if hasattr(self.monitor, 'analyzer'):
                    self.monitor.analyzer.analyze_request(
                        metrics.endpoint,
                        metrics.execution_time,
                        metrics.to_dict()
                    )

                # 检查是否需要告警
                if hasattr(self.monitor, 'alert_manager'):
                    self.monitor.alert_manager.handle_alert(metrics)

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
