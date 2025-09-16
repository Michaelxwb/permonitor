"""
生产环境示例

演示在生产环境中使用Web性能监控工具的最佳实践
"""
import time
import random
import os
import logging
from flask import Flask, jsonify, request, g
from web_performance_monitor import PerformanceMonitor, Config

def create_production_app():
    """创建生产环境配置的Flask应用"""
    app = Flask(__name__)
    
    # 生产环境配置
    # 直接配置
    config = Config(
        threshold_seconds=float(os.getenv('WPM_THRESHOLD_SECONDS', '2.0')),
        alert_window_days=int(os.getenv('WPM_ALERT_WINDOW_DAYS', '7')),
        enable_local_file=os.getenv('WPM_ENABLE_LOCAL_FILE', 'true').lower() == 'true',
        local_output_dir=os.getenv('WPM_LOCAL_OUTPUT_DIR', '/tmp/log/performance_monitor'),
        enable_mattermost=os.getenv('WPM_ENABLE_MATTERMOST', 'false').lower() == 'true',
        mattermost_server_url=os.getenv('WPM_MATTERMOST_SERVER_URL', ''),
        mattermost_token=os.getenv('WPM_MATTERMOST_TOKEN', ''),
        mattermost_channel_id=os.getenv('WPM_MATTERMOST_CHANNEL_ID', ''),
        log_level=os.getenv('WPM_LOG_LEVEL', 'WARNING')
    )
    
    # 如果环境变量未设置，使用生产环境默认值
    if not any(os.getenv(key) for key in ['WPM_THRESHOLD_SECONDS', 'WPM_ALERT_WINDOW_DAYS']):
        config = Config(
            # 生产环境推荐配置
            threshold_seconds=0.5,              # 生产环境更宽松的阈值
            alert_window_days=30,               # 30天重复告警窗口
            max_performance_overhead=0.02,      # 2%性能开销限制
            
            # 本地文件通知
            enable_local_file=True,
            local_output_dir="/tmp/log/performance_monitor",
            
            # Mattermost通知
            enable_mattermost=bool(os.getenv('MATTERMOST_SERVER_URL')),
            mattermost_server_url=os.getenv('MATTERMOST_SERVER_URL', ''),
            mattermost_token=os.getenv('MATTERMOST_TOKEN', ''),
            mattermost_channel_id=os.getenv('MATTERMOST_CHANNEL_ID', ''),
            mattermost_max_retries=3,
            
            # 生产环境日志级别
            log_level=os.getenv('LOG_LEVEL', 'WARNING')
        )
    
    # 创建监控器
    monitor = PerformanceMonitor(config)
    
    # 只在非调试模式下启用监控
    if not app.debug:
        app.wsgi_app = monitor.create_middleware()(app.wsgi_app)
    
    # 创建装饰器用于关键业务函数
    performance_monitor = monitor.create_decorator()
    
    # 关键业务函数
    @performance_monitor
    def process_payment(amount: float, currency: str) -> dict:
        """支付处理 - 关键业务逻辑"""  
        # 模拟支付处理时间
        processing_time = random.uniform(0.5, 2.5)
        time.sleep(processing_time)
        
        success = processing_time < 2.0  # 模拟成功/失败
        
        return {
            'amount': amount,
            'currency': currency,
            'success': success,
            'processing_time': processing_time,
            'transaction_id': f"txn_{int(time.time())}"
        }
    
    @performance_monitor
    def generate_report(report_type: str) -> dict:
        """报告生成 - 可能耗时的操作"""
        # 不同类型报告的处理时间
        processing_times = {
            'summary': 0.3,
            'detailed': 1.5,
            'comprehensive': 3.0
        }
        
        processing_time = processing_times.get(report_type, 1.0)
        time.sleep(processing_time)
        
        return {
            'report_type': report_type,
            'processing_time': processing_time,
            'status': 'completed',
            'size_mb': processing_time * 10
        }
    
    # API路由
    @app.route('/health')
    def health_check():
        """健康检查端点"""
        return jsonify({
            "status": "healthy",
            "monitoring": monitor.is_monitoring_enabled(),
            "timestamp": int(time.time())
        })
    
    @app.route('/api/v1/payments', methods=['POST'])
    def create_payment():
        """创建支付"""
        data = request.get_json() or {}
        amount = data.get('amount', 100.0)
        currency = data.get('currency', 'USD')
        
        # 使用监控的支付处理函数
        result = process_payment(amount, currency)
        
        status_code = 200 if result['success'] else 400
        return jsonify(result), status_code
    
    @app.route('/api/v1/reports/<report_type>')
    def get_report(report_type):
        """获取报告"""
        if report_type not in ['summary', 'detailed', 'comprehensive']:
            return jsonify({"error": "Invalid report type"}), 400
        
        # 使用监控的报告生成函数
        result = generate_report(report_type)
        
        return jsonify(result)
    
    @app.route('/api/v1/users/<int:user_id>')
    def get_user(user_id):
        """获取用户信息"""
        # 模拟数据库查询
        time.sleep(1.0)
        
        return jsonify({
            "user_id": user_id,
            "name": f"User {user_id}",
            "email": f"user{user_id}@example.com"
        })
    
    # 管理端点（仅在调试模式或特定环境下可用）
    if app.debug or os.getenv('ENABLE_ADMIN_ENDPOINTS') == 'true':
        @app.route('/admin/monitoring/stats')
        def monitoring_stats():
            """监控统计信息"""
            return jsonify(monitor.get_stats())
        
        @app.route('/admin/monitoring/test')
        def test_monitoring():
            """测试监控系统"""
            return jsonify(monitor.test_alert_system())
        
        @app.route('/admin/monitoring/cleanup')
        def cleanup_monitoring():
            """清理监控资源"""
            monitor.cleanup()
            return jsonify({"message": "Cleanup completed"})
    
    # 错误处理
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Resource not found"}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"Internal error: {error}")
        return jsonify({"error": "Internal server error"}), 500
    
    # 请求日志中间件
    @app.before_request
    def before_request():
        g.start_time = time.time()
        
        # 记录请求开始（仅在调试模式）
        if app.debug:
            app.logger.info(f"Request started: {request.method} {request.path}")
    
    @app.after_request
    def after_request(response):
        # 添加响应时间头
        if hasattr(g, 'start_time'):
            duration = time.time() - g.start_time
            response.headers['X-Response-Time'] = f"{duration:.3f}"
        
        # 记录请求完成（仅在调试模式）
        if app.debug:
            app.logger.info(f"Request completed: {response.status_code}")
        
        return response
    
    return app, monitor

