#!/usr/bin/env python3
"""
Sanic集成自动化测试

测试Sanic框架的性能监控功能
"""

import asyncio
import aiohttp
import time
import subprocess
import signal
import os
import json
from pathlib import Path


class SanicIntegrationTest:
    """Sanic集成测试类"""
    
    def __init__(self):
        self.base_url = "http://127.0.0.1:8002"
        self.process = None
        self.reports_dir = Path("./sanic_reports")
        
    async def start_sanic_server(self):
        """启动Sanic服务器"""
        print("🚀 启动Sanic服务器...")
        
        # 清理旧的报告文件
        if self.reports_dir.exists():
            for file in self.reports_dir.glob("*.html"):
                file.unlink()
            print(f"🧹 清理了旧的报告文件")
        
        # 启动Sanic应用
        self.process = subprocess.Popen(
            ["python3", "examples/sanic_integration.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid  # 创建新的进程组
        )
        
        # 等待服务器启动
        await asyncio.sleep(3)
        
        # 检查服务器是否启动成功
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health") as response:
                    if response.status == 200:
                        print("✅ Sanic服务器启动成功")
                        return True
                    else:
                        print(f"❌ 服务器启动失败，状态码: {response.status}")
                        return False
        except Exception as e:
            print(f"❌ 连接服务器失败: {e}")
            return False
    
    async def stop_sanic_server(self):
        """停止Sanic服务器"""
        if self.process:
            print("🛑 停止Sanic服务器...")
            try:
                # 终止整个进程组
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                self.process.wait(timeout=5)
            except:
                try:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                except:
                    pass
            
            # 获取输出
            stdout, stderr = self.process.communicate()
            if stdout:
                print("服务器输出:")
                print(stdout.decode('utf-8'))
            if stderr:
                print("服务器错误:")
                print(stderr.decode('utf-8'))
    
    async def test_endpoints(self):
        """测试各个端点"""
        print("\n🌐 开始测试端点...")
        
        async with aiohttp.ClientSession() as session:
            # 测试根路径
            print("GET /")
            try:
                async with session.get(f"{self.base_url}/") as response:
                    data = await response.json()
                    print(f"  状态码: {response.status}")
                    print(f"  响应: {data.get('message', '无消息')}")
                    assert response.status == 200
                    assert 'Sanic性能监控示例' in data.get('message', '')
            except Exception as e:
                print(f"  ❌ 测试失败: {e}")
                return False
            
            # 测试慢接口
            print("GET /slow (应该触发告警)")
            try:
                start_time = time.time()
                async with session.get(f"{self.base_url}/slow") as response:
                    end_time = time.time()
                    data = await response.json()
                    actual_time = end_time - start_time
                    print(f"  状态码: {response.status}")
                    print(f"  实际响应时间: {actual_time:.3f}s")
                    print(f"  响应: {data.get('message', '无消息')}")
                    assert response.status == 200
                    assert actual_time >= 1.2  # 应该至少1.2秒
            except Exception as e:
                print(f"  ❌ 测试失败: {e}")
                return False
            
            # 测试用户接口
            print("GET /users/123")
            try:
                async with session.get(f"{self.base_url}/users/123") as response:
                    data = await response.json()
                    print(f"  状态码: {response.status}")
                    print(f"  用户ID: {data.get('id')}")
                    print(f"  用户名: {data.get('name')}")
                    assert response.status == 200
                    assert data.get('id') == 123
            except Exception as e:
                print(f"  ❌ 测试失败: {e}")
                return False
            
            # 测试计算接口
            print("POST /calculate")
            try:
                payload = {"numbers": [1, 2, 3, 4, 5]}
                async with session.post(f"{self.base_url}/calculate", json=payload) as response:
                    data = await response.json()
                    print(f"  状态码: {response.status}")
                    print(f"  计算结果: sum={data.get('sum')}, avg={data.get('average')}")
                    assert response.status == 200
                    assert data.get('sum') == 15
                    assert data.get('average') == 3.0
            except Exception as e:
                print(f"  ❌ 测试失败: {e}")
                return False
            
            # 测试健康检查
            print("GET /health")
            try:
                async with session.get(f"{self.base_url}/health") as response:
                    data = await response.json()
                    print(f"  状态码: {response.status}")
                    print(f"  健康状态: {data.get('status')}")
                    assert response.status == 200
                    assert data.get('status') == 'healthy'
            except Exception as e:
                print(f"  ❌ 测试失败: {e}")
                return False
            
            # 测试统计接口
            print("GET /stats")
            try:
                async with session.get(f"{self.base_url}/stats") as response:
                    data = await response.json()
                    print(f"  状态码: {response.status}")
                    print(f"  总请求数: {data.get('total_requests')}")
                    print(f"  慢请求数: {data.get('slow_requests')}")
                    print(f"  告警发送数: {data.get('alerts_sent')}")
                    assert response.status == 200
                    assert data.get('total_requests') > 0
            except Exception as e:
                print(f"  ❌ 测试失败: {e}")
                return False
        
        return True
    
    async def check_performance_reports(self):
        """检查性能报告生成情况"""
        print("\n📊 检查性能报告生成情况...")
        
        # 等待报告生成
        await asyncio.sleep(2)
        
        if self.reports_dir.exists():
            report_files = list(self.reports_dir.glob("*.html"))
            if report_files:
                print(f"✅ 找到 {len(report_files)} 个性能报告:")
                for file in report_files:
                    size = file.stat().st_size
                    print(f"  📄 {file.name} ({size} bytes)")
                return True
            else:
                print("❌ 没有找到HTML报告文件")
                return False
        else:
            print(f"❌ 报告目录 {self.reports_dir} 不存在")
            return False
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始Sanic集成自动化测试...")
        
        try:
            # 启动服务器
            if not await self.start_sanic_server():
                print("❌ 服务器启动失败，测试中止")
                return False
            
            # 测试端点
            if not await self.test_endpoints():
                print("❌ 端点测试失败")
                return False
            
            # 检查报告
            if not await self.check_performance_reports():
                print("❌ 性能报告检查失败")
                return False
            
            print("\n🎉 所有测试通过！Sanic集成成功！")
            return True
            
        except Exception as e:
            print(f"\n❌ 测试过程出错: {e}")
            import traceback
            traceback.print_exc()
            return False
            
        finally:
            await self.stop_sanic_server()


async def main():
    """主函数"""
    # 检查Sanic是否安装
    try:
        import sanic
        print(f"✅ Sanic已安装，版本: {sanic.__version__}")
    except ImportError:
        print("❌ Sanic未安装，请先安装: pip install sanic")
        return
    
    # 运行测试
    tester = SanicIntegrationTest()
    success = await tester.run_all_tests()
    
    if success:
        print("\n✨ Sanic性能监控集成测试全部通过！")
    else:
        print("\n💥 Sanic性能监控集成测试失败！")
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())