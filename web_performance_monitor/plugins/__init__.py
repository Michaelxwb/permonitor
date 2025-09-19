"""
内置框架插件模块

包含Flask、FastAPI等内置框架的插件实现。
"""

from .flask_plugin import FlaskPlugin
from .fastapi_plugin import FastAPIPlugin
from .notification_plugin import NotificationPlugin

__all__ = ['FlaskPlugin', 'FastAPIPlugin', 'NotificationPlugin']