"""
测试运行器

提供便捷的测试执行和报告功能
"""

import sys
import os
import pytest
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_integration_tests():
    """运行集成测试"""
    print("=" * 60)
    print("运行集成测试套件")
    print("=" * 60)
    
    test_files = [
        'tests/test_integration.py',
        'tests/test_performance_validation.py'
    ]
    
    # 运行测试
    args = [
        '-v',  # 详细输出
        '--tb=short',  # 简短的错误回溯
        '--durations=10',  # 显示最慢的10个测试
        '--capture=no',  # 不捕获输出，显示print语句
    ] + test_files
    
    start_time = time.time()
    result = pytest.main(args)
    end_time = time.time()
    
    print(f"\n测试完成，耗时: {end_time - start_time:.2f}秒")
    return result


def run_unit_tests():
    """运行单元测试"""
    print("=" * 60)
    print("运行单元测试套件")
    print("=" * 60)
    
    test_files = [
        'tests/test_config.py'
    ]
    
    args = [
        '-v',
        '--tb=short',
        '--durations=5',
        '--capture=no',
    ] + test_files
    
    start_time = time.time()
    result = pytest.main(args)
    end_time = time.time()
    
    print(f"\n单元测试完成，耗时: {end_time - start_time:.2f}秒")
    return result


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("运行完整测试套件")
    print("=" * 60)
    
    args = [
        'tests/',
        '-v',
        '--tb=short',
        '--durations=15',
        '--capture=no',
        '--strict-markers',  # 严格标记模式
    ]
    
    start_time = time.time()
    result = pytest.main(args)
    end_time = time.time()
    
    print(f"\n所有测试完成，耗时: {end_time - start_time:.2f}秒")
    return result


def run_performance_tests():
    """运行性能测试"""
    print("=" * 60)
    print("运行性能验证测试")
    print("=" * 60)
    
    args = [
        'tests/test_performance_validation.py',
        '-v',
        '--tb=short',
        '--durations=10',
        '--capture=no',
        '-m', 'not slow',  # 跳过标记为slow的测试
    ]
    
    start_time = time.time()
    result = pytest.main(args)
    end_time = time.time()
    
    print(f"\n性能测试完成，耗时: {end_time - start_time:.2f}秒")
    return result


def run_quick_tests():
    """运行快速测试（跳过耗时的测试）"""
    print("=" * 60)
    print("运行快速测试套件")
    print("=" * 60)
    
    args = [
        'tests/',
        '-v',
        '--tb=line',  # 单行错误回溯
        '--durations=5',
        '--capture=no',
        '-m', 'not slow',  # 跳过慢测试
        '--maxfail=5',  # 最多5个失败后停止
    ]
    
    start_time = time.time()
    result = pytest.main(args)
    end_time = time.time()
    
    print(f"\n快速测试完成，耗时: {end_time - start_time:.2f}秒")
    return result


def run_coverage_tests():
    """运行带覆盖率的测试"""
    print("=" * 60)
    print("运行覆盖率测试")
    print("=" * 60)
    
    try:
        import pytest_cov
    except ImportError:
        print("警告: pytest-cov 未安装，跳过覆盖率测试")
        return run_all_tests()
    
    args = [
        'tests/',
        '--cov=web_performance_monitor',
        '--cov-report=html',
        '--cov-report=term-missing',
        '--cov-fail-under=80',  # 覆盖率低于80%时失败
        '-v',
        '--tb=short',
    ]
    
    start_time = time.time()
    result = pytest.main(args)
    end_time = time.time()
    
    print(f"\n覆盖率测试完成，耗时: {end_time - start_time:.2f}秒")
    print("HTML覆盖率报告生成在: htmlcov/index.html")
    return result


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python test_runner.py [command]")
        print("")
        print("可用命令:")
        print("  unit        - 运行单元测试")
        print("  integration - 运行集成测试")
        print("  performance - 运行性能测试")
        print("  all         - 运行所有测试")
        print("  quick       - 运行快速测试")
        print("  coverage    - 运行覆盖率测试")
        return 1
    
    command = sys.argv[1].lower()
    
    # 设置环境变量
    os.environ['PYTHONPATH'] = str(project_root)
    
    if command == 'unit':
        return run_unit_tests()
    elif command == 'integration':
        return run_integration_tests()
    elif command == 'performance':
        return run_performance_tests()
    elif command == 'all':
        return run_all_tests()
    elif command == 'quick':
        return run_quick_tests()
    elif command == 'coverage':
        return run_coverage_tests()
    else:
        print(f"未知命令: {command}")
        return 1


if __name__ == '__main__':
    sys.exit(main())