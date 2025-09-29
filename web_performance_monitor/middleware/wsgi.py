"""
WSGI中间件实现

提供WSGI兼容的中间件功能
"""

from typing import Callable, Any


class WSGIMiddleware:
    """WSGI中间件基类

    为WSGI应用提供通用的性能监控中间件功能
    """

    def __init__(self, monitor: Any):
        """初始化WSGI中间件

        Args:
            monitor: 性能监控器实例
        """
        self.monitor = monitor
        self.logger = monitor.logger

    def create_middleware(self) -> Callable:
        """创建WSGI中间件

        Returns:
            Callable: WSGI中间件函数
        """
        from ..adapters.wsgi import WSGIAdapter
        adapter = WSGIAdapter(self.monitor)
        return adapter.create_middleware()
