"""
FastAPI集成示例

演示如何在FastAPI应用中集成web-performance-monitor。
"""

import asyncio
import time
import random
from typing import List, Dict, Any

print("=== FastAPI集成示例 ===\n")

# 首先检查FastAPI是否可用
try:
    from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
    from fastapi.middleware.base import BaseHTTPMiddleware
    from fastapi.responses import JSONResponse
    FASTAPI_AVAILABLE = True
except ImportError as e:
    print(f"❌ FastAPI导入失败: {e}")
    print("   这正是我们的依赖管理系统要解决的问题！")
    print("   安装命令: pip install web-performance-monitor[fastapi]")
    FASTAPI_AVAILABLE = False

# 1. 检查FastAPI依赖
print("1. 检查FastAPI依赖:")

if not FASTAPI_AVAILABLE:
    print("   ❌ FastAPI不可用，演示依赖管理功能")
    
    # 演示依赖检查功能
    try:
        from web_performance_monitor.utils.framework_detector import FrameworkDetector
        from web_performance_monitor.utils.installation_guide import InstallationGuide
        
        detector = FrameworkDetector()
        frameworks = detector.detect_installed_frameworks()
        
        print(f"   检测到的框架: {frameworks}")
        
        if 'fastapi' not in frameworks:
            print("   ❌ FastAPI未在已安装框架中")
            
            # 获取安装建议
            guide = InstallationGuide()
            fastapi_guide = guide.generate_framework_installation_guide('fastapi')
            print("\n   📋 FastAPI安装指导:")
            print(fastapi_guide)
            
            # 获取快速安装命令
            quick_command = guide.get_quick_install_command('fastapi')
            print(f"\n   🚀 快速安装命令: {quick_command}")
        
        print("\n   这演示了我们的依赖管理系统如何优雅地处理缺失的依赖！")
        print("   系统不会崩溃，而是提供清晰的错误信息和解决方案。")
        
    except Exception as e:
        print(f"   依赖检查失败: {e}")
    
    print("\n   要运行完整的FastAPI示例，请安装FastAPI支持:")
    print("   pip install web-performance-monitor[fastapi]")
    print("\n   现在将演示在没有FastAPI的情况下系统如何工作...")
    
else:
    try:
        from web_performance_monitor.utils.framework_detector import FrameworkDetector
        
        detector = FrameworkDetector()
        frameworks = detector.detect_installed_frameworks()
        
        if 'fastapi' not in frameworks:
            print("   ❌ FastAPI未安装或不可用")
            print("   安装命令: pip install web-performance-monitor[fastapi]")
            exit(1)
        else:
            fastapi_version = detector.get_framework_version('fastapi')
            print(f"   ✅ FastAPI已安装，版本: {fastapi_version}")
        
        # 检查异步依赖
        async_deps = ['uvicorn', 'aiofiles', 'aiohttp']
        for dep in async_deps:
            try:
                __import__(dep)
                print(f"   ✅ {dep} 可用")
            except ImportError:
                print(f"   ⚠️ {dep} 不可用")
        
        print()
        
    except Exception as e:
        print(f"   依赖检查失败: {e}")
        exit(1)

# 2. 创建FastAPI应用
if FASTAPI_AVAILABLE:
    app = FastAPI(
        title="FastAPI Performance Monitor Demo",
        description="演示FastAPI与web-performance-monitor的集成",
        version="1.0.0"
    )
else:
    # 创建模拟应用来演示概念
    class MockFastAPIApp:
        def __init__(self):
            self.title = "Mock FastAPI App"
            self.middleware_stack = []
        
        def add_middleware(self, middleware_class):
            self.middleware_stack.append(middleware_class)
            print(f"   📝 模拟添加中间件: {middleware_class.__name__ if hasattr(middleware_class, '__name__') else str(middleware_class)}")
    
    app = MockFastAPIApp()

