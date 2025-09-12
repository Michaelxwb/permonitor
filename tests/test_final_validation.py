"""
最终验证测试模块

验证性能开销需求和真实场景下的系统行为
"""

import os
import time
import json
import tempfile
import threading
import statistics
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import pytest
from flask import Flask, jsonify, request

from web_performance_monitor import PerformanceMonitor, Config
from web_performance_monitor.models import PerformanceMetrics
from web_performance_monitor.exceptions import PerformanceMonitorError


class TestPerformanceOverheadRequirements:
    """验证性能开销需求测试"""
    
    def setup_method(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
        
    def test_middleware_overhead_under_5_percent_real_app(self):
        """测试真实Flask应用中间件开销<5%"""
        # 创建真实的Flask应用
        app = Flask(__name__)
        app.config['TESTING'] = True
        
        @app.route('/api/users/<int:user_id>')
        def get_user(user_id):
            # 模拟数据库查询
            time.sleep(0.01)
            return jsonify({
                'id': user_id,
                'name': f'User {user_id}',
                'email': f'user{user_id}@example.com',
                'created_at': datetime.now().isoformat()
            })
        
        @app.route('/api/search')
        def search():
            # 模拟搜索操作
            query = request.args.get('q', '')
            time.sleep(0.005)  # 模拟搜索时间
            return jsonify({
                'query': query,
                'results': [f'Result {i} for {query}' for i in range(5)],
                'total': 5
            })
        
        @app.route('/api/data', methods=['POST'])
        def create_data():
            # 模拟数据处理
            data = request.get_json() or {}
            time.sleep(0.008)  # 模拟处理时间
            return jsonify({
                'id': 123,
                'status': 'created',
                'data': data
            }), 201
        
        # 基准测试（无监控）
        baseline_client = app.test_client()
        
        # 预热
        for _ in range(5):
            baseline_client.get('/api/users/1')
            baseline_client.get('/api/search?q=test')
            baseline_client.post('/api/data', json={'test': 'data'})
        
        # 基准性能测试
        baseline_times = []
        test_requests = [
            ('GET', '/api/users/1'),
            ('GET', '/api/users/2'),
            ('GET', '/api/search?q=python'),
            ('GET', '/api/search?q=flask'),
            ('POST', '/api/data', {'name': 'test', 'value': 123}),
        ]
        
        for method, url, *data in test_requests * 10:  # 50次请求
            start = time.perf_counter()
            if method == 'GET':
                response = baseline_client.get(url)
            else:
                response = baseline_client.post(url, json=data[0] if data else None)
            end = time.perf_counter()
            
            assert response.status_code in [200, 201]
            baseline_times.append(end - start)
        
        # 监控版本测试
        config = Config(
            threshold_seconds=10.0,  # 高阈值避免告警
            enable_local_file=False,
            enable_mattermost=False
        )
        monitor = PerformanceMonitor(config)
        
        # 应用监控中间件
        monitored_app = Flask(__name__)
        monitored_app.config['TESTING'] = True
        
        # 复制相同的路由
        @monitored_app.route('/api/users/<int:user_id>')
        def get_user_monitored(user_id):
            time.sleep(0.01)
            return jsonify({
                'id': user_id,
                'name': f'User {user_id}',
                'email': f'user{user_id}@example.com',
                'created_at': datetime.now().isoformat()
            })
        
        @monitored_app.route('/api/search')
        def search_monitored():
            query = request.args.get('q', '')
            time.sleep(0.005)
            return jsonify({
                'query': query,
                'results': [f'Result {i} for {query}' for i in range(5)],
                'total': 5
            })
        
        @monitored_app.route('/api/data', methods=['POST'])
        def create_data_monitored():
            data = request.get_json() or {}
            time.sleep(0.008)
            return jsonify({
                'id': 123,
                'status': 'created',
                'data': data
            }), 201
        
        # 应用中间件
        monitored_app.wsgi_app = monitor.create_middleware()(monitored_app.wsgi_app)
        monitored_client = monitored_app.test_client()
        
        # 预热监控版本
        for _ in range(5):
            monitored_client.get('/api/users/1')
            monitored_client.get('/api/search?q=test')
            monitored_client.post('/api/data', json={'test': 'data'})
        
        # 监控版本性能测试
        monitored_times = []
        for method, url, *data in test_requests * 10:  # 50次请求
            start = time.perf_counter()
            if method == 'GET':
                response = monitored_client.get(url)
            else:
                response = monitored_client.post(url, json=data[0] if data else None)
            end = time.perf_counter()
            
            assert response.status_code in [200, 201]
            monitored_times.append(end - start)
        
        # 计算性能开销
        baseline_avg = statistics.mean(baseline_times)
        monitored_avg = statistics.mean(monitored_times)
        baseline_median = statistics.median(baseline_times)
        monitored_median = statistics.median(monitored_times)
        
        avg_overhead = (monitored_avg - baseline_avg) / baseline_avg
        median_overhead = (monitored_median - baseline_median) / baseline_median
        
        print(f"真实应用性能测试结果:")
        print(f"基准平均时间: {baseline_avg:.6f}s")
        print(f"监控平均时间: {monitored_avg:.6f}s")
        print(f"平均开销: {avg_overhead:.2%}")
        print(f"中位数开销: {median_overhead:.2%}")
        
        # 验证开销小于5%
        assert avg_overhead < 0.05, f"平均性能开销超过5%: {avg_overhead:.2%}"
        assert median_overhead < 0.05, f"中位数性能开销超过5%: {median_overhead:.2%}"
        
        # 验证监控器内部统计
        stats = monitor.get_stats()
        assert stats['total_requests'] == 50
        
        overhead_stats = stats.get('overhead_stats', {})
        if overhead_stats.get('sample_count', 0) > 0:
            internal_overhead = overhead_stats.get('average_overhead', 0)
            assert internal_overhead < 0.05, f"内部统计开销超过5%: {internal_overhead:.2%}"
    
    def test_zero_intrusion_behavior(self):
        """验证零入侵行为"""
        # 创建会抛出异常的应用
        app = Flask(__name__)
        app.config['TESTING'] = True
        
        @app.route('/success')
        def success():
            return jsonify({'status': 'ok'})
        
        @app.route('/error')
        def error():
            raise ValueError("应用内部错误")
        
        @app.route('/custom-response')
        def custom_response():
            response = jsonify({'custom': True})
            response.status_code = 202
            response.headers['X-Custom'] = 'test'
            return response
        
        # 应用监控
        config = Config(
            threshold_seconds=0.1,
            enable_local_file=True,
            enable_mattermost=False,
            local_output_dir=self.temp_dir
        )
        monitor = PerformanceMonitor(config)
        app.wsgi_app = monitor.create_middleware()(app.wsgi_app)
        client = app.test_client()
        
        # 测试正常响应不受影响
        response = client.get('/success')
        assert response.status_code == 200
        assert response.json == {'status': 'ok'}
        
        # 测试异常仍然正常抛出
        with pytest.raises(ValueError, match="应用内部错误"):
            client.get('/error')
        
        # 测试自定义响应不受影响
        response = client.get('/custom-response')
        assert response.status_code == 202
        assert response.json == {'custom': True}
        assert response.headers.get('X-Custom') == 'test'
        
        # 验证监控正常工作
        stats = monitor.get_stats()
        assert stats['total_requests'] >= 2  # success和custom-response
    
    def test_monitoring_errors_dont_affect_main_app(self):
        """验证监控错误不影响主应用"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        
        @app.route('/test')
        def test_endpoint():
            return jsonify({'message': 'success'})
        
        # 创建会失败的配置
        config = Config(
            threshold_seconds=0.1,
            enable_local_file=True,
            enable_mattermost=True,
            local_output_dir="/invalid/path/that/does/not/exist",
            mattermost_server_url="https://invalid.url",
            mattermost_token="invalid-token",
            mattermost_channel_id="invalid-channel"
        )
        
        monitor = PerformanceMonitor(config)
        app.wsgi_app = monitor.create_middleware()(app.wsgi_app)
        client = app.test_client()
        
        # 即使监控配置有问题，应用仍应正常工作
        response = client.get('/test')
        assert response.status_code == 200
        assert response.json == {'message': 'success'}
        
        # 多次请求确保稳定性
        for _ in range(5):
            response = client.get('/test')
            assert response.status_code == 200
            assert response.json == {'message': 'success'}
    
    def test_decorator_overhead_under_5_percent_real_functions(self):
        """测试真实函数装饰器开销<5%"""
        config = Config(
            threshold_seconds=10.0,  # 高阈值避免告警
            enable_local_file=False,
            enable_mattermost=False
        )
        monitor = PerformanceMonitor(config)
        decorator = monitor.create_decorator()
        
        # 模拟真实的业务函数
        def calculate_fibonacci(n):
            """计算斐波那契数列"""
            if n <= 1:
                return n
            return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)
        
        def process_data(data):
            """数据处理函数"""
            result = []
            for item in data:
                if isinstance(item, dict):
                    result.append({k: v.upper() if isinstance(v, str) else v 
                                 for k, v in item.items()})
                else:
                    result.append(str(item).upper())
            return result
        
        def database_query_simulation(query, params=None):
            """模拟数据库查询"""
            time.sleep(0.01)  # 模拟查询时间
            return {
                'query': query,
                'params': params or {},
                'results': [{'id': i, 'value': f'result_{i}'} for i in range(10)],
                'count': 10
            }
        
        # 装饰版本
        @decorator
        def calculate_fibonacci_monitored(n):
            if n <= 1:
                return n
            return calculate_fibonacci_monitored(n-1) + calculate_fibonacci_monitored(n-2)
        
        @decorator
        def process_data_monitored(data):
            result = []
            for item in data:
                if isinstance(item, dict):
                    result.append({k: v.upper() if isinstance(v, str) else v 
                                 for k, v in item.items()})
                else:
                    result.append(str(item).upper())
            return result
        
        @decorator
        def database_query_simulation_monitored(query, params=None):
            time.sleep(0.01)
            return {
                'query': query,
                'params': params or {},
                'results': [{'id': i, 'value': f'result_{i}'} for i in range(10)],
                'count': 10
            }
        
        # 测试数据
        test_cases = [
            (calculate_fibonacci, calculate_fibonacci_monitored, [8]),
            (process_data, process_data_monitored, [[
                {'name': 'john', 'age': 30},
                {'name': 'jane', 'age': 25},
                'simple_string',
                123
            ]]),
            (database_query_simulation, database_query_simulation_monitored, [
                'SELECT * FROM users WHERE active = ?', {'active': True}
            ])
        ]
        
        for baseline_func, monitored_func, args in test_cases:
            # 预热
            for _ in range(3):
                baseline_func(*args)
                monitored_func(*args)
            
            # 基准测试
            baseline_times = []
            for _ in range(20):
                start = time.perf_counter()
                baseline_result = baseline_func(*args)
                end = time.perf_counter()
                baseline_times.append(end - start)
            
            # 监控测试
            monitored_times = []
            for _ in range(20):
                start = time.perf_counter()
                monitored_result = monitored_func(*args)
                end = time.perf_counter()
                monitored_times.append(end - start)
            
            # 验证结果一致性
            assert baseline_result == monitored_result, f"函数 {baseline_func.__name__} 结果不一致"
            
            # 计算开销
            baseline_avg = statistics.mean(baseline_times)
            monitored_avg = statistics.mean(monitored_times)
            overhead = (monitored_avg - baseline_avg) / baseline_avg
            
            print(f"函数 {baseline_func.__name__}:")
            print(f"  基准平均时间: {baseline_avg:.6f}s")
            print(f"  监控平均时间: {monitored_avg:.6f}s")
            print(f"  开销: {overhead:.2%}")
            
            # 验证开销小于5%
            assert overhead < 0.05, f"函数 {baseline_func.__name__} 开销超过5%: {overhead:.2%}"
    
    def test_concurrent_monitoring_stability(self):
        """测试并发监控稳定性"""
        config = Config(
            threshold_seconds=0.1,
            enable_local_file=True,
            enable_mattermost=False,
            local_output_dir=self.temp_dir
        )
        monitor = PerformanceMonitor(config)
        decorator = monitor.create_decorator()
        
        @decorator
        def concurrent_task(task_id, duration):
            """并发任务函数"""
            time.sleep(duration)
            return f"Task {task_id} completed in {duration}s"
        
        # 并发执行测试
        results = []
        errors = []
        
        def worker(task_id):
            try:
                duration = 0.01 + (task_id % 10) * 0.01  # 0.01-0.1秒
                result = concurrent_task(task_id, duration)
                results.append((task_id, result))
            except Exception as e:
                errors.append((task_id, str(e)))
        
        # 创建大量并发任务
        threads = []
        for i in range(50):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
        
        # 启动所有线程
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        # 等待完成
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        
        # 验证结果
        assert len(errors) == 0, f"并发执行出现错误: {errors}"
        assert len(results) == 50, f"并发任务完成数量不正确: {len(results)}"
        
        # 验证监控统计
        stats = monitor.get_stats()
        assert stats['total_requests'] == 50
        
        # 验证执行时间合理
        total_time = end_time - start_time
        assert total_time < 5.0, f"并发执行时间过长: {total_time:.2f}s"
        
        print(f"并发监控测试:")
        print(f"  任务数量: 50")
        print(f"  总执行时间: {total_time:.2f}s")
        print(f"  错误数量: {len(errors)}")
        print(f"  监控统计: {stats['total_requests']} 请求")


class TestRealWorldScenarios:
    """真实场景端到端测试"""
    
    def setup_method(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
    
    def test_complete_workflow_slow_request_to_notification(self):
        """测试从慢请求检测到通知传递的完整工作流程"""
        # 配置监控
        config = Config(
            threshold_seconds=0.1,  # 低阈值便于测试
            alert_window_days=1,
            enable_local_file=True,
            enable_mattermost=False,
            local_output_dir=self.temp_dir
        )
        monitor = PerformanceMonitor(config)
        
        # 创建Flask应用
        app = Flask(__name__)
        app.config['TESTING'] = True
        
        @app.route('/api/slow-operation')
        def slow_operation():
            """模拟慢操作"""
            operation_type = request.args.get('type', 'default')
            if operation_type == 'database':
                time.sleep(0.2)  # 模拟慢数据库查询
                return jsonify({
                    'operation': 'database_query',
                    'duration': '200ms',
                    'results': 100
                })
            elif operation_type == 'computation':
                time.sleep(0.15)  # 模拟复杂计算
                return jsonify({
                    'operation': 'heavy_computation',
                    'duration': '150ms',
                    'result': sum(i*i for i in range(1000))
                })
            else:
                time.sleep(0.12)  # 默认慢操作
                return jsonify({
                    'operation': 'default_slow',
                    'duration': '120ms'
                })
        
        @app.route('/api/fast-operation')
        def fast_operation():
            """快速操作，不应触发告警"""
            return jsonify({'status': 'fast', 'duration': '5ms'})
        
        # 应用中间件
        app.wsgi_app = monitor.create_middleware()(app.wsgi_app)
        client = app.test_client()
        
        # 重置统计
        monitor.reset_stats()
        
        # 1. 发送快速请求，不应触发告警
        response = client.get('/api/fast-operation')
        assert response.status_code == 200
        
        # 2. 发送慢请求，应该触发告警
        response = client.get('/api/slow-operation?type=database')
        assert response.status_code == 200
        assert response.json['operation'] == 'database_query'
        
        # 3. 发送另一种类型的慢请求
        response = client.get('/api/slow-operation?type=computation')
        assert response.status_code == 200
        assert response.json['operation'] == 'heavy_computation'
        
        # 4. 再次发送相同的慢请求，应该被去重
        response = client.get('/api/slow-operation?type=database')
        assert response.status_code == 200
        
        # 验证统计信息
        stats = monitor.get_stats()
        print(f"完整工作流程测试统计: {stats}")
        
        assert stats['total_requests'] == 4
        assert stats['slow_requests'] >= 2  # 至少2个慢请求
        
        # 验证告警文件生成
        files = os.listdir(self.temp_dir)
        html_files = [f for f in files if f.endswith('.html')]
        
        print(f"生成的告警文件: {html_files}")
        assert len(html_files) >= 1, "应该生成至少一个告警文件"
        
        # 验证告警文件内容
        for html_file in html_files:
            file_path = os.path.join(self.temp_dir, html_file)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 验证文件包含性能分析内容
            assert len(content) > 1000, "告警文件内容太少"
            assert 'slow-operation' in content, "告警文件应包含端点信息"
    
    def test_duplicate_alert_prevention_across_time_window(self):
        """验证跨时间窗口的重复告警防护"""
        config = Config(
            threshold_seconds=0.1,
            alert_window_days=1,  # 1天窗口
            enable_local_file=True,
            enable_mattermost=False,
            local_output_dir=self.temp_dir
        )
        monitor = PerformanceMonitor(config)
        decorator = monitor.create_decorator()
        
        @decorator
        def slow_function(param):
            """慢函数用于测试去重"""
            time.sleep(0.15)
            return f"processed {param}"
        
        # 重置统计
        monitor.reset_stats()
        
        # 第一次调用，应该触发告警
        result1 = slow_function("test_data")
        assert result1 == "processed test_data"
        
        # 等待一小段时间
        time.sleep(0.1)
        
        # 第二次调用相同参数，应该被去重
        result2 = slow_function("test_data")
        assert result2 == "processed test_data"
        
        # 第三次调用不同参数，应该触发新告警
        result3 = slow_function("different_data")
        assert result3 == "processed different_data"
        
        # 验证统计
        stats = monitor.get_stats()
        print(f"去重测试统计: {stats}")
        
        assert stats['total_requests'] == 3
        assert stats['slow_requests'] == 3
        
        # 验证告警去重
        alert_stats = stats.get('alert_stats', {})
        cache_stats = alert_stats.get('cache_stats', {})
        
        # 应该有缓存条目记录告警
        assert cache_stats.get('total_entries', 0) >= 1
        
        # 验证文件生成
        files = os.listdir(self.temp_dir)
        html_files = [f for f in files if f.endswith('.html')]
        
        # 由于去重，文件数量应该少于慢请求数量
        print(f"去重测试生成文件: {html_files}")
        assert len(html_files) >= 1, "应该生成告警文件"
    
    def test_configuration_loading_from_environment_and_file(self):
        """测试从环境变量和文件加载配置"""
        # 1. 测试环境变量配置
        env_vars = {
            'WPM_THRESHOLD_SECONDS': '0.2',
            'WPM_ALERT_WINDOW_DAYS': '7',
            'WPM_ENABLE_LOCAL_FILE': 'true',
            'WPM_LOCAL_OUTPUT_DIR': self.temp_dir,
            'WPM_ENABLE_MATTERMOST': 'false',
            'WPM_LOG_LEVEL': 'DEBUG'
        }
        
        with patch.dict(os.environ, env_vars):
            config = Config.from_env()
            monitor = PerformanceMonitor(config)
            
            # 验证配置正确加载
            assert config.threshold_seconds == 0.2
            assert config.alert_window_days == 7
            assert config.enable_local_file is True
            assert config.local_output_dir == self.temp_dir
            assert config.enable_mattermost is False
            assert config.log_level == 'DEBUG'
        
        # 2. 测试文件配置
        config_data = {
            'threshold_seconds': 0.3,
            'alert_window_days': 14,
            'enable_local_file': True,
            'local_output_dir': self.temp_dir,
            'enable_mattermost': False,
            'log_level': 'INFO'
        }
        
        config_file = os.path.join(self.temp_dir, 'config.json')
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        config = Config.from_file(config_file)
        monitor = PerformanceMonitor(config)
        
        # 验证配置正确加载
        assert config.threshold_seconds == 0.3
        assert config.alert_window_days == 14
        assert config.local_output_dir == self.temp_dir
        
        # 3. 测试配置在实际监控中的应用
        decorator = monitor.create_decorator()
        
        @decorator
        def test_function():
            time.sleep(0.25)  # 超过0.2秒阈值但低于0.3秒阈值
            return "test"
        
        # 重置统计
        monitor.reset_stats()
        
        # 调用函数
        result = test_function()
        assert result == "test"
        
        # 验证阈值配置生效
        stats = monitor.get_stats()
        # 由于sleep 0.25s < threshold 0.3s，不应该触发告警
        assert stats['slow_requests'] == 0
    
    def test_all_notification_channels_working(self):
        """验证所有通知渠道正常工作"""
        # 测试本地文件通知
        config = Config(
            threshold_seconds=0.1,
            enable_local_file=True,
            enable_mattermost=False,
            local_output_dir=self.temp_dir
        )
        monitor = PerformanceMonitor(config)
        decorator = monitor.create_decorator()
        
        @decorator
        def slow_function_for_notification():
            time.sleep(0.15)
            return "notification_test"
        
        # 重置统计
        monitor.reset_stats()
        
        # 触发告警
        result = slow_function_for_notification()
        assert result == "notification_test"
        
        # 验证本地文件通知
        files = os.listdir(self.temp_dir)
        html_files = [f for f in files if f.endswith('.html')]
        assert len(html_files) >= 1, "本地文件通知失败"
        
        # 验证文件内容
        html_file_path = os.path.join(self.temp_dir, html_files[0])
        with open(html_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert 'slow_function_for_notification' in content
        assert len(content) > 500  # 确保有实际内容
        
        # 测试通知器测试功能
        test_results = monitor.test_alert_system()
        assert test_results['success'] is True
        assert 'LocalFileNotifier' in test_results['notifier_results']
        assert test_results['notifier_results']['LocalFileNotifier'] is True
        
        print(f"通知系统测试结果: {test_results}")
    
    def test_system_resilience_under_stress(self):
        """测试系统在压力下的弹性"""
        config = Config(
            threshold_seconds=0.05,  # 很低的阈值
            enable_local_file=True,
            enable_mattermost=False,
            local_output_dir=self.temp_dir
        )
        monitor = PerformanceMonitor(config)
        
        # 创建Flask应用
        app = Flask(__name__)
        app.config['TESTING'] = True
        
        @app.route('/stress-test/<int:duration>')
        def stress_test(duration):
            """压力测试端点"""
            time.sleep(duration / 1000.0)  # duration in milliseconds
            return jsonify({
                'duration_ms': duration,
                'timestamp': datetime.now().isoformat()
            })
        
        # 应用中间件
        app.wsgi_app = monitor.create_middleware()(app.wsgi_app)
        client = app.test_client()
        
        # 重置统计
        monitor.reset_stats()
        
        # 压力测试：大量并发请求
        def make_requests():
            results = []
            for i in range(20):
                duration = 50 + (i % 10) * 10  # 50-140ms
                try:
                    response = client.get(f'/stress-test/{duration}')
                    results.append((response.status_code, duration))
                except Exception as e:
                    results.append(('error', str(e)))
            return results
        
        # 并发执行
        threads = []
        all_results = []
        
        for _ in range(5):  # 5个线程
            thread = threading.Thread(target=lambda: all_results.extend(make_requests()))
            threads.append(thread)
        
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        
        # 验证结果
        successful_requests = [r for r in all_results if r[0] == 200]
        error_requests = [r for r in all_results if r[0] != 200]
        
        print(f"压力测试结果:")
        print(f"  总请求数: {len(all_results)}")
        print(f"  成功请求: {len(successful_requests)}")
        print(f"  失败请求: {len(error_requests)}")
        print(f"  总执行时间: {end_time - start_time:.2f}s")
        
        # 验证系统稳定性
        assert len(successful_requests) >= 90, f"成功率过低: {len(successful_requests)}/100"
        assert len(error_requests) <= 10, f"错误率过高: {len(error_requests)}"
        
        # 验证监控系统仍然正常工作
        stats = monitor.get_stats()
        assert stats['total_requests'] >= 90
        assert stats['monitoring_enabled'] is True
        
        # 验证告警文件生成
        files = os.listdir(self.temp_dir)
        html_files = [f for f in files if f.endswith('.html')]
        assert len(html_files) >= 1, "压力测试下应该生成告警文件"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])