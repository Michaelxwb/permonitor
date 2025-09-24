"""
Tornado集成示例

演示如何在Tornado项目中集成性能监控
"""

import json
from datetime import datetime

import tornado.gen
import tornado.ioloop
import tornado.web

# 导入性能监控
from web_performance_monitor import PerformanceMonitor, Config

# 配置性能监控
config = Config(
    threshold_seconds=0.5,
    enable_local_file=True,
    local_output_dir="./tornado_reports",
    enable_mattermost=False,
    log_level="INFO"
)

monitor = PerformanceMonitor(config)

# 创建性能装饰器
performance_monitor = monitor.create_decorator()


@performance_monitor
def query_database(user_id):
    """模拟数据库查询"""
    import time
    time.sleep(0.4)  # 模拟数据库查询时间
    return {
        "id": user_id,
        "name": f"User {user_id}",
        "email": f"user{user_id}@example.com",
        "created_at": datetime.now().isoformat()
    }


@performance_monitor
def complex_calculation(data):
    """模拟复杂计算"""
    import time
    time.sleep(0.9)  # 模拟复杂计算
    return {
        "sum": sum(data),
        "average": sum(data) / len(data) if data else 0,
        "max": max(data) if data else 0,
        "min": min(data) if data else 0
    }


class BaseHandler(tornado.web.RequestHandler):
    """基础处理器"""

    def prepare(self):
        """请求预处理"""
        self.start_time = tornado.util.time_func()

    def on_finish(self):
        """请求后处理"""
        if hasattr(self, 'start_time'):
            execution_time = tornado.util.time_func() - self.start_time
            # 这里可以添加额外的监控逻辑
            if execution_time > monitor.config.threshold_seconds:
                self.application.monitor.logger.info(
                    f"慢请求检测: {self.request.method} {self.request.path} "
                    f"({execution_time:.2f}s)"
                )


class MainHandler(BaseHandler):
    """主页处理器"""

    def get(self):
        """GET请求处理"""
        self.write({
            "message": "Tornado性能监控示例",
            "monitoring": "已启用",
            "framework": "Tornado",
            "version": tornado.version
        })


class SlowHandler(BaseHandler):
    """慢响应处理器"""

    @tornado.gen.coroutine
    def get(self):
        """异步慢响应处理"""
        yield tornado.gen.sleep(1.2)  # 超过阈值，会触发告警
        self.write({
            "message": "这是一个慢响应端点",
            "delay": 1.2,
            "type": "async"
        })


class UserHandler(BaseHandler):
    """用户处理器"""

    def get(self, user_id):
        """获取用户信息"""
        try:
            user_data = query_database(int(user_id))
            self.write(user_data)
        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})


class CalculateHandler(BaseHandler):
    """计算处理器"""

    def post(self):
        """处理计算请求"""
        try:
            data = json.loads(self.request.body)
            numbers = data.get('numbers', [1, 2, 3, 4, 5])
            result = complex_calculation(numbers)
            self.write(result)
        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})


class HealthHandler(BaseHandler):
    """健康检查处理器"""

    def get(self):
        """健康检查"""
        self.write({"status": "healthy", "timestamp": datetime.now().isoformat()})


class StatsHandler(BaseHandler):
    """统计处理器"""

    def get(self):
        """获取监控统计"""
        stats = monitor.get_stats()
        self.write(stats)


# Tornado应用配置
class TornadoApplication(tornado.web.Application):
    """Tornado应用类"""

    def __init__(self):
        handlers = [
            (r"/", MainHandler),
            (r"/slow", SlowHandler),
            (r"/user/([0-9]+)", UserHandler),
            (r"/calculate", CalculateHandler),
            (r"/health", HealthHandler),
            (r"/stats", StatsHandler),
        ]

        settings = {
            "debug": True,
            "autoreload": True,
        }

        super().__init__(handlers, **settings)
        self.monitor = monitor


def make_app():
    """创建Tornado应用"""
    return TornadoApplication()


if __name__ == "__main__":
    print("Tornado性能监控示例")
    print("支持的URL:")
    print("  http://localhost:8888/ - 首页")
    print("  http://localhost:8888/slow - 慢响应端点")
    print("  http://localhost:8888/user/123 - 用户详情")
    print("  http://localhost:8888/calculate - 计算端点（POST）")
    print("  http://localhost:8888/health - 健康检查")
    print("  http://localhost:8888/stats - 监控统计")
    print("\n性能报告将保存在 ./tornado_reports/ 目录")

    # 创建应用
    app = make_app()

    # 启动服务器
    port = 8888
    app.listen(port)
    print(f"\n服务器启动在 http://localhost:{port}")
    print("按 Ctrl+C 停止服务器")

    try:
        tornado.ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        print("\n服务器已停止")
