"""
统一配置系统

扩展现有配置类以支持多框架和异步特性
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

from .config import Config


@dataclass
class UnifiedConfig(Config):
    """统一配置类，支持所有web框架"""
    
    # 框架特定配置
    framework_specific: Dict[str, Any] = field(default_factory=dict)
    
    # FastAPI特定配置
    fastapi_async_timeout: float = 30.0
    fastapi_concurrent_notifications: bool = True
    fastapi_max_concurrent_alerts: int = 10
    
    # 告警重试配置
    alert_max_retries: int = 3
    alert_retry_delay: float = 1.0
    
    # Flask特定配置
    flask_wsgi_buffer_size: int = 8192
    flask_request_body_limit: int = 10240
    
    
    
    def validate_for_framework(self, framework: str) -> None:
        """验证框架特定配置"""
        if framework == 'fastapi':
            if self.fastapi_async_timeout <= 0:
                raise ValueError("FastAPI异步超时时间必须大于0")
            if self.fastapi_max_concurrent_alerts <= 0:
                raise ValueError("FastAPI最大并发告警数必须大于0")
        
        # 验证告警重试配置
        if self.alert_max_retries < 0:
            raise ValueError("告警最大重试次数不能为负数")
        if self.alert_retry_delay < 0:
            raise ValueError("告警重试延迟不能为负数")
        elif framework == 'flask':
            if self.flask_wsgi_buffer_size <= 0:
                raise ValueError("Flask WSGI缓冲区大小必须大于0")
            if self.flask_request_body_limit <= 0:
                raise ValueError("Flask请求体限制必须大于0")
    
    def get_framework_config(self, framework: str) -> Dict[str, Any]:
        """获取框架特定配置"""
        base_config = {
            'threshold_seconds': self.threshold_seconds,
            'alert_window_days': self.alert_window_days,
            'max_performance_overhead': self.max_performance_overhead,
        }
        
        if framework == 'fastapi':
            base_config.update({
                'async_timeout': self.fastapi_async_timeout,
                'concurrent_notifications': self.fastapi_concurrent_notifications,
                'max_concurrent_alerts': self.fastapi_max_concurrent_alerts,
                'alert_max_retries': self.alert_max_retries,
                'alert_retry_delay': self.alert_retry_delay,
            })
        elif framework == 'flask':
            base_config.update({
                'wsgi_buffer_size': self.flask_wsgi_buffer_size,
                'request_body_limit': self.flask_request_body_limit,
            })
        
        return base_config
    
    def get_effective_config(self) -> Dict[str, Any]:
        """获取生效的配置信息，包含框架特定配置"""
        config_dict = super().get_effective_config()
        
        # 添加框架特定配置
        config_dict.update({
            'fastapi_async_timeout': self.fastapi_async_timeout,
            'fastapi_concurrent_notifications': self.fastapi_concurrent_notifications,
            'fastapi_max_concurrent_alerts': self.fastapi_max_concurrent_alerts,
            'flask_wsgi_buffer_size': self.flask_wsgi_buffer_size,
            'flask_request_body_limit': self.flask_request_body_limit,
            'framework_specific': self.framework_specific,
            'alert_max_retries': self.alert_max_retries,
            'alert_retry_delay': self.alert_retry_delay,
        })
        
        return config_dict