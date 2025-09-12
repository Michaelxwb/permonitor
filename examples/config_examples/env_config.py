"""
环境变量配置示例

演示如何使用环境变量配置性能监控工具
"""

import os
from flask import Flask
from web_performance_monitor import PerformanceMonitor, Config

# 设置环境变量
os.environ['WPM_THRESHOLD_SECONDS'] = '2.0'
os.environ['WPM_ALERT_WINDOW_DAYS'] = '7'
os.environ['WPM_ENABLE_LOCAL_FILE'] = 'true'
os.environ['WPM_LOCAL_OUTPUT_DIR'] = '/tmp/performance_reports'
os.environ['WPM_ENABLE_MATTERMOST'] = 'true'
os.environ['WPM_MATTERMOST_SERVER_URL'] = 'https://mattermost.example.com'
os.environ['WPM_MATTERMOST_TOKEN'] = 'your-mattermost-token'
os.environ['WPM_MATTERMOST_CHANNEL_ID'] = 'your-channel-id'
os.environ['WPM_LOG_LEVEL'] = 'DEBUG'

def create_app():
    """创建Flask应用并配置性能监控"""
    app = Flask(__name__)
    
    # 从环境变量加载配置
    config = Config.from_env()
    
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