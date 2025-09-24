# iFlow CLI - Web Performance Monitor 项目指南

## 项目概述

**Web Performance Monitor** 是一个基于 pyinstrument 的 Flask 应用性能监控和告警工具，提供零入侵的性能监控解决方案。该项目使用 Python 开发，支持 Flask 中间件和装饰器两种监控模式，能够自动生成详细的 HTML 性能分析报告并通过多种方式发送告警通知。

### 核心功能
- 🚀 **零入侵监控**: 通过中间件和装饰器模式实现无侵入性集成
- ⚡ **性能优先**: 监控工具本身的性能开销控制在5%以内
- 🔧 **灵活配置**: 支持环境变量、配置文件和代码配置三种方式
- 📊 **详细报告**: 基于 pyinstrument 生成详细的 HTML 性能分析报告
- 🔔 **多种通知**: 支持本地文件和 Mattermost 通知方式
- 🛡️ **容错机制**: 所有监控和通知错误都不影响原应用正常运行

## 技术栈

- **语言**: Python 3.7+
- **核心依赖**: 
  - `pyinstrument>=4.0.0` - 性能分析引擎
  - `flask>=2.0.0` - Web 框架支持
  - `requests>=2.25.0` - HTTP 请求处理
- **可选依赖**:
  - `mattermostdriver>=7.0.0` - Mattermost 通知
  - `sanic>=21.0.0` - Sanic 框架支持
- **开发工具**: pytest, black, flake8, mypy
- **构建工具**: setuptools, build, twine

## 项目结构

```
web_performance_monitor/
├── __init__.py              # 包入口和快速设置函数
├── monitor.py               # 核心监控器类（PerformanceMonitor）
├── config.py                # 配置管理（Config 类）
├── analyzer.py              # 性能分析和开销跟踪
├── alerts.py                # 告警管理器
├── models.py                # 数据模型定义
├── exceptions.py            # 自定义异常类
├── utils.py                 # 工具函数
├── formatters.py            # 格式化工具
├── logging_config.py        # 日志配置
├── cache.py                 # 缓存机制
├── error_handling.py        # 错误处理
└── notifiers/               # 通知器模块
    ├── __init__.py
    ├── base.py               # 通知器基类
    ├── factory.py            # 通知器工厂
    ├── local_file.py         # 本地文件通知器
    └── mattermost.py         # Mattermost 通知器
└── adapters/                # 框架适配器模块
    ├── __init__.py
    ├── base.py               # 适配器基类
    ├── wsgi.py               # WSGI适配器（Flask、Django等）
    ├── asgi.py               # ASGI适配器（FastAPI、Starlette等）
    └── sanic.py              # Sanic专用适配器

examples/                    # 示例代码
├── quick_start.py           # 5分钟快速开始
├── flask_middleware_example.py  # Flask 中间件示例
├── decorator_example.py     # 装饰器示例
├── production_example.py    # 生产环境配置
├── sanic_integration.py     # Sanic框架集成示例
├── fastapi_integration.py   # FastAPI集成示例
├── django_integration.py    # Django集成示例
├── tornado_integration.py   # Tornado集成示例
├── pyramid_integration.py   # Pyramid集成示例
└── config_examples/         # 配置示例

scripts/                     # 构建和发布脚本
├── build_and_test.py        # 构建和测试脚本
└── release.py               # 发布脚本

tests/                       # 测试套件
├── test_config.py           # 配置管理单元测试
├── test_integration.py      # 集成测试
├── test_performance_validation.py  # 性能验证测试
└── test_runner.py           # 测试运行器
```

## 开发环境设置

### 1. 环境准备
```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 安装开发依赖
pip install -e ".[dev]"
```

### 2. 代码质量工具
```bash
# 代码格式化
make format
# 或者
black web_performance_monitor/ tests/ examples/
isort web_performance_monitor/ tests/ examples/

# 代码检查
make lint
# 或者
flake8 web_performance_monitor/ tests/
mypy web_performance_monitor/

# 运行测试
make test
# 或者
pytest tests/ -v --cov=web_performance_monitor
```

