"""
Django集成示例

演示如何在Django项目中集成性能监控
"""

import django
from django.conf import settings
from django.core.wsgi import get_wsgi_application
from django.http import JsonResponse
from django.urls import path

# 配置Django设置
if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY='django-example-secret-key',
        ROOT_URLCONF=__name__,
        MIDDLEWARE=[],
        INSTALLED_APPS=[],
    )

# 初始化Django
django.setup()

# 导入性能监控
from web_performance_monitor import PerformanceMonitor, Config

# 配置性能监控
config = Config(
    threshold_seconds=0.5,
    enable_local_file=True,
    local_output_dir="./django_reports",
    enable_mattermost=False,
    log_level="INFO"
)

monitor = PerformanceMonitor(config)

# 创建性能装饰器
performance_monitor = monitor.create_decorator()


@performance_monitor  # 监控数据库查询函数
def get_user_data(user_id):
    """模拟数据库查询"""
    import time
    time.sleep(0.3)  # 模拟数据库查询时间
    return {
        "id": user_id,
        "name": f"User {user_id}",
        "email": f"user{user_id}@example.com"
    }


@performance_monitor  # 监控复杂计算任务
def complex_calculation(data):
    """模拟复杂计算"""
    import time
    time.sleep(0.8)  # 模拟复杂计算
    return {"result": sum(data)}


def index(request):
    """首页视图"""
    return JsonResponse({
        "message": "Django性能监控示例",
        "monitoring": "已启用",
        "framework": "Django"
    })


def slow_view(request):
    """慢响应视图"""
    import time
    time.sleep(1.2)  # 超过阈值，会触发告警
    return JsonResponse({
        "message": "这是一个慢响应视图",
        "delay": 1.2
    })


def user_view(request, user_id):
    """用户详情视图"""
    user_data = get_user_data(user_id)
    return JsonResponse(user_data)


def calculate_view(request):
    """计算视图"""
    numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    result = complex_calculation(numbers)
    return JsonResponse(result)


# URL配置
urlpatterns = [
    path('', index, name='index'),
    path('slow/', slow_view, name='slow_view'),
    path('user/<int:user_id>/', user_view, name='user_view'),
    path('calculate/', calculate_view, name='calculate_view'),
]

# WSGI应用
application = get_wsgi_application()

# 应用WSGI中间件
application = monitor.create_wsgi_middleware()(application)

if __name__ == "__main__":
    print("Django性能监控示例")
    print("支持的URL:")
    print("  http://localhost:8000/ - 首页")
    print("  http://localhost:8000/slow/ - 慢响应视图")
    print("  http://localhost:8000/user/123/ - 用户详情")
    print("  http://localhost:8000/calculate/ - 复杂计算")
    print("\n性能报告将保存在 ./django_reports/ 目录")

    # 运行开发服务器
    from django.core.management import execute_from_command_line

    execute_from_command_line(["manage.py", "runserver", "8000"])
