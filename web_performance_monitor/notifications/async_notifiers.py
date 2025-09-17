"""
异步通知器

提供异步通知发送功能
"""

import asyncio
import aiofiles
import aiohttp
import logging
from datetime import datetime
from typing import Any

from ..models.models import PerformanceMetrics
from ..utils.async_retry import AsyncRetryHandler


class AsyncLocalFileNotifier:
    """异步本地文件通知器"""

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.logger = logging.getLogger(self.__class__.__name__)

    async def send_notification_async(self, metrics: PerformanceMetrics, html_report: str) -> bool:
        """异步发送本地文件通知"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"peralert_{timestamp}_{metrics.endpoint.replace('/', '_')}.html"
            filepath = f"{self.output_dir}/{filename}"

            async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
                await f.write(html_report)

            self.logger.info(f"异步本地文件通知已保存: {filepath}")
            return True

        except Exception as e:
            self.logger.error(f"异步本地文件通知失败: {e}")
            return False


class AsyncMattermostNotifier:
    """异步Mattermost通知器"""

    def __init__(self, server_url: str, token: str, channel_id: str):
        self.server_url = server_url.rstrip('/')
        self.token = token
        self.channel_id = channel_id
        self.logger = logging.getLogger(self.__class__.__name__)

    async def send_notification_async(self, metrics: PerformanceMetrics, html_report: str) -> bool:
        """异步发送Mattermost通知"""
        try:
            return await AsyncRetryHandler.retry_async_operation(
                self._send_mattermost_message,
                max_retries=3,
                delay=1.0,
                backoff_factor=2.0,
                metrics=metrics,
                html_report=html_report
            )
        except Exception as e:
            self.logger.error(f"异步Mattermost通知最终失败: {e}")
            return False

    async def _send_mattermost_message(self, metrics: PerformanceMetrics, html_report: str) -> bool:
        """发送Mattermost消息"""
        url = f"{self.server_url}/api/v4/posts"
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }

        message = f"""
**性能告警** 🚨

**接口**: {metrics.endpoint}
**执行时间**: {metrics.execution_time:.2f}秒
**请求方法**: {metrics.request_method}
**状态码**: {metrics.status_code}
**时间**: {metrics.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

详细性能报告已生成。
        """.strip()

        data = {
            'channel_id': self.channel_id,
            'message': message
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                if response.status == 201:
                    self.logger.info("异步Mattermost通知发送成功")
                    return True
                else:
                    error_text = await response.text()
                    self.logger.error(f"异步Mattermost通知失败: {response.status} - {error_text}")
                    return False
