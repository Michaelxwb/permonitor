#!/usr/bin/env python3
"""
Web Performance Monitor 发布脚本

使用方法:
    python scripts/release.py 1.0.1
    python scripts/release.py 1.0.1 --test  # 发布到测试PyPI
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, check=True):
    """运行命令并打印输出"""
    print(f"🔧 执行: {cmd}")
    result = subprocess.run(cmd, shell=True, check=check)
    return result.returncode == 0


def update_version(version):
    """更新版本号"""
    print(f"📝 更新版本号到 {version}")
    
    # 更新setup.py
    setup_py = Path("setup.py")
    if setup_py.exists():
        content = setup_py.read_text(encoding='utf-8')
        content = content.replace(
            'version="1.0.0"',
            f'version="{version}"'
        )
        setup_py.write_text(content, encoding='utf-8')
    
    # 更新pyproject.toml
    pyproject = Path("pyproject.toml")
    if pyproject.exists():
        content = pyproject.read_text(encoding='utf-8')
        content = content.replace(
            'version = "1.0.0"',
            f'version = "{version}"'
        )
        pyproject.write_text(content, encoding='utf-8')


def clean_build():
    """清理构建目录"""
    print("🧹 清理构建目录...")
    dirs_to_clean = ["build", "dist", "*.egg-info"]
    for pattern in dirs_to_clean:
        run_command(f"rm -rf {pattern}", check=False)


def run_tests():
    """运行测试"""
    print("🧪 运行测试...")
    return run_command("python -m pytest tests/ -v", check=False)


def build_package():
    """构建包"""
    print("📦 构建包...")
    return run_command("python -m build")


def check_package():
    """检查包"""
    print("🔍 检查包...")
    return run_command("twine check dist/*")


def upload_package(test=False):
    """上传包到PyPI"""
    if test:
        print("📤 上传到测试PyPI...")
        return run_command("twine upload --repository testpypi dist/*")
    else:
        print("📤 上传到正式PyPI...")
        return run_command("twine upload dist/*")


def create_git_tag(version):
    """创建Git标签"""
    print(f"🏷️ 创建Git标签 v{version}")
    run_command("git add .")
    run_command(f'git commit -m "Release version {version}"', check=False)
    run_command(f"git tag v{version}")


def main():
    parser = argparse.ArgumentParser(description="发布Web Performance Monitor到PyPI")
    parser.add_argument("version", help="版本号 (例如: 1.0.1)")
    parser.add_argument("--test", action="store_true", help="发布到测试PyPI")
    parser.add_argument("--skip-tests", action="store_true", help="跳过测试")
    parser.add_argument("--skip-git", action="store_true", help="跳过Git操作")
    
    args = parser.parse_args()
    
    print(f"🚀 开始发布版本 {args.version}")
    
    # 检查必要工具
    required_tools = ["python", "twine", "git"]
    for tool in required_tools:
        if not run_command(f"which {tool}", check=False):
            print(f"❌ 缺少必要工具: {tool}")
            return 1
    
    try:
        # 1. 更新版本号
        update_version(args.version)
        
        # 2. 运行测试
        if not args.skip_tests:
            if not run_tests():
                print("❌ 测试失败，停止发布")
                return 1
        
        # 3. 清理构建目录
        clean_build()
        
        # 4. 构建包
        if not build_package():
            print("❌ 构建失败")
            return 1
        
        # 5. 检查包
        if not check_package():
            print("❌ 包检查失败")
            return 1
        
        # 6. 上传包
        if not upload_package(test=args.test):
            print("❌ 上传失败")
            return 1
        
        # 7. 创建Git标签
        if not args.skip_git:
            create_git_tag(args.version)
            print("🔄 推送到Git...")
            run_command("git push origin main", check=False)
            run_command(f"git push origin v{args.version}", check=False)
        
        # 8. 验证安装
        print("✅ 验证安装...")
        if args.test:
            print("从测试PyPI安装:")
            print(f"pip install --index-url https://test.pypi.org/simple/ web-performance-monitor=={args.version}")
        else:
            print("从正式PyPI安装:")
            print(f"pip install web-performance-monitor=={args.version}")
        
        print(f"🎉 版本 {args.version} 发布成功!")
        
        if args.test:
            print("📋 下一步:")
            print("1. 测试安装包是否正常工作")
            print("2. 如果一切正常，运行: python scripts/release.py {args.version}")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n❌ 发布被用户中断")
        return 1
    except Exception as e:
        print(f"❌ 发布过程中出现错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())