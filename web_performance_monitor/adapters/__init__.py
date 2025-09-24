"""
框架适配器模块

提供各种Python Web框架的专用适配器
"""

from .base import BaseFrameworkAdapter
from .wsgi import WSGIAdapter
from .asgi import ASGIAdapter

__all__ = [
    "BaseFrameworkAdapter",
    "WSGIAdapter",
    "ASGIAdapter",
]