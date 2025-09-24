#!/usr/bin/env python3
"""
构建和测试脚本

用于本地测试包的构建和安装
"""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path


def run_command(cmd, check=True, cwd=None):
    """运行命令"""
    print(f"🔧 执行: {cmd}")
    # 替换python为python3以确保兼容性
    if cmd.startswith("python ") or cmd == "python":
        cmd = cmd.replace("python", "python3", 1)
    result = subprocess.run(cmd, shell=True, check=check, cwd=cwd)
    return result.returncode == 0


def main():
    print("🏗️ 开始构建和测试流程")

    # 1. 清理构建目录
    print("🧹 清理构建目录...")
    for pattern in ["build", "dist", "*.egg-info"]:
        run_command(f"rm -rf {pattern}", check=False)

    # 2. 运行测试
    print("🧪 运行测试...")
    if not run_command("python -m pytest tests/ -v", check=False):
        print("⚠️ 测试失败，但继续构建...")

    # 3. 构建包
    print("📦 构建包...")
    if not run_command("python -m build"):
        print("❌ 构建失败")
        return 1

    # 4. 检查包
    print("🔍 检查包...")
    if not run_command("twine check dist/*"):
        print("❌ 包检查失败")
        return 1

    # 5. 列出生成的文件
    print("📋 生成的文件:")
    dist_dir = Path("dist")
    if dist_dir.exists():
        for file in dist_dir.iterdir():
            size = file.stat().st_size
            print(f"  {file.name} ({size:,} bytes)")

    # 6. 本地安装测试
    print("🧪 本地安装测试...")

    # 创建临时虚拟环境
    with tempfile.TemporaryDirectory() as temp_dir:
        venv_dir = Path(temp_dir) / "test_env"

        # 创建虚拟环境
        print("📦 创建测试虚拟环境...")
        if not run_command(f"python -m venv {venv_dir}"):
            print("❌ 创建虚拟环境失败")
            return 1

        # 激活虚拟环境的Python路径
        if os.name == 'nt':  # Windows
            python_exe = venv_dir / "Scripts" / "python.exe"
            pip_exe = venv_dir / "Scripts" / "pip.exe"
        else:  # Unix/Linux/macOS
            python_exe = venv_dir / "bin" / "python"
            pip_exe = venv_dir / "bin" / "pip"

        # 升级pip
        print("⬆️ 升级pip...")
        run_command(f"{pip_exe} install --upgrade pip", check=False)

        # 安装wheel文件
        wheel_files = list(Path("dist").glob("*.whl"))
        if wheel_files:
            wheel_file = wheel_files[0]
            print(f"📦 安装 {wheel_file.name}...")
            if not run_command(f"{pip_exe} install {wheel_file}"):
                print("❌ 安装失败")
                return 1
        else:
            print("❌ 没有找到wheel文件")
            return 1

        # 测试导入
        print("🧪 测试导入...")
        test_script = '''
import sys
try:
    from web_performance_monitor import PerformanceMonitor, Config
    print("✅ 导入成功!")

    # 测试基本功能
    config = Config()
    monitor = PerformanceMonitor(config)
    print("✅ 基本功能测试成功!")

    # 测试装饰器
    decorator = monitor.create_decorator()

    @decorator
    def test_function():
        return "test"

    result = test_function()
    print(f"✅ 装饰器测试成功: {result}")

    print("🎉 所有测试通过!")

except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
'''

        if not run_command(f'{python_exe} -c "{test_script}"'):
            print("❌ 导入测试失败")
            return 1

    print("✅ 构建和测试完成!")
    print("\n📋 下一步:")
    print("1. 如果测试通过，可以发布到测试PyPI:")
    print("   python scripts/release.py 1.0.0 --test")
    print("2. 测试PyPI验证后，发布到正式PyPI:")
    print("   python scripts/release.py 1.0.0")

    return 0


if __name__ == "__main__":
    sys.exit(main())
