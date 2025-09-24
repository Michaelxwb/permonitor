"""
通用WSGI框架集成示例

演示如何在任意WSGI兼容框架中集成性能监控
包括Flask、Django、Pyramid、Bottle等
"""

import json
import time
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

# 导入性能监控
from web_performance_monitor import PerformanceMonitor, Config

# 配置性能监控
config = Config(
    threshold_seconds=0.5,
    enable_local_file=True,
    local_output_dir="./wsgi_reports",
    enable_mattermost=False,
    log_level="INFO"
)

monitor = PerformanceMonitor(config)

# 创建性能装饰器
performance_monitor = monitor.create_decorator()


@performance_monitor
def process_data(data):
    """处理数据"""
    time.sleep(0.3)  # 模拟处理时间
    return {"processed": data, "timestamp": time.time()}


@performance_monitor
def complex_calculation(numbers):
    """复杂计算"""
    time.sleep(0.8)  # 模拟复杂计算
    return {
        "sum": sum(numbers),
        "average": sum(numbers) / len(numbers) if numbers else 0,
        "max": max(numbers) if numbers else 0,
        "min": min(numbers) if numbers else 0
    }


def handle_request(environ, start_response):
    """处理WSGI请求"""
    path = environ.get('PATH_INFO', '/')
    method = environ.get('REQUEST_METHOD', 'GET')

    # 解析查询参数
    query_string = environ.get('QUERY_STRING', '')
    params = parse_qs(query_string)

    # 标准化参数（解析parse_qs返回的列表）
    normalized_params = {k: v[0] if len(v) == 1 else v for k, v in params.items()}

    try:
        if path == '/' and method == 'GET':
            response_data = {
                "message": "通用WSGI性能监控示例",
                "monitoring": "已启用",
                "framework": "WSGI通用",
                "path": path,
                "method": method,
                "params": normalized_params
            }
            status = '200 OK'

        elif path == '/slow' and method == 'GET':
            # 慢响应模拟
            delay = float(normalized_params.get('delay', [1.2])[0])
            time.sleep(delay)
            response_data = {
                "message": "慢响应端点",
                "delay": delay,
                "type": "synchronous"
            }
            status = '200 OK'

        elif path.startswith('/user/') and method == 'GET':
            # 用户详情
            user_id = path.split('/')[-1]
            user_data = process_data({"user_id": user_id, "name": f"User {user_id}"})
            response_data = user_data
            status = '200 OK'

        elif path == '/calculate' and method == 'POST':
            # 计算端点
            try:
                content_length = int(environ.get('CONTENT_LENGTH', 0))
                if content_length > 0:
                    request_body = environ['wsgi.input'].read(content_length)
                    request_data = json.loads(request_body.decode('utf-8'))
                    numbers = request_data.get('numbers', [1, 2, 3, 4, 5])
                else:
                    numbers = [1, 2, 3, 4, 5]

                result = complex_calculation(numbers)
                response_data = result
                status = '200 OK'
            except (json.JSONDecodeError, ValueError) as e:
                response_data = {"error": f"Invalid JSON: {str(e)}"}
                status = '400 Bad Request'

        elif path == '/health' and method == 'GET':
            response_data = {
                "status": "healthy",
                "timestamp": time.time()
            }
            status = '200 OK'

        elif path == '/stats' and method == 'GET':
            stats = monitor.get_stats()
            response_data = stats
            status = '200 OK'

        else:
            response_data = {"error": "Not Found", "path": path}
            status = '404 Not Found'

    except Exception as e:
        response_data = {"error": f"Internal Server Error: {str(e)}"}
        status = '500 Internal Server Error'

    # 设置响应头
    response_body = json.dumps(response_data, ensure_ascii=False, indent=2)
    response_headers = [
        ('Content-Type', 'application/json'),
        ('Content-Length', str(len(response_body.encode('utf-8'))))
    ]

    start_response(status, response_headers)
    return [response_body.encode('utf-8')]


def create_wsgi_app():
    """创建WSGI应用"""
    # 应用WSGI中间件
    wsgi_middleware = monitor.create_wsgi_middleware()
    return wsgi_middleware(handle_request)


def main():
    """主函数"""
    print("通用WSGI性能监控示例")
    print("支持的URL:")
    print("  http://localhost:8000/ - 首页")
    print("  http://localhost:8000/slow - 慢响应端点")
    print("  http://localhost:8000/slow?delay=2.0 - 自定义延迟")
    print("  http://localhost:8000/user/123 - 用户详情")
    print("  http://localhost:8000/calculate - 计算端点（POST）")
    print("  http://localhost:8000/health - 健康检查")
    print("  http://localhost:8000/stats - 监控统计")
    print("\n性能报告将保存在 ./wsgi_reports/ 目录")
    print("\n这个示例展示了如何在不依赖特定框架的情况下使用WSGI中间件")

    # 创建WSGI应用
    app = create_wsgi_app()

    # 启动服务器
    port = 8000
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
