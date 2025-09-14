"""
FastAPI集成示例

演示如何在FastAPI应用中使用Web性能监控工具

依赖要求:
- fastapi>=0.100.0
- uvicorn>=0.20.0
- pydantic>=2.0.0

安装命令:
pip install web-performance-monitor[fastapi]
或
pip install -r requirements-fastapi.txt
"""

import os
import sys
import time
import asyncio
from typing import Dict, List, Optional

# 检查FastAPI依赖
try:
    from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel
    import uvicorn
except ImportError as e:
    print(f"❌ FastAPI依赖缺失: {e}")
    print("请安装FastAPI依赖:")
    print("  pip install web-performance-monitor[fastapi]")
    print("或者:")
    print("  pip install fastapi uvicorn")
    sys.exit(1)

from web_performance_monitor import PerformanceMonitor, Config


# Pydantic模型
class User(BaseModel):
    id: int
    name: str
    email: str


class UserCreate(BaseModel):
    name: str
    email: str


class AnalyticsRequest(BaseModel):
    query_type: str
    parameters: Dict = {}


def create_fastapi_app():
    """创建FastAPI应用"""
    
    # 配置性能监控
    config = Config(
        threshold_seconds=0.5,              # FastAPI通常响应更快
        alert_window_days=3,
        max_performance_overhead=0.02,      # 2%性能开销限制
        
        # 本地文件通知
        enable_local_file=True,
        local_output_dir="./fastapi_reports",
        
        # 日志配置
        log_level="INFO"
    )
    
    # 创建监控器
    monitor = PerformanceMonitor(config)
    
    # 创建FastAPI应用
    app = FastAPI(
        title="FastAPI性能监控示例",
        description="演示Web性能监控工具与FastAPI的集成",
        version="1.0.0"
    )
    
    # 创建装饰器用于函数监控
    performance_monitor = monitor.create_decorator()
    
    # 业务函数示例
    @performance_monitor
    async def async_calculation(n: int) -> float:
        """异步计算函数"""
        result = 0
        for i in range(n):
            result += i ** 0.5
            if i % 10000 == 0:  # 让出控制权
                await asyncio.sleep(0)
        return result
    
    @performance_monitor
    async def database_query_simulation(query_type: str) -> Dict:
        """数据库查询模拟"""
        delays = {
            'fast': 0.05,
            'medium': 0.3,
            'slow': 0.8
        }
        
        delay = delays.get(query_type, 0.05)
        await asyncio.sleep(delay)
        
        return {
            'query_type': query_type,
            'delay': delay,
            'records': 50 if query_type == 'fast' else 500,
            'timestamp': time.time()
        }
    
    # 中间件：将WSGI中间件适配到ASGI
    @app.middleware("http")
    async def performance_middleware(request: Request, call_next):
        """FastAPI性能监控中间件"""
        
        # 将ASGI请求转换为WSGI环境
        environ = {
            'REQUEST_METHOD': request.method,
            'PATH_INFO': request.url.path,
            'QUERY_STRING': str(request.url.query) if request.url.query else '',
            'SERVER_NAME': request.url.hostname or 'localhost',
            'SERVER_PORT': str(request.url.port or 80),
            'wsgi.url_scheme': request.url.scheme,
            'CONTENT_TYPE': request.headers.get('content-type', ''),
            'CONTENT_LENGTH': request.headers.get('content-length', '0'),
            'REMOTE_ADDR': request.client.host if request.client else '127.0.0.1',
        }
        
        # 添加HTTP头
        for name, value in request.headers.items():
            key = f'HTTP_{name.upper().replace("-", "_")}'
            environ[key] = value
        
        # 模拟WSGI输入流
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                body = await request.body()
                import io
                environ['wsgi.input'] = io.BytesIO(body)
                environ['CONTENT_LENGTH'] = str(len(body))
            except Exception:
                environ['wsgi.input'] = io.BytesIO(b'')
        
        # 提取请求信息
        request_info = monitor._extract_request_info(environ)
        
        # 开始监控
        profiler = None
        start_time = time.perf_counter()
        status_code = 200
        
        try:
            # 启动性能分析
            profiler = monitor.analyzer.start_profiling()
            
            # 执行请求
            response = await call_next(request)
            status_code = response.status_code
            
            return response
            
        except Exception as e:
            status_code = 500
            raise
        
        finally:
            # 完成监控处理
            monitor._finalize_request_monitoring(
                profiler, start_time, request_info, status_code
            )
    
    # 路由定义
    @app.get("/", response_model=Dict)
    async def root():
        """根路径 - 快速响应"""
        stats = monitor.get_stats()
        return {
            "message": "FastAPI性能监控示例",
            "framework": "FastAPI",
            "monitoring_stats": {
                "total_requests": stats.get('total_requests', 0),
                "slow_requests": stats.get('slow_requests', 0),
                "alerts_sent": stats.get('alerts_sent', 0),
                "monitoring_enabled": stats.get('monitoring_enabled', True)
            },
            "config": {
                "threshold": config.threshold_seconds,
                "alert_window": config.alert_window_days,
                "max_overhead": f"{config.max_performance_overhead * 100:.1f}%"
            }
        }
    
    @app.get("/api/users", response_model=List[User])
    async def get_users():
        """获取用户列表 - 快速响应"""
        return [
            User(id=1, name="Alice", email="alice@example.com"),
            User(id=2, name="Bob", email="bob@example.com"),
            User(id=3, name="Charlie", email="charlie@example.com")
        ]
    
    @app.post("/api/users", response_model=User)
    async def create_user(user: UserCreate):
        """创建用户 - 中等响应"""
        await asyncio.sleep(0.4)  # 模拟数据库操作
        return User(id=999, name=user.name, email=user.email)
    
    @app.get("/api/analytics", response_model=Dict)
    async def get_analytics():
        """获取分析数据 - 慢响应，会触发告警"""
        # 使用装饰器监控的异步函数
        result = await async_calculation(50000)
        
        # 额外延迟
        await asyncio.sleep(0.8)
        
        return {
            "analytics": {
                "calculation_result": result,
                "processing_time": "~0.8s",
                "status": "completed",
                "framework": "FastAPI"
            }
        }
    
    @app.post("/api/query", response_model=Dict)
    async def database_query(request: AnalyticsRequest):
        """数据库查询API"""
        # 使用装饰器监控的异步函数
        result = await database_query_simulation(request.query_type)
        
        return {
            "database_query": result,
            "request_parameters": request.parameters
        }
    
    @app.get("/api/reports", response_model=Dict)
    async def get_reports():
        """获取报告 - 接近阈值的响应"""
        await asyncio.sleep(0.45)  # 接近0.5秒阈值
        
        return {
            "reports": [
                {"id": 1, "name": "月度报告", "type": "monthly"},
                {"id": 2, "name": "季度分析", "type": "quarterly"},
                {"id": 3, "name": "年度总结", "type": "yearly"}
            ],
            "generated_at": time.time(),
            "count": 3
        }
    
    @app.get("/admin/stats", response_model=Dict)
    async def admin_stats():
        """管理员统计信息"""
        return monitor.get_stats()
    
    @app.post("/admin/test-alert", response_model=Dict)
    async def test_alert():
        """测试告警系统"""
        result = monitor.test_alert_system()
        return result
    
    @app.post("/admin/reset-stats", response_model=Dict)
    async def reset_stats():
        """重置统计信息"""
        monitor.reset_stats()
        return {"message": "统计信息已重置"}
    
    @app.post("/admin/toggle-monitoring", response_model=Dict)
    async def toggle_monitoring():
        """切换监控状态"""
        if monitor.is_monitoring_enabled():
            monitor.disable_monitoring()
            status = "disabled"
        else:
            monitor.enable_monitoring()
            status = "enabled"
        
        return {
            "message": f"监控已{status}",
            "monitoring_enabled": monitor.is_monitoring_enabled()
        }
    
    @app.post("/admin/cleanup", response_model=Dict)
    async def cleanup():
        """清理资源"""
        monitor.cleanup()
        return {"message": "资源清理完成"}
    
    # 后台任务示例
    @app.post("/api/background-task", response_model=Dict)
    async def create_background_task(background_tasks: BackgroundTasks):
        """创建后台任务"""
        
        @performance_monitor
        async def background_work():
            """后台工作函数"""
            await asyncio.sleep(2.0)  # 模拟长时间任务
            return "Background task completed"
        
        background_tasks.add_task(background_work)
        
        return {
            "message": "后台任务已创建",
            "task_type": "background",
            "estimated_duration": "2秒"
        }
    
    # 异常处理
    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=404,
            content={"error": "API端点不存在", "path": request.url.path}
        )
    
    @app.exception_handler(500)
    async def internal_error_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"error": "内部服务器错误", "detail": str(exc)}
        )
    
    # 健康检查
    @app.get("/health", response_model=Dict)
    async def health_check():
        """健康检查端点"""
        return {
            "status": "healthy",
            "framework": "FastAPI",
            "monitoring": monitor.is_monitoring_enabled(),
            "timestamp": time.time()
        }
    
    return app, monitor


