# Vertex 桌面端应用

## 概述

Vertex 现在支持桌面端模式，使用 PyWebView 将 Gradio Web 应用封装为原生桌面应用，提供更好的用户体验。

## 功能特性

- 🖥️ **原生桌面体验**：独立的桌面窗口，无需浏览器
- 🎨 **完整功能**：包含所有 Web 版本的功能
- ⚡ **快速启动**：无需手动打开浏览器
- 🔧 **易于使用**：与 Web 版本相同的操作界面
- 📱 **响应式设计**：支持窗口大小调整

## 安装依赖

### 安装项目依赖（推荐）

```bash
# 安装项目依赖（包含桌面端支持）
pip install -e .

# 或使用uv安装
uv pip install -e .
```

### 可选依赖组安装

```bash
# 使用 uv 安装可选依赖组
uv add --optional desktop

# 或使用 pip 安装可选依赖组
pip install "vertex[desktop]"
```

### 直接安装PyWebView

```bash
# 使用 uv 安装
uv add pywebview

# 或使用 pip 安装
pip install pywebview
```

### 从源码安装

```bash
# 克隆项目后安装
git clone https://github.com/ashione/vertex.git
cd vertex
pip install -e .
# 或
uv pip install -e .
```

## 使用方法

### 通过 CLI 启动

```bash
# 启动桌面端模式
vertex --desktop

# 启动桌面端工作流编辑器
vertex workflow --desktop

# 启动桌面端RAG系统
vertex rag --desktop

# 指定端口和配置
vertex --desktop --port 7861 --config config/llm.yml
```

### 直接运行桌面应用

```bash
# 直接运行桌面应用模块
python -m vertex_flow.src.desktop_app

# 指定参数
python -m vertex_flow.src.desktop_app --port 7861 --width 1400 --height 900
```

### 可用参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--desktop` | 启用桌面端模式 | - |
| `--port` | 服务器端口 | 7860 |
| `--host` | 服务器主机地址 | 127.0.0.1 |
| `--config` | 配置文件路径 | - |
| `--title` | 窗口标题 | Vertex - AI工作流系统 |
| `--width` | 窗口宽度 | 1200 |
| `--height` | 窗口高度 | 800 |

## 技术架构

### 组件结构

```
DesktopApp
├── DeepResearchApp (核心应用逻辑)
├── Gradio Interface (Web界面)
└── PyWebView Window (桌面窗口)
```

### 工作流程

1. **启动服务器**：在后台线程中启动 Gradio 服务器
2. **创建窗口**：使用 PyWebView 创建桌面窗口
3. **加载应用**：将 Gradio 应用加载到桌面窗口中
4. **用户交互**：用户通过桌面窗口与应用交互

### 优势

- **性能优化**：服务器在后台运行，减少资源占用
- **稳定性**：独立的桌面进程，避免浏览器兼容性问题
- **用户体验**：原生桌面应用体验，支持系统集成
- **开发友好**：基于现有的 Web 应用，无需重写界面

## 故障排除

### 常见问题

#### 1. PyWebView 未安装

**错误信息**：
```
警告: PyWebView未安装，桌面端功能不可用
```

**解决方案**：
```bash
# 安装项目依赖（包含桌面端支持）
pip install -e .
# 或
uv pip install -e .

# 或直接安装PyWebView
pip install pywebview
```

#### 2. 端口被占用

**错误信息**：
```
Address already in use
```

**解决方案**：
```bash
# 使用不同端口
vertex dr --desktop --port 7861
```

#### 3. 窗口无法显示

**可能原因**：
- 系统缺少图形界面支持
- PyWebView 后端问题

**解决方案**：
```bash
# 尝试不同的后端
export WEBVIEW_GUI=gtk  # Linux
export WEBVIEW_GUI=cocoa  # macOS
export WEBVIEW_GUI=cef  # Windows
```

### 调试模式

```bash
# 启用调试模式
vertex dr --desktop --dev

# 查看详细日志
export WEBVIEW_DEBUG=1
vertex dr --desktop
```

## 开发说明

### 自定义窗口设置

```python
from vertex_flow.src.desktop_app import create_desktop_app

# 创建自定义桌面应用
desktop_app = create_desktop_app(
    config_path="config/llm.yml",
    host="127.0.0.1",
    port=7860,
    window_title="我的Vertex应用",
    window_width=1400,
    window_height=900
)
```

### 扩展桌面应用

```python
from vertex_flow.src.desktop_app import DesktopApp

class CustomDesktopApp(DesktopApp):
    def __init__(self, config_path=None):
        super().__init__(config_path, app_type="workflow_app")
    
    def custom_method(self):
        # 自定义功能
        pass
```

## 系统要求

- **操作系统**：Windows 10+, macOS 10.15+, Linux (Ubuntu 18.04+)
- **Python**：3.8+
- **内存**：至少 4GB RAM
- **存储**：至少 1GB 可用空间

## 更新日志

### v0.1.0
- 初始桌面端支持
- 支持 PyWebView 封装
- 支持多种应用类型（Workflow、Deep Research、RAG）
- 支持自定义窗口参数 