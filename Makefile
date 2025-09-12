# Web Performance Monitor - Makefile

.PHONY: help clean build test install dev-install upload upload-test check format lint

# 默认目标
help:
	@echo "Web Performance Monitor - 可用命令:"
	@echo ""
	@echo "开发命令:"
	@echo "  dev-install    安装开发依赖"
	@echo "  test          运行测试"
	@echo "  format        格式化代码"
	@echo "  lint          代码检查"
	@echo "  check         检查代码质量"
	@echo ""
	@echo "构建命令:"
	@echo "  clean         清理构建文件"
	@echo "  build         构建包"
	@echo "  install       本地安装测试"
	@echo ""
	@echo "发布命令:"
	@echo "  upload-test   上传到测试PyPI"
	@echo "  upload        上传到正式PyPI"
	@echo ""
	@echo "快捷命令:"
	@echo "  quick-build   快速构建和测试"
	@echo "  release-test  发布到测试PyPI"
	@echo "  release       发布到正式PyPI"

# 清理构建文件
clean:
	@echo "🧹 清理构建文件..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# 安装开发依赖
dev-install:
	@echo "📦 安装开发依赖..."
	pip install -e ".[dev]"
	pip install build twine

# 运行测试
test:
	@echo "🧪 运行测试..."
	python -m pytest tests/ -v --cov=web_performance_monitor --cov-report=term-missing

# 格式化代码
format:
	@echo "🎨 格式化代码..."
	black web_performance_monitor/ tests/ examples/
	isort web_performance_monitor/ tests/ examples/

# 代码检查
lint:
	@echo "🔍 代码检查..."
	flake8 web_performance_monitor/ tests/
	mypy web_performance_monitor/

# 检查代码质量
check: format lint test
	@echo "✅ 代码质量检查完成"

# 构建包
build: clean
	@echo "📦 构建包..."
	python -m build
	@echo "📋 生成的文件:"
	@ls -la dist/

# 检查包
check-package:
	@echo "🔍 检查包..."
	twine check dist/*

# 本地安装测试
install: build check-package
	@echo "📦 本地安装测试..."
	python scripts/build_and_test.py

# 上传到测试PyPI
upload-test: build check-package
	@echo "📤 上传到测试PyPI..."
	twine upload --repository testpypi dist/*

# 上传到正式PyPI
upload: build check-package
	@echo "📤 上传到正式PyPI..."
	twine upload dist/*

# 快速构建和测试
quick-build: clean build install
	@echo "✅ 快速构建和测试完成"

# 发布到测试PyPI
release-test: check build upload-test
	@echo "🎉 已发布到测试PyPI"
	@echo "测试安装: pip install --index-url https://test.pypi.org/simple/ web-performance-monitor"

# 发布到正式PyPI
release: check build upload
	@echo "🎉 已发布到正式PyPI"
	@echo "安装: pip install web-performance-monitor"

# 版本更新
bump-patch:
	@echo "⬆️ 更新补丁版本..."
	@python -c "import re; f='setup.py'; c=open(f).read(); v=re.search(r'version=\"(\d+)\.(\d+)\.(\d+)\"', c); nv=f'{v[1]}.{v[2]}.{int(v[3])+1}'; open(f, 'w').write(re.sub(r'version=\"\d+\.\d+\.\d+\"', f'version=\"{nv}\"', c)); print(f'版本更新为: {nv}')"

bump-minor:
	@echo "⬆️ 更新次版本..."
	@python -c "import re; f='setup.py'; c=open(f).read(); v=re.search(r'version=\"(\d+)\.(\d+)\.(\d+)\"', c); nv=f'{v[1]}.{int(v[2])+1}.0'; open(f, 'w').write(re.sub(r'version=\"\d+\.\d+\.\d+\"', f'version=\"{nv}\"', c)); print(f'版本更新为: {nv}')"

bump-major:
	@echo "⬆️ 更新主版本..."
	@python -c "import re; f='setup.py'; c=open(f).read(); v=re.search(r'version=\"(\d+)\.(\d+)\.(\d+)\"', c); nv=f'{int(v[1])+1}.0.0'; open(f, 'w').write(re.sub(r'version=\"\d+\.\d+\.\d+\"', f'version=\"{nv}\"', c)); print(f'版本更新为: {nv}')"