def main():
    """主函数"""
    print("🚀 FastAPI性能监控示例启动")
    print("=" * 50)
    
    # 创建应用
    app, monitor = create_fastapi_app()
    
    # 确保报告目录存在
    os.makedirs("./fastapi_reports", exist_ok=True)
    
    print("📊 配置信息:")
    config_info = monitor.config.get_effective_config()
    for key, value in config_info.items():
        if key != 'mattermost_token':  # 不显示敏感信息
            print(f"  {key}: {value}")
    
    print("\n🌐 API端点:")
    print("  GET  /                     - 首页和统计")
    print("  GET  /api/users           - 用户列表（快速）")
    print("  POST /api/users           - 创建用户（中等）")
    print("  GET  /api/reports         - 报告列表（接近阈值）")
    print("  GET  /api/analytics       - 分析数据（慢，会告警）")
    print("  POST /api/query           - 数据库查询")
    print("  POST /api/background-task - 后台任务")
    print("  GET  /health              - 健康检查")
    print("  GET  /admin/stats         - 详细统计信息")
    print("  POST /admin/test-alert    - 测试告警系统")
    print("  POST /admin/cleanup       - 清理资源")
    print("  POST /admin/reset-stats   - 重置统计")
    print("  POST /admin/toggle-monitoring - 切换监控状态")
    print("  GET  /docs                - API文档（Swagger UI）")
    print("  GET  /redoc               - API文档（ReDoc）")
    
    print("\n📁 性能报告目录: ./fastapi_reports/")
    print("📖 API文档: http://localhost:8001/docs")
    print("\n按 Ctrl+C 停止服务器")
    print("=" * 50)
    
    # 启动服务器
    import uvicorn
    
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8001,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n\n🛑 服务器已停止")
        
        # 显示最终统计
        stats = monitor.get_stats()
        print("\n📊 最终统计:")
        print(f"  总请求: {stats.get('total_requests', 0)}")
        print(f"  慢请求: {stats.get('slow_requests', 0)}")
        print(f"  告警数: {stats.get('alerts_sent', 0)}")
        
        overhead_stats = stats.get('overhead_stats', {})
        if overhead_stats.get('sample_count', 0) > 0:
            avg_overhead = overhead_stats.get('average_overhead', 0) * 100
            print(f"  平均开销: {avg_overhead:.2f}%")
        
        # 清理
        monitor.cleanup()
        print("\n✅ 清理完成")


if __name__ == '__main__':
    main()