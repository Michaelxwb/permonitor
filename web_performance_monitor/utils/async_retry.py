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
        timeout: float = None,
        *args, **kwargs
    ) -> Any:
        """异步操作重试机制
        
        Args:
            operation: 要执行的异步操作
            max_retries: 最大重试次数
            delay: 初始延迟时间（秒）
            backoff_factor: 延迟时间增长因子
            timeout: 操作超时时间（秒）
            *args, **kwargs: 传递给操作的参数
        
        Returns:
            Any: 操作返回值
            
        Raises:
            Exception: 如果所有重试都失败
        """
        logger = logging.getLogger(__name__)
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                # 如果设置了超时，使用wait_for执行
                if timeout is not None:
                    return await asyncio.wait_for(operation(*args, **kwargs), timeout=timeout)
                else:
                    return await operation(*args, **kwargs)
            except asyncio.TimeoutError as e:
                last_exception = e
                logger.error(f"异步操作超时 ({timeout}秒): {e}")
                if attempt < max_retries:
                    wait_time = delay * (backoff_factor ** attempt)
                    logger.warning(f"异步操作超时，{wait_time}秒后重试 (尝试 {attempt + 1}/{max_retries + 1})")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"异步操作最终超时，已达到最大重试次数")
                # 重新抛出超时异常，让调用者能够捕获
                if attempt == max_retries:
                    raise e
            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    wait_time = delay * (backoff_factor ** attempt)
                    logger.warning(f"异步操作失败，{wait_time}秒后重试 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"异步操作最终失败，已达到最大重试次数: {e}")
        
        raise last_exception