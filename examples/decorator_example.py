"""
装饰器使用示例

演示如何使用装饰器模式监控特定函数
"""

import random
import time
from datetime import datetime

from web_performance_monitor import PerformanceMonitor, Config

# 配置性能监控
config = Config(
    threshold_seconds=0.5,  # 0.5秒阈值（更敏感）
    alert_window_days=1,  # 1天重复告警窗口
    enable_local_file=True,  # 启用本地文件通知
    local_output_dir="./function_reports",  # 函数报告目录
    enable_mattermost=False,  # 禁用Mattermost
    log_level="INFO"
)

# 创建性能监控器
monitor = PerformanceMonitor(config)

# 创建装饰器
performance_monitor = monitor.create_decorator()


# 示例业务函数
@performance_monitor
def calculate_fibonacci(n: int) -> int:
    """计算斐波那契数列（递归实现，性能较差）"""
    if n <= 1:
        return n
    return calculate_fibonacci(n - 1) + calculate_fibonacci(n - 2)


@performance_monitor
def process_data(data: list) -> dict:
    """处理数据列表"""
    time.sleep(0.1)  # 模拟I/O操作

    result = {
        'count': len(data),
        'sum': sum(data) if data else 0,
        'average': sum(data) / len(data) if data else 0,
        'max': max(data) if data else None,
        'min': min(data) if data else None,
        'processed_at': datetime.now().isoformat()
    }

    return result


@performance_monitor
def simulate_database_query(table: str, conditions: dict = None) -> list:
    """模拟数据库查询"""
    # 模拟不同的查询时间
    query_time = random.uniform(0.1, 1.5)
    time.sleep(query_time)

    # 模拟查询结果
    result_count = random.randint(1, 100)
    results = [
        {
            'id': i,
            'table': table,
            'conditions': conditions or {},
            'timestamp': datetime.now().isoformat()
        }
        for i in range(result_count)
    ]

    return results


@performance_monitor
def complex_calculation(iterations: int = 1000000) -> float:
    """复杂计算任务"""
    result = 0.0
    for i in range(iterations):
        result += (i ** 0.5) / (i + 1)
    return result


@performance_monitor
def file_processing(filename: str, operation: str = "read") -> dict:
    """文件处理操作"""
    # 模拟文件操作时间
    if operation == "read":
        time.sleep(0.2)
        size = random.randint(1024, 1024 * 1024)
    elif operation == "write":
        time.sleep(0.3)
        size = random.randint(512, 1024 * 512)
    else:
        time.sleep(0.1)
        size = 0

    return {
        'filename': filename,
        'operation': operation,
        'size_bytes': size,
        'success': True,
        'processed_at': datetime.now().isoformat()
    }


@performance_monitor
def api_call_simulation(endpoint: str, timeout: float = 1.0) -> dict:
    """模拟API调用"""
    # 模拟网络延迟
    delay = min(timeout, random.uniform(0.1, 2.0))
    time.sleep(delay)

    # 模拟不同的响应
    success = delay < timeout
    status_code = 200 if success else 408

    return {
        'endpoint': endpoint,
        'delay': delay,
        'timeout': timeout,
        'success': success,
        'status_code': status_code,
        'response_time': delay
    }


