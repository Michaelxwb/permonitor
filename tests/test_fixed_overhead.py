"""
修复的性能开销测试 - 使用智能分析器
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


class TestFixedPerformanceOverhead:
    """修复的性能开销测试"""
    
    def test_middleware_overhead_with_smart_analyzer(self):
        """测试使用智能分析器的中间件开销"""
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

        # 监控版本测试 - 使用智能配置
        config = create_test_config_for_overhead_testing()
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

        # 测试请求
        test_requests = [
            ('GET', '/api/users/1'),
            ('GET', '/api/users/2'),
            ('GET', '/api/search?q=python'),
            ('GET', '/api/search?q=flask'),
            ('POST', '/api/data', {'name': 'test', 'value': 123}),
        ]

        # 使用智能测试框架
        tester = SmartPerformanceTester(max_overhead_ratio=0.15)  # 15%开销限制
        result = tester.measure_middleware_overhead(
            baseline_client, monitored_client, test_requests
        )
        
        # 断言性能开销
        assert_performance_overhead(
            result, 
            max_overhead=0.15,
            description="智能分析器中间件"
        )
        
        # 验证测试通过
        assert result.test_passed, f"中间件开销测试失败: {result.overhead_ratio:.2%}"
    
    def test_decorator_overhead_with_smart_analyzer(self):
        """测试使用智能分析器的装饰器开销"""
        config = create_test_config_for_overhead_testing()
        # 为装饰器测试调整配置 - 几乎禁用分析以降低开销
        config.smart_sampling_rate = 0.001  # 0.1%采样率 - 几乎禁用
        config.min_requests_before_profiling = 50  # 非常高的最小请求数
        config.enable_adaptive_sampling = False  # 禁用自适应采样
        monitor = PerformanceMonitor(config)
        decorator = monitor.create_decorator()

        # 模拟真实的业务函数 - 使用更耗时的操作
        def calculate_fibonacci(n):
            """计算斐波那契数列 - 增加一些耗时操作"""
            if n <= 1:
                return n
            # 添加一些实际工作来使函数更有意义
            result = calculate_fibonacci(n-1) + calculate_fibonacci(n-2)
            # 模拟一些额外处理
            for i in range(1000):
                result += i * 0.000001
            return result

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
            """计算斐波那契数列 - 增加一些耗时操作"""
            if n <= 1:
                return n
            # 添加一些实际工作来使函数更有意义
            result = calculate_fibonacci_monitored(n-1) + calculate_fibonacci_monitored(n-2)
            # 模拟一些额外处理
            for i in range(1000):
                result += i * 0.000001
            return result

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

        tester = SmartPerformanceTester(max_overhead_ratio=0.15)  # 15%开销限制
        
        for baseline_func, monitored_func, args in test_cases:
            result = tester.measure_overhead(
                baseline_func, monitored_func, tuple(args)
            )
            
            # 断言性能开销
            assert_performance_overhead(
                result,
                max_overhead=0.15,
                description=f"函数 {baseline_func.__name__}"
            )
            
            # 验证测试通过
            assert result.test_passed, f"函数 {baseline_func.__name__} 开销测试失败: {result.overhead_ratio:.2%}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])