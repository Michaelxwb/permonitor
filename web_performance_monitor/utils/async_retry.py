"""
异步重试处理器

提供异步操作的重试机制
"""

import asyncio
import logging
from typing import Callable, Any


class AsyncRetryHandler:
    """异步重试处理器 - 满足Requirement 5中的异步重试机制"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @staticmethod
    async def retry_async_operation(
        operation: Callable, 
        max_retries: int = 3, 
        delay: float = 1.0,
        backoff_factor: float = 2.0,
        *args, **kwargs
    ) -> Any:
        """异步操作重试机制"""
        logger = logging.getLogger(__name__)
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return await operation(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    wait_time = delay * (backoff_factor ** attempt)
                    logger.warning(f"异步操作失败，{wait_time}秒后重试 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"异步操作最终失败，已达到最大重试次数: {e}")
        
        raise last_exception