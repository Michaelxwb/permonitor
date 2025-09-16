"""
监控器工厂和自动检测

提供监控器创建和框架自动检测功能
"""

import sys
import inspect
import logging
from typing import Optional, Type, List

from ..core.base import BaseWebMonitor
from ..config.unified_config import UnifiedConfig


class MonitorFactory:
    """监控器工厂类"""
    
    _monitor_registry = {}
    _logger = logging.getLogger(__name__)
    
    @classmethod
    def create_monitor(cls, config: UnifiedConfig, 
                      framework: Optional[str] = None) -> BaseWebMonitor:
        """创建监控器实例"""
        if framework is None:
            framework = cls.detect_framework()
        
        if framework not in cls._monitor_registry:
            # 延迟导入以避免循环依赖
            cls._register_default_monitors()
        
        if framework not in cls._monitor_registry:
            raise ValueError(f"不支持的框架: {framework}")
        
        monitor_class = cls._monitor_registry[framework]
        return monitor_class(config)
    
    @classmethod
    def detect_framework(cls) -> str:
        """自动检测web框架类型 - 满足Requirement 10的自动检测要求"""
        # 检测FastAPI
        if cls._is_fastapi_available():
            cls._logger.info("检测到FastAPI框架")
            return 'fastapi'
        
        # 检测Flask
        if cls._is_flask_available():
            cls._logger.info("检测到Flask框架")
            return 'flask'
        
        raise RuntimeError("无法检测到支持的web框架")
    
    @classmethod
    def _is_fastapi_available(cls) -> bool:
        """检测FastAPI是否可用 - 满足Requirement 10的自动检测要求"""
        try:
            import fastapi
            
            # 检查是否有FastAPI应用实例在运行
            # 创建副本以避免在迭代时修改字典
            modules_copy = dict(sys.modules)
            for name, obj in modules_copy.items():
                if hasattr(obj, 'FastAPI'):
                    return True
                # 检查模块中是否有FastAPI应用实例
                for attr_name in dir(obj):
                    try:
                        attr = getattr(obj, attr_name, None)
                        if attr is not None and attr is not NotImplemented and hasattr(attr, '__class__') and 'FastAPI' in str(attr.__class__):
                            return True
                    except:
                        continue
            
            # 检查调用栈中是否有FastAPI相关代码
            frame = inspect.currentframe()
            try:
                while frame:
                    if 'fastapi' in str(frame.f_code.co_filename).lower():
                        return True
                    frame = frame.f_back
            finally:
                del frame
            
            return 'fastapi' in sys.modules
        except ImportError:
            return False
    
    @classmethod
    def _is_flask_available(cls) -> bool:
        """检测Flask是否可用 - 满足Requirement 10的自动检测要求"""
        try:
            import flask
            
            # 检查是否有Flask应用实例
            # 创建副本以避免在迭代时修改字典
            modules_copy = dict(sys.modules)
            for name, obj in modules_copy.items():
                if hasattr(obj, 'Flask'):
                    return True
                # 检查模块中是否有Flask应用实例
                for attr_name in dir(obj):
                    try:
                        attr = getattr(obj, attr_name, None)
                        if attr is not None and attr is not NotImplemented and hasattr(attr, '__class__') and 'Flask' in str(attr.__class__):
                            return True
                    except:
                        continue
            
            # 检查调用栈中是否有Flask相关代码
            frame = inspect.currentframe()
            try:
                while frame:
                    if 'flask' in str(frame.f_code.co_filename).lower():
                        return True
                    frame = frame.f_back
            finally:
                del frame
            
            return 'flask' in sys.modules
        except ImportError:
            return False
    
    @classmethod
    def register_monitor(cls, framework: str, monitor_class: Type[BaseWebMonitor]):
        """注册新的监控器类型"""
        cls._monitor_registry[framework] = monitor_class
        cls._logger.info(f"注册监控器: {framework} -> {monitor_class.__name__}")
    
    @classmethod
    def get_supported_frameworks(cls) -> List[str]:
        """获取支持的框架列表"""
        cls._register_default_monitors()
        return list(cls._monitor_registry.keys())
    
    @classmethod
    def _register_default_monitors(cls):
        """注册默认监控器"""
        if not cls._monitor_registry:
            try:
                from .flask_monitor import FlaskMonitor
                cls._monitor_registry['flask'] = FlaskMonitor
            except ImportError:
                cls._logger.warning("Flask监控器导入失败")
            
            try:
                from .fastapi_monitor import FastAPIMonitor
                cls._monitor_registry['fastapi'] = FastAPIMonitor
            except ImportError:
                cls._logger.warning("FastAPI监控器导入失败")


def create_web_monitor(framework: str = None, config: dict = None) -> BaseWebMonitor:
    """创建web监控器的统一入口"""
    if config is None:
        # 使用默认配置
        unified_config = UnifiedConfig()
    else:
        unified_config = UnifiedConfig.from_dict(config)
    
    return MonitorFactory.create_monitor(unified_config, framework)