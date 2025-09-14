"""
通知器抽象基类

定义所有通知器必须实现的接口
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import PerformanceMetrics


class BaseNotifier(ABC):
    """通知器抽象基类
    
    所有具体的通知器实现都必须继承此类并实现send_notification方法
    """
    
    @abstractmethod
    def send_notification(self, metrics: 'PerformanceMetrics', html_report: str) -> bool:
        """发送通知
        
        Args:
            metrics: 性能指标数据
            html_report: HTML格式的性能报告
            
        Returns:
            bool: 发送是否成功
            
        Raises:
            NotificationError: 通知发送失败时抛出
        """
        pass
    
    def validate_config(self) -> bool:
        """验证通知器配置是否有效
        
        Returns:
            bool: 配置是否有效
        """
        return True