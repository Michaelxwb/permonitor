"""
配置管理模块

提供灵活的配置管理，支持环境变量和配置文件
"""

import os
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from .exceptions import ConfigurationError
from .utils import validate_threshold, validate_window_days


@dataclass
class Config:
    """性能监控配置类
    
    支持通过环境变量、配置文件或直接参数进行配置
    """
    
    # 性能阈值配置
    threshold_seconds: float = 1.0                      # 默认1秒阈值
    alert_window_days: int = 10                         # 默认10天重复告警窗口
    max_performance_overhead: float = 0.05              # 最大5%性能开销

    # 本地文件配置
    enable_local_file: bool = True                      # 默认启用本地文件通知
    local_output_dir: str = "/tmp"                      # 默认输出目录
    
    # Mattermost配置
    enable_mattermost: bool = False                     # 默认不启用Mattermost
    mattermost_server_url: str = ""                     # Mattermost服务器URL
    mattermost_token: str = ""                          # Mattermost访问令牌
    mattermost_channel_id: str = ""                     # Mattermost频道ID
    mattermost_max_retries: int = 3                     # 最大重试次数
    
    # 日志配置
    log_level: str = "INFO"                             # 日志级别
    
    def __post_init__(self):
        """初始化后验证配置"""
        self.validate()
    
    @classmethod
    def from_env(cls) -> 'Config':
        """从环境变量加载配置
        
        支持的环境变量：
        - WPM_THRESHOLD_SECONDS: 响应时间阈值
        - WPM_ALERT_WINDOW_DAYS: 重复告警时间窗口
        - WPM_MAX_PERFORMANCE_OVERHEAD: 最大性能开销
        - WPM_ENABLE_LOCAL_FILE: 启用本地文件通知
        - WPM_LOCAL_OUTPUT_DIR: 本地文件输出目录
        - WPM_ENABLE_MATTERMOST: 启用Mattermost通知
        - WPM_MATTERMOST_SERVER_URL: Mattermost服务器URL
        - WPM_MATTERMOST_TOKEN: Mattermost访问令牌
        - WPM_MATTERMOST_CHANNEL_ID: Mattermost频道ID
        - WPM_MATTERMOST_MAX_RETRIES: Mattermost最大重试次数
        - WPM_LOG_LEVEL: 日志级别
        
        Returns:
            Config: 从环境变量加载的配置实例
        """
        try:
            return cls(
                threshold_seconds=float(os.getenv('WPM_THRESHOLD_SECONDS', '1.0')),
                alert_window_days=int(os.getenv('WPM_ALERT_WINDOW_DAYS', '10')),
                max_performance_overhead=float(os.getenv('WPM_MAX_PERFORMANCE_OVERHEAD', '0.05')),
                
                enable_local_file=os.getenv('WPM_ENABLE_LOCAL_FILE', 'true').lower() == 'true',
                local_output_dir=os.getenv('WPM_LOCAL_OUTPUT_DIR', '/tmp'),
                
                enable_mattermost=os.getenv('WPM_ENABLE_MATTERMOST', 'false').lower() == 'true',
                mattermost_server_url=os.getenv('WPM_MATTERMOST_SERVER_URL', ''),
                mattermost_token=os.getenv('WPM_MATTERMOST_TOKEN', ''),
                mattermost_channel_id=os.getenv('WPM_MATTERMOST_CHANNEL_ID', ''),
                mattermost_max_retries=int(os.getenv('WPM_MATTERMOST_MAX_RETRIES', '3')),
                
                log_level=os.getenv('WPM_LOG_LEVEL', 'INFO')
            )
        except (ValueError, TypeError) as e:
            raise ConfigurationError(f"环境变量配置错误: {e}")
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'Config':
        """从字典加载配置
        
        Args:
            config_dict: 配置字典
            
        Returns:
            Config: 从字典加载的配置实例
            
        Raises:
            ConfigurationError: 配置无效时抛出
        """
        try:
            # 过滤掉不存在的字段
            valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
            filtered_dict = {k: v for k, v in config_dict.items() if k in valid_fields}
            
            return cls(**filtered_dict)
        except (ValueError, TypeError) as e:
            raise ConfigurationError(f"配置字典格式错误: {e}")
    
    @classmethod
    def from_file(cls, config_path: str) -> 'Config':
        """从配置文件加载配置
        
        支持JSON格式的配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            Config: 从文件加载的配置实例
            
        Raises:
            ConfigurationError: 文件读取或解析失败时抛出
        """
        try:
            if not os.path.exists(config_path):
                raise ConfigurationError(f"配置文件不存在: {config_path}")
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config_dict = json.load(f)
            
            return cls.from_dict(config_dict)
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"配置文件JSON格式错误: {e}")
        except IOError as e:
            raise ConfigurationError(f"配置文件读取失败: {e}")
    
    def validate(self) -> None:
        """验证配置有效性
        
        无效配置会使用默认值并记录警告
        
        Raises:
            ConfigurationError: 关键配置无效时抛出
        """
        logger = logging.getLogger(__name__)
        
        # 验证阈值
        try:
            self.threshold_seconds = validate_threshold(self.threshold_seconds)
        except ValueError as e:
            logger.warning(f"阈值配置无效，使用默认值1.0秒: {e}")
            self.threshold_seconds = 1.0
        
        # 验证时间窗口
        try:
            self.alert_window_days = validate_window_days(self.alert_window_days)
        except ValueError as e:
            logger.warning(f"时间窗口配置无效，使用默认值10天: {e}")
            self.alert_window_days = 10
        
        # 验证性能开销
        if not isinstance(self.max_performance_overhead, (int, float)) or not (0 < self.max_performance_overhead <= 1):
            logger.warning(f"性能开销配置无效，使用默认值5%: {self.max_performance_overhead}")
            self.max_performance_overhead = 0.05
        
        # 验证重试次数
        if not isinstance(self.mattermost_max_retries, int) or self.mattermost_max_retries < 0:
            logger.warning(f"重试次数配置无效，使用默认值3: {self.mattermost_max_retries}")
            self.mattermost_max_retries = 3
        
        # 验证输出目录
        if self.enable_local_file and not self.local_output_dir:
            logger.warning("本地文件输出目录为空，使用默认值/tmp")
            self.local_output_dir = "/tmp"
        
        # 验证Mattermost配置
        if self.enable_mattermost:
            missing_fields = []
            if not self.mattermost_server_url:
                missing_fields.append("mattermost_server_url")
            if not self.mattermost_token:
                missing_fields.append("mattermost_token")
            if not self.mattermost_channel_id:
                missing_fields.append("mattermost_channel_id")
            
            if missing_fields:
                logger.warning(f"Mattermost配置不完整，缺少字段: {missing_fields}，将禁用Mattermost通知")
                self.enable_mattermost = False
        
        # 验证日志级别
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.log_level.upper() not in valid_levels:
            logger.warning(f"日志级别无效，使用默认值INFO: {self.log_level}")
            self.log_level = "INFO"
        
        # 检查是否至少启用一种通知方式
        if not self.enable_local_file and not self.enable_mattermost:
            logger.warning("未启用任何通知方式，将启用本地文件通知")
            self.enable_local_file = True
    
    def get_effective_config(self) -> Dict[str, Any]:
        """获取生效的配置信息
        
        用于日志记录和调试，敏感信息会被脱敏
        
        Returns:
            Dict[str, Any]: 生效的配置字典
        """
        config_dict = {
            'threshold_seconds': self.threshold_seconds,
            'alert_window_days': self.alert_window_days,
            'max_performance_overhead': self.max_performance_overhead,
            'enable_local_file': self.enable_local_file,
            'local_output_dir': self.local_output_dir,
            'enable_mattermost': self.enable_mattermost,
            'mattermost_server_url': self.mattermost_server_url,
            'mattermost_channel_id': self.mattermost_channel_id,
            'mattermost_max_retries': self.mattermost_max_retries,
            'log_level': self.log_level
        }
        
        # 脱敏处理
        if self.mattermost_token:
            config_dict['mattermost_token'] = f"{self.mattermost_token[:8]}***"
        else:
            config_dict['mattermost_token'] = ""
        
        return config_dict
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（包含敏感信息）
        
        Returns:
            Dict[str, Any]: 完整的配置字典
        """
        return {
            'threshold_seconds': self.threshold_seconds,
            'alert_window_days': self.alert_window_days,
            'max_performance_overhead': self.max_performance_overhead,
            'enable_local_file': self.enable_local_file,
            'local_output_dir': self.local_output_dir,
            'enable_mattermost': self.enable_mattermost,
            'mattermost_server_url': self.mattermost_server_url,
            'mattermost_token': self.mattermost_token,
            'mattermost_channel_id': self.mattermost_channel_id,
            'mattermost_max_retries': self.mattermost_max_retries,
            'log_level': self.log_level
        }