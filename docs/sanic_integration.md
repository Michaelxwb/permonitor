# Sanic框架集成指南

本文档详细介绍如何在Sanic异步Web框架中集成web-performance-monitor性能监控工具。

## 🚀 快速开始

### 安装依赖

```bash
# 安装基础包和Sanic支持
pip install web-performance-monitor[sanic]

# 或者安装所有功能
pip install web-performance-monitor[all]
```

### 基本集成

```python
from sanic import Sanic
from sanic.response import json
from web_performance_monitor import PerformanceMonitor, Config

# 创建Sanic应用
app = Sanic("PerformanceMonitorDemo")

# 配置性能监控
config = Config(
    threshold_seconds=0.5,              # 响应时间阈值
    enable_local_file=True,             # 启用本地文件通知
    local_output_dir="./sanic_reports"  # 报告输出目录
)

monitor = PerformanceMonitor(config)

# 创建Sanic适配器
from web_performance_monitor.adapters.sanic import SanicAdapter
sanic_adapter = SanicAdapter(monitor)

# 应用请求监控中间件
@app.middleware('request')
async def monitor_request(request):
    return sanic_adapter._monitor_sanic_request(request)

# 应用响应监控中间件
@app.middleware('response')
async def monitor_response(request, response):
    sanic_adapter.process_response(request, response)

# 定义路由
@app.route('/')
async def hello_world(request):
    return json({"message": "Hello, Sanic with Performance Monitoring!"})

@app.route('/slow')
async def slow_endpoint(request):
    import asyncio
    await asyncio.sleep(1.2)  # 模拟慢响应
    return json({"message": "This is a slow endpoint"})

if __name__ == '__main__':
    app.run(host="127.0.0.1", port=8000, debug=False, single_process=True)
```

## 📋 详细配置

### 配置选项

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `threshold_seconds` | 响应时间阈值，超过此值触发告警 | 1.0 |
| `enable_local_file` | 是否启用本地文件报告 | True |
| `local_output_dir` | 性能报告输出目录 | "./reports" |
| `enable_mattermost` | 是否启用Mattermost通知 | False |
| `log_level` | 日志级别 | "INFO" |

### 环境变量配置

```bash
# 基础配置
export WPM_THRESHOLD_SECONDS=0.5
export WPM_ENABLE_LOCAL_FILE=true
export WPM_LOCAL_OUTPUT_DIR=./sanic_reports

# Mattermost通知配置（可选）
export WPM_ENABLE_MATTERMOST=true
export WPM_MATTERMOST_SERVER_URL=https://mattermost.example.com
export WPM_MATTERMOST_TOKEN=your-bot-token
```

```python
from web_performance_monitor import Config, PerformanceMonitor

# 从环境变量加载配置
config = Config.from_env()
monitor = PerformanceMonitor(config)
```

## 🎯 高级用法

### 装饰器模式

除了中间件模式，还可以使用装饰器监控特定函数：

```python
# 创建性能装饰器
performance_monitor = monitor.create_decorator()

@performance_monitor
async def async_database_query(user_id):
    """监控异步数据库查询"""
    await asyncio.sleep(0.3)  # 模拟数据库查询
    return {"id": user_id, "name": f"User {user_id}"}

@performance_monitor
def complex_calculation(data):
    """监控复杂计算"""
    import time
    time.sleep(0.8)  # 模拟复杂计算
    return {"result": sum(data), "average": sum(data) / len(data)}

# 在路由中使用
@app.route('/users/<user_id:int>')
async def get_user(request, user_id: int):
    user_data = await async_database_query(user_id)
    return json(user_data)

@app.route('/calculate', methods=['POST'])
async def calculate(request):
    data = request.json.get('numbers', [])
    result = complex_calculation(data)
    return json(result)
```

### 数据模型集成

与Pydantic模型集成：

```python
from pydantic import BaseModel
from sanic.response import json

class User(BaseModel):
    id: int
    name: str
    email: str

class CalculationRequest(BaseModel):
    numbers: list[int]

@app.route('/users', methods=['POST'])
async def create_user(request):
    try:
        user_data = CalculationRequest(**request.json)
        # 业务逻辑处理
        return json(user_data.dict())
    except Exception as e:
        return json({"error": str(e)}, status=400)
```

### 错误处理和日志

```python
import logging
from sanic.exceptions import SanicException

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.exception(SanicException)
async def handle_exception(request, exception):
    """全局异常处理"""
    logger.error(f"Request error: {exception}")
    return json({"error": str(exception)}, status=500)

@app.route('/error')
async def error_endpoint(request):
    """测试错误处理"""
    raise SanicException("Something went wrong", status_code=500)
```

## 📊 性能报告

### 报告文件

性能报告保存在配置的目录中，文件名为：
```
performance_alert_<endpoint>_<timestamp>.html
```

示例：
```
performance_alert__slow_20250924_215202_186.html
performance_alert__calculate_20250924_215203_301.html
performance_alert___main__.process_business_logic_20250924_215203_299.html
```

### 报告内容

每个报告包含：
- 📈 **调用栈分析** - 详细的函数调用时间线
- ⏱️ **性能指标** - 执行时间、内存使用等
- 🔍 **代码热点** - 性能瓶颈定位
- 📋 **请求信息** - URL、参数、状态码等

### 查看报告

直接在浏览器中打开HTML文件：
```bash
open sanic_reports/performance_alert__slow_20250924_215202_186.html
```

## 🧪 测试验证

### 运行自动化测试

```bash
# 运行Sanic集成测试
python test_sanic_integration.py

# 手动测试
python examples/sanic_integration.py
```

### 测试端点

启动服务器后，可以测试以下端点：

```bash
# 基础测试
curl http://127.0.0.1:8002/
curl http://127.0.0.1:8002/health

# 慢接口测试（会触发告警）
curl http://127.0.0.1:8002/slow

# 用户接口测试
curl http://127.0.0.1:8002/users/123

# 计算接口测试
curl -X POST http://127.0.0.1:8002/calculate \
  -H "Content-Type: application/json" \
  -d '{"numbers": [1, 2, 3, 4, 5]}'

# 获取监控统计
curl http://127.0.0.1:8002/stats
```

## 🔧 故障排除

### 常见问题

1. **ImportError: No module named 'sanic'**
   ```bash
   pip install sanic
   # 或
   pip install web-performance-monitor[sanic]
   ```

2. **JSON序列化错误**
   - 确保使用自定义JSON序列化函数处理datetime对象
   - 参考上面的`get_stats`函数实现

3. **中间件不生效**
   - 检查中间件注册顺序
   - 确保适配器实例正确创建
   - 验证请求/响应中间件都正确注册

4. **性能报告未生成**
   - 检查`local_output_dir`目录是否存在
   - 确认`enable_local_file=True`
   - 验证是否有超过阈值的请求

### 性能优化建议

1. **合理设置阈值** - 根据实际业务需求调整
2. **控制报告数量** - 定期清理旧的报告文件
3. **监控开销** - 确保监控本身开销<5%
4. **异步处理** - 充分利用Sanic的异步特性

## 📚 相关资源

- [Sanic官方文档](https://sanic.readthedocs.io/)
- [web-performance-monitor GitHub](https://github.com/example/web-performance-monitor)
- [pyinstrument文档](https://pyinstrument.readthedocs.io/)
- [性能优化最佳实践](https://example.com/performance-guide)

## 🤝 贡献

欢迎提交Issue和Pull Request来改进Sanic框架支持！

## 📄 许可证

MIT License - 详见项目根目录的LICENSE文件