def demonstrate_function_monitoring():
    """演示函数监控功能"""
    print("🔍 函数性能监控演示")
    print("=" * 50)

    print(f"📊 监控配置: 阈值={config.threshold_seconds}s")
    print(f"📁 报告目录: {config.local_output_dir}")
    print()

    # 创建报告目录
    import os
    os.makedirs(config.local_output_dir, exist_ok=True)

    test_cases = [
        {
            'name': '快速函数调用',
            'func': lambda: process_data([1, 2, 3, 4, 5]),
            'description': '处理小数据集，应该很快完成'
        },
        {
            'name': '中等复杂度计算',
            'func': lambda: complex_calculation(100000),
            'description': '中等复杂度计算，可能接近阈值'
        },
        {
            'name': '慢速斐波那契计算',
            'func': lambda: calculate_fibonacci(30),
            'description': '递归计算，应该超过阈值触发告警'
        },
        {
            'name': '数据库查询模拟',
            'func': lambda: simulate_database_query('users', {'active': True}),
            'description': '模拟数据库查询，随机延迟'
        },
        {
            'name': '文件读取操作',
            'func': lambda: file_processing('data.txt', 'read'),
            'description': '模拟文件读取操作'
        },
        {
            'name': '慢速API调用',
            'func': lambda: api_call_simulation('/api/slow', timeout=0.3),
            'description': '模拟慢速API调用，可能超时'
        }
    ]

    results = []

    for i, test_case in enumerate(test_cases, 1):
        print(f"{i}. {test_case['name']}")
        print(f"   描述: {test_case['description']}")

        start_time = time.time()
        try:
            result = test_case['func']()
            execution_time = time.time() - start_time
            success = True
            error = None
        except Exception as e:
            execution_time = time.time() - start_time
            success = False
            error = str(e)
            result = None

        will_alert = execution_time > config.threshold_seconds

        print(f"   执行时间: {execution_time:.3f}s")
        print(f"   状态: {'✅ 成功' if success else '❌ 失败'}")
        print(f"   告警: {'🚨 是' if will_alert else '✅ 否'}")

        if error:
            print(f"   错误: {error}")

        results.append({
            'name': test_case['name'],
            'execution_time': execution_time,
            'success': success,
            'will_alert': will_alert,
            'error': error
        })

        print()
        time.sleep(0.5)  # 避免过快执行

    return results


def show_monitoring_stats():
    """显示监控统计信息"""
    print("📊 监控统计信息")
    print("=" * 30)

    stats = monitor.get_stats()

    print(f"监控状态: {'启用' if stats.get('monitoring_enabled') else '禁用'}")
    print(f"总请求数: {stats.get('total_requests', 0)}")
    print(f"慢请求数: {stats.get('slow_requests', 0)}")
    print(f"告警发送数: {stats.get('alerts_sent', 0)}")
    print(f"慢请求率: {stats.get('slow_request_rate', 0):.2f}%")

    overhead_stats = stats.get('overhead_stats', {})
    if overhead_stats.get('sample_count', 0) > 0:
        print(f"平均性能开销: {overhead_stats.get('average_overhead', 0) * 100:.2f}%")
        print(f"最大性能开销: {overhead_stats.get('max_overhead', 0) * 100:.2f}%")

    print()


def test_exception_handling():
    """测试异常处理"""
    print("🧪 测试异常处理")
    print("=" * 20)

    @performance_monitor
    def function_with_exception():
        """会抛出异常的函数"""
        time.sleep(0.2)
        raise ValueError("这是一个测试异常")

    @performance_monitor
    def function_with_return_value(x: int, y: int) -> int:
        """有返回值的函数"""
        time.sleep(0.1)
        return x + y

    # 测试异常处理
    try:
        function_with_exception()
    except ValueError as e:
        print(f"✅ 异常正确传播: {e}")

    # 测试返回值
    result = function_with_return_value(10, 20)
    print(f"✅ 返回值正确: {result}")

    print()


def main():
    """主函数"""
    print("🚀 装饰器性能监控演示")
    print("=" * 50)

    # 运行演示
    results = demonstrate_function_monitoring()

    # 显示统计信息
    show_monitoring_stats()

    # 测试异常处理
    test_exception_handling()

    # 测试告警系统
    print("🧪 测试告警系统")
    print("=" * 20)
    test_result = monitor.test_alert_system()
    print(f"告警系统测试: {'✅ 成功' if test_result.get('success') else '❌ 失败'}")

    if test_result.get('notifier_results'):
        for notifier, success in test_result['notifier_results'].items():
            print(f"  {notifier}: {'✅ 正常' if success else '❌ 失败'}")

    print()

    # 总结
    print("📋 执行总结")
    print("=" * 15)

    total_tests = len(results)
    successful_tests = sum(1 for r in results if r['success'])
    alert_tests = sum(1 for r in results if r['will_alert'])

    print(f"总测试数: {total_tests}")
    print(f"成功执行: {successful_tests}")
    print(f"触发告警: {alert_tests}")
    print(f"成功率: {(successful_tests / total_tests) * 100:.1f}%")

    # 显示最慢的函数
    slowest = max(results, key=lambda x: x['execution_time'])
    print(f"最慢函数: {slowest['name']} ({slowest['execution_time']:.3f}s)")

    print(f"\n📁 性能报告已保存到: {config.local_output_dir}")

    # 清理
    monitor.cleanup()
    print("\n✅ 演示完成")


if __name__ == '__main__':
    main()
