#!/usr/bin/env python3
"""
测试FastAPI性能监控
"""

import asyncio
import time
import subprocess
import requests
import os
from pathlib import Path

def test_fastapi_monitoring():
    """测试FastAPI性能监控功能"""

    print("🚀 启动FastAPI应用进行测试...")

    # 清理旧的报告文件
    reports_dir = Path("../fastapi_reports")
    if reports_dir.exists():
        for file in reports_dir.glob("*.html"):
            file.unlink()
        print(f"🧹 清理了旧的报告文件")

    # 启动FastAPI应用
    print("📡 启动FastAPI服务器...")
    process = subprocess.Popen(
        ["python3", "-m", "uvicorn", "examples.fastapi_integration:app", "--port", "8001"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd="/Users/jahan/workspace/permonitor"
    )

    # 等待服务器启动
    time.sleep(3)

    try:
        print("🌐 测试各个端点...")

        # 测试根路径
        print("GET http://localhost:8001/")
        response = requests.get("http://localhost:8001/")
        print(f"  状态码: {response.status_code}, 响应时间: {response.elapsed.total_seconds():.3f}s")

        # 测试慢接口
        print("GET http://localhost:8001/slow (应该触发告警)")
        start_time = time.time()
        response = requests.get("http://localhost:8001/slow")
        end_time = time.time()
        print(f"  状态码: {response.status_code}, 实际响应时间: {end_time - start_time:.3f}s")

        # 测试用户接口
        print("GET http://localhost:8001/users/123")
        response = requests.get("http://localhost:8001/users/123")
        print(f"  状态码: {response.status_code}, 响应时间: {response.elapsed.total_seconds():.3f}s")

        # 测试计算接口
        print("POST http://localhost:8001/calculate")
        response = requests.post(
            "http://localhost:8001/calculate",
            json={"numbers": [1, 2, 3, 4, 5]}
        )
        print(f"  状态码: {response.status_code}, 响应时间: {response.elapsed.total_seconds():.3f}s")

        # 等待一段时间让报告生成
        print("⏳ 等待报告生成...")
        time.sleep(2)

        # 检查报告文件
        print("📊 检查生成的性能报告...")
        if reports_dir.exists():
            report_files = list(reports_dir.glob("*.html"))
            if report_files:
                print(f"✅ 找到 {len(report_files)} 个性能报告:")
                for file in report_files:
                    size = file.stat().st_size
                    print(f"  📄 {file.name} ({size} bytes)")

                    # 显示报告内容的前几行
                    content = file.read_text(encoding='utf-8')
                    lines = content.split('\n')[:10]
                    print(f"     报告预览:")
                    for line in lines:
                        if line.strip():
                            print(f"     {line.strip()}")
                    print()
            else:
                print("❌ 没有找到HTML报告文件")

                # 检查目录内容
                files = list(reports_dir.iterdir())
                if files:
                    print(f"目录内容: {[f.name for f in files]}")
                else:
                    print("目录为空")
        else:
            print(f"❌ 报告目录 {reports_dir} 不存在")

        # 获取监控统计
        print("📈 获取监控统计信息...")
        response = requests.get("http://localhost:8001/stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"总请求数: {stats.get('total_requests', 0)}")
            print(f"慢请求数: {stats.get('slow_requests', 0)}")
            print(f"告警发送数: {stats.get('alerts_sent', 0)}")
            print(f"慢请求比例: {stats.get('slow_request_rate', 0):.1f}%")
        else:
            print(f"无法获取统计信息: {response.status_code}")

    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")

    finally:
        # 停止服务器
        print("🛑 停止FastAPI服务器...")
        process.terminate()
        process.wait()

        stdout, stderr = process.communicate()
        if stdout:
            print("服务器输出:")
            print(stdout.decode('utf-8'))
        if stderr:
            print("服务器错误:")
            print(stderr.decode('utf-8'))

if __name__ == "__main__":
    test_fastapi_monitoring()
