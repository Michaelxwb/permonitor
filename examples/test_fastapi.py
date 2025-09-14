"""
FastAPI示例测试脚本

测试FastAPI性能监控的各个功能

依赖要求:
- requests>=2.25.0

安装命令:
pip install requests
"""

import sys
import time
import json
from typing import Dict, Any

# 检查requests依赖
try:
    import requests
except ImportError as e:
    print(f"❌ 依赖缺失: {e}")
    print("请安装requests:")
    print("  pip install requests")
    sys.exit(1)


class FastAPITester:
    """FastAPI测试器"""
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def test_endpoint(self, method: str, endpoint: str, data: Dict = None, expected_status: int = 200) -> Dict[str, Any]:
        """测试单个端点"""
        url = f"{self.base_url}{endpoint}"
        
        print(f"🔍 测试 {method} {endpoint}")
        
        start_time = time.time()
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")
            
            end_time = time.time()
            duration = end_time - start_time
            
            result = {
                'endpoint': endpoint,
                'method': method,
                'status_code': response.status_code,
                'duration': duration,
                'success': response.status_code == expected_status,
                'response_size': len(response.content)
            }
            
            if response.status_code == expected_status:
                try:
                    result['response_data'] = response.json()
                except:
                    result['response_data'] = response.text[:200]  # 前200字符
            else:
                result['error'] = response.text
            
            # 显示结果
            status_icon = "✅" if result['success'] else "❌"
            print(f"  {status_icon} 状态码: {response.status_code}, 耗时: {duration:.3f}s")
            
            return result
            
        except Exception as e:
            print(f"  ❌ 请求失败: {e}")
            return {
                'endpoint': endpoint,
                'method': method,
                'success': False,
                'error': str(e)
            }
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始FastAPI性能监控测试")
        print("=" * 60)
        
        results = []
        
        # 1. 健康检查
        print("\n📋 1. 健康检查")
        results.append(self.test_endpoint('GET', '/health'))
        
        # 2. 首页
        print("\n🏠 2. 首页统计")
        results.append(self.test_endpoint('GET', '/'))
        
        # 3. 快速端点
        print("\n⚡ 3. 快速端点测试")
        results.append(self.test_endpoint('GET', '/api/users'))
        
        # 4. 中等速度端点
        print("\n🔄 4. 中等速度端点测试")
        results.append(self.test_endpoint('POST', '/api/users', {
            'name': 'Test User',
            'email': 'test@example.com'
        }))
        
        # 5. 接近阈值的端点
        print("\n⏰ 5. 接近阈值端点测试")
        results.append(self.test_endpoint('GET', '/api/reports'))
        
        # 6. 慢端点（会触发告警）
        print("\n🐌 6. 慢端点测试（会触发告警）")
        results.append(self.test_endpoint('GET', '/api/analytics'))
        
        # 7. 数据库查询测试
        print("\n💾 7. 数据库查询测试")
        for query_type in ['fast', 'medium', 'slow']:
            results.append(self.test_endpoint('POST', '/api/query', {
                'query_type': query_type,
                'parameters': {'test': True}
            }))
        
        # 8. 后台任务
        print("\n🔧 8. 后台任务测试")
        results.append(self.test_endpoint('POST', '/api/background-task'))
        
        # 9. 管理端点
        print("\n👨‍💼 9. 管理端点测试")
        results.append(self.test_endpoint('GET', '/admin/stats'))
        results.append(self.test_endpoint('POST', '/admin/test-alert'))
        
        # 10. 重置统计
        print("\n🔄 10. 重置统计")
        results.append(self.test_endpoint('POST', '/admin/reset-stats'))
        
        # 等待一下让监控系统处理
        print("\n⏳ 等待监控系统处理...")
        time.sleep(2)
        
        # 11. 最终统计
        print("\n📊 11. 最终统计")
        final_stats = self.test_endpoint('GET', '/admin/stats')
        results.append(final_stats)
        
        # 显示测试总结
        self.show_summary(results, final_stats)
        
        return results
    
    def show_summary(self, results: list, final_stats: Dict):
        """显示测试总结"""
        print("\n" + "=" * 60)
        print("📊 测试总结")
        print("=" * 60)
        
        # 统计测试结果
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r.get('success', False))
        failed_tests = total_tests - successful_tests
        
        print(f"总测试数: {total_tests}")
        print(f"成功: {successful_tests} ✅")
        print(f"失败: {failed_tests} ❌")
        print(f"成功率: {(successful_tests/total_tests)*100:.1f}%")
        
        # 性能统计
        durations = [r.get('duration', 0) for r in results if r.get('duration')]
        if durations:
            print(f"\n⏱️ 响应时间统计:")
            print(f"  平均: {sum(durations)/len(durations):.3f}s")
            print(f"  最快: {min(durations):.3f}s")
            print(f"  最慢: {max(durations):.3f}s")
        
        # 监控统计
        if final_stats.get('success') and final_stats.get('response_data'):
            stats_data = final_stats['response_data']
            print(f"\n📈 监控统计:")
            print(f"  总请求数: {stats_data.get('total_requests', 0)}")
            print(f"  慢请求数: {stats_data.get('slow_requests', 0)}")
            print(f"  告警数: {stats_data.get('alerts_sent', 0)}")
            print(f"  慢请求率: {stats_data.get('slow_request_rate', 0):.1f}%")
            
            overhead_stats = stats_data.get('overhead_stats', {})
            if overhead_stats.get('sample_count', 0) > 0:
                avg_overhead = overhead_stats.get('average_overhead', 0) * 100
                print(f"  平均监控开销: {avg_overhead:.2f}%")
        
        # 失败的测试详情
        if failed_tests > 0:
            print(f"\n❌ 失败的测试:")
            for result in results:
                if not result.get('success', False):
                    print(f"  {result.get('method', 'N/A')} {result.get('endpoint', 'N/A')}: {result.get('error', 'Unknown error')}")
        
        print("\n✅ 测试完成！")


def main():
    """主函数"""
    print("FastAPI性能监控测试工具")
    print("请确保FastAPI服务器正在运行 (python examples/fastapi_example.py)")
    print()
    
    # 检查服务器是否运行
    try:
        response = requests.get("http://localhost:8001/health", timeout=5)
        if response.status_code == 200:
            print("✅ FastAPI服务器运行正常")
        else:
            print("❌ FastAPI服务器响应异常")
            return
    except requests.exceptions.RequestException as e:
        print(f"❌ 无法连接到FastAPI服务器: {e}")
        print("请先启动服务器: python examples/fastapi_example.py")
        return
    
    # 运行测试
    tester = FastAPITester()
    results = tester.run_all_tests()
    
    # 保存测试结果
    with open('fastapi_test_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n📄 测试结果已保存到: fastapi_test_results.json")


if __name__ == '__main__':
    main()