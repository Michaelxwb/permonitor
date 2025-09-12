"""
数据模型定义

定义性能监控相关的数据结构
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional


@dataclass
class PerformanceMetrics:
    """性能指标数据模型"""
    endpoint: str                           # 接口端点
    request_url: str                        # 完整请求URL
    request_params: Dict[str, Any]          # 请求参数
    execution_time: float                   # 执行时间（秒）
    timestamp: datetime                     # 时间戳
    request_method: str                     # HTTP方法
    status_code: int                        # 响应状态码
    profiler_data: Optional[str] = None     # pyinstrument分析数据
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'endpoint': self.endpoint,
            'request_url': self.request_url,
            'request_params': self.request_params,
            'execution_time': self.execution_time,
            'timestamp': self.timestamp.isoformat(),
            'request_method': self.request_method,
            'status_code': self.status_code,
            'profiler_data': self.profiler_data
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PerformanceMetrics':
        """从字典创建实例
        
        Args:
            data: 包含性能指标数据的字典
            
        Returns:
            PerformanceMetrics: 性能指标实例
        """
        # 解析时间戳
        if isinstance(data.get('timestamp'), str):
            from datetime import datetime
            timestamp = datetime.fromisoformat(data['timestamp'])
        else:
            timestamp = data.get('timestamp', datetime.now())
        
        return cls(
            endpoint=data.get('endpoint', ''),
            request_url=data.get('request_url', ''),
            request_params=data.get('request_params', {}),
            execution_time=data.get('execution_time', 0.0),
            timestamp=timestamp,
            request_method=data.get('request_method', 'GET'),
            status_code=data.get('status_code', 200),
            profiler_data=data.get('profiler_data')
        )
    
    def to_json(self) -> str:
        """转换为JSON字符串
        
        Returns:
            str: JSON格式的性能指标数据
        """
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    def get_cache_key(self) -> str:
        """生成缓存键
        
        基于端点、URL和参数生成唯一的缓存键
        
        Returns:
            str: 缓存键
        """
        import hashlib
        import json
        
        # 创建包含关键信息的字符串
        key_data = {
            'endpoint': self.endpoint,
            'request_url': self.request_url,
            'request_params': self.request_params
        }
        
        key_string = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
        
        # 生成MD5哈希
        return hashlib.md5(key_string.encode('utf-8')).hexdigest()
    
    def format_summary(self) -> str:
        """格式化摘要信息
        
        Returns:
            str: 格式化的摘要字符串
        """
        return (f"{self.request_method} {self.endpoint} "
                f"({self.execution_time:.2f}s, {self.status_code})")
    
    def is_slow(self, threshold: float) -> bool:
        """判断是否为慢请求
        
        Args:
            threshold: 时间阈值（秒）
            
        Returns:
            bool: 是否超过阈值
        """
        return self.execution_time > threshold


@dataclass
class AlertRecord:
    """告警记录数据模型"""
    endpoint: str                           # 接口端点
    request_url: str                        # 请求URL
    request_params: Dict[str, Any]          # 请求参数
    alert_time: datetime                    # 告警时间
    execution_time: float                   # 执行时间
    notification_status: Dict[str, bool]    # 各通知方式的发送状态
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'endpoint': self.endpoint,
            'request_url': self.request_url,
            'request_params': self.request_params,
            'alert_time': self.alert_time.isoformat(),
            'execution_time': self.execution_time,
            'notification_status': self.notification_status
        }


@dataclass
class CacheEntry:
    """缓存条目数据模型"""
    key: str                                # 缓存键
    timestamp: datetime                     # 时间戳
    data: Any                               # 缓存数据
    
    def is_expired(self, window_days: int) -> bool:
        """检查缓存是否过期
        
        Args:
            window_days: 时间窗口（天）
            
        Returns:
            bool: 是否过期
        """
        from datetime import timedelta
        expiry_time = self.timestamp + timedelta(days=window_days)
        return datetime.now() > expiry_time