### 3. 快速构建和测试
```bash
# 清理、构建和本地安装测试
make quick-build

# 完整检查流程
make check  # 包含格式化、lint和测试
```

## 构建和发布

### 构建流程
```bash
# 清理构建文件
make clean

# 构建包
make build

# 检查包
make check-package

# 本地安装测试
make install
```

### 发布到 PyPI
```bash
# 发布到测试 PyPI
make upload-test

# 发布到正式 PyPI
make upload

# 完整发布流程（包含检查、构建、发布）
make release-test  # 测试环境
make release       # 正式环境
```

### 版本管理
```bash
# 更新补丁版本（1.0.0 -> 1.0.1）
make bump-patch

# 更新次版本（1.0.0 -> 1.1.0）
make bump-minor

# 更新主版本（1.0.0 -> 2.0.0）
make bump-major
```

## 核心模块说明

### PerformanceMonitor（monitor.py）
核心监控器类，提供两种监控模式：
- **Flask 中间件模式**: 自动监控所有 HTTP 请求
- **装饰器模式**: 监控特定的关键函数

主要方法：
- `create_middleware()`: 创建 Flask 中间件
- `create_decorator()`: 创建性能监控装饰器
- `get_stats()`: 获取监控统计信息
- `test_alert_system()`: 测试告警系统

### Config（config.py）
配置管理类，支持多种配置方式：
- 环境变量配置（推荐生产环境使用）
- 配置文件（JSON 格式）
- 代码直接配置

关键配置项：
- `threshold_seconds`: 响应时间阈值
- `alert_window_days`: 重复告警时间窗口
- `enable_local_file`: 本地文件通知开关
- `enable_mattermost`: Mattermost 通知开关
- `url_blacklist`: URL 黑名单（支持正则表达式）

### PerformanceAnalyzer（analyzer.py）
性能分析模块，集成 pyinstrument：
- 性能数据收集和分析
- 性能开销跟踪
- HTML 报告生成
- 执行时间测量

### AlertManager（alerts.py）
告警管理器，处理告警逻辑：
- 阈值检查和告警触发
- 重复告警去重（基于时间窗口）
- 多通知器管理
- 告警统计跟踪

## 使用模式

### 1. Flask 中间件模式（推荐）
自动监控所有 HTTP 请求，零入侵集成：
```python
from flask import Flask
from web_performance_monitor import PerformanceMonitor, Config

app = Flask(__name__)

# 配置监控
config = Config(
    threshold_seconds=1.0,
    enable_local_file=True,
    local_output_dir="/tmp/reports"
)

monitor = PerformanceMonitor(config)

# 应用中间件（只需要这一行！）
app.wsgi_app = monitor.create_middleware()(app.wsgi_app)

@app.route('/api/users')
def get_users():
    return {"users": []}
```

### 2. 装饰器模式
监控特定函数，支持同步和异步函数：

```python
from web_performance_monitor import PerformanceMonitor, Config

config = Config(threshold_seconds=0.5)
monitor = PerformanceMonitor(config)

# 同步函数监控
@monitor.create_decorator()
def slow_database_query(user_id):
    return database.query_user_data(user_id)

# 异步函数监控（Sanic、FastAPI等）
@monitor.create_decorator()
async def async_api_call(endpoint):
    await asyncio.sleep(0.1)
    return await fetch_data(endpoint)
```

### 3. Sanic框架专用模式
针对 Sanic 异步框架的优化集成：

```python
from sanic import Sanic
from web_performance_monitor import PerformanceMonitor, Config
from web_performance_monitor.adapters.sanic import SanicAdapter

app = Sanic("MyApp")

# 配置监控
config = Config(threshold_seconds=0.5)
monitor = PerformanceMonitor(config)

# 创建Sanic适配器
sanic_adapter = SanicAdapter(monitor)

# 应用中间件
@app.middleware('request')
async def monitor_request(request):
    return sanic_adapter._monitor_sanic_request(request)

@app.middleware('response')
async def monitor_response(request, response):
    sanic_adapter.process_response(request, response)

@app.route('/api/users')
async def get_users(request):
    return json({"users": []})

if __name__ == '__main__':
    app.run(host="127.0.0.1", port=8000)
```

