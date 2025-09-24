"""
工具函数模块

提供通用的工具函数
"""

import logging
from typing import Callable, Any


def safe_execute(func: Callable, *args, **kwargs) -> Any:
    """安全执行函数，捕获所有异常

    Args:
        func: 要执行的函数
        *args: 位置参数
        **kwargs: 关键字参数

    Returns:
        Any: 函数执行结果，异常时返回None
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
        return None


def validate_threshold(threshold: float) -> float:
    """验证阈值配置

    Args:
        threshold: 阈值

    Returns:
        float: 验证后的阈值

    Raises:
        ValueError: 阈值无效时抛出
    """
    if not isinstance(threshold, (int, float)) or threshold <= 0:
        raise ValueError(f"阈值必须是正数，当前值: {threshold}")
    return float(threshold)


def validate_window_days(days: int) -> int:
    """验证时间窗口配置

    Args:
        days: 天数

    Returns:
        int: 验证后的天数

    Raises:
        ValueError: 天数无效时抛出
    """
    if not isinstance(days, int) or days <= 0:
        raise ValueError(f"时间窗口必须是正整数，当前值: {days}")
    return days
