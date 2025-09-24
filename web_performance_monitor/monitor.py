"""
性能监控器主模块

提供多种Web框架的监控集成和装饰器两种监控模式
"""

import time
import asyncio
import functools
from datetime import datetime
from typing import Callable, Any
from urllib.parse import parse_qs

from .alerts import AlertManager
from .analyzer import PerformanceAnalyzer, PerformanceOverheadTracker
from .config import Config
from .formatters import ConfigFormatter
from .models import PerformanceMetrics
from .utils import safe_execute


class PerformanceMonitor:
    """性能监控器主类

    提供多种Web框架的监控集成和装饰器两种监控模式
    """

    def __init__(self, config: Config):
        """初始化性能监控器

        Args:
            config: 配置实例
        """
        self.config = config

        # 设置日志
        from .logging_config import setup_logging_from_config
        self.perf_logger = setup_logging_from_config(config)
        self.logger = self.perf_logger.get_logger()

        # 初始化组件
        self.analyzer = PerformanceAnalyzer()
        self.alert_manager = AlertManager(config)
        self.overhead_tracker = PerformanceOverheadTracker()

        # 统计信息
        self._total_requests = 0
        self._slow_requests = 0
        self._alerts_sent = 0
        self._monitoring_enabled = True

        self.logger.info("性能监控器初始化完成")
        self.logger.info(
            ConfigFormatter.format_config_summary(config.get_effective_config()))

    def create_middleware(self) -> Callable:
        """创建WSGI中间件，兼容所有WSGI框架（Flask、Django、Pyramid等）
        
        Returns:
            Callable: WSGI中间件函数
            
        Note:
            这是create_wsgi_middleware的别名，为了向后兼容
        """
        return self.create_wsgi_middleware()

        def middleware(app):
            """WSGI中间件包装器"""

            def wsgi_wrapper(environ, start_response):
                """WSGI应用包装器"""
                return self._monitor_request(app, environ, start_response)

            return wsgi_wrapper

        self.logger.info("WSGI中间件已创建")
        return middleware

    def create_wsgi_middleware(self) -> Callable:
        """创建通用WSGI中间件，支持所有WSGI兼容框架
        
        Returns:
            Callable: WSGI中间件函数
            
        支持的框架：
            - Flask
            - Django
            - Pyramid
            - Bottle
            - 任何WSGI兼容框架
        """
        from .adapters.wsgi import WSGIAdapter
        adapter = WSGIAdapter(self)
        return adapter.create_middleware()

    def create_asgi_middleware(self) -> Callable:
        """创建ASGI中间件，支持异步Web框架
        
        Returns:
            Callable: ASGI中间件函数
            
        支持的框架：
            - FastAPI
            - Starlette
            - Quart
            - 任何ASGI兼容框架
        """
        from .adapters.asgi import ASGIAdapter
        adapter = ASGIAdapter(self)
        return adapter.create_middleware()

    def create_sanic_middleware(self) -> Callable:
        """创建Sanic中间件，支持Sanic异步框架
        
        Returns:
            Callable: Sanic中间件函数
            
        支持的框架：
            - Sanic
        """
        from .adapters.sanic import SanicAdapter
        adapter = SanicAdapter(self)
        return adapter.create_middleware()

    def create_decorator(self) -> Callable:
        """创建性能监控装饰器，用于监控特定函数

        Returns:
            Callable: 装饰器函数
        """

        def decorator(func: Callable) -> Callable:
            """装饰器实现"""

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                """函数包装器"""
                return self._monitor_function(func, *args, **kwargs)

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                """异步函数包装器"""
                return await self._monitor_async_function(func, *args, **kwargs)

            # 根据函数类型选择合适的包装器
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return wrapper

        self.logger.debug("性能监控装饰器已创建")
        return decorator

    def _monitor_request(self, app, environ, start_response):
        """监控HTTP请求，确保零入侵和性能开销控制

        Args:
            app: WSGI应用
            environ: WSGI环境变量
            start_response: WSGI响应函数

        Returns:
            响应迭代器
        """
        if not self._monitoring_enabled:
            return app(environ, start_response)

        # 提取请求信息
        request_info = self._extract_request_info(environ)

        # 开始监控
        profiler = None
        start_time = time.perf_counter()
        status_code = [200]  # 默认状态码

        try:
            # 启动性能分析
            profiler = safe_execute(self.analyzer.start_profiling)
            if not profiler:
                # 如果分析器启动失败，直接执行原应用
                return app(environ, start_response)

            def custom_start_response(status, headers, exc_info=None):
                """自定义响应函数，捕获状态码"""
                try:
                    status_code[0] = int(status.split()[0])
                except (ValueError, IndexError):
                    status_code[0] = 200
                return start_response(status, headers, exc_info)

            # 执行应用并收集响应
            app_iter = app(environ, custom_start_response)

            try:
                for data in app_iter:
                    yield data
            finally:
                if hasattr(app_iter, 'close'):
                    app_iter.close()

        except Exception as e:
            self.logger.error(f"请求监控异常: {e}")
            # 设置错误状态码
            status_code[0] = 500
            # 确保异常不影响原应用
            if profiler:
                safe_execute(self.analyzer.stop_profiling, profiler)
            raise

        finally:
            # 完成监控处理
            self._finalize_request_monitoring(
                profiler, start_time, request_info, status_code[0]
            )

    def _monitor_function(self, func: Callable, *args, **kwargs) -> Any:
        """监控函数执行，保持原函数返回值和异常处理行为

        Args:
            func: 被监控的函数
            *args: 函数位置参数
            **kwargs: 函数关键字参数

        Returns:
            Any: 函数执行结果
        """
        if not self._monitoring_enabled:
            return func(*args, **kwargs)

        # 创建函数信息
        func_info = {
            'endpoint': f"{func.__module__}.{func.__name__}",
            'request_url': f"function://{func.__name__}",
            'request_params': {
                'args_count': len(args),
                'kwargs_keys': list(kwargs.keys()) if kwargs else [],
                'function_module': func.__module__,
                'function_name': func.__name__
            },
            'request_method': 'FUNCTION'
        }

        profiler = None
        start_time = time.perf_counter()
        result = None
        exception_occurred = False

        try:
            # 启动性能分析
            profiler = safe_execute(self.analyzer.start_profiling)
            if not profiler:
                # 如果分析器启动失败，直接执行原函数
                return func(*args, **kwargs)

            # 执行原函数
            result = func(*args, **kwargs)
        except Exception as e:
            exception_occurred = True
            self.logger.debug(f"被监控函数抛出异常: {func.__name__} - {e}")
            raise  # 重新抛出异常，保持原函数行为

        finally:
            # 完成监控处理
            status_code = 500 if exception_occurred else 200
            self._finalize_function_monitoring(
                profiler, start_time, func_info, status_code
            )

        # 返回函数执行结果
        return result

    async def _monitor_async_function(self, func: Callable, *args, **kwargs) -> Any:
        """监控异步函数执行，保持原函数返回值和异常处理行为

        Args:
            func: 被监控的异步函数
            *args: 函数位置参数
            **kwargs: 函数关键字参数

        Returns:
            Any: 函数执行结果
        """
        if not self._monitoring_enabled:
            return await func(*args, **kwargs)

        # 创建函数信息
        func_info = {
            'endpoint': f"{func.__module__}.{func.__name__}",
            'request_url': f"function://{func.__name__}",
            'request_params': {
                'args_count': len(args),
                'kwargs_keys': list(kwargs.keys()) if kwargs else [],
                'function_module': func.__module__,
                'function_name': func.__name__
            },
            'request_method': 'FUNCTION'
        }

        profiler = None
        start_time = time.perf_counter()
        result = None
        exception_occurred = False

        try:
            # 启动性能分析
            profiler = safe_execute(self.analyzer.start_profiling)
            if not profiler:
                # 如果分析器启动失败，直接执行原函数
                return await func(*args, **kwargs)

            # 执行原异步函数
            result = await func(*args, **kwargs)
        except Exception as e:
            exception_occurred = True
            self.logger.debug(f"被监控异步函数抛出异常: {func.__name__} - {e}")
            raise  # 重新抛出异常，保持原函数行为

        finally:
            # 完成监控处理
            status_code = 500 if exception_occurred else 200
            self._finalize_function_monitoring(
                profiler, start_time, func_info, status_code
            )

        # 返回函数执行结果
        return result

    def _extract_request_info(self, environ: dict) -> dict:
        """从WSGI环境中提取请求信息

        Args:
            environ: WSGI环境变量

        Returns:
            dict: 请求信息
        """
        try:
            # 基本信息
            method = environ.get('REQUEST_METHOD', 'GET')
            path = environ.get('PATH_INFO', '/')
            query_string = environ.get('QUERY_STRING', '')

            # 构建完整URL
            scheme = environ.get('wsgi.url_scheme', 'http')
            server_name = environ.get('SERVER_NAME', 'localhost')
            server_port = environ.get('SERVER_PORT', '80')

            if (scheme == 'https' and server_port == '443') or (
                scheme == 'http' and server_port == '80'):
                url = f"{scheme}://{server_name}{path}"
            else:
                url = f"{scheme}://{server_name}:{server_port}{path}"

            if query_string:
                url += f"?{query_string}"

            # 解析查询参数
            params = {}
            if query_string:
                params.update(parse_qs(query_string, keep_blank_values=True))

            # 尝试获取POST参数
            content_type = environ.get('CONTENT_TYPE', '')
            content_length = int(environ.get('CONTENT_LENGTH', 0))

            if method in ['POST', 'PUT',
                          'PATCH'] and content_length > 0 and content_length < 10240:  # 限制大小10KB
                try:
                    # 读取请求体数据
                    post_data = environ['wsgi.input'].read(content_length)

                    # 重置输入流，确保应用能正常读取
                    import io
                    environ['wsgi.input'] = io.BytesIO(post_data)

                    # 根据Content-Type解析数据
                    if 'application/json' in content_type:
                        # JSON数据
                        import json
                        try:
                            json_data = json.loads(post_data.decode('utf-8'))
                            params['json_body'] = json_data
                        except json.JSONDecodeError:
                            params['json_body'] = {'error': 'invalid_json',
                                                   'size': len(post_data)}

                    elif 'application/x-www-form-urlencoded' in content_type:
                        # 表单数据
                        post_params = parse_qs(post_data.decode('utf-8'),
                                               keep_blank_values=True)
                        params.update(post_params)

                    elif 'multipart/form-data' in content_type:
                        # 文件上传等多部分数据
                        params['multipart_data'] = {'size': len(post_data),
                                                    'type': 'multipart'}

                    else:
                        # 其他类型的数据
                        params['request_body'] = {'content_type': content_type,
                                                  'size': len(post_data)}

                except (ValueError, UnicodeDecodeError, KeyError, ImportError) as e:
                    params['body_parse_error'] = str(e)
                    self.logger.debug(f"解析请求体失败: {e}")

            # 添加请求头信息
            headers_info = {}
            for key, value in environ.items():
                if key.startswith('HTTP_'):
                    header_name = key[5:].replace('_', '-').lower()
                    # 记录有用的头信息，对敏感头进行脱敏
                    useful_headers = [
                        'content-type', 'user-agent', 'accept', 'content-length',
                        'accept-language', 'accept-encoding', 'referer', 'origin',
                        'x-requested-with', 'x-forwarded-for', 'x-real-ip'
                    ]

                    if header_name in useful_headers:
                        # 对可能包含敏感信息的头进行脱敏
                        if any(sensitive in header_name for sensitive in
                               ['authorization', 'cookie', 'token']):
                            headers_info[header_name] = '***'
                        else:
                            headers_info[header_name] = value

            # 添加一些WSGI环境信息
            if environ.get('REMOTE_ADDR'):
                headers_info['remote-addr'] = environ['REMOTE_ADDR']
            if environ.get('REQUEST_METHOD'):
                headers_info['method'] = environ['REQUEST_METHOD']
            if environ.get('HTTP_TRACEID'):
                headers_info['traceid'] = environ['HTTP_TRACEID']
            if headers_info:
                params['headers'] = headers_info

            return {
                'endpoint': path,
                'request_url': url,
                'request_params': params,
                'request_method': method
            }

        except Exception as e:
            self.logger.warning(f"提取请求信息失败: {e}")
            return {
                'endpoint': '/',
                'request_url': 'http://localhost/',
                'request_params': {},
                'request_method': 'GET'
            }

    def _finalize_request_monitoring(self, profiler, start_time: float,
                                     request_info: dict, status_code: int) -> None:
        """完成请求监控处理

        Args:
            profiler: 性能分析器实例
            start_time: 开始时间
            request_info: 请求信息
            status_code: 响应状态码
        """
        try:
            end_time = time.perf_counter()
            total_time = end_time - start_time

            # 更新统计
            self._total_requests += 1

            if profiler:
                # 停止性能分析
                html_report = safe_execute(self.analyzer.stop_profiling, profiler)
                execution_time = safe_execute(self.analyzer.get_execution_time,
                                              profiler) or total_time

                # 跟踪性能开销
                self.overhead_tracker.track_overhead(execution_time, total_time)

                # 检查性能开销是否超标
                if self.overhead_tracker.check_overhead_threshold(
                    self.config.max_performance_overhead):
                    self.logger.warning("性能监控开销超过阈值，考虑调整配置")

                # 记录请求完成
                self.perf_logger.log_request_end(
                    request_info['endpoint'],
                    request_info['request_method'],
                    execution_time,
                    status_code,
                    execution_time > self.config.threshold_seconds
                )

                # 处理性能指标 - 即使没有HTML报告也要处理
                # 如果没有HTML报告，创建一个简单的报告
                if not html_report:
                    html_report = f"<html><body><h1>性能报告</h1><p>执行时间: {execution_time:.3f}秒</p></body></html>"

                self._process_performance_metrics(
                    request_info, execution_time, status_code, html_report
                )

        except Exception as e:
            self.logger.error(f"完成请求监控处理失败: {e}")

    def _finalize_function_monitoring(self, profiler, start_time: float,
                                      func_info: dict, status_code: int) -> None:
        """完成函数监控处理

        Args:
            profiler: 性能分析器实例
            start_time: 开始时间
            func_info: 函数信息
            status_code: 状态码
        """
        try:
            end_time = time.perf_counter()
            total_time = end_time - start_time

            # 更新统计
            self._total_requests += 1

            if profiler:
                # 停止性能分析
                html_report = safe_execute(self.analyzer.stop_profiling, profiler)
                execution_time = safe_execute(self.analyzer.get_execution_time,
                                              profiler) or total_time

                # 跟踪性能开销
                self.overhead_tracker.track_overhead(execution_time, total_time)

                # 处理性能指标
                if html_report:
                    self._process_performance_metrics(
                        func_info, execution_time, status_code, html_report
                    )

        except Exception as e:
            self.logger.error(f"完成函数监控处理失败: {e}")

    def _process_performance_metrics(self, info: dict, execution_time: float,
                                     status_code: int, html_report: str) -> None:
        """处理性能指标数据

        Args:
            info: 请求或函数信息
            execution_time: 执行时间
            status_code: 状态码
            html_report: HTML报告
        """
        try:
            # 注意：统计更新由调用者负责，避免重复计数
            # 创建性能指标
            metrics = PerformanceMetrics(
                endpoint=info['endpoint'],
                request_url=info['request_url'],
                request_params=info['request_params'],
                execution_time=execution_time,
                timestamp=datetime.now(),
                request_method=info['request_method'],
                status_code=status_code,
                profiler_data=html_report
            )
            
            # 创建性能指标
            metrics = PerformanceMetrics(
                endpoint=info['endpoint'],
                request_url=info['request_url'],
                request_params=info['request_params'],
                execution_time=execution_time,
                timestamp=datetime.now(),
                request_method=info['request_method'],
                status_code=status_code,
                profiler_data=html_report
            )

            # 检查是否需要告警
            if metrics.is_slow(self.config.threshold_seconds):
                self._slow_requests += 1

                # 处理告警
                try:
                    alert_record = self.alert_manager.process_metrics(metrics,
                                                                      html_report)
                    if alert_record:
                        self._alerts_sent += 1
                        self.logger.info(f"性能告警已发送: {metrics.format_summary()}")
                except Exception as e:
                    self.logger.error(f"处理告警失败: {e}")

        except Exception as e:
            self.logger.error(f"处理性能指标失败: {e}")

    def get_stats(self) -> dict:
        """获取监控统计信息

        Returns:
            dict: 统计信息
        """
        try:
            overhead_stats = self.overhead_tracker.get_overhead_stats()
            alert_stats = self.alert_manager.get_alert_stats()

            return {
                'monitoring_enabled': self._monitoring_enabled,
                'total_requests': self._total_requests,
                'slow_requests': self._slow_requests,
                'alerts_sent': self._alerts_sent,
                'slow_request_rate': (self._slow_requests / max(self._total_requests,
                                                                1)) * 100,
                'overhead_stats': overhead_stats,
                'alert_stats': alert_stats,
                'config': self.config.get_effective_config()
            }
        except Exception as e:
            self.logger.error(f"获取统计信息失败: {e}")
            return {'error': str(e)}

    def enable_monitoring(self) -> None:
        """启用监控"""
        self._monitoring_enabled = True
        self.logger.info("性能监控已启用")

    def disable_monitoring(self) -> None:
        """禁用监控"""
        self._monitoring_enabled = False
        self.logger.info("性能监控已禁用")

    def is_monitoring_enabled(self) -> bool:
        """检查监控是否启用

        Returns:
            bool: 监控是否启用
        """
        return self._monitoring_enabled

    def reset_stats(self) -> None:
        """重置统计信息"""
        self._total_requests = 0
        self._slow_requests = 0
        self._alerts_sent = 0
        self.overhead_tracker.reset_stats()
        self.logger.info("监控统计信息已重置")

    def cleanup(self) -> None:
        """清理资源"""
        try:
            # 清理过期告警
            cleaned = self.alert_manager.cleanup_old_alerts()
            if cleaned > 0:
                self.logger.info(f"清理了 {cleaned} 个过期告警记录")

            # 重置开销跟踪器
            self.overhead_tracker.reset_stats()

        except Exception as e:
            self.logger.error(f"清理资源失败: {e}")

    def test_alert_system(self) -> dict:
        """测试告警系统

        Returns:
            dict: 测试结果
        """
        try:
            # 测试通知器
            notifier_results = self.alert_manager.test_notifiers()

            # 创建测试指标
            test_metrics = PerformanceMetrics(
                endpoint="/test/alert",
                request_url="http://localhost/test/alert",
                request_params={"test": True},
                execution_time=self.config.threshold_seconds + 1.0,  # 超过阈值
                timestamp=datetime.now(),
                request_method="GET",
                status_code=200
            )

            test_html = "<html><body><h1>测试性能报告</h1></body></html>"

            # 强制发送测试告警
            alert_record = self.alert_manager.force_alert(test_metrics, test_html)

            return {
                'success': True,
                'notifier_results': notifier_results,
                'test_alert_sent': alert_record is not None,
                'alert_record': alert_record.to_dict() if alert_record else None
            }

        except Exception as e:
            self.logger.error(f"测试告警系统失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def __str__(self) -> str:
        """字符串表示"""
        return f"PerformanceMonitor(enabled={self._monitoring_enabled}, threshold={self.config.threshold_seconds}s)"
