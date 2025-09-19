"""
基本使用示例

演示web-performance-monitor的基本使用方法。
"""

# 1. 基本导入和依赖检查
print("=== 基本使用示例 ===\n")

# 检查依赖状态
try:
    from web_performance_monitor import check_dependencies, get_dependency_status
    
    print("1. 检查依赖状态:")
    status = get_dependency_status()
    print(f"   支持的框架: {status.get('supported_frameworks', [])}")
    print(f"   可用的框架: {status.get('available_frameworks', [])}")
    print(f"   警告数量: {len(status.get('warnings', []))}")
    print()
    
    # 详细依赖报告
    print("2. 详细依赖报告:")
    report = check_dependencies()
    print(report)
    print()
    
except ImportError as e:
    print(f"导入失败: {e}")
    print("请确保已安装web-performance-monitor")
    print("安装命令: pip install web-performance-monitor[all]")
    exit(1)

# 2. 自动框架检测
print("3. 自动框架检测:")
try:
    from web_performance_monitor.utils.framework_detector import FrameworkDetector
    
    detector = FrameworkDetector()
    
    # 检测已安装的框架
    installed_frameworks = detector.detect_installed_frameworks()
    print(f"   已安装的框架: {installed_frameworks}")
    
    # 检测项目中使用的框架
    project_framework = detector.detect_framework_from_environment()
    print(f"   项目框架: {project_framework}")
    
    # 获取框架版本信息
    for framework in installed_frameworks:
        version = detector.get_framework_version(framework)
        print(f"   {framework} 版本: {version}")
    
    print()
    
except Exception as e:
    print(f"框架检测失败: {e}")

# 3. 创建监控器
print("4. 创建监控器:")
try:
    from web_performance_monitor import create_web_monitor
    
    # 自动检测并创建监控器
    monitor = create_web_monitor()
    print(f"   自动创建的监控器: {type(monitor).__name__}")
    
    # 指定框架创建监控器
    if 'flask' in installed_frameworks:
        flask_monitor = create_web_monitor('flask')
        print(f"   Flask监控器: {type(flask_monitor).__name__}")
    
    if 'fastapi' in installed_frameworks:
        fastapi_monitor = create_web_monitor('fastapi')
        print(f"   FastAPI监控器: {type(fastapi_monitor).__name__}")
    
    print()
    
except Exception as e:
    print(f"创建监控器失败: {e}")

# 4. 获取安装建议
print("5. 安装建议:")
try:
    from web_performance_monitor.utils.installation_guide import InstallationGuide
    
    guide = InstallationGuide()
    
    # 生成个性化安装指导
    env_guide = guide.generate_environment_specific_guide()
    print(f"   环境指导: {env_guide.get('summary', '已生成')}")
    if 'recommendations' in env_guide and env_guide['recommendations']:
        print("   安装建议:")
        for rec in env_guide['recommendations'][:3]:  # 只显示前3个
            if isinstance(rec, dict):
                print(f"     - {rec.get('description', 'N/A')}: {rec.get('command', 'N/A')}")
            else:
                print(f"     - {rec}")
    else:
        print("   ✅ 当前环境配置良好，无需额外安装")
    
    # 获取快速安装命令
    quick_command = guide.generate_installation_command(['all'])
    print(f"快速安装命令: {quick_command}")
    print()
    
except Exception as e:
    print(f"获取安装建议失败: {e}")

# 5. 插件系统使用
print("6. 插件系统:")
try:
    from web_performance_monitor.core.plugin_system import get_plugin_manager
    
    plugin_manager = get_plugin_manager()
    
    # 获取所有可用框架
    available_frameworks = plugin_manager.get_available_frameworks()
    print(f"   可用框架: {available_frameworks}")
    
    # 获取框架信息
    for framework in available_frameworks:
        info = plugin_manager.get_framework_info(framework)
        if info:
            metadata = info['metadata']
            status = info['status']
            print(f"   {framework}:")
            print(f"     描述: {metadata['description']}")
            print(f"     版本要求: {metadata['version_range']}")
            print(f"     已安装: {status['installed']}")
            print(f"     版本: {status['version']}")
    
    print()
    
except Exception as e:
    print(f"插件系统使用失败: {e}")

# 6. 冲突检测
print("7. 冲突检测:")
try:
    from web_performance_monitor.core.conflict_resolver import ConflictResolver, DependencyInfo
    
    resolver = ConflictResolver()
    
    # 创建依赖信息进行测试
    dependencies = [
        DependencyInfo("flask", version_spec=">=2.0.0", required_by=["app"]),
        DependencyInfo("fastapi", version_spec=">=0.100.0", required_by=["app"]),
        DependencyInfo("mattermostdriver", version_spec=">=7.0.0", required_by=["notifications"])
    ]
    
    # 分析冲突
    result = resolver.analyze_and_resolve(dependencies)
    
    print(f"   检测到的冲突数量: {result['total_conflicts']}")
    print(f"   有严重冲突: {result['has_critical_conflicts']}")
    
    if result['total_conflicts'] > 0:
        print("   冲突报告:")
        print(result['report'])
    else:
        print("   ✅ 没有检测到依赖冲突")
    
    print()
    
except Exception as e:
    print(f"冲突检测失败: {e}")

print("=== 基本使用示例完成 ===")