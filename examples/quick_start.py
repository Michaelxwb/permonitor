"""
快速开始示例

演示如何快速集成Web性能监控工具
"""

import time

from flask import Flask, jsonify

# 方式1：使用quick_setup快速配置
from web_performance_monitor import quick_setup

app = Flask(__name__)

# 快速设置，使用默认配置
monitor = quick_setup(
    threshold_seconds=1.0,  # 1秒阈值
    enable_local_file=True,  # 启用本地文件通知
    local_output_dir="../reports/quick_reports"  # 报告输出目录
)

# 应用中间件
app.wsgi_app = monitor.create_middleware()(app.wsgi_app)


@app.route('/')
def index():
    """首页"""
    return jsonify({
        "message": "Web性能监控快速开始示例",
        "monitoring": "已启用",
        "threshold": "1.0秒"
    })


@app.route('/fast')
def fast():
    """快速响应"""
    return jsonify({"message": "快速响应", "time": "< 1s"})


@app.route('/slow')
def slow():
    """慢响应 - 会触发告警"""
    time.sleep(2)
    return jsonify({"message": "慢响应", "time": "2s", "alert": "已触发"})


if __name__ == '__main__':
    print("🚀 快速开始示例")
    print("访问 http://localhost:5000/slow 触发告警")
    print("报告将保存到 ../reports/ 目录")

    app.run(debug=True, port=5000)
