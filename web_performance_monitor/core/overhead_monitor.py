"""
性能开销监控器

确保监控开销不超过5%
"""

import logging
from typing import List


class PerformanceOverheadMonitor:
    """性能开销监控器 - 确保监控开销不超过5%"""
    
    def __init__(self, max_overhead_ratio: float = 0.05):
        self.max_overhead_ratio = max_overhead_ratio
        self.overhead_samples: List[float] = []
        self.max_samples = 100
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def record_overhead(self, original_time: float, monitoring_time: float):
        """记录监控开销"""
        if original_time > 0:
            overhead_ratio = (monitoring_time - original_time) / original_time
            overhead_ratio = max(0.0, overhead_ratio)  # 确保不为负数
            
            self.overhead_samples.append(overhead_ratio)
            
            # 保持样本数量在限制内
            if len(self.overhead_samples) > self.max_samples:
                self.overhead_samples.pop(0)
            
            # 检查是否超过阈值
            if overhead_ratio > self.max_overhead_ratio:
                self.logger.warning(f"监控开销超过阈值: {overhead_ratio:.2%} > {self.max_overhead_ratio:.2%}")
    
    def get_average_overhead(self) -> float:
        """获取平均监控开销"""
        if not self.overhead_samples:
            return 0.0
        return sum(self.overhead_samples) / len(self.overhead_samples)
    
    def is_overhead_acceptable(self) -> bool:
        """检查监控开销是否可接受"""
        avg_overhead = self.get_average_overhead()
        return avg_overhead <= self.max_overhead_ratio
    
    def get_overhead_stats(self) -> dict:
        """获取开销统计信息"""
        if not self.overhead_samples:
            return {
                'sample_count': 0,
                'average_overhead': 0.0,
                'max_overhead': 0.0,
                'min_overhead': 0.0,
                'is_acceptable': True
            }
        
        return {
            'sample_count': len(self.overhead_samples),
            'average_overhead': self.get_average_overhead(),
            'max_overhead': max(self.overhead_samples),
            'min_overhead': min(self.overhead_samples),
            'is_acceptable': self.is_overhead_acceptable()
        }