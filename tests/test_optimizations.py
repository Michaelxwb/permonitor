#!/usr/bin/env python3
"""
优化功能综合验证脚本

验证所有新增和优化的功能是否正常工作
"""

import sys
import time
import asyncio
from datetime import datetime

def test_basic_import():
    """测试基本导入功能"""
    print("🧪 测试基本导入...")
    try:
        from web_performance_monitor import PerformanceMonitor, Config
        print("✅ 基本导入成功")
        return True
    except Exception as e:
        print(f"❌ 基本导入失败: {e}")
        return False

def test_wsgi_middleware():
    """测试WSGI中间件功能"""
    print("🧪 测试WSGI中间件...")
    try:
        from web_performance_monitor import PerformanceMonitor, Config

        config = Config(
            threshold_seconds=0.1,
            enable_local_file=True,
            local_output_dir="../test_reports"
        )
        monitor = PerformanceMonitor(config)

        # 测试新方法
        wsgi_middleware = monitor.create_wsgi_middleware()
        old_middleware = monitor.create_middleware()  # 向后兼容

        if callable(wsgi_middleware) and callable(old_middleware):
            print("✅ WSGI中间件功能正常")
            return True
        else:
            print("❌ WSGI中间件功能异常")
            return False

    except Exception as e:
        print(f"❌ WSGI中间件测试失败: {e}")
        return False

def test_asgi_middleware():
    """测试ASGI中间件功能"""
    print("🧪 测试ASGI中间件...")
    try:
        from web_performance_monitor import PerformanceMonitor, Config

        config = Config(
            threshold_seconds=0.1,
            enable_local_file=True,
            local_output_dir="../test_reports"
        )
        monitor = PerformanceMonitor(config)

        # 测试ASGI中间件
        asgi_middleware = monitor.create_asgi_middleware()

        if callable(asgi_middleware):
            print("✅ ASGI中间件功能正常")
            return True
        else:
            print("❌ ASGI中间件功能异常")
            return False

    except Exception as e:
        print(f"❌ ASGI中间件测试失败: {e}")
        return False

def test_decorator_enhancement():
    """测试装饰器增强功能"""
    print("🧪 测试装饰器增强功能...")
    try:
        from web_performance_monitor import PerformanceMonitor, Config

        config = Config(
            threshold_seconds=0.1,
            enable_local_file=True,
            local_output_dir="../test_reports"
        )
        monitor = PerformanceMonitor(config)

        # 测试自定义名称装饰器
        decorator = monitor.create_decorator(name="自定义测试函数")

        @decorator
        def test_function():
            time.sleep(0.05)
            return "success"

        result = test_function()

        if result == "success":
            print("✅ 装饰器增强功能正常")
            return True
        else:
            print("❌ 装饰器增强功能异常")
            return False

    except Exception as e:
        print(f"❌ 装饰器增强测试失败: {e}")
        return False

def test_async_decorator():
    """测试异步装饰器功能"""
    print("🧪 测试异步装饰器...")

    async def run_async_test():
        try:
            from web_performance_monitor import PerformanceMonitor, Config

            config = Config(
                threshold_seconds=0.1,
                enable_local_file=True,
                local_output_dir="../test_reports"
            )
            monitor = PerformanceMonitor(config)

            # 测试异步装饰器
            async_decorator = monitor.create_async_decorator(name="异步测试函数")

            @async_decorator
            async def async_test_function():
                await asyncio.sleep(0.05)
                return "async_success"

            result = await async_test_function()

            if result == "async_success":
                print("✅ 异步装饰器功能正常")
                return True
            else:
                print("❌ 异步装饰器功能异常")
                return False

        except Exception as e:
            print(f"❌ 异步装饰器测试失败: {e}")
            return False

    # 运行异步测试
    try:
        return asyncio.run(run_async_test())
    except Exception as e:
        print(f"❌ 异步测试运行失败: {e}")
        return False

def test_config_validation():
    """测试配置验证功能"""
    print("🧪 测试配置验证...")
    try:
        from web_performance_monitor import PerformanceMonitor, Config

        # 测试有效配置
        config = Config(
            threshold_seconds=1.0,
            alert_window_days=7,
            enable_local_file=True,
            local_output_dir="../test_reports"
        )

        monitor = PerformanceMonitor(config)
        stats = monitor.get_stats()

        if isinstance(stats, dict) and 'total_requests' in stats:
            print("✅ 配置验证功能正常")
            return True
        else:
            print("❌ 配置验证功能异常")
            return False

    except Exception as e:
        print(f"❌ 配置验证测试失败: {e}")
        return False

def test_performance_metrics():
    """测试性能指标模型"""
    print("🧪 测试性能指标模型...")
    try:
        from web_performance_monitor.models import PerformanceMetrics
        from datetime import datetime

        metrics = PerformanceMetrics(
            endpoint="/test",
            request_url="http://localhost/test",
            request_params={"param": "value"},
            execution_time=0.5,
            timestamp=datetime.now(),
            request_method="GET",
            status_code=200
        )

        # 测试各种方法
        metrics_dict = metrics.to_dict()
        metrics_json = metrics.to_json()
        is_slow = metrics.is_slow(0.3)
        cache_key = metrics.get_cache_key()
        summary = metrics.format_summary()

        if all([metrics_dict, metrics_json, isinstance(is_slow, bool), cache_key, summary]):
            print("✅ 性能指标模型功能正常")
            return True
        else:
            print("❌ 性能指标模型功能异常")
            return False

    except Exception as e:
        print(f"❌ 性能指标模型测试失败: {e}")
        return False

def test_adapter_structure():
    """测试适配器结构"""
    print("🧪 测试适配器结构...")
    try:
        from web_performance_monitor.adapters import BaseFrameworkAdapter, WSGIAdapter, ASGIAdapter
        from web_performance_monitor.middleware import WSGIMiddleware, ASGIMiddleware

        # 验证适配器存在且可导入
        adapters = [BaseFrameworkAdapter, WSGIAdapter, ASGIAdapter]
        middlewares = [WSGIMiddleware, ASGIMiddleware]

        if all(adapters) and all(middlewares):
            print("✅ 适配器结构完整")
            return True
        else:
            print("❌ 适配器结构不完整")
            return False

    except Exception as e:
        print(f"❌ 适配器结构测试失败: {e}")
        return False

def run_all_tests():
    """运行所有测试"""
    print("🚀 开始性能监控优化功能验证")
    print("=" * 50)

    tests = [
        test_basic_import,
        test_wsgi_middleware,
        test_asgi_middleware,
        test_decorator_enhancement,
        test_async_decorator,
        test_config_validation,
        test_performance_metrics,
        test_adapter_structure,
    ]

    passed = 0
    total = len(tests)

    start_time = time.time()

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ 测试异常: {e}")
        print()

    end_time = time.time()
    execution_time = end_time - start_time

    print("=" * 50)
    print(f"📊 测试结果汇总:")
    print(f"   通过: {passed}/{total}")
    print(f"   失败: {total - passed}/{total}")
    print(f"   执行时间: {execution_time:.2f}秒")
    print(f"   成功率: {(passed/total)*100:.1f}%")

    if passed == total:
        print("🎉 所有测试通过！优化功能验证成功")
        return True
    else:
        print("⚠️  部分测试失败，请检查相关功能")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
