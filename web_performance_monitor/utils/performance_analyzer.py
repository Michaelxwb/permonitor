"""
性能分析器层次结构

定义抽象基类和同步/异步实现
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional, Any
import pyinstrument

from ..exceptions.exceptions import ProfilingError


class BasePerformanceAnalyzer(ABC):
    """性能分析器抽象基类"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def start_profiling(self) -> Optional[pyinstrument.Profiler]:
        """开始性能分析"""
        pass
    
    @abstractmethod
    def stop_profiling(self, profiler: pyinstrument.Profiler) -> Optional[str]:
        """停止性能分析并生成HTML报告"""
        pass
    
    @abstractmethod
    def get_execution_time(self, profiler: pyinstrument.Profiler) -> float:
        """获取执行时间"""
        pass


class SyncPerformanceAnalyzer(BasePerformanceAnalyzer):
    """同步性能分析器"""
    
    def start_profiling(self) -> Optional[pyinstrument.Profiler]:
        """开始同步性能分析"""
        try:
            profiler = pyinstrument.Profiler(async_mode='disabled')
            profiler.start()
            return profiler
        except Exception as e:
            if "already a profiler running" in str(e):
                self.logger.debug(f"无法启动性能分析器: {e}")
                return None
            else:
                self.logger.debug(f"启动性能分析失败: {e}")
                return None
    
    def stop_profiling(self, profiler: pyinstrument.Profiler) -> Optional[str]:
        """停止同步性能分析"""
        if profiler is None:
            return None
            
        try:
            profiler.stop()
            # 只在需要详细报告时才生成HTML
            # 对于性能开销测试，我们可以选择不生成HTML报告
            return None
        except Exception as e:
            self.logger.debug(f"停止性能分析失败: {e}")
            return None
    
    def get_execution_time(self, profiler: pyinstrument.Profiler) -> float:
        """获取同步执行时间"""
        if profiler is None:
            return 0.0
            
        try:
            session = profiler.last_session
            if session and session.duration:
                return session.duration
            return 0.0
        except Exception:
            return 0.0


class AsyncPerformanceAnalyzer(BasePerformanceAnalyzer):
    """异步性能分析器"""
    
    async def start_profiling_async(self) -> Optional[pyinstrument.Profiler]:
        """开始异步性能分析"""
        try:
            profiler = pyinstrument.Profiler(async_mode='enabled')
            profiler.start()
            return profiler
        except Exception as e:
            if "already a profiler running" in str(e):
                self.logger.debug(f"无法启动异步性能分析器: {e}")
                return None
            else:
                self.logger.debug(f"启动异步性能分析失败: {e}")
                return None
    
    async def stop_profiling_async(self, profiler: pyinstrument.Profiler) -> Optional[str]:
        """停止异步性能分析"""
        if profiler is None:
            return None
            
        try:
            profiler.stop()
            # 只在需要详细报告时才生成HTML
            # 对于性能开销测试，我们可以选择不生成HTML报告
            return None
        except Exception as e:
            self.logger.debug(f"停止异步性能分析失败: {e}")
            return None
    
    async def get_execution_time_async(self, profiler: pyinstrument.Profiler) -> float:
        """获取异步执行时间"""
        if profiler is None:
            return 0.0
            
        try:
            session = profiler.last_session
            if session and session.duration:
                return session.duration
            return 0.0
        except Exception:
            return 0.0
    
    # 为了兼容基类接口，提供同步版本
    def start_profiling(self) -> Optional[pyinstrument.Profiler]:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # 如果没有事件循环，创建一个新的
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.start_profiling_async())
    
    def stop_profiling(self, profiler: pyinstrument.Profiler) -> Optional[str]:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # 如果没有事件循环，创建一个新的
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.stop_profiling_async(profiler))
    
    def get_execution_time(self, profiler: pyinstrument.Profiler) -> float:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # 如果没有事件循环，创建一个新的
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.get_execution_time_async(profiler))