"""
性能分析器模块

基于pyinstrument实现性能分析和开销跟踪
"""

import logging
import time
from collections import deque
from typing import Optional

from pyinstrument import Profiler

from .exceptions import ProfilingError


class PerformanceAnalyzer:
    """性能分析器

    使用pyinstrument进行性能分析，生成详细的HTML报告
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def start_profiling(self) -> Optional[Profiler]:
        """开始pyinstrument性能分析

        Returns:
            Profiler: pyinstrument分析器实例，如果启动失败则返回None

        Raises:
            ProfilingError: 启动分析失败时抛出
        """
        try:
            # 使用async_mode='disabled'来避免多分析器冲突问题
            profiler = Profiler(async_mode='disabled')
            profiler.start()
            return profiler
        except Exception as e:
            # 检查是否是分析器冲突错误
            if "already a profiler running" in str(e):
                self.logger.warning(f"无法启动性能分析器: {e}")
                return None
            else:
                raise ProfilingError(f"启动性能分析失败: {e}")

    def stop_profiling(self, profiler: Optional[Profiler]) -> Optional[str]:
        """停止分析并生成包含详细性能分析的HTML报告

        Args:
            profiler: pyinstrument分析器实例

        Returns:
            str: HTML格式的性能报告，如果分析器无效则返回None

        Raises:
            ProfilingError: 停止分析或生成报告失败时抛出
        """
        # 如果分析器无效，直接返回
        if profiler is None:
            return None

        try:
            profiler.stop()

            # 生成HTML报告
            html_report = profiler.output_html()

            # 记录分析统计信息
            session = profiler.last_session
            if session:
                self.logger.debug(f"性能分析完成，采样数: {session.sample_count}")

            return html_report

        except Exception as e:
            raise ProfilingError(f"生成性能报告失败: {e}")

    def get_execution_time(self, profiler: Optional[Profiler]) -> float:
        """获取精确的执行时间

        Args:
            profiler: pyinstrument分析器实例

        Returns:
            float: 执行时间（秒）

        Raises:
            ProfilingError: 获取执行时间失败时抛出
        """
        # 如果分析器无效，返回0
        if profiler is None:
            return 0.0

        try:
            session = profiler.last_session
            if session and session.duration:
                return session.duration
            else:
                # 如果无法从session获取，返回0
                self.logger.warning("无法从profiler获取执行时间")
                return 0.0
        except Exception as e:
            raise ProfilingError(f"获取执行时间失败: {e}")


class PerformanceOverheadTracker:
    """监控工具性能开销跟踪器

    确保监控开销小于配置的阈值（默认5%）
    """

    def __init__(self, max_samples: int = 1000):
        """初始化开销跟踪器

        Args:
            max_samples: 最大样本数量，超过后会移除最旧的样本
        """
        self.overhead_samples: deque = deque(maxlen=max_samples)
        self.logger = logging.getLogger(__name__)
        self._total_overhead = 0.0
        self._sample_count = 0

    def track_overhead(self, original_time: float, monitored_time: float) -> None:
        """跟踪性能开销

        Args:
            original_time: 原始执行时间
            monitored_time: 监控后的执行时间
        """
        if original_time <= 0 or monitored_time <= 0:
            return

        overhead_ratio = (monitored_time - original_time) / original_time
        overhead_ratio = max(0.0, overhead_ratio)  # 确保不为负数

        # 添加到样本队列
        self.overhead_samples.append({
            'overhead_ratio': overhead_ratio,
            'original_time': original_time,
            'monitored_time': monitored_time,
            'timestamp': time.time()
        })

        # 更新统计信息
        self._total_overhead += overhead_ratio
        self._sample_count += 1

        # 记录调试信息
        self.logger.debug(
            f"性能开销跟踪: 原始时间={original_time:.4f}s, "
            f"监控时间={monitored_time:.4f}s, 开销={overhead_ratio:.2%}"
        )

    def get_average_overhead(self) -> float:
        """获取平均性能开销百分比

        Returns:
            float: 平均性能开销百分比（0-1之间）
        """
        if not self.overhead_samples:
            return 0.0

        total_overhead = sum(
            sample['overhead_ratio'] for sample in self.overhead_samples)
        return total_overhead / len(self.overhead_samples)

    def get_recent_overhead(self, recent_count: int = 100) -> float:
        """获取最近N次的平均性能开销

        Args:
            recent_count: 最近的样本数量

        Returns:
            float: 最近的平均性能开销百分比
        """
        if not self.overhead_samples:
            return 0.0

        recent_samples = list(self.overhead_samples)[-recent_count:]
        total_overhead = sum(sample['overhead_ratio'] for sample in recent_samples)
        return total_overhead / len(recent_samples)

    def check_overhead_threshold(self, threshold: float = 0.05) -> bool:
        """检查性能开销是否超过阈值

        Args:
            threshold: 开销阈值（默认5%）

        Returns:
            bool: 是否超过阈值
        """
        current_overhead = self.get_average_overhead()

        if current_overhead > threshold:
            self.logger.warning(
                f"性能开销超过阈值: 当前={current_overhead:.2%}, 阈值={threshold:.2%}"
            )
            return True

        return False

    def get_overhead_stats(self) -> dict:
        """获取开销统计信息

        Returns:
            dict: 包含各种统计信息的字典
        """
        if not self.overhead_samples:
            return {
                'sample_count': 0,
                'average_overhead': 0.0,
                'recent_overhead': 0.0,
                'max_overhead': 0.0,
                'min_overhead': 0.0
            }

        overheads = [sample['overhead_ratio'] for sample in self.overhead_samples]

        return {
            'sample_count': len(self.overhead_samples),
            'average_overhead': sum(overheads) / len(overheads),
            'recent_overhead': self.get_recent_overhead(50),  # 最近50次
            'max_overhead': max(overheads),
            'min_overhead': min(overheads)
        }

    def reset_stats(self) -> None:
        """重置统计信息"""
        self.overhead_samples.clear()
        self._total_overhead = 0.0
        self._sample_count = 0
        self.logger.info("性能开销统计信息已重置")


class TimingContext:
    """计时上下文管理器

    用于精确测量代码执行时间
    """

    def __init__(self, name: str = ""):
        self.name = name
        self.start_time = 0.0
        self.end_time = 0.0
        self.duration = 0.0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        self.duration = self.end_time - self.start_time

    def get_duration(self) -> float:
        """获取执行时间

        Returns:
            float: 执行时间（秒）
        """
        return self.duration
