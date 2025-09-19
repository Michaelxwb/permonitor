"""
依赖故障排除示例

演示如何诊断和解决依赖相关问题。
"""

import sys
import os
from typing import Dict, List, Any, Optional

print("=== 依赖故障排除示例 ===\n")

class DependencyTroubleshooter:
    """依赖故障排除器"""
    
    def __init__(self):
        self.issues = []
        self.solutions = []
    
    def run_full_diagnosis(self):
        """运行完整诊断"""
        print("1. 开始完整依赖诊断...")
        
        # 基础环境检查
        self.check_python_version()
        self.check_pip_version()
        self.check_virtual_environment()
        
        # 包安装检查
        self.check_core_dependencies()
        self.check_framework_dependencies()
        self.check_optional_dependencies()
        
        # 版本兼容性检查
        self.check_version_compatibility()
        
        # 导入测试
        self.test_imports()
        
        # 配置检查
        self.check_configuration()
        
        # 生成报告
        self.generate_report()
    
    def check_python_version(self):
        """检查Python版本"""
        print("\n2. Python环境检查:")
        
        python_version = sys.version_info
        version_str = f"{python_version.major}.{python_version.minor}.{python_version.micro}"
        
        print(f"   Python版本: {version_str}")
        
        if python_version < (3, 7):
            self.issues.append("Python版本过低")
            self.solutions.append("升级到Python 3.7或更高版本")
            print("   ❌ Python版本过低，需要3.7+")
        else:
            print("   ✅ Python版本符合要求")
        
        print(f"   Python路径: {sys.executable}")
        print(f"   平台: {sys.platform}")
    
    def check_pip_version(self):
        """检查pip版本"""
        print("\n3. pip检查:")
        
        try:
            import subprocess
            result = subprocess.run([sys.executable, '-m', 'pip', '--version'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                pip_version = result.stdout.strip()
                print(f"   pip版本: {pip_version}")
                print("   ✅ pip可用")
            else:
                self.issues.append("pip不可用")
                self.solutions.append("重新安装pip: python -m ensurepip --upgrade")
                print("   ❌ pip不可用")
        
        except Exception as e:
            self.issues.append(f"pip检查失败: {e}")
            self.solutions.append("检查Python安装是否完整")
            print(f"   ❌ pip检查失败: {e}")
    
    def check_virtual_environment(self):
        """检查虚拟环境"""
        print("\n4. 虚拟环境检查:")
        
        in_venv = hasattr(sys, 'real_prefix') or (
            hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
        )
        
        if in_venv:
            print("   ✅ 运行在虚拟环境中")
            print(f"   虚拟环境路径: {sys.prefix}")
        else:
            print("   ⚠️ 未使用虚拟环境")
            self.solutions.append("建议使用虚拟环境: python -m venv myenv")
        
        # 检查环境变量
        virtual_env = os.getenv('VIRTUAL_ENV')
        if virtual_env:
            print(f"   VIRTUAL_ENV: {virtual_env}")
    
    def check_core_dependencies(self):
        """检查核心依赖"""
        print("\n5. 核心依赖检查:")
        
        core_deps = {
            'pyinstrument': '4.6.0',
            'requests': '2.25.0'
        }
        
        for package, min_version in core_deps.items():
            self._check_package(package, min_version, required=True)
    
    def check_framework_dependencies(self):
        """检查框架依赖"""
        print("\n6. 框架依赖检查:")
        
        framework_deps = {
            'flask': {
                'packages': {'flask': '2.0.0'},
                'description': 'Flask web框架'
            },
            'fastapi': {
                'packages': {
                    'fastapi': '0.100.0',
                    'uvicorn': '0.20.0',
                    'aiofiles': '24.1.0',
                    'aiohttp': '3.12.0'
                },
                'description': 'FastAPI异步web框架'
            }
        }
        
        for framework, info in framework_deps.items():
            print(f"\n   {framework} ({info['description']}):")
            
            all_available = True
            for package, min_version in info['packages'].items():
                available = self._check_package(package, min_version, required=False, indent="     ")
                if not available:
                    all_available = False
            
            if all_available:
                print(f"     ✅ {framework} 完全可用")
            else:
                print(f"     ⚠️ {framework} 部分可用或不可用")
                self.solutions.append(f"安装{framework}支持: pip install web-performance-monitor[{framework}]")
    
    def check_optional_dependencies(self):
        """检查可选依赖"""
        print("\n7. 可选依赖检查:")
        
        optional_deps = {
            'mattermostdriver': {
                'min_version': '7.0.0',
                'description': 'Mattermost通知支持',
                'install_group': 'notifications'
            }
        }
        
        for package, info in optional_deps.items():
            print(f"\n   {package} ({info['description']}):")
            available = self._check_package(package, info['min_version'], required=False, indent="     ")
            
            if not available:
                self.solutions.append(f"安装{info['description']}: pip install web-performance-monitor[{info['install_group']}]")
    
    def _check_package(self, package_name: str, min_version: str, required: bool = True, indent: str = "   ") -> bool:
        """检查单个包"""
        try:
            # 尝试导入包
            module = __import__(package_name)
            
            # 获取版本
            version = getattr(module, '__version__', 'unknown')
            print(f"{indent}✅ {package_name} v{version}")
            
            # 检查版本兼容性
            if version != 'unknown' and min_version:
                try:
                    from packaging import version as pkg_version
                    if pkg_version.parse(version) < pkg_version.parse(min_version):
                        print(f"{indent}⚠️ 版本过低，需要 >= {min_version}")
                        if required:
                            self.issues.append(f"{package_name} 版本过低")
                            self.solutions.append(f"升级{package_name}: pip install --upgrade {package_name}")
                        return False
                except ImportError:
                    # 没有packaging库，跳过版本检查
                    pass
            
            return True
            
        except ImportError:
            print(f"{indent}❌ {package_name} 未安装")
            if required:
                self.issues.append(f"{package_name} 未安装")
                self.solutions.append(f"安装{package_name}: pip install {package_name}")
            return False
        
        except Exception as e:
            print(f"{indent}❌ {package_name} 检查失败: {e}")
            if required:
                self.issues.append(f"{package_name} 检查失败")
            return False
    
    def check_version_compatibility(self):
        """检查版本兼容性"""
        print("\n8. 版本兼容性检查:")
        
        try:
            from web_performance_monitor.core.conflict_resolver import ConflictResolver, DependencyInfo
            
            resolver = ConflictResolver()
            
            # 创建依赖信息
            dependencies = [
                DependencyInfo("pyinstrument", version_spec=">=4.6.0", required_by=["core"]),
                DependencyInfo("requests", version_spec=">=2.25.0", required_by=["core"]),
                DependencyInfo("flask", version_spec=">=2.0.0", required_by=["flask_support"]),
                DependencyInfo("fastapi", version_spec=">=0.100.0", required_by=["fastapi_support"]),
                DependencyInfo("uvicorn", version_spec=">=0.20.0", required_by=["fastapi_support"]),
                DependencyInfo("mattermostdriver", version_spec=">=7.0.0", required_by=["notifications"])
            ]
            
            # 检测冲突
            result = resolver.analyze_and_resolve(dependencies)
            
            if result['total_conflicts'] == 0:
                print("   ✅ 没有检测到版本冲突")
            else:
                print(f"   ⚠️ 检测到 {result['total_conflicts']} 个版本冲突")
                
                for conflict in result['conflicts']:
                    print(f"     - {conflict.description}")
                    self.issues.append(conflict.description)
                
                # 添加解决方案
                for step in result['resolution_plan']:
                    for action in step['actions']:
                        self.solutions.append(action)
        
        except Exception as e:
            print(f"   ❌ 版本兼容性检查失败: {e}")
            self.issues.append("版本兼容性检查失败")
    
    def test_imports(self):
        """测试导入"""
        print("\n9. 导入测试:")
        
        import_tests = [
            ('web_performance_monitor', '核心模块'),
            ('web_performance_monitor.utils.framework_detector', '框架检测器'),
            ('web_performance_monitor.utils.dependency_manager', '依赖管理器'),
            ('web_performance_monitor.core.plugin_system', '插件系统'),
            ('web_performance_monitor.monitors.factory', '监控器工厂'),
            ('web_performance_monitor.config.unified_config', '统一配置')
        ]
        
        for module_name, description in import_tests:
            try:
                __import__(module_name)
                print(f"   ✅ {description} 导入成功")
            except ImportError as e:
                print(f"   ❌ {description} 导入失败: {e}")
                self.issues.append(f"{description} 导入失败")
                self.solutions.append(f"检查 {module_name} 模块安装")
            except Exception as e:
                print(f"   ❌ {description} 导入错误: {e}")
                self.issues.append(f"{description} 导入错误")
    
    def check_configuration(self):
        """检查配置"""
        print("\n10. 配置检查:")
        
        # 检查环境变量
        env_vars = [
            'WPM_DEPENDENCY_CHECK_MODE',
            'WPM_SKIP_DEPENDENCY_CHECK',
            'WPM_STRICT_MODE',
            'WPM_DEBUG',
            'WPM_LOG_LEVEL'
        ]
        
        print("   环境变量:")
        for var in env_vars:
            value = os.getenv(var)
            if value:
                print(f"     {var} = {value}")
            else:
                print(f"     {var} = (未设置)")
        
        # 检查配置文件
        try:
            from web_performance_monitor.config.unified_config import UnifiedConfig
            
            config = UnifiedConfig()
            print("\n   配置状态:")
            print(f"     依赖检查模式: {config.dependency_config.check_mode}")
            print(f"     跳过依赖检查: {config.dependency_config.skip_dependency_check}")
            print(f"     严格模式: {config.dependency_config.strict_mode}")
            print("   ✅ 配置加载成功")
            
        except Exception as e:
            print(f"   ❌ 配置加载失败: {e}")
            self.issues.append("配置加载失败")
            self.solutions.append("检查配置文件和环境变量设置")
    
    def generate_report(self):
        """生成诊断报告"""
        print("\n" + "="*50)
        print("诊断报告")
        print("="*50)
        
        if not self.issues:
            print("\n✅ 恭喜！没有发现任何问题。")
            print("   您的环境配置正确，可以正常使用web-performance-monitor。")
        else:
            print(f"\n⚠️ 发现 {len(self.issues)} 个问题:")
            for i, issue in enumerate(self.issues, 1):
                print(f"   {i}. {issue}")
            
            print(f"\n🛠️ 建议的解决方案:")
            for i, solution in enumerate(set(self.solutions), 1):
                print(f"   {i}. {solution}")
        
        print("\n" + "="*50)
        print("额外建议")
        print("="*50)
        
        print("\n1. 如果遇到安装问题:")
        print("   - 确保使用最新版本的pip: python -m pip install --upgrade pip")
        print("   - 清理pip缓存: pip cache purge")
        print("   - 使用虚拟环境避免依赖冲突")
        
        print("\n2. 如果遇到导入问题:")
        print("   - 检查Python路径和PYTHONPATH环境变量")
        print("   - 确保在正确的虚拟环境中运行")
        print("   - 重新安装包: pip uninstall web-performance-monitor && pip install web-performance-monitor[all]")
        
        print("\n3. 如果遇到版本冲突:")
        print("   - 创建新的虚拟环境")
        print("   - 使用pip-tools管理依赖版本")
        print("   - 查看详细的依赖树: pip show web-performance-monitor")
        
        print("\n4. 获取帮助:")
        print("   - 查看文档: https://github.com/your-repo/web-performance-monitor")
        print("   - 提交issue: https://github.com/your-repo/web-performance-monitor/issues")
        print("   - 运行详细诊断: python -m web_performance_monitor.utils.diagnostics")

def run_quick_check():
    """运行快速检查"""
    print("快速依赖检查:")
    
    try:
        # 检查核心导入
        import web_performance_monitor
        print("✅ 核心模块可用")
        
        # 检查依赖状态
        status = web_performance_monitor.get_dependency_status()
        print(f"✅ 支持的框架: {status.get('supported_frameworks', [])}")
        print(f"✅ 可用的框架: {status.get('available_frameworks', [])}")
        
        if status.get('warnings'):
            print(f"⚠️ 警告: {len(status['warnings'])} 个")
            for warning in status['warnings'][:3]:  # 只显示前3个
                print(f"   - {warning}")
        
        return True
        
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        print("建议运行完整诊断以获取详细信息")
        return False
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False

def main():
    """主函数"""
    print("选择诊断模式:")
    print("1. 快速检查")
    print("2. 完整诊断")
    print("3. 自动修复（实验性）")
    
    try:
        choice = input("\n请选择 (1-3): ").strip()
    except KeyboardInterrupt:
        print("\n\n诊断已取消")
        return
    
    if choice == '1':
        print("\n" + "="*30)
        run_quick_check()
    elif choice == '2':
        print("\n" + "="*30)
        troubleshooter = DependencyTroubleshooter()
        troubleshooter.run_full_diagnosis()
    elif choice == '3':
        print("\n自动修复功能正在开发中...")
        print("目前请根据诊断报告手动解决问题")
    else:
        print("\n无效选择，运行快速检查:")
        run_quick_check()

if __name__ == "__main__":
    main()

print("\n=== 依赖故障排除示例完成 ===")