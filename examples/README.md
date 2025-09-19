# Web Performance Monitor 使用示例

本目录包含了 `web-performance-monitor` 的各种使用示例，帮助您快速上手和深入了解该库的功能。

## 📁 示例文件说明

### 1. `basic_usage.py` - 基本使用示例
演示库的基本功能和API使用方法。

**包含内容：**
- 依赖状态检查
- 自动框架检测
- 监控器创建
- 安装建议获取
- 插件系统使用
- 冲突检测

**运行方式：**
```bash
python examples/basic_usage.py
```

### 2. `flask_integration.py` - Flask集成示例
完整的Flask应用集成示例，展示多种集成方式。

**包含内容：**
- 中间件集成（推荐）
- 装饰器集成
- 手动监控
- 错误处理
- 配置示例

**运行方式：**
```bash
# 确保已安装Flask支持
pip install web-performance-monitor[flask]

# 运行示例
python examples/flask_integration.py
```

**访问地址：**
- 首页: http://localhost:5000
- 数据API: http://localhost:5000/api/data
- 慢端点: http://localhost:5000/api/slow
- 错误测试: http://localhost:5000/api/error
- 手动监控: http://localhost:5000/api/manual

### 3. `fastapi_integration.py` - FastAPI集成示例
完整的FastAPI应用集成示例，展示异步监控功能。

**包含内容：**
- 异步中间件集成
- 异步装饰器
- 后台任务监控
- 并发操作监控
- 依赖注入示例

**运行方式：**
```bash
# 确保已安装FastAPI支持
pip install web-performance-monitor[fastapi]

# 运行示例
python examples/fastapi_integration.py

# 或使用uvicorn
uvicorn fastapi_integration:app --host 0.0.0.0 --port 8000 --reload
```

**访问地址：**
- 首页: http://localhost:8000
- API文档: http://localhost:8000/docs
- 数据API: http://localhost:8000/api/data
- 后台任务: http://localhost:8000/api/background
- 并发操作: http://localhost:8000/api/concurrent

### 4. `multi_framework_setup.py` - 多框架环境配置
演示如何在同一项目中配置多个框架的监控。

**包含内容：**
- 多框架检测和配置
- 统一配置管理
- 性能数据收集
- 部署配置示例
- Docker Compose配置

**运行方式：**
```bash
# 安装所有框架支持
pip install web-performance-monitor[all]

# 运行示例
python examples/multi_framework_setup.py
```

### 5. `dependency_troubleshooting.py` - 依赖故障排除
交互式的依赖问题诊断和解决工具。

**包含内容：**
- 完整的环境诊断
- 依赖检查
- 版本兼容性检查
- 配置验证
- 解决方案建议

**运行方式：**
```bash
python examples/dependency_troubleshooting.py
```

## 🚀 快速开始

### 1. 安装依赖

根据您的需求选择安装方式：

```bash
# 最小安装（仅核心功能）
pip install web-performance-monitor

# Flask支持
pip install web-performance-monitor[flask]

# FastAPI支持
pip install web-performance-monitor[fastapi]

# 通知支持
pip install web-performance-monitor[notifications]

# 完整安装（推荐）
pip install web-performance-monitor[all]
```

### 2. 基本使用

```python
from web_performance_monitor import create_web_monitor, check_dependencies

# 检查依赖状态
print(check_dependencies())

# 创建监控器（自动检测框架）
monitor = create_web_monitor()

# 或指定框架
flask_monitor = create_web_monitor('flask')
fastapi_monitor = create_web_monitor('fastapi')
```

### 3. Flask集成

```python
from flask import Flask
from web_performance_monitor import create_web_monitor

app = Flask(__name__)
monitor = create_web_monitor('flask')

# 使用中间件（推荐）
app.wsgi_app = monitor.get_middleware()(app.wsgi_app)

@app.route('/')
def hello():
    return 'Hello, World!'
```

### 4. FastAPI集成

```python
from fastapi import FastAPI
from web_performance_monitor import create_web_monitor

app = FastAPI()
monitor = create_web_monitor('fastapi')

# 添加中间件
app.add_middleware(monitor.get_middleware())

@app.get("/")
async def read_root():
    return {"Hello": "World"}
```

