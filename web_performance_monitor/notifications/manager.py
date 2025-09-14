"""
通知管理器

处理同步和异步通知发送
"""

import asyncio
import logging
from typing import List, Any

from ..config.unified_config import UnifiedConfig
from ..models.models import PerformanceMetrics


class SyncNotificationManager:
    """同步通知管理器"""
    
    def __init__(self, config: UnifiedConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.notifiers = self._create_notifiers()
    
    def _create_notifiers(self) -> List[Any]:
        """创建同步通知器列表"""
        from .notifiers.factory import NotificationFactory
        factory = NotificationFactory(self.config)
        return factory.create_notifiers()
    
    def send_notifications(self, metrics: PerformanceMetrics, html_report: str) -> bool:
        """发送同步通知"""
        if not self.notifiers:
            return False
        
        success_count = 0
        for notifier in self.notifiers:
            try:
                if notifier.send_notification(metrics, html_report):
                    success_count += 1
            except Exception as e:
                self.logger.error(f"同步通知发送失败: {notifier.__class__.__name__} - {e}")
        
        return success_count > 0


class AsyncNotificationManager:
    """异步通知管理器"""
    
    def __init__(self, config: UnifiedConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.notifiers = self._create_notifiers()
    
    def _create_notifiers(self) -> List[Any]:
        """创建异步通知器列表"""
        notifiers = []
        
        if self.config.enable_local_file:
            from .async_notifiers import AsyncLocalFileNotifier
            notifiers.append(AsyncLocalFileNotifier(self.config.local_output_dir))
        
        if self.config.enable_mattermost:
            from .async_notifiers import AsyncMattermostNotifier
            notifiers.append(AsyncMattermostNotifier(
                self.config.mattermost_server_url,
                self.config.mattermost_token,
                self.config.mattermost_channel_id
            ))
        
        return notifiers
    
    async def send_notifications_async(self, metrics: PerformanceMetrics, html_report: str) -> bool:
        """并发发送所有通知"""
        if not self.notifiers:
            return False
        
        # 控制并发数量，满足Requirement 5中的并发控制要求
        max_concurrent = getattr(self.config, 'fastapi_max_concurrent_alerts', 10)
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def limited_send(notifier):
            async with semaphore:
                return await self._safe_send_notification_async(notifier, metrics, html_report)
        
        # 创建并发任务
        tasks = [limited_send(notifier) for notifier in self.notifiers]
        
        # 并发执行所有通知任务
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 记录结果
        success_count = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"通知器 {self.notifiers[i].__class__.__name__} 发送失败: {result}")
            elif result:
                self.logger.info(f"通知器 {self.notifiers[i].__class__.__name__} 发送成功")
                success_count += 1
        
        return success_count > 0
    
    async def _safe_send_notification_async(self, notifier: Any,
                                          metrics: PerformanceMetrics, html_report: str) -> bool:
        """安全发送异步通知"""
        try:
            return await notifier.send_notification_async(metrics, html_report)
        except Exception as e:
            self.logger.error(f"异步通知发送异常: {e}")
            return False