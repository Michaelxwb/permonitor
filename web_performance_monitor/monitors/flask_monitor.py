"""
Flask监控器实现

提供Flask框架特定的监控功能
"""

import functools
from typing import Callable, Dict, Any
from urllib.parse import parse_qs

from ..core.base import BaseWebMonitor, RequestExecutionContext, FunctionExecutionContext
from ..utils.performance_analyzer import SyncPerformanceAnalyzer
from ..alerts.manager import SyncAlertManager
from ..config.unified_config import UnifiedConfig


class FlaskMonitor(BaseWebMonitor):
    """Flask框架监控器实现"""
    
    def create_middleware(self) -> Callable:
        """创建Flask WSGI中间件"""
        def middleware(app):
            def wsgi_wrapper(environ, start_response):
                context = FlaskRequestContext(app, environ, start_response, self)
                return self._monitor_execution(context)
            return wsgi_wrapper
        return middleware
    
    def create_decorator(self) -> Callable:
        """创建Flask装饰器"""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                context = FunctionExecutionContext(func, args, kwargs)
                return self._monitor_execution(context)
            return wrapper
        return decorator
    
    def _extract_request_info(self, environ: dict) -> Dict[str, Any]:
        """从WSGI环境中提取请求信息"""
        try:
            # 基本信息
            method = environ.get('REQUEST_METHOD', 'GET')
            path = environ.get('PATH_INFO', '/')
            query_string = environ.get('QUERY_STRING', '')
            
            # 构建完整URL
            scheme = environ.get('wsgi.url_scheme', 'http')
            server_name = environ.get('SERVER_NAME', 'localhost')
            server_port = environ.get('SERVER_PORT', '80')
            
            if (scheme == 'https' and server_port == '443') or (scheme == 'http' and server_port == '80'):
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
            
            if method in ['POST', 'PUT', 'PATCH'] and content_length > 0 and content_length < self.config.flask_request_body_limit:
                try:
                    # 读取请求体数据
                    post_data = environ['wsgi.input'].read(content_length)
                    
                    # 重置输入流，确保应用能正常读取
                    import io
                    environ['wsgi.input'] = io.BytesIO(post_data)
                    
                    # 根据Content-Type解析数据
                    if 'application/json' in content_type:
                        import json
                        try:
                            json_data = json.loads(post_data.decode('utf-8'))
                            params['json_body'] = json_data
                        except json.JSONDecodeError:
                            params['json_body'] = {'error': 'invalid_json', 'size': len(post_data)}
                    
                    elif 'application/x-www-form-urlencoded' in content_type:
                        post_params = parse_qs(post_data.decode('utf-8'), keep_blank_values=True)
                        params.update(post_params)
                    
                    elif 'multipart/form-data' in content_type:
                        params['multipart_data'] = {'size': len(post_data), 'type': 'multipart'}
                    
                    else:
                        params['request_body'] = {'content_type': content_type, 'size': len(post_data)}
                        
                except (ValueError, UnicodeDecodeError, KeyError, ImportError) as e:
                    params['body_parse_error'] = str(e)
                    self.logger.debug(f"解析请求体失败: {e}")
            
            # 添加请求头信息
            headers_info = {}
            for key, value in environ.items():
                if key.startswith('HTTP_'):
                    header_name = key[5:].replace('_', '-').lower()
                    useful_headers = [
                        'content-type', 'user-agent', 'accept', 'content-length',
                        'accept-language', 'accept-encoding', 'referer', 'origin',
                        'x-requested-with', 'x-forwarded-for', 'x-real-ip'
                    ]
                    
                    if header_name in useful_headers:
                        if any(sensitive in header_name for sensitive in ['authorization', 'cookie', 'token']):
                            headers_info[header_name] = '***'
                        else:
                            headers_info[header_name] = value
            
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
    
    def _create_analyzer(self) -> SyncPerformanceAnalyzer:
        """创建同步性能分析器"""
        return SyncPerformanceAnalyzer()
    
    def _create_alert_manager(self) -> SyncAlertManager:
        """创建同步告警管理器"""
        return SyncAlertManager(self.config)


class FlaskRequestContext(RequestExecutionContext):
    """Flask请求执行上下文"""
    
    def __init__(self, app, environ, start_response, monitor):
        super().__init__(app, environ, monitor)
        self.start_response = start_response
        self.status_code = [200]
    
    def execute(self):
        """执行Flask WSGI应用"""
        def custom_start_response(status, headers, exc_info=None):
            try:
                self.status_code[0] = int(status.split()[0])
            except (ValueError, IndexError):
                self.status_code[0] = 200
            return self.start_response(status, headers, exc_info)
        
        app_iter = self.app(self.request_data, custom_start_response)
        
        try:
            for data in app_iter:
                yield data
        finally:
            if hasattr(app_iter, 'close'):
                app_iter.close()