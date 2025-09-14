"""
告警管理器层次结构

定义抽象基类和同步/异步实现
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional

from ..config.unified_config import UnifiedConfig
from ..models.models import PerformanceMetrics, AlertRecord
from ..utils.cache import CacheManager


class BaseAlertManager(ABC):
    """告警管理器抽象基类"""
    
    def __init__(self, config: UnifiedConfig):
        self.config = config
        self.cache_manager = CacheManager()
        self.notification_manager = self._create_notification_manager()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def _create_notification_manager(self) -> Any:
        """创建通知管理器"""
        pass
    
    @abstractmethod
    def process_alert(self, metrics: PerformanceMetrics, html_report: str) -> None:
        """处理告警"""
        pass
    
    def should_alert(self, metrics: PerformanceMetrics) -> bool:
        """判断是否应该发送告警"""
        if metrics.execution_time <= self.config.threshold_seconds:
            return False
        
        # 检查URL黑名单
        if self.config.is_url_blacklisted(metrics.request_url):
            self.logger.info(f"跳过黑名单URL告警: {metrics.request_url}")
            return False
        
        # 检查重复告警
        alert_key = self.cache_manager.generate_metrics_key(metrics)
        
        return not self.cache_manager.is_recently_alerted(
            alert_key, self.config.alert_window_days
        )
    
    def cleanup(self) -> None:
        """清理资源"""
        try:
            self.cache_manager.cleanup_expired_entries(self.config.alert_window_days)
        except Exception as e:
            self.logger.error(f"清理资源失败: {e}")


class SyncAlertManager(BaseAlertManager):
    """同步告警管理器"""
    
    def _create_notification_manager(self) -> Any:
        from ..notifications.manager import SyncNotificationManager
        return SyncNotificationManager(self.config)
    
    def process_alert(self, metrics: PerformanceMetrics, html_report: str) -> Optional[AlertRecord]:
        """处理同步告警"""
        if self.should_alert(metrics):
            try:
                success = self.notification_manager.send_notifications(metrics, html_report)
                
                # 标记已告警
                alert_key = self.cache_manager.generate_metrics_key(metrics)
                self.cache_manager.mark_alerted(alert_key)
                
                return AlertRecord(
                    endpoint=metrics.endpoint,
                    request_url=metrics.request_url,
                    request_params=metrics.request_params,
                    alert_time=metrics.timestamp,
                    execution_time=metrics.execution_time,
                    notification_status={'sync_notification': success}
                )
                
            except Exception as e:
                self.logger.error(f"处理告警失败: {e}")
                return None
        return None


class AsyncAlertManager(BaseAlertManager):
    """异步告警管理器 - 支持并发处理和重试机制"""
    
    def __init__(self, config: UnifiedConfig):
        super().__init__(config)
        # 创建信号量控制并发告警处理数量
        self.alert_semaphore = asyncio.Semaphore(
            getattr(config, 'fastapi_max_concurrent_alerts', 10)
        )
        # 跟踪正在处理的告警
        self._active_alerts = set()
        self._alert_stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'retried': 0
        }
    
    def _create_notification_manager(self) -> Any:
        from ..notifications.manager import AsyncNotificationManager
        return AsyncNotificationManager(self.config)
    
    async def process_alert_async(self, metrics: PerformanceMetrics, html_report: str) -> Optional[AlertRecord]:
        """处理异步告警 - 支持并发控制和重试机制"""
        if not self.should_alert(metrics):
            return None
        
        # 使用信号量控制并发数量
        async with self.alert_semaphore:
            alert_key = self.cache_manager.generate_metrics_key(metrics)
            
            # 防止重复处理同一告警
            if alert_key in self._active_alerts:
                self.logger.debug(f"告警正在处理中，跳过: {alert_key}")
                return None
            
            self._active_alerts.add(alert_key)
            self._alert_stats['total_processed'] += 1
            
            try:
                return await self._process_alert_with_retry(metrics, html_report, alert_key)
            finally:
                self._active_alerts.discard(alert_key)
    
    async def _process_alert_with_retry(self, metrics: PerformanceMetrics, 
                                      html_report: str, alert_key: str) -> Optional[AlertRecord]:
        """带重试机制的告警处理"""
        from ..utils.async_retry import AsyncRetryHandler
        
        max_retries = getattr(self.config, 'alert_max_retries', 3)
        retry_delay = getattr(self.config, 'alert_retry_delay', 1.0)
        
        try:
            # 使用异步重试机制发送通知
            success = await AsyncRetryHandler.retry_async_operation(
                self._send_notifications_safe,
                max_retries=max_retries,
                delay=retry_delay,
                backoff_factor=2.0,
                metrics=metrics,
                html_report=html_report
            )
            
            if success:
                self._alert_stats['successful'] += 1
                # 标记已告警
                self.cache_manager.mark_alerted(alert_key, {
                    'metrics': metrics.to_dict(),
                    'processed_at': datetime.now().isoformat()
                })
                
                return AlertRecord(
                    endpoint=metrics.endpoint,
                    request_url=metrics.request_url,
                    request_params=metrics.request_params,
                    alert_time=metrics.timestamp,
                    execution_time=metrics.execution_time,
                    notification_status={'async_notification': True}
                )
            else:
                self._alert_stats['failed'] += 1
                self.logger.error(f"告警处理最终失败: {alert_key}")
                return None
                
        except Exception as e:
            self._alert_stats['failed'] += 1
            self.logger.error(f"处理异步告警异常: {e}")
            return None
    
    async def _send_notifications_safe(self, metrics: PerformanceMetrics, html_report: str) -> bool:
        """安全发送通知，包装异常处理"""
        try:
            return await self.notification_manager.send_notifications_async(metrics, html_report)
        except Exception as e:
            self.logger.warning(f"通知发送失败，将重试: {e}")
            raise  # 重新抛出异常以触发重试
    
    async def process_multiple_alerts_async(self, alerts_data: list) -> list:
        """并发处理多个告警"""
        if not alerts_data:
            return []
        
        self.logger.info(f"开始并发处理 {len(alerts_data)} 个告警")
        
        # 创建并发任务
        tasks = []
        for alert_data in alerts_data:
            metrics = alert_data['metrics']
            html_report = alert_data['html_report']
            task = asyncio.create_task(
                self.process_alert_async(metrics, html_report)
            )
            tasks.append(task)
        
        # 并发执行所有告警处理
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        successful_alerts = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"告警 {i} 处理异常: {result}")
            elif result:
                successful_alerts.append(result)
        
        self.logger.info(f"并发告警处理完成: {len(successful_alerts)}/{len(alerts_data)} 成功")
        return successful_alerts
    
    def get_alert_stats(self) -> Dict[str, Any]:
        """获取告警处理统计信息"""
        return {
            **self._alert_stats,
            'active_alerts': len(self._active_alerts),
            'semaphore_available': self.alert_semaphore._value,
            'max_concurrent': getattr(self.config, 'fastapi_max_concurrent_alerts', 10)
        }
    
    async def cleanup_async(self) -> None:
        """异步清理资源"""
        try:
            # 等待所有活跃的告警处理完成
            if self._active_alerts:
                self.logger.info(f"等待 {len(self._active_alerts)} 个活跃告警处理完成...")
                # 最多等待30秒
                for _ in range(30):
                    if not self._active_alerts:
                        break
                    await asyncio.sleep(1)
                
                if self._active_alerts:
                    self.logger.warning(f"仍有 {len(self._active_alerts)} 个告警未完成处理")
            
            # 清理缓存
            self.cleanup()
            self.logger.info("异步告警管理器清理完成")
            
        except Exception as e:
            self.logger.error(f"异步清理失败: {e}")
    
    def process_alert(self, metrics: PerformanceMetrics, html_report: str) -> Optional[AlertRecord]:
        """同步接口兼容"""
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.process_alert_async(metrics, html_report))
        except RuntimeError:
            # 如果没有运行的事件循环，创建一个新的
            return asyncio.run(self.process_alert_async(metrics, html_report))