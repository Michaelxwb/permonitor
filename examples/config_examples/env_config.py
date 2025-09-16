"""
直接配置示例

演示如何直接配置性能监控工具
"""

from flask import Flask
from web_performance_monitor import PerformanceMonitor, Config

def create_app():
    """创建Flask应用并配置性能监控"""
    app = Flask(__name__)
    
    # 直接配置
    config = Config(
        threshold_seconds=2.0,
        alert_window_days=7,
        enable_local_file=True,
        local_output_dir='/tmp/performance_reports',
        enable_mattermost=True,
        mattermost_server_url='https://mattermost.example.com',
        mattermost_token='your-mattermost-token',
        mattermost_channel_id='your-channel-id',
        log_level='DEBUG'
    )
    
    # 打印生效的配置（脱敏后）
    print("生效的配置:")
    for key, value in config.get_effective_config().items():
        print(f"  {key}: {value}")
    
    # 创建性能监控器
    monitor = PerformanceMonitor(config)
    
    # 应用中间件
    app.wsgi_app = monitor.create_middleware()(app.wsgi_app)
    
    @app.route('/api/test')
    def test_endpoint():
        """测试端点"""
        import time
        time.sleep(1.5)  # 模拟慢请求
        return {"message": "测试成功"}
    
    return app

if __name__ == '__main__':
    app = create_app()
    print("启动Flask应用，访问 http://localhost:5000/api/test 触发性能监控")
    app.run(debug=True, port=5000)