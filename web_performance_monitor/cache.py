"""
缓存管理模块

提供告警缓存管理，防止重复告警
"""

import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from .models import CacheEntry, PerformanceMetrics
from .exceptions import CacheError


class CacheManager:
    """缓存管理器
    
    管理告警历史缓存，防止重复告警
    """
    
    def __init__(self, max_entries: int = 10000):
        """初始化缓存管理器
        
        Args:
            max_entries: 最大缓存条目数，防止内存无限增长
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()  # 线程安全
        self._max_entries = max_entries
        self.logger = logging.getLogger(__name__)
    
    def is_recently_alerted(self, key: str, window_days: int = 10) -> bool:
        """检查是否在配置的时间窗口内（默认10天）已告警
        
        Args:
            key: 缓存键
            window_days: 时间窗口（天）
            
        Returns:
            bool: 是否在时间窗口内已告警
        """
        with self._lock:
            try:
                entry = self._cache.get(key)
                if not entry:
                    return False
                
                # 检查是否过期
                if entry.is_expired(window_days):
                    # 清理过期条目
                    del self._cache[key]
                    self.logger.debug(f"清理过期缓存条目: {key}")
                    return False
                
                self.logger.debug(f"发现重复告警: {key}")
                return True
                
            except Exception as e:
                self.logger.error(f"检查缓存失败: {e}")
                return False
    
    def mark_alerted(self, key: str, data: Any = None) -> None:
        """标记已告警，防止重复通知
        
        Args:
            key: 缓存键
            data: 关联数据（可选）
        """
        with self._lock:
            try:
                # 检查是否超过最大条目数
                if len(self._cache) >= self._max_entries:
                    # 清理最旧的条目（清理10%的条目）
                    cleanup_count = max(1, self._max_entries // 10)
                    self._cleanup_oldest_entries(cleanup_count)
                    self.logger.info(f"缓存条目达到上限，清理了 {cleanup_count} 个最旧条目")
                
                entry = CacheEntry(
                    key=key,
                    timestamp=datetime.now(),
                    data=data
                )
                self._cache[key] = entry
                self.logger.debug(f"标记告警缓存: {key}")
                
            except Exception as e:
                self.logger.error(f"标记告警缓存失败: {e}")
                raise CacheError(f"标记告警缓存失败: {e}")
    
    def generate_alert_key(self, endpoint: str, request_url: str, request_params: dict) -> str:
        """生成告警缓存键，基于接口、URL和参数
        
        Args:
            endpoint: 接口端点
            request_url: 请求URL
            request_params: 请求参数
            
        Returns:
            str: 生成的缓存键
        """
        import hashlib
        import json
        
        try:
            # 创建包含关键信息的字符串
            key_data = {
                'endpoint': endpoint,
                'request_url': request_url,
                'request_params': request_params
            }
            
            # 排序确保一致性
            key_string = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
            
            # 生成MD5哈希作为缓存键
            cache_key = hashlib.md5(key_string.encode('utf-8')).hexdigest()
            
            self.logger.debug(f"生成缓存键: {endpoint} -> {cache_key}")
            return cache_key
            
        except Exception as e:
            self.logger.error(f"生成缓存键失败: {e}")
            # 返回简化的键
            return f"{endpoint}_{hash(str(request_params))}"
    
    def generate_metrics_key(self, metrics: PerformanceMetrics) -> str:
        """从性能指标生成缓存键
        
        Args:
            metrics: 性能指标数据
            
        Returns:
            str: 生成的缓存键
        """
        return self.generate_alert_key(
            metrics.endpoint,
            metrics.request_url,
            metrics.request_params
        )
    
    def cleanup_expired_entries(self, window_days: int) -> int:
        """清理过期的缓存条目
        
        Args:
            window_days: 时间窗口（天）
            
        Returns:
            int: 清理的条目数量
        """
        with self._lock:
            try:
                expired_keys = []
                
                for key, entry in self._cache.items():
                    if entry.is_expired(window_days):
                        expired_keys.append(key)
                
                # 删除过期条目
                for key in expired_keys:
                    del self._cache[key]
                
                if expired_keys:
                    self.logger.info(f"清理了 {len(expired_keys)} 个过期缓存条目")
                
                return len(expired_keys)
                
            except Exception as e:
                self.logger.error(f"清理过期缓存失败: {e}")
                return 0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息
        
        Returns:
            Dict[str, Any]: 缓存统计信息
        """
        with self._lock:
            try:
                now = datetime.now()
                total_entries = len(self._cache)
                
                # 统计不同时间段的条目
                recent_1h = 0
                recent_24h = 0
                recent_7d = 0
                
                for entry in self._cache.values():
                    age = now - entry.timestamp
                    if age <= timedelta(hours=1):
                        recent_1h += 1
                    if age <= timedelta(days=1):
                        recent_24h += 1
                    if age <= timedelta(days=7):
                        recent_7d += 1
                
                # 获取大小信息
                size_info = self.get_cache_size_info()
                
                return {
                    'total_entries': total_entries,
                    'max_entries': self._max_entries,
                    'usage_percentage': size_info['usage_percentage'],
                    'available_slots': size_info['available_slots'],
                    'recent_1h': recent_1h,
                    'recent_24h': recent_24h,
                    'recent_7d': recent_7d,
                    'oldest_entry': min((entry.timestamp for entry in self._cache.values()), default=None),
                    'newest_entry': max((entry.timestamp for entry in self._cache.values()), default=None)
                }
                
            except Exception as e:
                self.logger.error(f"获取缓存统计失败: {e}")
                return {'error': str(e)}
    
    def get_recent_alerts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """获取最近的告警记录
        
        Args:
            hours: 时间范围（小时）
            
        Returns:
            List[Dict[str, Any]]: 最近的告警记录列表
        """
        with self._lock:
            try:
                cutoff_time = datetime.now() - timedelta(hours=hours)
                recent_alerts = []
                
                for key, entry in self._cache.items():
                    if entry.timestamp >= cutoff_time:
                        recent_alerts.append({
                            'key': key,
                            'timestamp': entry.timestamp,
                            'data': entry.data
                        })
                
                # 按时间排序（最新的在前）
                recent_alerts.sort(key=lambda x: x['timestamp'], reverse=True)
                
                return recent_alerts
                
            except Exception as e:
                self.logger.error(f"获取最近告警失败: {e}")
                return []
    
    def clear_cache(self) -> None:
        """清空所有缓存"""
        with self._lock:
            try:
                cache_size = len(self._cache)
                self._cache.clear()
                self.logger.info(f"已清空缓存，删除了 {cache_size} 个条目")
                
            except Exception as e:
                self.logger.error(f"清空缓存失败: {e}")
                raise CacheError(f"清空缓存失败: {e}")
    
    def remove_entry(self, key: str) -> bool:
        """删除指定的缓存条目
        
        Args:
            key: 缓存键
            
        Returns:
            bool: 是否成功删除
        """
        with self._lock:
            try:
                if key in self._cache:
                    del self._cache[key]
                    self.logger.debug(f"删除缓存条目: {key}")
                    return True
                else:
                    self.logger.debug(f"缓存条目不存在: {key}")
                    return False
                    
            except Exception as e:
                self.logger.error(f"删除缓存条目失败: {e}")
                return False
    
    def _cleanup_oldest_entries(self, count: int) -> int:
        """清理最旧的缓存条目
        
        Args:
            count: 要清理的条目数量
            
        Returns:
            int: 实际清理的条目数量
        """
        try:
            if not self._cache:
                return 0
            
            # 按时间戳排序，获取最旧的条目
            sorted_entries = sorted(
                self._cache.items(),
                key=lambda x: x[1].timestamp
            )
            
            # 删除最旧的条目
            cleanup_count = min(count, len(sorted_entries))
            for i in range(cleanup_count):
                key = sorted_entries[i][0]
                del self._cache[key]
            
            self.logger.debug(f"清理了 {cleanup_count} 个最旧的缓存条目")
            return cleanup_count
            
        except Exception as e:
            self.logger.error(f"清理最旧条目失败: {e}")
            return 0
    
    def get_cache_size_info(self) -> Dict[str, Any]:
        """获取缓存大小信息
        
        Returns:
            Dict[str, Any]: 缓存大小信息
        """
        with self._lock:
            return {
                'current_entries': len(self._cache),
                'max_entries': self._max_entries,
                'usage_percentage': (len(self._cache) / self._max_entries) * 100,
                'available_slots': self._max_entries - len(self._cache)
            }
    
    def get_entry(self, key: str) -> Optional[CacheEntry]:
        """获取指定的缓存条目
        
        Args:
            key: 缓存键
            
        Returns:
            Optional[CacheEntry]: 缓存条目，不存在时返回None
        """
        with self._lock:
            return self._cache.get(key)
    
    def __len__(self) -> int:
        """获取缓存条目数量"""
        return len(self._cache)
    
    def __contains__(self, key: str) -> bool:
        """检查缓存中是否包含指定键"""
        return key in self._cache