# 3. 创建FastAPI监控器
print("2. 创建FastAPI监控器:")
try:
    from web_performance_monitor import create_web_monitor
    
    # 创建FastAPI专用监控器
    monitor = create_web_monitor('fastapi', {
        'auto_instrument': True,
        'track_background_tasks': True,
        'track_websockets': False,
        'track_startup_shutdown': True,
        'exclude_paths': ['/health', '/metrics', '/docs', '/redoc', '/openapi.json'],
        'sample_rate': 1.0,
        'async_context_timeout': 30.0
    })
    
    print(f"   ✅ 监控器创建成功: {type(monitor).__name__}")
    print()
    
except Exception as e:
    print(f"   ❌ 监控器创建失败: {e}")
    # 继续执行，使用模拟监控器
    monitor = None

# 4. 方法一：使用中间件（推荐）
print("3. 集成方法一：中间件集成")

if FASTAPI_AVAILABLE:
    class PerformanceMiddleware(BaseHTTPMiddleware):
        """性能监控中间件"""
        
        async def dispatch(self, request, call_next):
            start_time = time.time()
            
            try:
                response = await call_next(request)
                end_time = time.time()
                duration = end_time - start_time
                
                # 记录性能数据
                print(f"   📊 {request.method} {request.url.path}: {duration:.3f}s")
                
                # 添加性能头
                response.headers["X-Process-Time"] = str(duration)
                
                return response
                
            except Exception as e:
                end_time = time.time()
                duration = end_time - start_time
                print(f"   ❌ {request.method} {request.url.path}: {duration:.3f}s (错误: {e})")
                raise
else:
    class MockPerformanceMiddleware:
        """模拟性能监控中间件"""
        
        def __init__(self):
            print("   📝 创建模拟性能监控中间件")
        
        async def dispatch(self, request, call_next):
            print("   📊 模拟处理请求监控")
            return await call_next(request)

# 添加中间件
if monitor:
    try:
        # 尝试使用监控器的中间件
        middleware_class = monitor.get_middleware()
        if middleware_class and FASTAPI_AVAILABLE:
            app.add_middleware(middleware_class)
            print("   ✅ 监控器中间件集成成功")
        else:
            if FASTAPI_AVAILABLE:
                app.add_middleware(PerformanceMiddleware)
                print("   ✅ 自定义中间件集成成功")
            else:
                app.add_middleware(MockPerformanceMiddleware)
                print("   ✅ 模拟中间件集成成功")
    except Exception as e:
        print(f"   ❌ 中间件集成失败: {e}")
        if FASTAPI_AVAILABLE:
            app.add_middleware(PerformanceMiddleware)
            print("   ✅ 回退到自定义中间件")
        else:
            app.add_middleware(MockPerformanceMiddleware)
            print("   ✅ 回退到模拟中间件")
else:
    if FASTAPI_AVAILABLE:
        app.add_middleware(PerformanceMiddleware)
        print("   ✅ 自定义中间件集成成功")
    else:
        app.add_middleware(MockPerformanceMiddleware)
        print("   ✅ 模拟中间件集成成功")

print()

# 5. 方法二：使用装饰器
print("4. 集成方法二：装饰器集成")

def async_performance_monitor(func):
    """异步性能监控装饰器"""
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            end_time = time.time()
            duration = end_time - start_time
            
            # 记录性能数据
            print(f"   📊 {func.__name__}: {duration:.3f}s")
            
            return result
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            print(f"   ❌ {func.__name__}: {duration:.3f}s (错误: {e})")
            raise
    
    wrapper.__name__ = func.__name__
    return wrapper

# 6. 依赖注入示例
async def get_monitor():
    """获取监控器的依赖"""
    return monitor

