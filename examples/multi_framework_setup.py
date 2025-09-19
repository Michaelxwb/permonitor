"""
多框架环境配置示例

演示如何在同一个项目中配置和使用多个web框架的监控。
"""

import os
import sys
from typing import Dict, Any, Optional

print("=== 多框架环境配置示例 ===\n")

# 1. 环境检测和配置
print("1. 环境检测和配置:")

class MultiFrameworkManager:
    """多框架管理器"""
    
    def __init__(self):
        self.available_frameworks = {}
        self.monitors = {}
        self.configs = {}
    
    def detect_frameworks(self):
        """检测可用的框架"""
        try:
            from web_performance_monitor.utils.framework_detector import FrameworkDetector
            
            detector = FrameworkDetector()
            frameworks = detector.detect_installed_frameworks()
            
            for framework in frameworks:
                version = detector.get_framework_version(framework)
                self.available_frameworks[framework] = version
                print(f"   ✅ {framework} v{version} 可用")
            
            if not frameworks:
                print("   ⚠️ 未检测到任何web框架")
                print("   建议安装: pip install web-performance-monitor[all]")
            
            return frameworks
            
        except Exception as e:
            print(f"   ❌ 框架检测失败: {e}")
            return []
    
    def setup_framework_configs(self):
        """设置框架配置"""
        print("\n2. 设置框架配置:")
        
        # Flask配置
        self.configs['flask'] = {
            'auto_instrument': True,
            'track_templates': True,
            'track_database': True,
            'exclude_paths': ['/health', '/metrics', '/flask-admin'],
            'sample_rate': 1.0
        }
        print("   ✅ Flask配置已设置")
        
        # FastAPI配置
        self.configs['fastapi'] = {
            'auto_instrument': True,
            'track_background_tasks': True,
            'track_websockets': False,
            'track_startup_shutdown': True,
            'exclude_paths': ['/health', '/metrics', '/docs', '/redoc', '/openapi.json'],
            'sample_rate': 1.0,
            'async_context_timeout': 30.0
        }
        print("   ✅ FastAPI配置已设置")
        
        # 通知配置
        self.configs['notifications'] = {
            'mattermost': {
                'url': os.getenv('MATTERMOST_URL', 'https://your-mattermost-server.com'),
                'token': os.getenv('MATTERMOST_TOKEN', 'your-bot-token'),
                'channel': os.getenv('MATTERMOST_CHANNEL', 'monitoring-alerts'),
                'alert_on_threshold': True,
                'alert_on_error': True,
                'batch_notifications': False,
                'rate_limit': 10
            }
        }
        print("   ✅ 通知配置已设置")
    
    def create_monitors(self):
        """创建监控器"""
        print("\n3. 创建监控器:")
        
        try:
            from web_performance_monitor import create_web_monitor
            
            for framework in self.available_frameworks:
                if framework in self.configs:
                    try:
                        monitor = create_web_monitor(framework, self.configs[framework])
                        self.monitors[framework] = monitor
                        print(f"   ✅ {framework} 监控器创建成功")
                    except Exception as e:
                        print(f"   ❌ {framework} 监控器创建失败: {e}")
                else:
                    print(f"   ⚠️ {framework} 没有配置，跳过")
            
        except Exception as e:
            print(f"   ❌ 监控器创建失败: {e}")
    
    def get_monitor(self, framework: str):
        """获取指定框架的监控器"""
        return self.monitors.get(framework)
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态信息"""
        return {
            'available_frameworks': self.available_frameworks,
            'configured_frameworks': list(self.configs.keys()),
            'active_monitors': list(self.monitors.keys())
        }

# 初始化多框架管理器
manager = MultiFrameworkManager()
frameworks = manager.detect_frameworks()
manager.setup_framework_configs()
manager.create_monitors()

# 显示状态
status = manager.get_status()
print(f"\n状态总结:")
print(f"   可用框架: {list(status['available_frameworks'].keys())}")
print(f"   已配置框架: {status['configured_frameworks']}")
print(f"   活跃监控器: {status['active_monitors']}")

# 2. Flask应用示例
print("\n4. Flask应用示例:")

if 'flask' in frameworks:
    try:
        from flask import Flask, jsonify
        import time
        
        flask_app = Flask(__name__)
        flask_monitor = manager.get_monitor('flask')
        
        # 集成监控器
        if flask_monitor:
            try:
                middleware = flask_monitor.get_middleware()
                if middleware:
                    flask_app.wsgi_app = middleware(flask_app.wsgi_app)
                    print("   ✅ Flask监控中间件已集成")
            except Exception as e:
                print(f"   ⚠️ Flask监控中间件集成失败: {e}")
        
        @flask_app.route('/flask/api/data')
        def flask_data():
            time.sleep(0.1)  # 模拟处理时间
            return jsonify({
                'framework': 'Flask',
                'data': ['item1', 'item2', 'item3'],
                'timestamp': time.time()
            })
        
        @flask_app.route('/flask/health')
        def flask_health():
            return jsonify({'status': 'healthy', 'framework': 'Flask'})
        
        print("   ✅ Flask应用配置完成")
        
    except Exception as e:
        print(f"   ❌ Flask应用配置失败: {e}")
else:
    print("   ⚠️ Flask不可用，跳过Flask应用配置")

# 3. FastAPI应用示例
print("\n5. FastAPI应用示例:")

if 'fastapi' in frameworks:
    try:
        from fastapi import FastAPI
        from fastapi.middleware.base import BaseHTTPMiddleware
        import asyncio
        
        fastapi_app = FastAPI(title="Multi-Framework FastAPI")
        fastapi_monitor = manager.get_monitor('fastapi')
        
        # 集成监控器
        if fastapi_monitor:
            try:
                middleware = fastapi_monitor.get_middleware()
                if middleware:
                    fastapi_app.add_middleware(middleware)
                    print("   ✅ FastAPI监控中间件已集成")
            except Exception as e:
                print(f"   ⚠️ FastAPI监控中间件集成失败: {e}")
        
        @fastapi_app.get('/fastapi/api/data')
        async def fastapi_data():
            await asyncio.sleep(0.1)  # 模拟异步处理时间
            return {
                'framework': 'FastAPI',
                'data': ['async_item1', 'async_item2', 'async_item3'],
                'timestamp': time.time()
            }
        
        @fastapi_app.get('/fastapi/health')
        async def fastapi_health():
            return {'status': 'healthy', 'framework': 'FastAPI'}
        
        print("   ✅ FastAPI应用配置完成")
        
    except Exception as e:
        print(f"   ❌ FastAPI应用配置失败: {e}")
else:
    print("   ⚠️ FastAPI不可用，跳过FastAPI应用配置")

# 4. 统一配置管理
print("\n6. 统一配置管理:")

class UnifiedConfigManager:
    """统一配置管理器"""
    
    def __init__(self):
        self.load_config()
    
    def load_config(self):
        """加载配置"""
        try:
            from web_performance_monitor.config.unified_config import UnifiedConfig
            
            self.config = UnifiedConfig()
            print("   ✅ 统一配置加载成功")
            
            # 显示关键配置
            dep_config = self.config.dependency_config
            print(f"   依赖检查模式: {dep_config.check_mode}")
            print(f"   跳过依赖检查: {dep_config.skip_dependency_check}")
            print(f"   严格模式: {dep_config.strict_mode}")
            
        except Exception as e:
            print(f"   ❌ 统一配置加载失败: {e}")
            self.config = None
    
    def get_framework_config(self, framework: str) -> Dict[str, Any]:
        """获取框架特定配置"""
        if not self.config:
            return {}
        
        # 这里可以根据框架返回特定配置
        base_config = {
            'monitoring_enabled': True,
            'sample_rate': 1.0,
            'debug_mode': os.getenv('DEBUG', 'false').lower() == 'true'
        }
        
        if framework == 'flask':
            base_config.update({
                'track_templates': True,
                'track_database': True
            })
        elif framework == 'fastapi':
            base_config.update({
                'track_background_tasks': True,
                'async_context_timeout': 30.0
            })
        
        return base_config

config_manager = UnifiedConfigManager()

# 5. 依赖冲突检测
print("\n7. 依赖冲突检测:")

try:
    from web_performance_monitor.core.conflict_resolver import ConflictResolver, DependencyInfo
    
    resolver = ConflictResolver()
    
    # 创建依赖信息
    dependencies = []
    
    if 'flask' in frameworks:
        dependencies.append(
            DependencyInfo("flask", version_spec=">=2.0.0", required_by=["flask_app"])
        )
    
    if 'fastapi' in frameworks:
        dependencies.extend([
            DependencyInfo("fastapi", version_spec=">=0.100.0", required_by=["fastapi_app"]),
            DependencyInfo("uvicorn", version_spec=">=0.20.0", required_by=["fastapi_app"]),
            DependencyInfo("aiofiles", version_spec=">=24.1.0", required_by=["fastapi_app"]),
            DependencyInfo("aiohttp", version_spec=">=3.12.0", required_by=["fastapi_app"])
        ])
    
    # 检测冲突
    result = resolver.analyze_and_resolve(dependencies)
    
    print(f"   检测到的冲突数量: {result['total_conflicts']}")
    
    if result['total_conflicts'] > 0:
        print("   ⚠️ 发现依赖冲突:")
        for conflict in result['conflicts']:
            print(f"     - {conflict.description}")
        
        print("\n   建议的解决方案:")
        for i, step in enumerate(result['resolution_plan'], 1):
            print(f"     {i}. {step['description']}")
    else:
        print("   ✅ 没有检测到依赖冲突")
    
except Exception as e:
    print(f"   ❌ 冲突检测失败: {e}")

# 6. 性能监控示例
print("\n8. 性能监控示例:")

class PerformanceCollector:
    """性能数据收集器"""
    
    def __init__(self):
        self.metrics = {
            'flask': {'requests': 0, 'total_time': 0.0, 'errors': 0},
            'fastapi': {'requests': 0, 'total_time': 0.0, 'errors': 0}
        }
    
    def record_request(self, framework: str, duration: float, error: bool = False):
        """记录请求"""
        if framework in self.metrics:
            self.metrics[framework]['requests'] += 1
            self.metrics[framework]['total_time'] += duration
            if error:
                self.metrics[framework]['errors'] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {}
        
        for framework, metrics in self.metrics.items():
            if metrics['requests'] > 0:
                avg_time = metrics['total_time'] / metrics['requests']
                error_rate = metrics['errors'] / metrics['requests']
                
                stats[framework] = {
                    'requests': metrics['requests'],
                    'avg_response_time': f"{avg_time:.3f}s",
                    'error_rate': f"{error_rate:.2%}",
                    'total_time': f"{metrics['total_time']:.3f}s"
                }
            else:
                stats[framework] = {
                    'requests': 0,
                    'avg_response_time': '0.000s',
                    'error_rate': '0.00%',
                    'total_time': '0.000s'
                }
        
        return stats

collector = PerformanceCollector()

# 模拟一些请求数据
import random
for _ in range(10):
    # 模拟Flask请求
    if 'flask' in frameworks:
        duration = random.uniform(0.1, 0.5)
        error = random.random() < 0.1
        collector.record_request('flask', duration, error)
    
    # 模拟FastAPI请求
    if 'fastapi' in frameworks:
        duration = random.uniform(0.05, 0.3)
        error = random.random() < 0.05
        collector.record_request('fastapi', duration, error)

stats = collector.get_stats()
print("   性能统计:")
for framework, data in stats.items():
    if data['requests'] > 0:
        print(f"   {framework}:")
        print(f"     请求数: {data['requests']}")
        print(f"     平均响应时间: {data['avg_response_time']}")
        print(f"     错误率: {data['error_rate']}")
        print(f"     总耗时: {data['total_time']}")

# 7. 部署建议
print("\n9. 部署建议:")

def generate_deployment_config():
    """生成部署配置"""
    
    print("   Docker Compose 配置示例:")
    
    compose_config = """
