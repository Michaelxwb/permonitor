"""
异步错误处理器

提供异步操作的错误处理和超时控制
"""

import asyncio
import logging
from typing import Callable, Any


class AsyncErrorHandler:
    """异步错误处理器"""
    
    @staticmethod
    async def safe_execute_async(coro_func: Callable, *args, **kwargs) -> Any:
        """安全执行异步函数"""
        logger = logging.getLogger(__name__)
        try:
            return await coro_func(*args, **kwargs)
        except asyncio.TimeoutError:
            logger.error(f"异步操作超时: {coro_func.__name__}")
            return None
        except asyncio.CancelledError:
            logger.warning(f"异步操作被取消: {coro_func.__name__}")
            return None
        except Exception as e:
            logger.error(f"异步操作异常 {coro_func.__name__}: {e}")
            return None
    
    @staticmethod
    async def safe_execute_with_timeout(coro_func: Callable, timeout: float, *args, **kwargs) -> Any:
        """带超时的安全异步执行"""
        logger = logging.getLogger(__name__)
        try:
            return await asyncio.wait_for(coro_func(*args, **kwargs), timeout=timeout)
        except asyncio.TimeoutError:
            logger.error(f"异步操作超时 ({timeout}s): {coro_func.__name__}")
            return None
        except Exception as e:
            logger.error(f"异步操作异常 {coro_func.__name__}: {e}")
            return None


class FrameworkCompatibilityError(Exception):
    """框架兼容性错误"""
    pass


class AsyncOperationError(Exception):
    """异步操作错误"""
    pass