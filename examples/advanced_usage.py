"""
高级用法示例

演示Web性能监控工具的高级功能
"""

import os
import time
from flask import Flask, jsonify, request
from web_performance_monitor import PerformanceMonitor, Config


def create_advanced_app():
    """创建高级配置的Flask应用"""
    app = Flask(__name__)

    # 高级配置
    config = Config(
        # 性能配置
        threshold_seconds=0.8,  # 更严格的阈值
        alert_window_days=7,  # 7天重复告警窗口
        max_performance_overhead=0.03,  # 3%性能开销限制

        # 本地文件通知
        enable_local_file=True,
        local_output_dir="../reports/advanced_reports",

        # Mattermost通知（如果配置了环境变量）
        enable_mattermost=bool(os.getenv('MATTERMOST_SERVER_URL')),
        mattermost_server_url=os.getenv('MATTERMOST_SERVER_URL', ''),
        mattermost_token=os.getenv('MATTERMOST_TOKEN', ''),
        mattermost_channel_id=os.getenv('MATTERMOST_CHANNEL_ID', ''),
        mattermost_max_retries=5,

        # 日志配置
        log_level="DEBUG",
        enable_url_whitelist=True,
        url_whitelist=["/api/analytics"]
    )

    # 创建监控器
    monitor = PerformanceMonitor(config)

    # 应用中间件
    app.wsgi_app = monitor.create_middleware()(app.wsgi_app)

    # 创建装饰器
    performance_monitor = monitor.create_decorator()

    # 业务函数示例
    @performance_monitor
    def complex_calculation(n: int) -> float:
        """复杂计算函数"""
        result = 0
        for i in range(n):
            result += i ** 0.5
        return result

    @performance_monitor
    def database_simulation(query_type: str) -> dict:
        """数据库查询模拟"""
        delays = {
            'fast': 0.1,
            'medium': 0.5,
            'slow': 1.2
        }

        delay = delays.get(query_type, 0.1)
        time.sleep(delay)

        return {
            'query_type': query_type,
            'delay': delay,
            'records': 100 if query_type == 'fast' else 1000
        }

    # 路由定义
    @app.route('/')
    def index():
        """首页"""
        stats = monitor.get_stats()
        return jsonify({
            "message": "高级用法示例",
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
        })

    @app.route('/api/users')
    def get_users():
        """用户API - 快速响应"""
        return jsonify({
            "users": [
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"}
            ],
            "count": 2
        })

    @app.route('/api/reports')
    def get_reports():
        """报告API - 中等响应"""
        time.sleep(0.6)  # 接近阈值
        return jsonify({
            "reports": ["report1", "report2", "report3"],
            "generated_at": time.time()
        })

    @app.route('/api/analytics')
    def get_analytics():
        """分析API - 慢响应"""
        # 使用装饰器监控的函数
        result = complex_calculation(100000)

        time.sleep(1.0)  # 超过阈值

        return jsonify({
            "analytics": {
                "calculation_result": result,
                "processing_time": "~1.6s",
                "status": "completed"
            }
        })

    @app.route('/api/database/<query_type>')
    def database_query(query_type):
        """数据库查询API"""
        # 使用装饰器监控的函数
        result = database_simulation(query_type)

        return jsonify({
            "database_query": result,
            "query_type": query_type
        })

    @app.route('/admin/stats')
    def admin_stats():
        """管理员统计信息"""
        stats = monitor.get_stats()
        return jsonify(stats)

    @app.route('/admin/test-alert')
    def test_alert():
        """测试告警系统"""
        result = monitor.test_alert_system()
        return jsonify(result)

    @app.route('/admin/cleanup')
    def cleanup():
        """清理资源"""
        monitor.cleanup()
        return jsonify({"message": "资源清理完成"})

    @app.route('/admin/reset-stats')
    def reset_stats():
        """重置统计信息"""
        monitor.reset_stats()
        return jsonify({"message": "统计信息已重置"})

    @app.route('/admin/toggle-monitoring')
    def toggle_monitoring():
        """切换监控状态"""
        if monitor.is_monitoring_enabled():
            monitor.disable_monitoring()
            status = "disabled"
        else:
            monitor.enable_monitoring()
            status = "enabled"

        return jsonify({
            "message": f"监控已{status}",
            "monitoring_enabled": monitor.is_monitoring_enabled()
        })

    # 错误处理
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "API端点不存在"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({"error": "内部服务器错误"}), 500

    # 请求钩子
    @app.before_request
    def log_request_info():
        """记录请求信息"""
        app.logger.info(f"Request: {request.method} {request.path}")

    return app, monitor


def main():
    """主函数"""
    print("🚀 高级用法示例启动")
    print("=" * 50)

    # 创建应用
    app, monitor = create_advanced_app()

    # 确保报告目录存在
    os.makedirs("../reports/advanced_reports", exist_ok=True)

    print("📊 配置信息:")
    config_info = monitor.config.get_effective_config()
    for key, value in config_info.items():
        if key != 'mattermost_token':  # 不显示敏感信息
            print(f"  {key}: {value}")

    print("\n🌐 API端点:")
    print("  GET  /                     - 首页和统计")
    print("  GET  /api/users           - 用户列表（快速）")
    print("  GET  /api/reports         - 报告列表（中等）")
    print("  GET  /api/analytics       - 分析数据（慢，会告警）")
    print("  GET  /api/database/<type> - 数据库查询（fast/medium/slow）")
    print("  GET  /admin/stats         - 详细统计信息")
    print("  GET  /admin/test-alert    - 测试告警系统")
    print("  GET  /admin/cleanup       - 清理资源")
    print("  GET  /admin/reset-stats   - 重置统计")
    print("  GET  /admin/toggle-monitoring - 切换监控状态")

    print("\n📁 性能报告目录: ./advanced_reports/")

    if os.getenv('MATTERMOST_SERVER_URL'):
        print("💬 Mattermost通知: 已配置")
    else:
        print("💬 Mattermost通知: 未配置（设置环境变量启用）")
        print("   MATTERMOST_SERVER_URL=https://your-server.com")
        print("   MATTERMOST_TOKEN=your-token")
        print("   MATTERMOST_CHANNEL_ID=your-channel-id")

    print("\n按 Ctrl+C 停止服务器")
    print("=" * 50)

    try:
        app.run(
        host='0.0.0.0',
        port=5001,
        debug=False
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