version: '3.8'

services:
  flask-app:
    build: .
    command: python flask_app.py
    ports:
      - "5000:5000"
    environment:
      - WPM_DEPENDENCY_CHECK_MODE=lenient
      - WPM_LOG_LEVEL=INFO
      - FLASK_ENV=production
    volumes:
      - ./logs:/app/logs

  fastapi-app:
    build: .
    command: uvicorn fastapi_app:app --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
    environment:
      - WPM_DEPENDENCY_CHECK_MODE=lenient
      - WPM_LOG_LEVEL=INFO
    volumes:
      - ./logs:/app/logs

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - flask-app
      - fastapi-app
"""
    
    print(compose_config)
    
    print("   Nginx 配置示例:")
    
    nginx_config = """
events {
    worker_connections 1024;
}

http {
    upstream flask_backend {
        server flask-app:5000;
    }
    
    upstream fastapi_backend {
        server fastapi-app:8000;
    }
    
    server {
        listen 80;
        
        location /flask/ {
            proxy_pass http://flask_backend/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
        
        location /fastapi/ {
            proxy_pass http://fastapi_backend/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
        
        location /health {
            return 200 'OK';
            add_header Content-Type text/plain;
        }
    }
}
"""
    
    print(nginx_config)

generate_deployment_config()

# 8. 总结
print("\n10. 总结:")
print(f"   ✅ 检测到 {len(frameworks)} 个可用框架")
print(f"   ✅ 创建了 {len(manager.monitors)} 个监控器")
print(f"   ✅ 配置了统一的性能监控")
print(f"   ✅ 提供了部署配置示例")

if len(frameworks) == 0:
    print("\n   建议:")
    print("   1. 安装所需框架: pip install web-performance-monitor[all]")
    print("   2. 重新运行此示例")
elif len(frameworks) < 2:
    print("\n   建议:")
    print("   1. 考虑安装其他框架以体验多框架监控")
    print("   2. 根据项目需求选择合适的框架组合")
else:
    print("\n   下一步:")
    print("   1. 根据示例配置你的应用")
    print("   2. 自定义监控配置以满足需求")
    print("   3. 部署到生产环境")

print("\n=== 多框架环境配置示例完成 ===")