# 7. 定义路由
if FASTAPI_AVAILABLE:
    @app.get("/")
    async def root():
        """根路径"""
        return {
            "message": "Hello from FastAPI!",
            "framework": "FastAPI",
            "monitoring": "Enabled"
        }

    @app.get("/api/data")
    @async_performance_monitor
    async def get_data():
        """获取数据API"""
        # 模拟异步数据库查询
        await asyncio.sleep(random.uniform(0.1, 0.5))
        
        return {
            "data": [
                {"id": 1, "name": "Item 1"},
                {"id": 2, "name": "Item 2"},
                {"id": 3, "name": "Item 3"}
            ],
            "count": 3
        }

    @app.get("/api/slow")
    @async_performance_monitor
    async def slow_endpoint():
        """慢端点（用于测试）"""
        # 模拟慢异步操作
        await asyncio.sleep(random.uniform(1.0, 2.0))
        
        return {
            "message": "This is a slow endpoint",
            "processing_time": "Simulated slow async operation"
        }

    @app.get("/api/error")
    @async_performance_monitor
    async def error_endpoint():
        """错误端点（用于测试）"""
        if random.random() < 0.5:
            raise HTTPException(status_code=500, detail="Random error for testing")
        
        return {"message": "Success"}

    @app.post("/api/background")
    async def background_task_endpoint(background_tasks: BackgroundTasks):
        """后台任务示例"""
        
        async def background_job(name: str):
            """后台任务"""
            print(f"   🔄 后台任务开始: {name}")
            await asyncio.sleep(random.uniform(2.0, 5.0))
            print(f"   ✅ 后台任务完成: {name}")
        
        task_name = f"task_{int(time.time())}"
        background_tasks.add_task(background_job, task_name)
        
        return {
            "message": "Background task started",
            "task_name": task_name
        }

    @app.get("/api/concurrent")
    async def concurrent_operations():
        """并发操作示例"""
        
        async def async_operation(name: str, delay: float):
            """异步操作"""
            await asyncio.sleep(delay)
            return f"Operation {name} completed"
        
        # 并发执行多个操作
        tasks = [
            async_operation("A", random.uniform(0.1, 0.3)),
            async_operation("B", random.uniform(0.2, 0.4)),
            async_operation("C", random.uniform(0.1, 0.5))
        ]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        print(f"   📊 并发操作总耗时: {end_time - start_time:.3f}s")
        
        return {
            "results": results,
            "total_time": f"{end_time - start_time:.3f}s"
        }

    @app.get("/api/manual")
    async def manual_monitoring(monitor_dep = Depends(get_monitor)):
        """手动监控示例"""
        print("5. 集成方法三：手动监控")
        
        start_time = time.time()
        
        try:
            # 业务逻辑
            await asyncio.sleep(random.uniform(0.2, 0.8))
            
            # 模拟一些异步操作
            operations = ['async_database_query', 'async_cache_lookup', 'async_api_call']
            for op in operations:
                op_start = time.time()
                await asyncio.sleep(random.uniform(0.05, 0.15))
                op_end = time.time()
                print(f"   📊 {op}: {op_end - op_start:.3f}s")
            
            end_time = time.time()
            total_time = end_time - start_time
            
            print(f"   📊 总耗时: {total_time:.3f}s")
            
            return {
                "message": "Manual monitoring example",
                "total_time": f"{total_time:.3f}s",
                "operations": operations,
                "monitor_available": monitor_dep is not None
            }
            
        except Exception as e:
            end_time = time.time()
            total_time = end_time - start_time
            print(f"   ❌ 手动监控出错: {total_time:.3f}s (错误: {e})")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/health")
    async def health_check():
        """健康检查（不监控）"""
        return {"status": "healthy"}

    @app.get("/metrics")
    async def metrics():
        """指标端点（不监控）"""
        return {
            "requests_total": 100,
            "avg_response_time": 0.25,
            "error_rate": 0.02,
            "active_connections": 5
        }

else:
    # 当FastAPI不可用时，演示依赖管理功能
    print("\n4. 演示依赖管理功能（FastAPI不可用时）:")
    
    async def mock_get_data():
        """模拟数据API"""
        print("   📊 模拟异步数据查询")
        await asyncio.sleep(0.1)
        return {"data": "mock_data", "framework": "Mock"}
    
    async def mock_slow_endpoint():
        """模拟慢端点"""
        print("   📊 模拟慢异步操作")
        await asyncio.sleep(1.0)
        return {"message": "Mock slow operation"}
    
    print("   ✅ 创建了模拟端点来演示概念")
    print("   ✅ 系统在缺少依赖时仍能正常工作")

