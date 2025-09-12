# Web Performance Monitor

[![PyPI version](https://badge.fury.io/py/web-performance-monitor.svg)](https://badge.fury.io/py/web-performance-monitor)
[![Python Support](https://img.shields.io/pypi/pyversions/web-performance-monitor.svg)](https://pypi.org/project/web-performance-monitor/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

基于pyinstrument的Flask应用性能监控和告警工具，提供零入侵的性能监控解决方案。

## ✨ 功能特性

- 🚀 **零入侵监控**: 通过中间件和装饰器模式实现无侵入性集成
- ⚡ **性能优先**: 监控工具本身的性能开销控制在5%以内
- 🔧 **灵活配置**: 支持环境变量、配置文件和代码配置三种方式
- 📊 **详细报告**: 基于pyinstrument生成详细的HTML性能分析报告
- 🔔 **多种通知**: 支持本地文件和Mattermost通知方式
- 🛡️ **容错机制**: 所有监控和通知错误都不影响原应用正常运行
- 📈 **智能告警**: 基于时间窗口的重复告警去重机制
- 🔍 **参数追踪**: 自动提取和记录请求参数，支持敏感信息脱敏
- 🏷️ **追踪支持**: 支持TraceID、SpanID等分布式追踪标识

## 🚀 快速开始

### 安装

```bash
# 基础安装
pip install web-performance-monitor

# 包含Mattermost支持
pip install web-performance-monitor[mattermost]

# 开发环境安装
pip install web-performance-monitor[dev]
```

### 5分钟快速接入

#### 1. Flask中间件模式（推荐）

最简单的接入方式，自动监控所有HTTP请求：

```python
from flask import Flask
from web_performance_monitor import PerformanceMonitor, Config

app = Flask(__name__)

# 基础配置
config = Config(
    threshold_seconds=1.0,              # 响应时间阈值
    enable_local_file=True,             # 启用本地文件通知
    local_output_dir="/tmp/reports",    # 输出目录
)

monitor = PerformanceMonitor(config)

# 零入侵集成 - 只需要这一行代码！
app.wsgi_app = monitor.create_middleware()(app.wsgi_app)

@app.route('/api/users')
def get_users():
    # 业务逻辑 - 会被自动监控
    return {"users": []}

if __name__ == '__main__':
    app.run()
```

#### 2. 装饰器模式

监控特定的关键函数：

```python
from web_performance_monitor import PerformanceMonitor, Config

config = Config(threshold_seconds=0.5)
monitor = PerformanceMonitor(config)

@monitor.create_decorator()
def slow_database_query(user_id):
    # 关键业务逻辑 - 独立监控
    return database.query_user_data(user_id)

@monitor.create_decorator()
def complex_calculation(data):
    # 复杂计算逻辑
    return process_complex_data(data)
```

#### 3. 环境变量配置

生产环境推荐使用环境变量配置：

```bash
# 基础配置
export WPM_THRESHOLD_SECONDS=2.0
export WPM_ALERT_WINDOW_DAYS=7
export WPM_ENABLE_LOCAL_FILE=true
export WPM_LOCAL_OUTPUT_DIR=/var/log/performance

# Mattermost通知配置
export WPM_ENABLE_MATTERMOST=true
export WPM_MATTERMOST_SERVER_URL=https://mattermost.example.com
export WPM_MATTERMOST_TOKEN=your-bot-token
export WPM_MATTERMOST_CHANNEL_ID=your-channel-id
```

```python
from web_performance_monitor import Config, PerformanceMonitor

# 从环境变量自动加载配置
config = Config.from_env()
monitor = PerformanceMonitor(config)

# 应用到Flask应用
app.wsgi_app = monitor.create_middleware()(app.wsgi_app)
```

## 📋 详细接入指南

### Flask应用接入

#### 方式1: 应用工厂模式

```python
from flask import Flask
from web_performance_monitor import PerformanceMonitor, Config

def create_app():
    app = Flask(__name__)
    
    # 配置监控
    config = Config(
        threshold_seconds=1.0,
        enable_local_file=True,
        local_output_dir="/var/log/performance"
    )
    
    monitor = PerformanceMonitor(config)
    app.wsgi_app = monitor.create_middleware()(app.wsgi_app)
    
    return app

app = create_app()
```

#### 方式2: 蓝图应用

```python
from flask import Flask, Blueprint
from web_performance_monitor import PerformanceMonitor, Config

# 创建蓝图
api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/users')
def get_users():
    return {"users": []}

# 主应用
app = Flask(__name__)
app.register_blueprint(api_bp)

# 应用监控（会监控所有蓝图的路由）
config = Config.from_env()
monitor = PerformanceMonitor(config)
app.wsgi_app = monitor.create_middleware()(app.wsgi_app)
```

#### 方式3: 条件监控

```python
import os
from flask import Flask
from web_performance_monitor import PerformanceMonitor, Config

app = Flask(__name__)

# 只在生产环境启用监控
if os.getenv('FLASK_ENV') == 'production':
    config = Config(
        threshold_seconds=2.0,  # 生产环境阈值更高
        enable_mattermost=True,
        mattermost_server_url=os.getenv('MATTERMOST_URL'),
        mattermost_token=os.getenv('MATTERMOST_TOKEN'),
        mattermost_channel_id=os.getenv('MATTERMOST_CHANNEL')
    )
    monitor = PerformanceMonitor(config)
    app.wsgi_app = monitor.create_middleware()(app.wsgi_app)
```

### 函数监控接入

#### 数据库操作监控

```python
from web_performance_monitor import PerformanceMonitor, Config

config = Config(threshold_seconds=0.5)
monitor = PerformanceMonitor(config)

@monitor.create_decorator()
def query_user_data(user_id):
    """监控数据库查询性能"""
    return db.session.query(User).filter_by(id=user_id).first()

@monitor.create_decorator()
def bulk_insert_data(data_list):
    """监控批量插入性能"""
    return db.session.bulk_insert_mappings(DataModel, data_list)
```

#### 外部API调用监控

```python
import requests
from web_performance_monitor import PerformanceMonitor, Config

config = Config(threshold_seconds=3.0)  # API调用阈值设置更高
monitor = PerformanceMonitor(config)

@monitor.create_decorator()
def call_external_api(endpoint, data):
    """监控外部API调用"""
    response = requests.post(f"https://api.example.com/{endpoint}", json=data)
    return response.json()

@monitor.create_decorator()
def fetch_user_profile(user_id):
    """监控用户资料获取"""
    return call_external_api(f"users/{user_id}", {})
```

#### 计算密集型任务监控

```python
@monitor.create_decorator()
def calculate_risk_score(data):
    """监控风险评分计算"""
    # 复杂的计算逻辑
    return complex_algorithm(data)

@monitor.create_decorator()
def generate_report(report_type, filters):
    """监控报告生成"""
    return report_generator.create_report(report_type, filters)
```

## ⚙️ 配置选项

### 完整配置表

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|----------|--------|------|
| threshold_seconds | WPM_THRESHOLD_SECONDS | 1.0 | 响应时间阈值（秒） |
| alert_window_days | WPM_ALERT_WINDOW_DAYS | 10 | 重复告警时间窗口（天） |
| max_performance_overhead | WPM_MAX_PERFORMANCE_OVERHEAD | 0.05 | 最大性能开销（5%） |
| enable_local_file | WPM_ENABLE_LOCAL_FILE | true | 启用本地文件通知 |
| local_output_dir | WPM_LOCAL_OUTPUT_DIR | /tmp | 本地文件输出目录 |
| enable_mattermost | WPM_ENABLE_MATTERMOST | false | 启用Mattermost通知 |
| mattermost_server_url | WPM_MATTERMOST_SERVER_URL | - | Mattermost服务器URL |
| mattermost_token | WPM_MATTERMOST_TOKEN | - | Mattermost访问令牌 |
| mattermost_channel_id | WPM_MATTERMOST_CHANNEL_ID | - | Mattermost频道ID |
| url_blacklist | WPM_URL_BLACKLIST | [] | URL黑名单（逗号分隔，支持正则） |
| enable_url_blacklist | WPM_ENABLE_URL_BLACKLIST | true | 启用URL黑名单功能 |
| log_level | WPM_LOG_LEVEL | INFO | 日志级别 |

### 配置示例

#### 开发环境配置

```python
config = Config(
    threshold_seconds=0.5,      # 开发环境阈值较低
    alert_window_days=1,        # 短时间窗口
    enable_local_file=True,
    local_output_dir="./dev_reports",
    enable_mattermost=False,    # 开发环境不发送通知
    log_level="DEBUG"
)
```

#### 测试环境配置

```python
config = Config(
    threshold_seconds=1.0,
    alert_window_days=3,
    enable_local_file=True,
    local_output_dir="/var/log/test_performance",
    enable_mattermost=True,
    mattermost_server_url="https://test-mattermost.company.com",
    mattermost_token=os.getenv('TEST_MATTERMOST_TOKEN'),
    mattermost_channel_id="test-alerts",
    log_level="INFO"
)
```

#### 生产环境配置

```python
config = Config(
    threshold_seconds=2.0,      # 生产环境阈值较高
    alert_window_days=7,        # 较长的去重窗口
    max_performance_overhead=0.03,  # 更严格的性能要求
    enable_local_file=True,
    local_output_dir="/var/log/performance",
    enable_mattermost=True,
    mattermost_server_url=os.getenv('MATTERMOST_URL'),
    mattermost_token=os.getenv('MATTERMOST_TOKEN'),
    mattermost_channel_id="production-alerts",
    log_level="WARNING"
)
```

## � UR功L黑名单功能

### 永久屏蔽无法优化的接口

在实际生产环境中，某些业务接口由于历史原因或复杂性无法快速优化，可以使用URL黑名单功能永久屏蔽告警。

#### 基本配置

```python
from web_performance_monitor import Config, PerformanceMonitor

config = Config(
    threshold_seconds=1.0,
    url_blacklist=[
        '/api/legacy/.*',           # 遗留API（正则匹配）
        '/health',                  # 健康检查（精确匹配）
        '.*\\.(jpg|png|gif)$',     # 图片资源（正则匹配）
        '/api/slow-report/.*'       # 已知慢接口
    ],
    enable_url_blacklist=True
)

monitor = PerformanceMonitor(config)
```

#### 环境变量配置

```bash
# 多个URL用逗号分隔，支持正则表达式
export WPM_URL_BLACKLIST="/api/legacy/.*,/health,/metrics,.*\\.(css|js)$"
export WPM_ENABLE_URL_BLACKLIST="true"
```

#### 动态管理黑名单

```python
# 添加黑名单规则
config.add_blacklist_url('/api/temp/.*')

# 移除黑名单规则
config.remove_blacklist_url('/api/temp/.*')

# 检查URL是否被屏蔽
is_blocked = config.is_url_blacklisted('/api/legacy/old-function')
```

#### 常用黑名单模式

```python
# 生产环境推荐配置
url_blacklist = [
    # 遗留系统接口
    '/api/legacy/.*',
    '/api/v1/old/.*',
    
    # 系统监控接口
    '/health',
    '/metrics',
    '/status',
    '/ping',
    
    # 静态资源
    '.*\\.(jpg|png|gif|ico|svg)$',
    '.*\\.(css|js|woff|ttf|eot)$',
    
    # 管理员接口（已知较慢）
    '/admin/.*',
    '/management/.*',
    
    # 报告和导出接口（业务需要，已知较慢）
    '/api/reports/generate/.*',
    '/api/export/.*',
    '/api/download/.*',
    
    # 第三方回调接口
    '/webhook/.*',
    '/callback/.*',
    
    # 调试和开发接口
    '/debug/.*',
    '/dev/.*'
]
```

#### 黑名单匹配逻辑

- 支持**正则表达式**匹配，提供强大的模式匹配能力
- 同时检查**完整URL**和**端点路径**
- 匹配成功的请求会跳过告警，但仍会被监控统计
- 自动验证正则表达式有效性，无效模式会被忽略

## 🔧 高级功能

### 监控统计信息

```python
# 获取监控统计
stats = monitor.get_stats()
print(f"总请求数: {stats['total_requests']}")
print(f"慢请求数: {stats['slow_requests']}")
print(f"慢请求率: {stats['slow_request_rate']:.1f}%")
print(f"告警发送数: {stats['alerts_sent']}")

# 获取性能开销统计
overhead_stats = stats.get('overhead_stats', {})
print(f"平均开销: {overhead_stats.get('average_overhead', 0):.2%}")
```

### 测试告警系统

```python
# 测试告警配置是否正常
test_results = monitor.test_alert_system()
if test_results['success']:
    print("✅ 告警系统配置正常")
    for notifier, result in test_results['notifier_results'].items():
        print(f"  {notifier}: {'✅' if result else '❌'}")
else:
    print(f"❌ 告警系统配置错误: {test_results['error']}")
```

### 重置监控数据

```python
# 重置所有统计数据
monitor.reset_stats()
print("监控统计已重置")
```

### 动态配置更新

```python
# 运行时更新配置
monitor.update_config(
    threshold_seconds=3.0,
    enable_mattermost=False
)
```

## 📊 告警报告说明

### HTML报告内容

生成的HTML报告包含以下信息：

- **基本信息**: 请求URL、方法、状态码、响应时间
- **请求参数**: JSON参数、查询参数、表单数据（敏感信息自动脱敏）
- **请求头信息**: User-Agent、Accept、TraceID等追踪信息
- **性能分析**: 基于pyinstrument的详细性能分析图表
- **调用栈**: 函数调用层次和耗时分布
- **系统信息**: 服务器时间、Python版本等环境信息

### 敏感信息保护

系统自动识别并脱敏以下敏感信息：
- 密码字段（password、passwd、pwd等）
- 令牌字段（token、auth、authorization等）
- 密钥字段（key、secret、credential等）

## 🎯 最佳实践

### 1. 阈值设置建议

```python
# 不同环境的推荐阈值
THRESHOLDS = {
    'development': 0.5,    # 开发环境：快速发现问题
    'testing': 1.0,        # 测试环境：模拟真实场景
    'staging': 1.5,        # 预发布环境：接近生产环境
    'production': 2.0,     # 生产环境：避免误报
}

config = Config(
    threshold_seconds=THRESHOLDS.get(os.getenv('ENV', 'development'), 1.0)
)
```

### 2. 监控范围控制

```python
# 只监控关键API
@app.route('/api/critical-operation')
def critical_operation():
    # 这个端点会被监控
    return process_critical_data()

# 排除健康检查等高频端点
@app.route('/health')
def health_check():
    # 可以通过路径过滤排除此类端点
    return {"status": "ok"}
```

### 3. 生产环境部署

```python
import os
from web_performance_monitor import Config, PerformanceMonitor

# 生产环境配置
config = Config(
    threshold_seconds=float(os.getenv('WPM_THRESHOLD', '2.0')),
    alert_window_days=int(os.getenv('WPM_WINDOW_DAYS', '7')),
    enable_local_file=True,
    local_output_dir=os.getenv('WPM_LOG_DIR', '/var/log/performance'),
    enable_mattermost=os.getenv('WPM_ENABLE_MATTERMOST', 'false').lower() == 'true',
    mattermost_server_url=os.getenv('MATTERMOST_URL'),
    mattermost_token=os.getenv('MATTERMOST_TOKEN'),
    mattermost_channel_id=os.getenv('MATTERMOST_CHANNEL'),
    log_level=os.getenv('WPM_LOG_LEVEL', 'WARNING')
)

monitor = PerformanceMonitor(config)
```

### 4. 日志管理

```bash
# 设置日志轮转（推荐使用logrotate）
# /etc/logrotate.d/web-performance-monitor
/var/log/performance/*.html {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 www-data www-data
}
```

## 🔍 故障排除

### 常见问题

#### 1. Mattermost连接失败

```python
# 检查配置
config = Config.from_env()
monitor = PerformanceMonitor(config)

# 测试连接
test_results = monitor.test_alert_system()
if not test_results['success']:
    print(f"连接失败: {test_results['error']}")
    
# 常见解决方案：
# - 确保server_url包含完整协议 (https://)
# - 验证token和channel_id的正确性
# - 检查网络连接和防火墙设置
```

#### 2. 性能开销过高

```python
# 检查性能开销
stats = monitor.get_stats()
overhead = stats.get('overhead_stats', {}).get('average_overhead', 0)

if overhead > 0.05:  # 超过5%
    print(f"⚠️ 性能开销过高: {overhead:.2%}")
    # 建议：提高阈值或减少监控频率
    monitor.update_config(threshold_seconds=3.0)
```

#### 3. 告警文件过多

```bash
# 清理旧的告警文件
find /var/log/performance -name "*.html" -mtime +30 -delete

# 或者在配置中设置更长的告警窗口
export WPM_ALERT_WINDOW_DAYS=30
```

## 📚 示例项目

查看 `examples/` 目录获取更多示例：

- `quick_start.py` - 5分钟快速开始
- `flask_middleware_example.py` - Flask中间件完整示例
- `decorator_example.py` - 装饰器使用示例
- `production_example.py` - 生产环境配置示例
- `advanced_usage.py` - 高级功能使用示例

## 🤝 贡献

欢迎提交Issue和Pull Request！

### 开发环境设置

```bash
# 克隆项目
git clone https://github.com/your-repo/web-performance-monitor.git
cd web-performance-monitor

# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 代码格式化
black web_performance_monitor/ tests/
isort web_performance_monitor/ tests/

# 类型检查
mypy web_performance_monitor/
```

### 构建和发布

```bash
# 使用Makefile
make clean build test

# 或使用脚本
python scripts/build_and_test.py
python scripts/release.py 1.0.1 --test  # 发布到测试PyPI
```

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🔗 相关链接

- [PyPI包](https://pypi.org/project/web-performance-monitor/)
- [问题反馈](https://github.com/your-repo/web-performance-monitor/issues)
- [更新日志](CHANGELOG.md)
- [pyinstrument文档](https://pyinstrument.readthedocs.io/)