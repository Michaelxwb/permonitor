"""
配置文件示例

演示如何使用配置文件配置性能监控工具
"""

import json
import tempfile
import os
from flask import Flask
from web_performance_monitor import PerformanceMonitor, Config

def create_config_file():
    """创建示例配置文件"""
    config_data = {
        "threshold_seconds": 1.5,
        "alert_window_days": 14,
        "max_performance_overhead": 0.03,
        "enable_local_file": True,
        "local_output_dir": "/var/log/performance",
        "enable_mattermost": False,
        "mattermost_server_url": "",
        "mattermost_token": "",
        "mattermost_channel_id": "",
        "mattermost_max_retries": 5,
        "log_level": "INFO"
    }
    
    # 创建临时配置文件
    config_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    json.dump(config_data, config_file, indent=2, ensure_ascii=False)
    config_file.close()
    
    print(f"配置文件已创建: {config_file.name}")
    print("配置内容:")
    print(json.dumps(config_data, indent=2, ensure_ascii=False))
    
    return config_file.name

def create_app():
    """创建Flask应用并配置性能监控"""
    app = Flask(__name__)
    
    # 创建配置文件
    config_path = create_config_file()
    
    try:
        # 从配置文件加载配置
        config = Config.from_file(config_path)
        
        # 打印生效的配置
        print("\n生效的配置:")
        for key, value in config.get_effective_config().items():
            print(f"  {key}: {value}")
        
        # 创建性能监控器
        monitor = PerformanceMonitor(config)
        
        # 应用中间件
        app.wsgi_app = monitor.create_middleware()(app.wsgi_app)
        
        @app.route('/api/slow')
        def slow_endpoint():
            """慢端点测试"""
            import time
            time.sleep(2.0)  # 超过阈值
            return {"message": "慢请求完成"}
        
        @app.route('/api/fast')
        def fast_endpoint():
            """快端点测试"""
            return {"message": "快请求完成"}
        
        return app
    
    finally:
        # 清理临时文件
        if os.path.exists(config_path):
            os.unlink(config_path)
            print(f"\n临时配置文件已删除: {config_path}")

if __name__ == '__main__':
    app = create_app()
    print("\n启动Flask应用:")
    print("- 访问 http://localhost:5000/api/slow 触发告警")
    print("- 访问 http://localhost:5000/api/fast 正常请求")
    app.run(debug=True, port=5000)