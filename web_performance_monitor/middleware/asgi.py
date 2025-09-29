"""
ASGI中间件实现

提供ASGI兼容的中间件功能
"""

from typing import Callable, Any


class ASGIMiddleware:
    """ASGI中间件基类

    为ASGI应用提供通用的性能监控中间件功能
    """

    def __init__(self, monitor: Any):
        """初始化ASGI中间件

        Args:
            monitor: 性能监控器实例
        """
        self.monitor = monitor
        self.logger = monitor.logger

    def create_middleware(self) -> Callable:
        """创建ASGI中间件

        Returns:
            Callable: ASGI中间件函数
        """
        from ..adapters.asgi import ASGIAdapter
        adapter = ASGIAdapter(self.monitor)
        return adapter.create_middleware()
