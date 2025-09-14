"""
请求信息模型

定义统一的请求信息数据结构
"""

from dataclasses import dataclass
from typing import Dict, Any, Callable


@dataclass
class RequestInfo:
    """统一的请求信息模型"""
    endpoint: str
    method: str
    url: str
    params: Dict[str, Any]
    headers: Dict[str, str]
    framework: str = "unknown"
    
    @classmethod
    def from_function(cls, func: Callable, args: tuple, kwargs: dict) -> 'RequestInfo':
        """从函数调用创建请求信息"""
        return cls(
            endpoint=f"{func.__module__}.{func.__name__}",
            method="FUNCTION",
            url=f"function://{func.__name__}",
            params={
                'args_count': len(args),
                'kwargs_keys': list(kwargs.keys()),
                'function_module': func.__module__,
                'function_name': func.__name__
            },
            headers={},
            framework="function"
        )