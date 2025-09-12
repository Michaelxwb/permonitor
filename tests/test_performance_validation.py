"""
性能验证测试模块

专门测试性能开销和监控精度
"""

import time
import statistics
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import pytest
from flask import Flask, jsonify

from web_performance_monitor import PerformanceMonitor, Config


class TestPerformanceOverheadValidation:
    """性能开销验证测试"""
    
    def setup_method(self):
        """测试前设置"""
        # 高阈值配置，避免告警影响性能测试
        self.config = Config(
            threshold_seconds=10.0,
            enable_local_file=False,  # 禁用文件写入
            enable_mattermost=False   # 禁用网络通知
        )
        self.monitor = PerformanceMonitor(self.config)
    
    def test_middleware_overhead_under_5_percent(self):
        """测试中间件性能开销小于5%"""
        # 创建基准应用（无监控）
        baseline_app = Flask(__name__)
        baseline_app.config['TESTING'] = True
        
        @baseline_app.route('/test')
        def baseline_endpoint():
            # 模拟一些计算工作
            result = sum(i * i for i in range(100))
            return jsonify({'result': result})
        
        baseline_client = baseline_app.test_client()
        
        # 创建监控应用
        monitored_app = Flask(__name__)
        monitored_app.config['TESTING'] = True
        
        @monitored_app.route('/test')
        def monitored_endpoint():
            # 相同的计算工作
            result = sum(i * i for i in range(100))
            return jsonify({'result': result})
        
        # 应用监控中间件
        monitored_app.wsgi_app = self.monitor.create_middleware()(monitored_app.wsgi_app)
        monitored_client = monitored_app.test_client()
        
        # 预热阶段
        for _ in range(5):
            baseline_client.get('/test')
            monitored_client.get('/test')
        
        # 基准测试
        baseline_times = []
        for _ in range(50):
            start = time.perf_counter()
            response = baseline_client.get('/test')
            end = time.perf_counter()
            assert response.status_code == 200
            baseline_times.append(end - start)
        
        # 监控测试
        monitored_times = []
        for _ in range(50):
            start = time.perf_counter()
            response = monitored_client.get('/test')
            end = time.perf_counter()
            assert response.status_code == 200
            monitored_times.append(end - start)
        
        # 统计分析
        baseline_avg = statistics.mean(baseline_times)
        monitored_avg = statistics.mean(monitored_times)
        baseline_median = statistics.median(baseline_times)
        monitored_median = statistics.median(monitored_times)
        
        # 计算开销
        avg_overhead = (monitored_avg - baseline_avg) / baseline_avg
        median_overhead = (monitored_median - baseline_median) / baseline_median
        
        print(f"基准平均时间: {baseline_avg:.6f}s")
        print(f"监控平均时间: {monitored_avg:.6f}s")
        print(f"平均开销: {avg_overhead:.2%}")
        print(f"中位数开销: {median_overhead:.2%}")
        
        # 验证开销小于5%
        assert avg_overhead < 0.05, f"平均性能开销过大: {avg_overhead:.2%}"
        assert median_overhead < 0.05, f"中位数性能开销过大: {median_overhead:.2%}"
        
        # 检查监控器内部统计
        stats = self.monitor.get_stats()
        overhead_stats = stats.get('overhead_stats', {})
        if overhead_stats.get('sample_count', 0) > 0:
            internal_overhead = overhead_stats.get('average_overhead', 0)
            assert internal_overhead < 0.05, f"内部统计开销过大: {internal_overhead:.2%}"
    
    def test_decorator_overhead_under_5_percent(self):
        """测试装饰器性能开销小于5%"""
        decorator = self.monitor.create_decorator()
        
        # 基准函数（无装饰器）
        def baseline_function():
            return sum(i * i for i in range(1000))
        
        # 监控函数（有装饰器）
        @decorator
        def monitored_function():
            return sum(i * i for i in range(1000))
        
        # 预热
        for _ in range(5):
            baseline_function()
            monitored_function()
        
        # 基准测试
        baseline_times = []
        for _ in range(100):
            start = time.perf_counter()
            result = baseline_function()
            end = time.perf_counter()
            baseline_times.append(end - start)
            assert result == sum(i * i for i in range(1000))
        
        # 监控测试
        monitored_times = []
        for _ in range(100):
            start = time.perf_counter()
            result = monitored_function()
            end = time.perf_counter()
            monitored_times.append(end - start)
            assert result == sum(i * i for i in range(1000))
        
        # 统计分析
        baseline_avg = statistics.mean(baseline_times)
        monitored_avg = statistics.mean(monitored_times)
        
        # 计算开销
        overhead = (monitored_avg - baseline_avg) / baseline_avg
        
        print(f"装饰器基准平均时间: {baseline_avg:.6f}s")
        print(f"装饰器监控平均时间: {monitored_avg:.6f}s")
        print(f"装饰器开销: {overhead:.2%}")
        
        # 验证开销小于5%
        assert overhead < 0.05, f"装饰器性能开销过大: {overhead:.2%}"
    
    def test_concurrent_performance_overhead(self):
        """测试并发情况下的性能开销"""
        decorator = self.monitor.create_decorator()
        
        def baseline_worker(worker_id):
            """基准工作函数"""
            times = []
            for i in range(10):
                start = time.perf_counter()
                result = sum(j * j for j in range(100))
                end = time.perf_counter()
                times.append(end - start)
            return times
        
        @decorator
        def monitored_worker(worker_id):
            """监控工作函数"""
            times = []
            for i in range(10):
                start = time.perf_counter()
                result = sum(j * j for j in range(100))
                end = time.perf_counter()
                times.append(end - start)
            return times
        
        # 并发基准测试
        with ThreadPoolExecutor(max_workers=4) as executor:
            baseline_futures = [executor.submit(baseline_worker, i) for i in range(4)]
            baseline_results = []
            for future in as_completed(baseline_futures):
                baseline_results.extend(future.result())
        
        # 并发监控测试
        with ThreadPoolExecutor(max_workers=4) as executor:
            monitored_futures = [executor.submit(monitored_worker, i) for i in range(4)]
            monitored_results = []
            for future in as_completed(monitored_futures):
                monitored_results.extend(future.result())
        
        # 统计分析
        baseline_avg = statistics.mean(baseline_results)
        monitored_avg = statistics.mean(monitored_results)
        overhead = (monitored_avg - baseline_avg) / baseline_avg
        
        print(f"并发基准平均时间: {baseline_avg:.6f}s")
        print(f"并发监控平均时间: {monitored_avg:.6f}s")
        print(f"并发开销: {overhead:.2%}")
        
        # 验证并发开销仍然小于5%
        assert overhead < 0.05, f"并发性能开销过大: {overhead:.2%}"
    
    def test_memory_overhead(self):
        """测试内存开销"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # 记录初始内存
        initial_memory = process.memory_info().rss
        
        # 创建大量监控函数
        decorator = self.monitor.create_decorator()
        functions = []
        
        for i in range(100):
            @decorator
            def test_func():
                return sum(j for j in range(100))
            functions.append(test_func)
        
        # 调用所有函数
        for func in functions:
            func()
        
        # 记录最终内存
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        print(f"初始内存: {initial_memory / 1024 / 1024:.2f} MB")
        print(f"最终内存: {final_memory / 1024 / 1024:.2f} MB")
        print(f"内存增长: {memory_increase / 1024 / 1024:.2f} MB")
        
        # 验证内存增长合理（小于50MB）
        assert memory_increase < 50 * 1024 * 1024, f"内存开销过大: {memory_increase / 1024 / 1024:.2f} MB"
    
    def test_overhead_tracking_accuracy(self):
        """测试开销跟踪的准确性"""
        # 创建已知开销的测试场景
        decorator = self.monitor.create_decorator()
        
        @decorator
        def test_function():
            # 固定的计算工作
            return sum(i * i for i in range(500))
        
        # 重置统计
        self.monitor.reset_stats()
        
        # 多次调用收集数据
        for _ in range(30):
            test_function()
        
        # 获取开销统计
        stats = self.monitor.get_stats()
        overhead_stats = stats.get('overhead_stats', {})
        
        assert overhead_stats.get('sample_count', 0) == 30
        
        avg_overhead = overhead_stats.get('average_overhead', 0)
        max_overhead = overhead_stats.get('max_overhead', 0)
        min_overhead = overhead_stats.get('min_overhead', 0)
        
        print(f"开销统计 - 平均: {avg_overhead:.2%}, 最大: {max_overhead:.2%}, 最小: {min_overhead:.2%}")
        
        # 验证统计数据合理性
        assert 0 <= avg_overhead < 0.05
        assert 0 <= min_overhead <= avg_overhead <= max_overhead
        assert max_overhead < 0.10  # 最大开销不超过10%


class TestMonitoringAccuracy:
    """监控精度测试"""
    
    def setup_method(self):
        """测试前设置"""
        self.config = Config(
            threshold_seconds=0.1,
            enable_local_file=False,
            enable_mattermost=False
        )
        self.monitor = PerformanceMonitor(self.config)
    
    def test_execution_time_accuracy(self):
        """测试执行时间测量精度"""
        decorator = self.monitor.create_decorator()
        
        # 创建已知执行时间的函数
        @decorator
        def timed_function(sleep_time):
            time.sleep(sleep_time)
            return sleep_time
        
        test_times = [0.05, 0.1, 0.15, 0.2, 0.25]
        measured_times = []
        
        for expected_time in test_times:
            # 重置统计
            self.monitor.reset_stats()
            
            # 执行函数
            start = time.perf_counter()
            result = timed_function(expected_time)
            end = time.perf_counter()
            actual_time = end - start
            
            # 获取监控器测量的时间
            stats = self.monitor.get_stats()
            overhead_stats = stats.get('overhead_stats', {})
            
            print(f"预期: {expected_time:.3f}s, 实际: {actual_time:.3f}s")
            
            # 验证时间测量精度（允许10%误差）
            time_diff = abs(actual_time - expected_time)
            assert time_diff < expected_time * 0.1, f"时间测量误差过大: {time_diff:.3f}s"
            
            measured_times.append(actual_time)
        
        # 验证测量的一致性
        for i, (expected, measured) in enumerate(zip(test_times, measured_times)):
            relative_error = abs(measured - expected) / expected
            assert relative_error < 0.1, f"测试{i}: 相对误差过大 {relative_error:.2%}"
    
    def test_threshold_detection_accuracy(self):
        """测试阈值检测精度"""
        # 设置精确的阈值
        config = Config(
            threshold_seconds=0.15,
            enable_local_file=False,
            enable_mattermost=False
        )
        monitor = PerformanceMonitor(config)
        decorator = monitor.create_decorator()
        
        @decorator
        def variable_time_function(sleep_time):
            time.sleep(sleep_time)
            return sleep_time
        
        # 测试不同的执行时间
        test_cases = [
            (0.10, False),  # 低于阈值
            (0.14, False),  # 接近但低于阈值
            (0.16, True),   # 略高于阈值
            (0.20, True),   # 明显高于阈值
        ]
        
        for sleep_time, should_alert in test_cases:
            # 重置统计
            monitor.reset_stats()
            
            # 执行函数
            variable_time_function(sleep_time)
            
            # 检查告警状态
            stats = monitor.get_stats()
            alerts_sent = stats.get('alerts_sent', 0)
            slow_requests = stats.get('slow_requests', 0)
            
            if should_alert:
                assert slow_requests > 0, f"时间 {sleep_time}s 应该被检测为慢请求"
            else:
                assert slow_requests == 0, f"时间 {sleep_time}s 不应该被检测为慢请求"
            
            print(f"时间: {sleep_time}s, 慢请求: {slow_requests}, 预期告警: {should_alert}")
    
    def test_concurrent_monitoring_accuracy(self):
        """测试并发监控的准确性"""
        decorator = self.monitor.create_decorator()
        
        @decorator
        def concurrent_function(thread_id, sleep_time):
            time.sleep(sleep_time)
            return f"thread-{thread_id}"
        
        # 重置统计
        self.monitor.reset_stats()
        
        # 并发执行不同时间的函数
        results = []
        threads = []
        
        def worker(thread_id, sleep_time):
            result = concurrent_function(thread_id, sleep_time)
            results.append((thread_id, result))
        
        # 创建不同执行时间的线程
        thread_configs = [
            (0, 0.05),  # 快
            (1, 0.15),  # 慢
            (2, 0.08),  # 快
            (3, 0.20),  # 慢
        ]
        
        for thread_id, sleep_time in thread_configs:
            thread = threading.Thread(target=worker, args=(thread_id, sleep_time))
            threads.append(thread)
        
        # 启动所有线程
        for thread in threads:
            thread.start()
        
        # 等待完成
        for thread in threads:
            thread.join()
        
        # 验证结果
        assert len(results) == 4
        
        # 检查统计准确性
        stats = self.monitor.get_stats()
        assert stats['total_requests'] == 4
        
        # 应该有2个慢请求（sleep_time >= threshold）
        expected_slow = sum(1 for _, sleep_time in thread_configs if sleep_time >= self.config.threshold_seconds)
        actual_slow = stats.get('slow_requests', 0)
        
        print(f"预期慢请求: {expected_slow}, 实际慢请求: {actual_slow}")
        assert actual_slow == expected_slow, "并发监控统计不准确"


class TestScalabilityValidation:
    """可扩展性验证测试"""
    
    def setup_method(self):
        """测试前设置"""
        self.config = Config(
            threshold_seconds=10.0,  # 高阈值避免告警
            enable_local_file=False,
            enable_mattermost=False
        )
        self.monitor = PerformanceMonitor(self.config)
    
    def test_high_frequency_monitoring(self):
        """测试高频监控性能"""
        decorator = self.monitor.create_decorator()
        
        @decorator
        def fast_function():
            return sum(i for i in range(10))
        
        # 重置统计
        self.monitor.reset_stats()
        
        # 高频调用
        start_time = time.perf_counter()
        call_count = 1000
        
        for _ in range(call_count):
            fast_function()
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # 计算每次调用的平均时间
        avg_time_per_call = total_time / call_count
        
        print(f"总时间: {total_time:.3f}s")
        print(f"调用次数: {call_count}")
        print(f"平均每次调用: {avg_time_per_call:.6f}s")
        
        # 验证高频调用性能合理
        assert avg_time_per_call < 0.001, f"高频调用性能不佳: {avg_time_per_call:.6f}s/call"
        
        # 验证统计准确性
        stats = self.monitor.get_stats()
        assert stats['total_requests'] == call_count
    
    def test_large_scale_concurrent_monitoring(self):
        """测试大规模并发监控"""
        decorator = self.monitor.create_decorator()
        
        @decorator
        def concurrent_task(task_id):
            # 模拟一些工作
            result = sum(i * i for i in range(50))
            return f"task-{task_id}-{result}"
        
        # 重置统计
        self.monitor.reset_stats()
        
        # 大规模并发测试
        start_time = time.perf_counter()
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(concurrent_task, i) for i in range(200)]
            results = [future.result() for future in as_completed(futures)]
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        print(f"200个并发任务总时间: {total_time:.3f}s")
        print(f"平均每个任务: {total_time / 200:.6f}s")
        
        # 验证所有任务完成
        assert len(results) == 200
        
        # 验证统计准确性
        stats = self.monitor.get_stats()
        assert stats['total_requests'] == 200
        
        # 验证并发性能合理
        assert total_time < 30, f"大规模并发性能不佳: {total_time:.3f}s"
    
    def test_memory_usage_under_load(self):
        """测试负载下的内存使用"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        decorator = self.monitor.create_decorator()
        
        @decorator
        def memory_test_function(data_size):
            # 创建一些数据
            data = list(range(data_size))
            return sum(data)
        
        # 重置统计
        self.monitor.reset_stats()
        
        # 执行大量操作
        for i in range(100):
            memory_test_function(1000)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        print(f"内存增长: {memory_increase / 1024 / 1024:.2f} MB")
        
        # 验证内存使用合理
        assert memory_increase < 100 * 1024 * 1024, f"内存使用过多: {memory_increase / 1024 / 1024:.2f} MB"
        
        # 验证统计准确性
        stats = self.monitor.get_stats()
        assert stats['total_requests'] == 100


if __name__ == '__main__':
    pytest.main([__file__, '-v'])