### 3. 环境变量配置（生产环境推荐）
```bash
export WPM_THRESHOLD_SECONDS=2.0
export WPM_ENABLE_LOCAL_FILE=true
export WPM_ENABLE_MATTERMOST=true
export WPM_MATTERMOST_SERVER_URL=https://mattermost.example.com
export WPM_MATTERMOST_TOKEN=your-bot-token
```

```python
from web_performance_monitor import Config, PerformanceMonitor

# 从环境变量自动加载配置
config = Config.from_env()
monitor = PerformanceMonitor(config)
```

## 测试策略

### 测试分类
1. **单元测试** (`test_config.py`): 配置管理功能测试
2. **集成测试** (`test_integration.py`): Flask 中间件和装饰器集成测试
3. **性能验证测试** (`test_performance_validation.py`): 性能开销和监控精度测试

### 运行测试
```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试类型
python test_runner.py unit         # 单元测试
python test_runner.py integration  # 集成测试
python test_runner.py performance  # 性能测试
python test_runner.py quick        # 快速测试（跳过慢测试）
python test_runner.py coverage     # 覆盖率测试

# 生成覆盖率报告
pytest tests/ --cov=web_performance_monitor --cov-report=html
```

### 测试重点
- ✅ 性能开销必须 < 5%
- ✅ Flask 中间件集成稳定性
- ✅ 装饰器模式不影响原函数行为
- ✅ 并发场景下的监控精度
- ✅ 错误处理和容错机制

## 开发最佳实践

### 1. 代码风格
- 遵循 PEP 8 编码规范
- 使用 black 进行代码格式化（行长度 88）
- 使用 isort 管理导入顺序
- 添加类型注解（mypy 检查通过）

### 2. 错误处理
- 所有监控相关错误都不应影响原应用
- 使用 `safe_execute` 包装可能失败的代码
- 详细的日志记录，便于问题排查
- 优雅降级（通知失败时继续监控）

### 3. 性能优化
- 严格控制监控开销 < 5%
- 使用缓存避免重复计算
- 异步处理非关键路径
- 内存使用优化

### 4. 配置管理
- 提供合理的默认值
- 支持运行时配置更新
- 配置验证和错误提示
- 敏感信息脱敏处理

## 发布流程

### 发布前检查清单
- [ ] 所有测试通过 (`make test`)
- [ ] 代码质量检查通过 (`make check`)
- [ ] 版本号更新正确
- [ ] CHANGELOG.md 已更新
- [ ] README.md 文档已更新
- [ ] 构建包检查通过 (`make check-package`)

### 发布步骤
1. 更新版本号（setup.py 和 pyproject.toml）
2. 更新文档和变更日志
3. 运行完整测试套件
4. 构建发布包
5. 上传到测试 PyPI 验证
6. 上传到正式 PyPI
7. 创建 Git 标签和发布

## 故障排除

### 常见问题
1. **Pyinstrument 冲突**: 同一线程不能运行多个 profiler
2. **Mattermost 连接失败**: 检查 server_url、token 和网络连接
3. **性能开销过高**: 调整阈值或优化监控逻辑
4. **测试失败**: 检查依赖包是否完整安装

### 调试技巧
- 使用 `monitor.test_alert_system()` 测试告警配置
- 查看日志文件获取详细错误信息
- 使用 `monitor.get_stats()` 获取监控统计
- 检查 HTML 报告了解性能分析结果

## 相关资源

- **PyPI 包**: https://pypi.org/project/web-performance-monitor/
- **GitHub 仓库**: [待补充]
- **文档**: README.md
- **测试报告**: tests/README.md
- **构建脚本**: Makefile, scripts/

---

*本指南基于项目当前状态生成，建议定期更新以反映最新的项目变化。*