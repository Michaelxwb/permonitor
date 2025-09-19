"""
统一配置系统

扩展现有配置类以支持多框架和异步特性
"""

import os
import json
import logging
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
    
    @classmethod
    def from_env(cls) -> 'UnifiedConfig':
        """从环境变量加载配置"""
        logger = logging.getLogger(__name__)
        
        # 基础配置
        config_dict = {
            'threshold_seconds': float(os.getenv('PERF_THRESHOLD_SECONDS', '1.0')),
            'alert_window_days': int(os.getenv('PERF_ALERT_WINDOW_DAYS', '10')),
            'max_performance_overhead': float(os.getenv('PERF_MAX_OVERHEAD', '0.05')),
            'smart_sampling_rate': float(os.getenv('PERF_SMART_SAMPLING_RATE', '0.1')),
            'min_requests_before_profiling': int(os.getenv('PERF_MIN_REQUESTS_BEFORE_PROFILING', '5')),
            'enable_adaptive_sampling': os.getenv('PERF_ENABLE_ADAPTIVE_SAMPLING', 'true').lower() == 'true',
            'enable_local_file': os.getenv('PERF_ENABLE_LOCAL_FILE', 'true').lower() == 'true',
            'local_output_dir': os.getenv('PERF_LOCAL_OUTPUT_DIR', '/tmp'),
            'enable_mattermost': os.getenv('PERF_ENABLE_MATTERMOST', 'false').lower() == 'true',
            'mattermost_server_url': os.getenv('PERF_MATTERMOST_SERVER_URL', ''),
            'mattermost_token': os.getenv('PERF_MATTERMOST_TOKEN', ''),
            'mattermost_channel_id': os.getenv('PERF_MATTERMOST_CHANNEL_ID', ''),
            'mattermost_max_retries': int(os.getenv('PERF_MATTERMOST_MAX_RETRIES', '3')),
            'log_level': os.getenv('PERF_LOG_LEVEL', 'INFO'),
            'enable_url_blacklist': os.getenv('PERF_ENABLE_URL_BLACKLIST', 'true').lower() == 'true',
            'url_blacklist': json.loads(os.getenv('PERF_URL_BLACKLIST', '[]')),
            'fastapi_async_timeout': float(os.getenv('PERF_FASTAPI_ASYNC_TIMEOUT', '30.0')),
            'fastapi_concurrent_notifications': os.getenv('PERF_FASTAPI_CONCURRENT_NOTIFICATIONS', 'true').lower() == 'true',
            'fastapi_max_concurrent_alerts': int(os.getenv('PERF_FASTAPI_MAX_CONCURRENT_ALERTS', '10')),
            'flask_wsgi_buffer_size': int(os.getenv('PERF_FLASK_WSGI_BUFFER_SIZE', '8192')),
            'flask_request_body_limit': int(os.getenv('PERF_FLASK_REQUEST_BODY_LIMIT', '10240')),
            'alert_max_retries': int(os.getenv('PERF_ALERT_MAX_RETRIES', '3')),
            'alert_retry_delay': float(os.getenv('PERF_ALERT_RETRY_DELAY', '1.0')),
        }
        
        logger.info("配置已从环境变量加载")
        return cls.from_dict(config_dict)
    
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