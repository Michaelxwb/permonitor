"""
Pyramid集成示例

演示如何在Pyramid项目中集成性能监控
"""

from pyramid.config import Configurator
from pyramid.response import Response
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPNotFound
import json
from datetime import datetime

# 导入性能监控
from web_performance_monitor import PerformanceMonitor, Config

# 配置性能监控
config = Config(
    threshold_seconds=0.5,
    enable_local_file=True,
    local_output_dir="./pyramid_reports",
    enable_mattermost=False,
    log_level="INFO"
)

monitor = PerformanceMonitor(config)

# 创建性能装饰器
performance_monitor = monitor.create_decorator()


@performance_monitor
def query_user_data(user_id):
    """模拟数据库查询"""
    import time
    time.sleep(0.3)  # 模拟数据库查询时间
    return {
        "id": user_id,
        "name": f"User {user_id}",
        "email": f"user{user_id}@example.com",
        "created_at": datetime.now().isoformat()
    }


@performance_monitor
def process_complex_data(data):
    """处理复杂数据"""
    import time
    time.sleep(0.7)  # 模拟复杂计算
    return {
        "sum": sum(data),
        "average": sum(data) / len(data) if data else 0,
        "max": max(data) if data else 0,
        "min": min(data) if data else 0,
        "count": len(data)
    }


# Pyramid视图函数
@view_config(route_name='index', renderer='json')
def index_view(request):
    """首页视图"""
    return {
        "message": "Pyramid性能监控示例",
        "monitoring": "已启用",
        "framework": "Pyramid",
        "version": "2.0"
    }


@view_config(route_name='slow', renderer='json')
def slow_view(request):
    """慢响应视图"""
    import time
    time.sleep(1.2)  # 超过阈值，会触发告警
    return {
        "message": "这是一个慢响应视图",
        "delay": 1.2
    }


@view_config(route_name='user', renderer='json')
def user_view(request):
    """用户详情视图"""
    user_id = int(request.matchdict['user_id'])
    try:
        user_data = query_user_data(user_id)
        return user_data
    except Exception as e:
        return Response(
            json.dumps({"error": str(e)}),
            content_type='application/json',
            status=500
        )


@view_config(route_name='calculate', renderer='json', request_method='POST')
def calculate_view(request):
    """计算视图"""
    try:
        data = request.json_body
        numbers = data.get('numbers', [1, 2, 3, 4, 5])
        result = process_complex_data(numbers)
        return result
    except Exception as e:
        return Response(
            json.dumps({"error": str(e)}),
            content_type='application/json',
            status=500
        )


@view_config(route_name='health', renderer='json')
def health_view(request):
    """健康检查视图"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@view_config(route_name='stats', renderer='json')
def stats_view(request):
    """统计视图"""
    stats = monitor.get_stats()
    return stats


# 自定义中间件
class PerformanceMonitoringMiddleware:
    """性能监控中间件"""
    
    def __init__(self, app):
        self.app = app
    
    def __call__(self, environ, start_response):
        """WSGI中间件实现"""
        # 使用WSGI中间件
        wsgi_middleware = monitor.create_wsgi_middleware()
        return wsgi_middleware(self.app)(environ, start_response)


def create_wsgi_app():
    """创建WSGI应用"""
    # 配置Pyramid
    config = Configurator()
    
    # 添加路由
    config.add_route('index', '/')
    config.add_route('slow', '/slow')
    config.add_route('user', '/user/{user_id}')
    config.add_route('calculate', '/calculate')
    config.add_route('health', '/health')
    config.add_route('stats', '/stats')
    
    # 扫描视图（装饰器方式）
    config.scan()
    
    # 创建WSGI应用
    app = config.make_wsgi_app()
    
    # 应用性能监控中间件
    app = PerformanceMonitoringMiddleware(app)
    
    return app


def main():
    """主函数"""
    print("Pyramid性能监控示例")
    print("支持的URL:")
    print("  http://localhost:6543/ - 首页")
    print("  http://localhost:6543/slow - 慢响应视图")
    print("  http://localhost:6543/user/123 - 用户详情")
    print("  http://localhost:6543/calculate - 计算端点（POST）")
    print("  http://localhost:6543/health - 健康检查")
    print("  http://localhost:6543/stats - 监控统计")
    print("\n性能报告将保存在 ./pyramid_reports/ 目录")
    
    # 创建应用
    app = create_wsgi_app()
    
    # 启动服务器
    from wsgiref.simple_server import make_server
    port = 6543
    server = make_server('0.0.0.0', port, app)
    
    print(f"\n服务器启动在 http://localhost:{port}")
    print("按 Ctrl+C 停止服务器")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止")
        server.shutdown()


if __name__ == "__main__":
    main()