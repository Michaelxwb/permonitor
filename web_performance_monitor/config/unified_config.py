"""
统一配置系统

扩展现有配置类以支持多框架和异步特性，包括依赖管理配置
"""

import os
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List

from .config import Config
from ..models.dependency_models import DependencyConfig


@dataclass
class UnifiedConfig(Config):
    """统一配置类，支持所有web框架和依赖管理"""
    
    # 框架特定配置
    framework_specific: Dict[str, Any] = field(default_factory=dict)
    
    # FastAPI特定配置
    fastapi_async_timeout: float = 30.0
    fastapi_concurrent_notifications: bool = True
    fastapi_max_concurrent_alerts: int = 10
    
    # Flask特定配置
    flask_wsgi_buffer_size: int = 8192
    flask_request_body_limit: int = 10240
    
    # 告警重试配置
    alert_max_retries: int = 3
    alert_retry_delay: float = 1.0
    
    # 依赖管理配置
    dependency_config: DependencyConfig = field(default_factory=DependencyConfig)
    
    # 自动检测配置
    enable_auto_detection: bool = True
    auto_detection_interval: int = 300  # 秒
    enable_framework_monitoring: bool = True
    
    # 优雅降级配置
    enable_graceful_degradation: bool = True
    fallback_to_basic_monitor: bool = True
    show_dependency_warnings: bool = True
    
    # 安装建议配置
    show_installation_suggestions: bool = True
    suggest_optimal_installation: bool = True
    include_size_estimates: bool = True
    
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
        
        # 依赖管理配置
        dependency_config_dict = {
            'skip_dependency_check': os.getenv('WPM_SKIP_DEPENDENCY_CHECK', 'false').lower() == 'true',
            'strict_dependencies': os.getenv('WPM_STRICT_DEPENDENCIES', 'false').lower() == 'true',
            'auto_install_deps': os.getenv('WPM_AUTO_INSTALL_DEPS', 'false').lower() == 'true',
            'preferred_frameworks': [fw.strip() for fw in os.getenv('WPM_PREFERRED_FRAMEWORKS', '').split(',') if fw.strip()],
            'notification_channels': [ch.strip() for ch in os.getenv('WPM_NOTIFICATION_CHANNELS', '').split(',') if ch.strip()]
        }
        config_dict['dependency_config'] = DependencyConfig(**dependency_config_dict)
        
        # 自动检测配置
        config_dict.update({
            'enable_auto_detection': os.getenv('WPM_ENABLE_AUTO_DETECTION', 'true').lower() == 'true',
            'auto_detection_interval': int(os.getenv('WPM_AUTO_DETECTION_INTERVAL', '300')),
            'enable_framework_monitoring': os.getenv('WPM_ENABLE_FRAMEWORK_MONITORING', 'true').lower() == 'true',
        })
        
        # 优雅降级配置
        config_dict.update({
            'enable_graceful_degradation': os.getenv('WPM_ENABLE_GRACEFUL_DEGRADATION', 'true').lower() == 'true',
            'fallback_to_basic_monitor': os.getenv('WPM_FALLBACK_TO_BASIC_MONITOR', 'true').lower() == 'true',
            'show_dependency_warnings': os.getenv('WPM_SHOW_DEPENDENCY_WARNINGS', 'true').lower() == 'true',
        })
        
        # 安装建议配置
        config_dict.update({
            'show_installation_suggestions': os.getenv('WPM_SHOW_INSTALLATION_SUGGESTIONS', 'true').lower() == 'true',
            'suggest_optimal_installation': os.getenv('WPM_SUGGEST_OPTIMAL_INSTALLATION', 'true').lower() == 'true',
            'include_size_estimates': os.getenv('WPM_INCLUDE_SIZE_ESTIMATES', 'true').lower() == 'true',
        })
        
        logger.info("配置已从环境变量加载")
        return cls.from_dict(config_dict)
    
    
    
    def validate_for_framework(self, framework: str) -> None:
        """验证框架特定配置"""
        if framework == 'fastapi':
            if self.fastapi_async_timeout <= 0:
                raise ValueError("FastAPI异步超时时间必须大于0")
            if self.fastapi_max_concurrent_alerts <= 0:
                raise ValueError("FastAPI最大并发告警数必须大于0")
        elif framework == 'flask':
            if self.flask_wsgi_buffer_size <= 0:
                raise ValueError("Flask WSGI缓冲区大小必须大于0")
            if self.flask_request_body_limit <= 0:
                raise ValueError("Flask请求体限制必须大于0")
        
        # 验证告警重试配置
        if self.alert_max_retries < 0:
            raise ValueError("告警最大重试次数不能为负数")
        if self.alert_retry_delay < 0:
            raise ValueError("告警重试延迟不能为负数")
        
        # 验证依赖管理配置
        self.validate_dependency_config()
        
        # 验证自动检测配置
        if self.auto_detection_interval <= 0:
            raise ValueError("自动检测间隔必须大于0")
    
    def validate_dependency_config(self) -> None:
        """验证依赖管理配置"""
        if not isinstance(self.dependency_config, DependencyConfig):
            raise ValueError("dependency_config必须是DependencyConfig实例")
        
        # 验证首选框架
        if self.dependency_config.preferred_frameworks:
            supported_frameworks = ['flask', 'fastapi']  # 可以从FrameworkDetector获取
            for framework in self.dependency_config.preferred_frameworks:
                if framework not in supported_frameworks:
                    raise ValueError(f"不支持的首选框架: {framework}")
        
        # 验证通知渠道
        if self.dependency_config.notification_channels:
            supported_channels = ['mattermost', 'file', 'console']
            for channel in self.dependency_config.notification_channels:
                if channel not in supported_channels:
                    raise ValueError(f"不支持的通知渠道: {channel}")
    
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
    
    def get_dependency_config_dict(self) -> Dict[str, Any]:
        """获取依赖配置的字典表示"""
        return {
            'skip_dependency_check': self.dependency_config.skip_dependency_check,
            'strict_dependencies': self.dependency_config.strict_dependencies,
            'auto_install_deps': self.dependency_config.auto_install_deps,
            'preferred_frameworks': self.dependency_config.preferred_frameworks,
            'notification_channels': self.dependency_config.notification_channels
        }
    
    def update_dependency_config(self, **kwargs) -> None:
        """更新依赖配置"""
        for key, value in kwargs.items():
            if hasattr(self.dependency_config, key):
                setattr(self.dependency_config, key, value)
            else:
                raise ValueError(f"未知的依赖配置项: {key}")
        
        # 重新验证配置
        self.validate_dependency_config()
    
    def is_framework_preferred(self, framework: str) -> bool:
        """检查框架是否在首选列表中"""
        if not self.dependency_config.preferred_frameworks:
            return True  # 没有首选框架时，所有框架都被接受
        return framework in self.dependency_config.preferred_frameworks
    
    def should_skip_dependency_check(self) -> bool:
        """是否应该跳过依赖检查"""
        return self.dependency_config.skip_dependency_check
    
    def is_strict_dependencies_mode(self) -> bool:
        """是否为严格依赖模式"""
        return self.dependency_config.strict_dependencies
    
    def get_auto_detection_config(self) -> Dict[str, Any]:
        """获取自动检测配置"""
        return {
            'enable_auto_detection': self.enable_auto_detection,
            'auto_detection_interval': self.auto_detection_interval,
            'enable_framework_monitoring': self.enable_framework_monitoring
        }
    
    def get_graceful_degradation_config(self) -> Dict[str, Any]:
        """获取优雅降级配置"""
        return {
            'enable_graceful_degradation': self.enable_graceful_degradation,
            'fallback_to_basic_monitor': self.fallback_to_basic_monitor,
            'show_dependency_warnings': self.show_dependency_warnings
        }
    
    def get_installation_suggestion_config(self) -> Dict[str, Any]:
        """获取安装建议配置"""
        return {
            'show_installation_suggestions': self.show_installation_suggestions,
            'suggest_optimal_installation': self.suggest_optimal_installation,
            'include_size_estimates': self.include_size_estimates
        }
    
    def get_effective_config(self) -> Dict[str, Any]:
        """获取生效的配置信息，包含框架特定配置和依赖管理配置"""
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
        
        # 添加依赖管理配置
        config_dict.update({
            'dependency_config': self.get_dependency_config_dict(),
            'enable_auto_detection': self.enable_auto_detection,
            'auto_detection_interval': self.auto_detection_interval,
            'enable_framework_monitoring': self.enable_framework_monitoring,
            'enable_graceful_degradation': self.enable_graceful_degradation,
            'fallback_to_basic_monitor': self.fallback_to_basic_monitor,
            'show_dependency_warnings': self.show_dependency_warnings,
            'show_installation_suggestions': self.show_installation_suggestions,
            'suggest_optimal_installation': self.suggest_optimal_installation,
            'include_size_estimates': self.include_size_estimates,
        })
        
        return config_dict
    
    @classmethod
    def create_with_dependency_config(
        cls, 
        dependency_config: Optional[DependencyConfig] = None,
        **kwargs
    ) -> 'UnifiedConfig':
        """
        创建带有依赖配置的UnifiedConfig实例
        
        Args:
            dependency_config: 依赖配置实例
            **kwargs: 其他配置参数
            
        Returns:
            UnifiedConfig: 配置实例
        """
        if dependency_config is None:
            dependency_config = DependencyConfig.from_env_vars(os.environ)
        
        kwargs['dependency_config'] = dependency_config
        return cls(**kwargs)
    
    def merge_with_env_dependency_config(self) -> None:
        """合并环境变量中的依赖配置"""
        env_dependency_config = DependencyConfig.from_env_vars(os.environ)
        
        # 合并配置（环境变量优先）
        if env_dependency_config.skip_dependency_check != DependencyConfig().skip_dependency_check:
            self.dependency_config.skip_dependency_check = env_dependency_config.skip_dependency_check
        
        if env_dependency_config.strict_dependencies != DependencyConfig().strict_dependencies:
            self.dependency_config.strict_dependencies = env_dependency_config.strict_dependencies
        
        if env_dependency_config.auto_install_deps != DependencyConfig().auto_install_deps:
            self.dependency_config.auto_install_deps = env_dependency_config.auto_install_deps
        
        if env_dependency_config.preferred_frameworks:
            self.dependency_config.preferred_frameworks = env_dependency_config.preferred_frameworks
        
        if env_dependency_config.notification_channels:
            self.dependency_config.notification_channels = env_dependency_config.notification_channels