## 🔧 配置选项

### 环境变量配置

```bash
# 依赖检查模式
export WPM_DEPENDENCY_CHECK_MODE=strict  # strict, lenient, disabled

# 跳过依赖检查
export WPM_SKIP_DEPENDENCY_CHECK=false

# 严格模式
export WPM_STRICT_MODE=false

# 调试模式
export WPM_DEBUG=false

# 日志级别
export WPM_LOG_LEVEL=INFO
```

### 代码配置

```python
from web_performance_monitor import create_web_monitor

# Flask配置
flask_config = {
    'auto_instrument': True,
    'track_templates': True,
    'track_database': True,
    'exclude_paths': ['/health', '/metrics'],
    'sample_rate': 1.0
}

flask_monitor = create_web_monitor('flask', flask_config)

# FastAPI配置
fastapi_config = {
    'auto_instrument': True,
    'track_background_tasks': True,
    'track_websockets': False,
    'exclude_paths': ['/docs', '/redoc'],
    'async_context_timeout': 30.0
}

fastapi_monitor = create_web_monitor('fastapi', fastapi_config)
```

## 🐛 故障排除

### 常见问题

1. **导入错误**
   ```bash
   # 检查安装
   pip list | grep web-performance-monitor
   
   # 重新安装
   pip uninstall web-performance-monitor
   pip install web-performance-monitor[all]
   ```

2. **依赖冲突**
   ```bash
   # 使用虚拟环境
   python -m venv myenv
   source myenv/bin/activate  # Linux/Mac
   myenv\Scripts\activate     # Windows
   pip install web-performance-monitor[all]
   ```

3. **版本不兼容**
   ```bash
   # 检查版本要求
   python examples/dependency_troubleshooting.py
   
   # 升级依赖
   pip install --upgrade flask fastapi uvicorn
   ```

### 诊断工具

运行诊断工具获取详细的问题分析：

```bash
python examples/dependency_troubleshooting.py
```

选择诊断模式：
- **快速检查**: 基本的依赖和导入测试
- **完整诊断**: 详细的环境分析和问题检测
- **自动修复**: 自动尝试解决常见问题（实验性）

## 📊 性能监控

### 监控指标

- **响应时间**: 请求处理时间
- **错误率**: 错误请求比例
- **吞吐量**: 每秒处理请求数
- **资源使用**: CPU和内存使用情况

### 数据收集

```python
# 获取性能统计
stats = monitor.get_stats()
print(f"平均响应时间: {stats['avg_response_time']}")
print(f"错误率: {stats['error_rate']}")

# 自定义指标
with monitor.track_operation('custom_operation'):
    # 您的业务逻辑
    pass
```

## 🔔 通知配置

### Mattermost通知

```python
notification_config = {
    'mattermost': {
        'url': 'https://your-mattermost-server.com',
        'token': 'your-bot-token',
        'channel': 'monitoring-alerts',
        'alert_on_threshold': True,
        'alert_on_error': True
    }
}

monitor = create_web_monitor('flask', {
    'notifications': notification_config
})
```

### 环境变量配置

```bash
export MATTERMOST_URL=https://your-mattermost-server.com
export MATTERMOST_TOKEN=your-bot-token
export MATTERMOST_CHANNEL=monitoring-alerts
```

## 🚀 部署示例

### Docker配置

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# 设置环境变量
ENV WPM_DEPENDENCY_CHECK_MODE=lenient
ENV WPM_LOG_LEVEL=INFO

EXPOSE 5000

CMD ["python", "app.py"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  web-app:
    build: .
    ports:
      - "5000:5000"
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
      - web-app
```

## 📚 更多资源

- **文档**: [完整文档链接]
- **API参考**: [API文档链接]
- **GitHub**: [项目仓库链接]
- **问题反馈**: [Issues链接]

## 🤝 贡献

欢迎提交示例和改进建议！请查看贡献指南了解详细信息。

## 📄 许可证

本项目采用 MIT 许可证。详见 LICENSE 文件。