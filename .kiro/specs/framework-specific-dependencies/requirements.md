# Requirements Document

## Introduction

本文档定义了web_performance_monitor包的框架特定依赖管理功能需求。该功能旨在解决当前包安装时会强制安装所有框架依赖（如aiofiles、aiohttp等）的问题，通过实现智能的依赖管理机制，让用户能够根据实际使用的Python web框架（Flask、FastAPI等）只安装必要的依赖包，从而减少不必要的依赖冲突和安装体积。

该功能的核心价值在于提供更灵活、更轻量的包安装体验，支持可选依赖和框架检测，让开发者能够按需安装依赖。

## Requirements

### Requirement 1

**User Story:** 作为一名Python开发者，我希望安装web_performance_monitor时只安装核心依赖，以便减少不必要的包体积和依赖冲突。

#### Acceptance Criteria

1. WHEN 用户执行`pip install web-performance-monitor`时 THEN 系统 SHALL 只安装核心依赖（pyinstrument、requests等）
2. WHEN 核心包被安装 THEN 系统 SHALL 不自动安装框架特定依赖（aiofiles、aiohttp、fastapi、uvicorn等）
3. WHEN 用户导入包但缺少框架依赖时 THEN 系统 SHALL 提供清晰的错误提示和安装建议
4. WHEN 核心功能被使用时 THEN 系统 SHALL 确保基础监控功能正常工作，不依赖特定框架

### Requirement 2

**User Story:** 作为一名Flask开发者，我希望能够安装Flask特定的依赖包，以便使用完整的Flask监控功能。

#### Acceptance Criteria

1. WHEN 用户执行`pip install web-performance-monitor[flask]`时 THEN 系统 SHALL 安装Flask相关依赖
2. WHEN Flask依赖被安装 THEN 系统 SHALL 包含flask>=2.0.0和其他Flask特定依赖
3. WHEN Flask模式被使用时 THEN 系统 SHALL 提供完整的Flask中间件和装饰器功能
4. WHEN Flask依赖缺失时 THEN 系统 SHALL 在运行时检测并提供安装建议

### Requirement 3

**User Story:** 作为一名FastAPI开发者，我希望能够安装FastAPI特定的依赖包，以便使用异步监控功能。

#### Acceptance Criteria

1. WHEN 用户执行`pip install web-performance-monitor[fastapi]`时 THEN 系统 SHALL 安装FastAPI相关依赖
2. WHEN FastAPI依赖被安装 THEN 系统 SHALL 包含fastapi>=0.100.0、uvicorn>=0.20.0、aiofiles>=24.1.0、aiohttp>=3.12.0
3. WHEN FastAPI模式被使用时 THEN 系统 SHALL 提供完整的异步监控和中间件功能
4. WHEN 异步功能被调用但缺少依赖时 THEN 系统 SHALL 提供具体的依赖安装指导

### Requirement 4

**User Story:** 作为一名全栈开发者，我希望能够同时安装多个框架的依赖，以便在不同项目中使用不同框架。

#### Acceptance Criteria

1. WHEN 用户执行`pip install web-performance-monitor[all]`时 THEN 系统 SHALL 安装所有支持框架的依赖
2. WHEN 用户执行`pip install web-performance-monitor[flask,fastapi]`时 THEN 系统 SHALL 安装指定框架的依赖
3. WHEN 多框架依赖被安装 THEN 系统 SHALL 确保依赖版本兼容性
4. WHEN 使用任何已安装框架时 THEN 系统 SHALL 自动检测并启用相应功能

### Requirement 5

**User Story:** 作为一名开发者，我希望系统能够自动检测当前环境中的框架，以便提供智能的依赖建议。

#### Acceptance Criteria

1. WHEN 系统启动时 THEN 系统 SHALL 检测当前环境中已安装的web框架
2. WHEN 检测到Flask但缺少监控依赖时 THEN 系统 SHALL 建议安装`pip install web-performance-monitor[flask]`
3. WHEN 检测到FastAPI但缺少异步依赖时 THEN 系统 SHALL 建议安装`pip install web-performance-monitor[fastapi]`
4. WHEN 未检测到任何框架时 THEN 系统 SHALL 提供框架选择指导

### Requirement 6

**User Story:** 作为一名系统管理员，我希望能够通过环境变量控制依赖检查行为，以便在不同部署环境中灵活配置。

#### Acceptance Criteria

1. WHEN 设置环境变量`WPM_SKIP_DEPENDENCY_CHECK=true`时 THEN 系统 SHALL 跳过运行时依赖检查
2. WHEN 设置环境变量`WPM_STRICT_DEPENDENCIES=true`时 THEN 系统 SHALL 在缺少依赖时抛出异常而非警告
3. WHEN 设置环境变量`WPM_AUTO_INSTALL_DEPS=true`时 THEN 系统 SHALL 尝试自动安装缺失的依赖（仅在开发环境）
4. WHEN 环境变量配置无效时 THEN 系统 SHALL 使用默认行为并记录警告

### Requirement 7

**User Story:** 作为一名包维护者，我希望能够轻松添加新框架的依赖支持，以便扩展包的适用范围。

#### Acceptance Criteria

1. WHEN 添加新框架支持时 THEN 系统 SHALL 支持通过配置文件定义新的依赖组
2. WHEN 新框架被添加时 THEN 系统 SHALL 自动支持`pip install web-performance-monitor[new-framework]`语法
3. WHEN 框架依赖配置更新时 THEN 系统 SHALL 保持向后兼容性
4. WHEN 依赖冲突发生时 THEN 系统 SHALL 提供清晰的冲突解决建议

### Requirement 8

**User Story:** 作为一名开发者，我希望获得清晰的依赖状态信息，以便了解当前安装的功能范围。

#### Acceptance Criteria

1. WHEN 导入包时 THEN 系统 SHALL 在日志中显示已安装的框架支持状态
2. WHEN 调用`monitor.get_supported_frameworks()`时 THEN 系统 SHALL 返回当前支持的框架列表
3. WHEN 调用`monitor.check_dependencies()`时 THEN 系统 SHALL 返回详细的依赖检查报告
4. WHEN 依赖状态发生变化时 THEN 系统 SHALL 提供相应的状态更新通知