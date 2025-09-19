"""
Flask集成示例

演示如何在Flask应用中集成web-performance-monitor。
"""

from flask import Flask, request, jsonify
import time
import random

# 创建Flask应用
app = Flask(__name__)

print("=== Flask集成示例 ===\n")

# 1. 检查Flask依赖
print("1. 检查Flask依赖:")
try:
    from web_performance_monitor import check_dependencies
    from web_performance_monitor.utils.framework_detector import FrameworkDetector
    
    detector = FrameworkDetector()
    frameworks = detector.detect_installed_frameworks()
    
    if 'flask' not in frameworks:
        print("   ❌ Flask未安装或不可用")
        print("   安装命令: pip install web-performance-monitor[flask]")
        exit(1)
    else:
        flask_version = detector.get_framework_version('flask')
        print(f"   ✅ Flask已安装，版本: {flask_version}")
    
    print()
    
except Exception as e:
    print(f"   依赖检查失败: {e}")
    exit(1)

# 2. 创建Flask监控器
print("2. 创建Flask监控器:")
try:
    from web_performance_monitor import create_web_monitor
    
    # 创建Flask专用监控器
    monitor = create_web_monitor('flask', {
        'auto_instrument': True,
        'track_templates': True,
        'track_database': True,
        'exclude_paths': ['/health', '/metrics'],
        'sample_rate': 1.0
    })
    
    print(f"   ✅ 监控器创建成功: {type(monitor).__name__}")
    print()
    
except Exception as e:
    print(f"   ❌ 监控器创建失败: {e}")
    # 继续执行，使用模拟监控器
    monitor = None

# 3. 方法一：使用中间件（推荐）
print("3. 集成方法一：中间件集成")
if monitor:
    try:
        # 获取中间件类
        middleware_class = monitor.get_middleware()
        if middleware_class:
            app.wsgi_app = middleware_class(app.wsgi_app)
            print("   ✅ 中间件集成成功")
        else:
            print("   ⚠️ 中间件不可用，使用装饰器方式")
    except Exception as e:
        print(f"   ❌ 中间件集成失败: {e}")
else:
    print("   ⚠️ 监控器不可用，跳过中间件集成")

print()

# 4. 方法二：使用装饰器
print("4. 集成方法二：装饰器集成")

def performance_monitor(f):
    """性能监控装饰器"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = f(*args, **kwargs)
            end_time = time.time()
            duration = end_time - start_time
            
            # 记录性能数据
            print(f"   📊 {f.__name__}: {duration:.3f}s")
            
            return result
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            print(f"   ❌ {f.__name__}: {duration:.3f}s (错误: {e})")
            raise
    
    wrapper.__name__ = f.__name__
    return wrapper

# 5. 定义路由
@app.route('/')
@performance_monitor
def home():
    """首页"""
    return jsonify({
        'message': 'Hello from Flask!',
        'framework': 'Flask',
        'monitoring': 'Enabled'
    })

@app.route('/api/data')
@performance_monitor
def get_data():
    """获取数据API"""
    # 模拟数据库查询
    time.sleep(random.uniform(0.1, 0.5))
    
    return jsonify({
        'data': [
            {'id': 1, 'name': 'Item 1'},
            {'id': 2, 'name': 'Item 2'},
            {'id': 3, 'name': 'Item 3'}
        ],
        'count': 3
    })

@app.route('/api/slow')
@performance_monitor
def slow_endpoint():
    """慢端点（用于测试）"""
    # 模拟慢查询
    time.sleep(random.uniform(1.0, 2.0))
    
    return jsonify({
        'message': 'This is a slow endpoint',
        'processing_time': 'Simulated slow operation'
    })

@app.route('/api/error')
@performance_monitor
def error_endpoint():
    """错误端点（用于测试）"""
    if random.random() < 0.5:
        raise ValueError("Random error for testing")
    
    return jsonify({'message': 'Success'})

@app.route('/health')
def health_check():
    """健康检查（不监控）"""
    return jsonify({'status': 'healthy'})

@app.route('/metrics')
def metrics():
    """指标端点（不监控）"""
    return jsonify({
        'requests_total': 100,
        'avg_response_time': 0.25,
        'error_rate': 0.02
    })

# 6. 方法三：手动监控
@app.route('/api/manual')
def manual_monitoring():
    """手动监控示例"""
    print("5. 集成方法三：手动监控")
    
    # 手动开始监控
    start_time = time.time()
    
    try:
        # 业务逻辑
        time.sleep(random.uniform(0.2, 0.8))
        
        # 模拟一些操作
        operations = ['database_query', 'cache_lookup', 'api_call']
        for op in operations:
            op_start = time.time()
            time.sleep(random.uniform(0.05, 0.15))
            op_end = time.time()
            print(f"   📊 {op}: {op_end - op_start:.3f}s")
        
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"   📊 总耗时: {total_time:.3f}s")
        
        return jsonify({
            'message': 'Manual monitoring example',
            'total_time': f"{total_time:.3f}s",
            'operations': operations
        })
        
    except Exception as e:
        end_time = time.time()
        total_time = end_time - start_time
        print(f"   ❌ 手动监控出错: {total_time:.3f}s (错误: {e})")
        raise

# 7. 错误处理
@app.errorhandler(Exception)
def handle_exception(e):
    """全局错误处理"""
    print(f"   ❌ 全局错误处理: {type(e).__name__}: {e}")
    
    return jsonify({
        'error': str(e),
        'type': type(e).__name__
    }), 500

# 8. 请求前后钩子
@app.before_request
def before_request():
    """请求前钩子"""
    request.start_time = time.time()

@app.after_request
def after_request(response):
    """请求后钩子"""
    if hasattr(request, 'start_time'):
        duration = time.time() - request.start_time
        print(f"   📊 请求 {request.method} {request.path}: {duration:.3f}s")
    
    return response

# 9. 配置示例
print("6. 配置示例:")
try:
    from web_performance_monitor.config.unified_config import UnifiedConfig
    
    config = UnifiedConfig()
    print(f"   依赖检查模式: {config.dependency_config.check_mode}")
    print(f"   跳过依赖检查: {config.dependency_config.skip_dependency_check}")
    print(f"   严格模式: {config.dependency_config.strict_mode}")
    print()
    
except Exception as e:
    print(f"   配置获取失败: {e}")

# 10. 运行应用
if __name__ == '__main__':
    print("7. 启动Flask应用:")
    print("   访问 http://localhost:5000 查看首页")
    print("   访问 http://localhost:5000/api/data 查看数据API")
    print("   访问 http://localhost:5000/api/slow 测试慢端点")
    print("   访问 http://localhost:5000/api/error 测试错误处理")
    print("   访问 http://localhost:5000/api/manual 查看手动监控")
    print("   访问 http://localhost:5000/health 查看健康检查")
    print("   访问 http://localhost:5000/metrics 查看指标")
    print()
    print("   按 Ctrl+C 停止应用")
    print()
    
    try:
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n   应用已停止")
    except Exception as e:
        print(f"\n   应用启动失败: {e}")

print("\n=== Flask集成示例完成 ===")