def setup_production_logging():
    """设置生产环境日志"""
    log_level = os.getenv('LOG_LEVEL', 'WARNING')
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('/tmp/log/app.log') if os.path.exists('/tmp/log') else logging.NullHandler()
        ]
    )

def main():
    """主函数"""
    # 设置生产环境日志
    setup_production_logging()
    
    print("🚀 生产环境示例启动")
    print("=" * 40)
    
    # 创建应用
    app, monitor = create_production_app()
    
    # 显示配置信息
    config_info = monitor.config.get_effective_config()
    print("📊 生产环境配置:")
    print(f"  阈值: {config_info.get('threshold_seconds')}s")
    print(f"  告警窗口: {config_info.get('alert_window_days')}天")
    print(f"  最大开销: {config_info.get('max_performance_overhead', 0) * 100:.1f}%")
    print(f"  本地文件: {'启用' if config_info.get('enable_local_file') else '禁用'}")
    print(f"  Mattermost: {'启用' if config_info.get('enable_mattermost') else '禁用'}")
    print(f"  日志级别: {config_info.get('log_level')}")
    
    print("\n🌐 生产API端点:")
    print("  GET  /health                    - 健康检查")
    print("  POST /api/v1/payments          - 创建支付")
    print("  GET  /api/v1/reports/<type>    - 获取报告")
    print("  GET  /api/v1/users/<id>        - 获取用户")
    
    if app.debug or os.getenv('ENABLE_ADMIN_ENDPOINTS') == 'true':
        print("\n🔧 管理端点:")
        print("  GET  /admin/monitoring/stats   - 监控统计")
        print("  GET  /admin/monitoring/test    - 测试监控")
        print("  GET  /admin/monitoring/cleanup - 清理资源")
    
    print("\n📝 环境变量配置:")
    print("  WPM_THRESHOLD_SECONDS=2.0")
    print("  WPM_ALERT_WINDOW_DAYS=30")
    print("  WPM_LOCAL_OUTPUT_DIR=/tmp/log/performance_monitor")
    print("  WPM_ENABLE_MATTERMOST=true")
    print("  WPM_MATTERMOST_SERVER_URL=https://your-server.com")
    print("  WPM_MATTERMOST_TOKEN=your-token")
    print("  WPM_MATTERMOST_CHANNEL_ID=your-channel")
    print("  LOG_LEVEL=WARNING")
    print("  ENABLE_ADMIN_ENDPOINTS=true")
    
    print("\n💡 生产环境建议:")
    print("  - 使用反向代理（nginx/Apache）")
    print("  - 配置日志轮转")
    print("  - 监控磁盘空间")
    print("  - 定期清理旧报告")
    print("  - 设置告警通知")
    
    print("\n按 Ctrl+C 停止服务器")
    print("=" * 40)
    
    try:
        # 生产环境配置
        port = int(os.getenv('PORT', 5001))
        host = os.getenv('HOST', '0.0.0.0')
        
        app.run(
            host=host,
            port=port,
            debug=False,
            threaded=True
        )
    except KeyboardInterrupt:
        print("\n\n🛑 服务器已停止")
        
        # 显示最终统计
        stats = monitor.get_stats()
        print(f"\n📊 运行统计:")
        print(f"  总请求: {stats.get('total_requests', 0)}")
        print(f"  慢请求: {stats.get('slow_requests', 0)}")
        print(f"  告警数: {stats.get('alerts_sent', 0)}")
        
        # 清理资源
        monitor.cleanup()
        print("\n✅ 资源清理完成")

if __name__ == '__main__':
    main()