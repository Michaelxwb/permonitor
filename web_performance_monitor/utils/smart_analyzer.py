"""
智能性能分析器 - 减少开销的实现

通过采样和条件触发来降低性能开销
"""

import time
import logging
import threading
from typing import Optional, Dict, Any, List
from collections import defaultdict, deque
import statistics
import random

from .analyzer import PerformanceAnalyzer
from ..exceptions.exceptions import ProfilingError


class SmartPerformanceAnalyzer:
    """智能性能分析器 - 通过采样和条件触发降低开销"""
    
    def __init__(self, sampling_rate: float = 0.1, min_requests_before_profiling: int = 10):
        """
        初始化智能分析器
        
        Args:
            sampling_rate: 采样率 (0.0-1.0)，默认10%
            min_requests_before_profiling: 开始分析前需要的最小请求数
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.sampling_rate = sampling_rate
        self.min_requests_before_profiling = min_requests_before_profiling
        
        # 基础分析器（用于详细分析）
        self.base_analyzer = PerformanceAnalyzer()
        
        # 简单计时器（低开销）
        self.simple_timer = SimpleTimer()
        
        # 请求统计
        self.request_stats = RequestStats()
        
        # 采样控制
        self._request_count = 0
        self._profiled_count = 0
        self._lock = threading.Lock()
        
        # 自适应采样
        self.adaptive_sampling = True
        self.current_sampling_rate = sampling_rate
        self.performance_history = deque(maxlen=100)  # 最近100次请求的性能数据
        
        self.logger.info(f"智能分析器初始化完成，采样率: {sampling_rate}")
    
    def should_profile(self, request_info: Dict[str, Any]) -> bool:
        """决定是否应该进行性能分析"""
        with self._lock:
            self._request_count += 1
            
            # 还没达到最小请求数，不进行详细分析
            if self._request_count < self.min_requests_before_profiling:
                return False
            
            # 自适应采样调整
            if self.adaptive_sampling and len(self.performance_history) >= 20:
                self._adjust_sampling_rate()
            
            # 基于采样率决定是否分析
            should_sample = random.random() < self.current_sampling_rate
            
            # 对慢请求强制分析（即使采样率未命中）
            endpoint = request_info.get('endpoint', '')
            avg_time = self.request_stats.get_average_time(endpoint)
            if avg_time and avg_time > 0.1:  # 平均响应时间超过100ms
                should_sample = True
                self.logger.debug(f"强制分析慢请求: {endpoint} (平均: {avg_time:.3f}s)")
            
            # 对非常快的函数降低采样率（避免过度开销）
            if avg_time and avg_time < 0.001:  # 小于1ms的函数
                should_sample = should_sample and random.random() < 0.1  # 额外90%过滤
                self.logger.debug(f"快速函数降低采样率: {endpoint} (平均: {avg_time:.3f}s)")
            
            if should_sample:
                self._profiled_count += 1
            
            return should_sample
    
    def start_profiling(self) -> Optional[Dict[str, Any]]:
        """开始性能分析（可能返回简单计时器或详细分析器）"""
        try:
            # 对于非常快的操作，只使用简单计时器，不进行详细分析
            # 这样可以避免pyinstrument的开销
            if self.current_sampling_rate < 0.1:
                return {'type': 'simple', 'timer': self.simple_timer.start()}
            
            # 尝试启动详细分析
            profiler = self.base_analyzer.start_profiling()
            if profiler:
                return {'type': 'detailed', 'profiler': profiler}
            else:
                # 回退到简单计时
                return {'type': 'simple', 'timer': self.simple_timer.start()}
        except Exception as e:
            self.logger.debug(f"启动分析失败，使用简单计时: {e}")
            return {'type': 'simple', 'timer': self.simple_timer.start()}
    
    def stop_profiling(self, profiling_context: Optional[Dict[str, Any]]) -> Optional[str]:
        """停止性能分析"""
        if not profiling_context:
            return None
        
        try:
            profiling_type = profiling_context.get('type', 'simple')
            
            if profiling_type == 'detailed':
                profiler = profiling_context.get('profiler')
                if profiler:
                    # 只在需要时生成HTML报告
                    return self.base_analyzer.stop_profiling(profiler)
            else:
                timer = profiling_context.get('timer')
                if timer:
                    elapsed = self.simple_timer.stop(timer)
                    # 简单计时器不生成HTML报告
                    return None
                    
        except Exception as e:
            self.logger.debug(f"停止分析失败: {e}")
            return None
        
        return None
    
    def get_execution_time(self, profiling_context: Optional[Dict[str, Any]]) -> float:
        """获取执行时间"""
        if not profiling_context:
            return 0.0
        
        try:
            profiling_type = profiling_context.get('type', 'simple')
            
            if profiling_type == 'detailed':
                profiler = profiling_context.get('profiler')
                if profiler:
                    return self.base_analyzer.get_execution_time(profiler)
            else:
                timer = profiling_context.get('timer')
                if timer:
                    return self.simple_timer.get_elapsed_time(timer)
                    
        except Exception as e:
            self.logger.debug(f"获取执行时间失败: {e}")
            return 0.0
        
        return 0.0
    
    def record_request(self, request_info: Dict[str, Any], execution_time: float, was_profiled: bool) -> None:
        """记录请求信息用于统计分析"""
        endpoint = request_info.get('endpoint', '')
        self.request_stats.record_request(endpoint, execution_time)
        
        # 记录到性能历史
        self.performance_history.append({
            'endpoint': endpoint,
            'execution_time': execution_time,
            'was_profiled': was_profiled,
            'timestamp': time.time()
        })
        
        # 如果检测到函数非常快，进一步降低采样率
        if execution_time < 0.001 and was_profiled:  # 小于1ms且被分析了
            self.current_sampling_rate = max(0.01, self.current_sampling_rate * 0.5)
            self.logger.debug(f"检测到快速函数，降低采样率到: {self.current_sampling_rate}")
    
    def _adjust_sampling_rate(self) -> None:
        """自适应调整采样率"""
        if not self.performance_history:
            return
        
        # 计算最近请求的平均响应时间
        recent_times = [req['execution_time'] for req in list(self.performance_history)[-20:]]
        avg_time = statistics.mean(recent_times)
        
        # 根据性能调整采样率
        if avg_time < 0.01:  # 很快的应用，降低采样率
            self.current_sampling_rate = max(0.01, self.sampling_rate * 0.5)
        elif avg_time > 0.1:  # 较慢的应用，提高采样率
            self.current_sampling_rate = min(0.5, self.sampling_rate * 2.0)
        else:
            self.current_sampling_rate = self.sampling_rate
        
        self.logger.debug(f"自适应采样率调整: {avg_time:.3f}s -> {self.current_sampling_rate}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取分析器统计信息"""
        with self._lock:
            return {
                'total_requests': self._request_count,
                'profiled_requests': self._profiled_count,
                'sampling_rate': self.current_sampling_rate,
                'profile_rate': self._profiled_count / max(self._request_count, 1),
                'request_stats': self.request_stats.get_stats(),
                'adaptive_sampling_enabled': self.adaptive_sampling
            }