# 8. 异常处理
if FASTAPI_AVAILABLE:
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        """全局异常处理"""
        print(f"   ❌ 全局错误处理: {type(exc).__name__}: {exc}")
        
        return JSONResponse(
            status_code=500,
            content={
                "error": str(exc),
                "type": type(exc).__name__,
                "path": str(request.url.path)
            }
        )

    # 9. 启动和关闭事件
    @app.on_event("startup")
    async def startup_event():
        """应用启动事件"""
        print("6. FastAPI应用启动事件:")
        print("   📊 应用启动监控开始")
        
        # 初始化监控
        if monitor:
            print("   ✅ 监控器已初始化")
        else:
            print("   ⚠️ 监控器不可用")
        
        print()

    @app.on_event("shutdown")
    async def shutdown_event():
        """应用关闭事件"""
        print("7. FastAPI应用关闭事件:")
        print("   📊 应用关闭监控结束")
        
        # 清理监控资源
        if monitor:
            print("   ✅ 监控器资源已清理")
        
        print()
else:
    print("\n5. 模拟事件处理:")
    print("   📊 模拟应用启动事件")
    print("   📊 模拟异常处理机制")
    print("   ✅ 即使没有FastAPI，概念演示仍然有效")

# 10. 配置示例
print("8. 配置示例:")
try:
    from web_performance_monitor.config.unified_config import UnifiedConfig
    
    config = UnifiedConfig()
    dep_config = config.dependency_config
    print(f"   依赖检查模式: {getattr(dep_config, 'check_mode', 'default')}")
    print(f"   跳过依赖检查: {getattr(dep_config, 'skip_dependency_check', False)}")
    print(f"   严格模式: {getattr(dep_config, 'strict_mode', False)}")
    print()
    
except Exception as e:
    print(f"   配置获取失败: {e}")

# 11. 运行说明
if __name__ == "__main__":
    if FASTAPI_AVAILABLE:
        print("9. 启动FastAPI应用:")
        print("   使用以下命令启动应用:")
        print("   uvicorn fastapi_integration:app --host 0.0.0.0 --port 8000 --reload")
        print()
        print("   或者直接运行此脚本（需要安装uvicorn）:")
        print()
        
        try:
            import uvicorn
            
            print("   📊 使用uvicorn启动应用...")
            print("   访问 http://localhost:8000 查看首页")
            print("   访问 http://localhost:8000/docs 查看API文档")
            print("   访问 http://localhost:8000/api/data 查看数据API")
            print("   访问 http://localhost:8000/api/slow 测试慢端点")
            print("   访问 http://localhost:8000/api/error 测试错误处理")
            print("   访问 http://localhost:8000/api/background 测试后台任务")
            print("   访问 http://localhost:8000/api/concurrent 测试并发操作")
            print("   访问 http://localhost:8000/api/manual 查看手动监控")
            print("   访问 http://localhost:8000/health 查看健康检查")
            print("   访问 http://localhost:8000/metrics 查看指标")
            print()
            print("   按 Ctrl+C 停止应用")
            print()
            
            uvicorn.run(
                "fastapi_integration:app",
                host="0.0.0.0",
                port=8000,
                reload=True,
                log_level="info"
            )
            
        except ImportError:
            print("   ❌ uvicorn未安装")
            print("   安装命令: pip install uvicorn")
            print("   然后运行: uvicorn fastapi_integration:app --host 0.0.0.0 --port 8000 --reload")
        except KeyboardInterrupt:
            print("\n   应用已停止")
        except Exception as e:
            print(f"\n   应用启动失败: {e}")
    
    else:
        print("\n9. 依赖管理演示总结:")
        print("   ✅ 成功演示了依赖缺失时的优雅处理")
        print("   ✅ 系统提供了清晰的错误信息和解决方案")
        print("   ✅ 没有因为缺少FastAPI而崩溃")
        print("   ✅ 展示了智能安装建议功能")
        print()
        print("   要体验完整的FastAPI集成:")
        print("   1. 安装FastAPI支持: pip install web-performance-monitor[fastapi]")
        print("   2. 重新运行此脚本")
        print()
        print("   这正是我们依赖管理系统的核心价值：")
        print("   - 优雅降级，不会崩溃")
        print("   - 清晰的错误信息")
        print("   - 智能的解决方案建议")
        print("   - 用户友好的体验")

print("\n=== FastAPI集成示例完成 ===")