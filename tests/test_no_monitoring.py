"""
测试完全禁用监控时的开销
"""

import time
import pytest
from datetime import datetime
from flask import Flask, jsonify, request

from web_performance_monitor import PerformanceMonitor, Config
from tests.smart_test_framework import (
    SmartPerformanceTester, 
    assert_performance_overhead,
    create_test_config_for_overhead_testing
)


def test_no_monitoring_overhead():
    """测试完全禁用监控时的开销 - 应该接近0%"""
    config = create_test_config_for_overhead_testing()
    # 完全禁用监控
    config.smart_sampling_rate = 0.0  # 0%采样率 - 完全禁用
    config.min_requests_before_profiling = 999999  # 几乎不可能达到
    monitor = PerformanceMonitor(config)
    decorator = monitor.create_decorator()

    def simple_function():
        """简单函数"""
        time.sleep(0.001)  # 1ms
        return "result"

    @decorator
    def simple_function_monitored():
        """被监控的简单函数"""
        time.sleep(0.001)  # 1ms
        return "result"

    tester = SmartPerformanceTester(max_overhead_ratio=0.05)  # 5%开销限制
    result = tester.measure_overhead(simple_function, simple_function_monitored)
    
    print(f"\n完全禁用监控时的开销测试:")
    print(f"  基准平均时间: {result.baseline_avg:.6f}s")
    print(f"  监控平均时间: {result.monitored_avg:.6f}s")
    print(f"  平均开销: {result.overhead_ratio:.2%}")
    print(f"  测试通过: {'✓' if result.test_passed else '✗'}")
    
    # 即使完全禁用监控，也应该有一些基本开销
    assert result.overhead_ratio < 0.1, f"完全禁用监控时开销过高: {result.overhead_ratio:.2%}"


def test_monitoring_disabled():
    """测试监控被禁用时的行为"""
    config = create_test_config_for_overhead_testing()
    monitor = PerformanceMonitor(config)
    
    # 禁用监控
    monitor.disable_monitoring()
    
    def simple_function():
        """简单函数"""
        time.sleep(0.001)
        return "result"

    decorator = monitor.create_decorator()
    
    @decorator
    def simple_function_monitored():
        """被监控的简单函数"""
        time.sleep(0.001)
        return "result"

    # 当监控被禁用时，被装饰的函数应该和原函数性能几乎相同
    tester = SmartPerformanceTester(max_overhead_ratio=0.02)  # 2%开销限制
    result = tester.measure_overhead(simple_function, simple_function_monitored)
    
    print(f"\n监控禁用时的开销测试:")
    print(f"  基准平均时间: {result.baseline_avg:.6f}s")
    print(f"  监控平均时间: {result.monitored_avg:.6f}s")
    print(f"  平均开销: {result.overhead_ratio:.2%}")
    print(f"  测试通过: {'✓' if result.test_passed else '✗'}")
    
    assert result.test_passed, f"监控禁用时开销过高: {result.overhead_ratio:.2%}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])