class SimpleTimer:
    """超轻量级计时器"""
    
    def __init__(self):
        self.timers = {}
        self._counter = 0
    
    def start(self) -> int:
        """开始计时"""
        timer_id = self._counter
        self._counter += 1
        self.timers[timer_id] = time.perf_counter()
        return timer_id
    
    def stop(self, timer_id: int) -> float:
        """停止计时并返回耗时"""
        start_time = self.timers.pop(timer_id, None)
        if start_time is None:
            return 0.0
        return time.perf_counter() - start_time
    
    def get_elapsed_time(self, timer_id: int) -> float:
        """获取已耗时"""
        start_time = self.timers.get(timer_id)
        if start_time is None:
            return 0.0
        return time.perf_counter() - start_time


class RequestStats:
    """请求统计"""
    
    def __init__(self):
        self.endpoint_stats = defaultdict(lambda: {'times': deque(maxlen=100), 'count': 0})
        self._lock = threading.Lock()
    
    def record_request(self, endpoint: str, execution_time: float) -> None:
        """记录请求"""
        with self._lock:
            stats = self.endpoint_stats[endpoint]
            stats['times'].append(execution_time)
            stats['count'] += 1
    
    def get_average_time(self, endpoint: str) -> Optional[float]:
        """获取平均响应时间"""
        with self._lock:
            stats = self.endpoint_stats.get(endpoint)
            if not stats or not stats['times']:
                return None
            return statistics.mean(stats['times'])
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            result = {}
            for endpoint, stats in self.endpoint_stats.items():
                if stats['times']:
                    result[endpoint] = {
                        'count': stats['count'],
                        'avg_time': statistics.mean(stats['times']),
                        'min_time': min(stats['times']),
                        'max_time': max(stats['times'])
                    }
            return result