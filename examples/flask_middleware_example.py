"""
Flask中间件使用示例

演示如何使用中间件模式自动监控所有HTTP请求
"""

import os
import time

from flask import Flask, request, jsonify

from web_performance_monitor import PerformanceMonitor, Config


def create_app():
    """创建Flask应用并配置性能监控"""
    app = Flask(__name__)

    # 配置性能监控
    config = Config(
        threshold_seconds=1.0,  # 1秒阈值
        alert_window_days=1,  # 1天重复告警窗口（用于演示）
        enable_local_file=True,  # 启用本地文件通知
        local_output_dir="../reports/performance_reports",  # 输出到当前目录
        enable_mattermost=False,  # 禁用Mattermost（演示用）
        log_level="INFO"
    )

    # 创建性能监控器
    monitor = PerformanceMonitor(config)

    # 应用中间件 - 零入侵集成
    app.wsgi_app = monitor.create_middleware()(app.wsgi_app)

    # 定义路由
    @app.route('/')
    def index():
        """首页"""
        return jsonify({
            "message": "Web性能监控演示应用",
            "endpoints": [
                "/fast - 快速响应端点",
                "/slow - 慢响应端点（会触发告警）",
                "/variable/<seconds> - 可变延迟端点",
                "/stats - 监控统计信息",
                "/test-alert - 测试告警系统"
            ]
        })

    @app.route('/fast')
    def fast_endpoint():
        """快速响应端点"""
        return jsonify({
            "message": "快速响应",
            "response_time": "< 0.1s",
            "status": "正常"
        })

    @app.route('/slow')
    def slow_endpoint():
        """慢响应端点 - 会触发告警"""
        time.sleep(2.0)  # 模拟慢操作
        return jsonify({
            "message": "慢响应完成",
            "response_time": "~2s",
            "status": "超过阈值，应该触发告警"
        })

    @app.route('/variable/<float:seconds>')
    def variable_delay_endpoint(seconds):
        """可变延迟端点"""
        # 限制延迟时间
        delay = min(max(seconds, 0), 10)
        time.sleep(delay)

        will_alert = delay > config.threshold_seconds

        return jsonify({
            "message": f"延迟 {delay} 秒完成",
            "delay_seconds": delay,
            "threshold": config.threshold_seconds,
            "will_alert": will_alert,
            "status": "会触发告警" if will_alert else "正常"
        })

    @app.route('/stats')
    def get_stats():
        """获取监控统计信息"""
        stats = monitor.get_stats()
        return jsonify(stats)

    @app.route('/test-alert')
    def test_alert():
        """测试告警系统"""
        result = monitor.test_alert_system()
        return jsonify(result)

    @app.route('/enable-monitoring')
    def enable_monitoring():
        """启用监控"""
        monitor.enable_monitoring()
        return jsonify({"message": "监控已启用", "enabled": True})

    @app.route('/disable-monitoring')
    def disable_monitoring():
        """禁用监控"""
        monitor.disable_monitoring()
        return jsonify({"message": "监控已禁用", "enabled": False})

    @app.route('/reset-stats')
    def reset_stats():
        """重置统计信息"""
        monitor.reset_stats()
        return jsonify({"message": "统计信息已重置"})

    @app.route('/cleanup')
    def cleanup():
        """清理资源"""
        monitor.cleanup()
        return jsonify({"message": "资源清理完成"})

    # 错误处理
    @app.errorhandler(404)
    def not_found(error):
        """404错误处理"""
        return jsonify({"error": "端点不存在", "code": 404}), 404

    @app.errorhandler(500)
    def internal_error(error):
        """500错误处理"""
        return jsonify({"error": "内部服务器错误", "code": 500}), 500

    # 添加请求前后钩子用于演示
    @app.before_request
    def before_request():
        """请求前钩子"""
        request.start_time = time.time()

    @app.after_request
    def after_request(response):
        """请求后钩子"""
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            response.headers['X-Response-Time'] = f"{duration:.3f}s"
        return response

    return app, monitor


def main():
    """主函数"""
    print("🚀 启动Web性能监控演示应用")
    print("=" * 50)

    # 创建应用
    app, monitor = create_app()

    # 确保输出目录存在
    os.makedirs("./performance_reports", exist_ok=True)

    print("📊 监控配置:")
    config_info = monitor.config.get_effective_config()
    for key, value in config_info.items():
        print(f"  {key}: {value}")

    print("\n🌐 可用端点:")
    print("  http://localhost:5000/          - 首页")
    print("  http://localhost:5000/fast      - 快速响应（不会告警）")
    print("  http://localhost:5000/slow      - 慢响应（会触发告警）")
    print("  http://localhost:5000/variable/1.5 - 1.5秒延迟（会告警）")
    print("  http://localhost:5000/stats     - 监控统计")
    print("  http://localhost:5000/test-alert - 测试告警")

    print("\n📁 性能报告将保存到: ./performance_reports/")
    print("\n按 Ctrl+C 停止服务器")
    print("=" * 50)

    try:
        # 启动Flask应用
        app.run(
            host='0.0.0.0',
            port=5001,
            debug=False,  # 生产环境应该关闭debug
            threaded=True
        )
    except KeyboardInterrupt:
        print("\n\n🛑 服务器已停止")

        # 显示最终统计
        print("\n📊 最终统计信息:")
        stats = monitor.get_stats()
        print(f"  总请求数: {stats.get('total_requests', 0)}")
        print(f"  慢请求数: {stats.get('slow_requests', 0)}")
        print(f"  告警发送数: {stats.get('alerts_sent', 0)}")
        print(f"  慢请求率: {stats.get('slow_request_rate', 0):.2f}%")

        overhead_stats = stats.get('overhead_stats', {})
        if overhead_stats.get('sample_count', 0) > 0:
            print(
                f"  平均性能开销: {overhead_stats.get('average_overhead', 0) * 100:.2f}%")

        # 清理资源
        monitor.cleanup()
        print("\n✅ 资源清理完成")


if __name__ == '__main__':
    main()
