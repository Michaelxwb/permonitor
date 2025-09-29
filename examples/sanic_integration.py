"""
Sanic集成示例

演示如何在Sanic项目中集成性能监控
"""

import asyncio
from sanic import Sanic
from sanic.response import json
from pydantic import BaseModel

# 导入性能监控
try:
    from web_performance_monitor import PerformanceMonitor, Config
except ImportError as e:
    print(f"导入错误: {e}")
    print("请先安装web-performance-monitor: pip install web-performance-monitor")
    exit(1)

# 配置性能监控
config = Config(
    threshold_seconds=0.5,
    enable_local_file=True,
    local_output_dir="../reports/sanic_reports",
    enable_mattermost=False,
    log_level="INFO",
    enable_url_whitelist=True,
    url_whitelist=["/slow"]
)

monitor = PerformanceMonitor(config)

# 创建Sanic应用
app = Sanic("PerformanceMonitorDemo")

# 数据模型
class User(BaseModel):
    id: int
    name: str
    email: str

class CalculationRequest(BaseModel):
    numbers: list[int]

# 创建性能装饰器
performance_monitor = monitor.create_decorator()

# 创建Sanic中间件
sanic_middleware = monitor.create_sanic_middleware()

# 被监控的函数
@performance_monitor
async def get_user_data(user_id: int) -> dict:
    """异步获取用户数据"""
    await asyncio.sleep(0.3)  # 模拟异步数据库查询
    return {
        "id": user_id,
        "name": f"User {user_id}",
        "email": f"user{user_id}@example.com"
    }

@performance_monitor
def process_business_logic(data: list[int]) -> dict:
    """处理复杂业务逻辑"""
    import time
    time.sleep(0.8)  # 模拟复杂计算
    return {
        "sum": sum(data),
        "average": sum(data) / len(data) if data else 0,
        "max": max(data) if data else 0,
        "min": min(data) if data else 0
    }

# 创建Sanic适配器实例
from web_performance_monitor.adapters.sanic import SanicAdapter
sanic_adapter = SanicAdapter(monitor)

# 请求中间件
@app.middleware('request')
async def monitor_request(request):
    """请求监控中间件"""
    return sanic_adapter._monitor_sanic_request(request)

# 响应中间件
@app.middleware('response')
async def monitor_response(request, response):
    """响应监控中间件"""
    sanic_adapter.process_response(request, response)

# Sanic路由
@app.route('/')
async def root(request):
    """根路径"""
    return json({
        "message": "Sanic性能监控示例",
        "monitoring": "已启用",
        "framework": "Sanic",
        "endpoints": [
            "/slow - 慢响应端点",
            "/users/<user_id> - 用户详情",
            "/calculate - 计算端点（POST）",
            "/health - 健康检查",
            "/stats - 监控统计"
        ]
    })

@app.route('/slow')
async def slow_endpoint(request):
    """慢响应端点"""
    await asyncio.sleep(1.2)  # 超过阈值，会触发告警
    return json({
        "message": "这是一个慢响应端点",
        "delay": 1.2
    })

@app.route('/users/<user_id:int>')
async def get_user(request, user_id: int):
    """获取用户信息"""
    try:
        await asyncio.sleep(1.2)  # 超过阈值，会触发告警
        user = await get_user_data(user_id)
        return json(user)
    except Exception as e:
        return json({"error": str(e)}, status=500)

@app.route('/calculate', methods=['POST'])
async def calculate(request):
    """计算端点"""
    try:
        data = request.json
        if not data or 'numbers' not in data:
            return json({"error": "缺少numbers字段"}, status=400)

        result = process_business_logic(data['numbers'])
        return json(result)
    except Exception as e:
        return json({"error": str(e)}, status=500)

@app.route('/health')
async def health_check(request):
    """健康检查端点"""
    return json({"status": "healthy"})

@app.route('/stats')
async def get_stats(request):
    """获取监控统计信息"""
    import json as json_lib
    from datetime import datetime, date

    stats = monitor.get_stats()

    # 自定义JSON序列化函数
    def json_serial(obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")

    # 处理所有可能的datetime对象
    def process_datetime_fields(data):
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (datetime, date)):
                    data[key] = value.isoformat()
                elif isinstance(value, dict):
                    process_datetime_fields(value)
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        if isinstance(item, (datetime, date)):
                            value[i] = item.isoformat()
                        elif isinstance(item, dict):
                            process_datetime_fields(item)
        return data

    # 处理datetime字段
    stats = process_datetime_fields(stats)

    # 返回JSON响应
    return json(stats, dumps=lambda obj: json_lib.dumps(obj, default=json_serial))

if __name__ == "__main__":
    print("Sanic性能监控示例")
    print("支持的URL:")
    print("  http://localhost:8000/ - 根路径")
    print("  http://localhost:8000/slow - 慢响应端点")
    print("  http://localhost:8000/users/123 - 用户详情")
    print("  http://localhost:8000/calculate - 计算端点（POST）")
    print("  http://localhost:8000/health - 健康检查")
    print("  http://localhost:8000/stats - 监控统计")
    print("\n性能报告将保存在 ./sanic_reports/ 目录")
    print("\n启动命令: python sanic_integration.py")

    # 运行Sanic应用
    app.run(host="127.0.0.1", port=8002, debug=False, single_process=True)
