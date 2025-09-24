"""
框架适配器模块

提供各种Python Web框架的专用适配器
"""

from .base import BaseFrameworkAdapter
from .wsgi import WSGIAdapter
from .asgi import ASGIAdapter

# Sanic适配器 - 可选依赖
try:
    from .sanic import SanicAdapter
    __all__.append("SanicAdapter")
except ImportError:
    pass

__all__ = [
    "BaseFrameworkAdapter",
    "WSGIAdapter", 
    "ASGIAdapter",
]