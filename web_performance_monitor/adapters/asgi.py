"""
ASGI适配器

为ASGI兼容框架提供监控适配，支持FastAPI、Starlette等异步框架
"""

import asyncio
from typing import Callable, Dict, Any, Optional, List, Union
from .base import BaseFrameworkAdapter


class ASGIAdapter(BaseFrameworkAdapter):
    """ASGI框架适配器
    
    支持所有ASGI兼容的Web框架，包括FastAPI、Starlette等
    """
    
    def get_adapter_name(self) -> str:
        """获取适配器名称"""
        return "ASGI"
    
    def create_middleware(self) -> Callable:
        """创建ASGI中间件
        
        Returns:
            Callable: ASGI中间件函数
        """
        def asgi_middleware(scope: Dict[str, Any]) -> Callable:
            """ASGI中间件工厂"""
            if scope['type'] == 'http':
                return self._create_http_middleware(scope)
            else:
                # 非HTTP请求（如WebSocket）直接通过
                return self._create_pass_through_middleware(scope)
        
        self.logger.info("ASGI中间件已创建")
        return asgi_middleware
    
    def _create_http_middleware(self, scope: Dict[str, Any]) -> Callable:
        """创建HTTP中间件
        
        Args:
            scope: ASGI作用域
            
        Returns:
            Callable: HTTP中间件函数
        """
        async def middleware(receive: Callable, send: Callable) -> None:
            """HTTP中间件实现"""
            await self._monitor_asgi_request(scope, receive, send)
        
        return middleware
    
    def _create_pass_through_middleware(self, scope: Dict[str, Any]) -> Callable:
        """创建透传中间件（用于非HTTP请求）
        
        Args:
            scope: ASGI作用域
            
        Returns:
            Callable: 透传中间件函数
        """
        async def middleware(receive: Callable, send: Callable) -> None:
            """透传中间件实现"""
            # 直接调用原始应用
            app = scope.get('app')
            if app:
                await app(scope, receive, send)
            else:
                # 如果没有app，直接透传
                message = await receive()
                await send(message)
        
        return middleware
    
    async def _monitor_asgi_request(self, scope: Dict[str, Any], 
                                   receive: Callable, send: Callable) -> None:
        """监控ASGI请求
        
        Args:
            scope: ASGI作用域
            receive: 接收函数
            send: 发送函数
        """
        import time
        from ..models import PerformanceMetrics
        
        # 提取请求信息
        request_data = self._extract_asgi_request(scope)
        request_context = self.create_request_context(request_data)
        
        # 开始监控
        start_time = time.time()
        status_code = 200
        response_headers = []
        
        # 包装send函数以捕获响应信息
        async def wrapped_send(message: Dict[str, Any]) -> None:
            nonlocal status_code, response_headers
            
            if message['type'] == 'http.response.start':
                status_code = message.get('status', 200)
                response_headers = message.get('headers', [])
            
            await send(message)
        
        try:
            # 接收请求体（如果需要）
            body = b''
            while True:
                message = await receive()
                if message['type'] == 'http.request':
                    body_chunk = message.get('body', b'')
                    if body_chunk:
                        body += body_chunk
                    if not message.get('more_body', False):
                        break
                elif message['type'] == 'http.disconnect':
                    return
            
            # 提取请求参数（从body或查询字符串）
            request_params = self._extract_request_params(request_data, body)
            
            # 调用原始应用
            app = scope.get('app')
            if app:
                # 创建新的receive函数，包含请求体
                async def new_receive():
                    if body:
                        return {
                            'type': 'http.request',
                            'body': body,
                            'more_body': False
                        }
                    else:
                        return {'type': 'http.request', 'body': b'', 'more_body': False}
                
                await app(scope, new_receive, wrapped_send)
            else:
                # 如果没有app，发送默认响应
                await wrapped_send({
                    'type': 'http.response.start',
                    'status': 404,
                    'headers': [(b'content-type', b'application/json')]
                })
                await wrapped_send({
                    'type': 'http.response.body',
                    'body': b'{"error": "Not Found"}'
                })
            
            # 计算执行时间
            execution_time = time.time() - start_time
            
            # 创建性能指标
            metrics_data = self.extract_performance_metrics(
                request_context,
                {'status_code': status_code, 'headers': response_headers},
                execution_time
            )
            
            # 处理性能指标
            await self._process_metrics_async(metrics_data, request_params)
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"ASGI请求处理错误: {e}")
            
            # 错误情况下也要记录性能指标
            metrics_data = self.extract_performance_metrics(
                request_context,
                {'status_code': 500, 'headers': []},
                execution_time
            )
            
            await self._process_metrics_async(metrics_data, {})
            
            # 发送错误响应
            await wrapped_send({
                'type': 'http.response.start',
                'status': 500,
                'headers': [(b'content-type', b'application/json')]
            })
            await wrapped_send({
                'type': 'http.response.body',
                'body': b'{"error": "Internal Server Error"}'
            })
    
    def _extract_asgi_request(self, scope: Dict[str, Any]) -> Dict[str, Any]:
        """提取ASGI请求信息
        
        Args:
            scope: ASGI作用域
            
        Returns:
            Dict[str, Any]: 标准化的请求数据
        """
        # 构建完整的URL
        url = self._build_asgi_url(scope)
        
        # 提取查询参数
        query_string = scope.get('query_string', b'').decode('utf-8')
        params = self._parse_query_string(query_string)
        
        # 提取请求头
        headers = {}
        for name, value in scope.get('headers', []):
            header_name = name.decode('utf-8').title()
            headers[header_name] = value.decode('utf-8')
        
        # 提取路径参数
        path_params = scope.get('path_params', {})
        
        return {
            'method': scope.get('method', 'GET'),
            'path': scope.get('path', '/'),
            'url': url,
            'params': {**params, **path_params},  # 合并查询参数和路径参数
            'headers': headers,
            'query_string': query_string,
            'type': scope.get('type', 'http'),
            'asgi': scope.get('asgi', {}),
            'path_params': path_params,
        }
    
    def _build_asgi_url(self, scope: Dict[str, Any]) -> str:
        """构建完整的ASGI URL
        
        Args:
            scope: ASGI作用域
            
        Returns:
            str: 完整的URL
        """
        scheme = scope.get('scheme', 'http')
        server = scope.get('server')
        path = scope.get('path', '/')
        query_string = scope.get('query_string', b'').decode('utf-8')
        
        if server:
            host, port = server
            if (scheme == 'https' and port == 443) or (scheme == 'http' and port == 80):
                base_url = f"{scheme}://{host}"
            else:
                base_url = f"{scheme}://{host}:{port}"
        else:
            base_url = f"{scheme}://localhost"
        
        if query_string:
            return f"{base_url}{path}?{query_string}"
        else:
            return f"{base_url}{path}"
    
    def _extract_request_params(self, request_data: Dict[str, Any], body: bytes) -> Dict[str, Any]:
        """提取请求参数
        
        Args:
            request_data: 请求数据
            body: 请求体
            
        Returns:
            Dict[str, Any]: 合并的请求参数
        """
        params = request_data.get('params', {}).copy()
        
        # 如果存在请求体，尝试解析为JSON
        if body:
            try:
                import json
                body_data = json.loads(body.decode('utf-8'))
                if isinstance(body_data, dict):
                    params.update(body_data)
            except (json.JSONDecodeError, UnicodeDecodeError):
                # 如果不是JSON，作为原始数据添加
                params['_body'] = body.decode('utf-8', errors='ignore')
        
        return params
    
    async def _process_metrics_async(self, metrics_data: Dict[str, Any], request_params: Dict[str, Any]):
        """异步处理性能指标
        
        Args:
            metrics_data: 性能指标数据
            request_params: 请求参数
        """
        # 使用监控器的内部处理逻辑
        if hasattr(self.monitor, '_process_performance_metrics'):
            # 如果是异步方法
            if asyncio.iscoroutinefunction(self.monitor._process_performance_metrics):
                await self.monitor._process_performance_metrics(metrics_data, request_params)
            else:
                # 在运行同步方法
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None, 
                    self.monitor._process_performance_metrics, 
                    metrics_data, 
                    request_params
                )
        else:
            # 如果没有专用方法，直接创建指标对象并处理
            await self._fallback_process_metrics(metrics_data, request_params)
    
    async def _fallback_process_metrics(self, metrics_data: Dict[str, Any], request_params: Dict[str, Any]):
        """备用性能指标处理方法
        
        Args:
            metrics_data: 性能指标数据
            request_params: 请求参数
        """
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
        
        # 使用监控器的分析器处理
        if hasattr(self.monitor, 'analyzer'):
            # 检查分析器方法是否是异步的
            if asyncio.iscoroutinefunction(self.monitor.analyzer.analyze_request):
                await self.monitor.analyzer.analyze_request(
                    metrics.endpoint,
                    metrics.execution_time,
                    metrics.to_dict()
                )
            else:
                # 在运行同步方法
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    self.monitor.analyzer.analyze_request,
                    metrics.endpoint,
                    metrics.execution_time,
                    metrics.to_dict()
                )
        
        # 检查是否需要告警
        if hasattr(self.monitor, 'alert_manager'):
            if metrics.is_slow(self.monitor.config.threshold_seconds):
                # 检查告警管理器方法是否是异步的
                if asyncio.iscoroutinefunction(self.monitor.alert_manager.handle_alert):
                    await self.monitor.alert_manager.handle_alert(metrics)
                else:
                    # 在运行同步方法
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        None,
                        self.monitor.alert_manager.handle_alert,
                        metrics
                    )