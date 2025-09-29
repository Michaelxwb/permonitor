"""
FastAPI集成示例

演示如何在FastAPI项目中集成性能监控
"""

import asyncio
import time

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel

# 导入性能监控
from web_performance_monitor import PerformanceMonitor, Config

# 配置性能监控
config = Config(
    threshold_seconds=0.5,
    enable_local_file=True,
    local_output_dir="../reports/fastapi_reports",
    enable_mattermost=False,
    log_level="DEBUG",
    # url_blacklist=["/slow"],
    enable_url_whitelist=True,
    url_whitelist=["/slow"]
)

monitor = PerformanceMonitor(config)

# 创建性能装饰器
performance_monitor = monitor.create_decorator()

# FastAPI应用
app = FastAPI(
    title="性能监控示例",
    description="FastAPI性能监控集成示例",
    version="1.0.0"
)

# 注意：为了监控所有HTTP请求，需要应用ASGI中间件
# 但由于ASGI中间件的复杂性，我们暂时使用装饰器模式监控关键函数
# 如果需要完整的HTTP请求监控，建议使用Flask框架或手动添加监控逻辑


# 数据模型
class User(BaseModel):
    id: int
    name: str
    email: str


class CalculationRequest(BaseModel):
    numbers: list[int]


# 被监控的函数
@performance_monitor
async def get_user_data(user_id: int) -> User:
    """异步获取用户数据"""
    await asyncio.sleep(0.3)  # 模拟异步数据库查询
    return User(
        id=user_id,
        name=f"User {user_id}",
        email=f"user{user_id}@example.com"
    )


@performance_monitor
def process_business_logic(data: list[int]) -> dict:
    """处理复杂业务逻辑"""
    time.sleep(0.8)  # 模拟复杂计算
    return {
        "sum": sum(data),
        "average": sum(data) / len(data) if data else 0,
        "max": max(data) if data else 0,
        "min": min(data) if data else 0
    }


# FastAPI路由
@app.get("/")
@performance_monitor
async def root():
    """根路径"""
    return {
        "message": "FastAPI性能监控示例",
        "monitoring": "已启用",
        "framework": "FastAPI"
    }


@app.get("/slow")
@performance_monitor
async def slow_endpoint():
    """慢响应端点"""
    await asyncio.sleep(1.2)  # 超过阈值，会触发告警
    return {
        "message": "这是一个慢响应端点",
        "delay": 1.2
    }


@app.get("/users/{user_id}", response_model=User)
@performance_monitor
async def get_user(user_id: int):
    """获取用户信息"""
    try:
        await asyncio.sleep(1.2)  # 超过阈值，会触发告警
        user = await get_user_data(user_id)
        return user
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/calculate")
@performance_monitor
async def calculate(request: CalculationRequest):
    """计算端点"""
    try:
        result = process_business_logic(request.numbers)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
@performance_monitor
async def health_check():
    """健康检查端点"""
    return {"status": "healthy"}


# 依赖注入示例
async def get_monitor():
    """获取监控器依赖"""
    return monitor


@app.get("/stats")
@performance_monitor
async def get_stats(monitor_instance: PerformanceMonitor = Depends(get_monitor)):
    """获取监控统计信息"""
    stats = monitor_instance.get_stats()
    return stats


if __name__ == "__main__":
    print("FastAPI性能监控示例")
    print("支持的URL:")
    print("  http://localhost:8000/ - 根路径")
    print("  http://localhost:8000/slow - 慢响应端点")
    print("  http://localhost:8000/users/123 - 用户详情")
    print("  http://localhost:8000/calculate - 计算端点（POST）")
    print("  http://localhost:8000/health - 健康检查")
    print("  http://localhost:8000/stats - 监控统计")
    print("\n性能报告将保存在 ./fastapi_reports/ 目录")
    print("\n启动命令: uvicorn fastapi_integration:app --reload")

    # 注意：FastAPI需要ASGI服务器，如uvicorn
    # 安装: pip install uvicorn
    # 运行: uvicorn fastapi_integration:app --reload
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
