"""
框架适配器基类

定义所有框架适配器的通用接口
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Optional, Dict


class BaseFrameworkAdapter(ABC):
    """框架适配器基类
    
    为不同Web框架提供统一的监控集成接口
    """
    
    def __init__(self, monitor: Any):
        """初始化适配器
        
        Args:
            monitor: 性能监控器实例
        """
        self.monitor = monitor
        self.logger = monitor.logger
    
    @abstractmethod
    def create_middleware(self) -> Callable:
        """创建框架中间件
        
        Returns:
            Callable: 框架特定的中间件
        """
        pass
    
    @abstractmethod
    def get_adapter_name(self) -> str:
        """获取适配器名称
        
        Returns:
            str: 适配器名称
        """
        pass
    
    def create_request_context(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建请求上下文
        
        Args:
            request_data: 请求数据
            
        Returns:
            Dict[str, Any]: 标准化的请求上下文
        """
        return {
            'endpoint': request_data.get('path', ''),
            'method': request_data.get('method', 'GET'),
            'url': request_data.get('url', ''),
            'params': request_data.get('params', {}),
            'headers': request_data.get('headers', {}),
        }
    
    def extract_performance_metrics(self, request_context: Dict[str, Any], 
                                  response_data: Dict[str, Any], 
                                  execution_time: float) -> Dict[str, Any]:
        """提取性能指标
        
        Args:
            request_context: 请求上下文
            response_data: 响应数据
            execution_time: 执行时间
            
        Returns:
            Dict[str, Any]: 性能指标数据
        """
        return {
            'endpoint': request_context.get('endpoint', ''),
            'request_url': request_context.get('url', ''),
            'request_params': request_context.get('params', {}),
            'execution_time': execution_time,
            'request_method': request_context.get('method', 'GET'),
            'status_code': response_data.get('status_code', 200),
        }