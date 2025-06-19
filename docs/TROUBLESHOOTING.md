# Vertex 故障排除指南

本文档列出了常见的Vertex启动和运行问题及其解决方案。

## 🚨 常见启动错误

### 1. Gradio Launch 错误

**错误信息**：
```
ValueError: When localhost is not accessible, a shareable link must be created. Please set share=True or check your proxy settings to allow access to localhost.
```

**原因**：
- 网络配置问题，localhost访问受限
- 代理设置阻止本地访问
- 端口被占用或防火墙限制

**错误信息**：
```
File "gradio/tunneling.py", line 60, in download_binary
    resp = httpx.get(BINARY_URL, timeout=30)
```

**原因**：
- Gradio无法下载隧道服务所需的二进制文件
- 网络连接问题（特别是在中国大陆）
- 防火墙或代理阻止了对gradio服务器的访问

**解决方案**：
1. **检查端口占用**：
   ```bash
   # 检查默认端口7860是否被占用
   lsof -i :7860
   
   # 使用其他端口启动
   vertex run --port 8080
   ```

2. **检查网络配置**：
   ```bash
   # 测试localhost连接
   curl http://localhost:7860
   ```

3. **配置代理设置**：
   ```bash
   # 临时禁用代理
   unset http_proxy https_proxy
   
   # 或配置代理白名单
   export no_proxy="localhost,127.0.0.1"
   ```

4. **网络连接问题（隧道下载失败）**：
   ```bash
   # 方法1: 使用国内网络或VPN
   # 方法2: 仅本地访问，不使用共享链接
   vertex run --port 8080  # 程序会自动尝试多种启动方式
   
   # 方法3: 手动设置仅本地访问
   export VERTEX_LOCAL_ONLY=true
   vertex run
   ```

5. **强制本地模式**：
   ```bash
   # 如果网络有问题，可以强制使用本地模式
   # 修改配置文件，设置 share=False
   vertex config check
   ```

### 2. 配置文件错误

**错误信息**：
```
FileNotFoundError: config file not found
```

**解决方案**：
```bash
# 初始化配置文件
vertex config init

# 检查配置状态
vertex config check

# 重置配置
vertex config reset
```

### 3. 依赖包冲突

**错误信息**：
```
TypeError: argument of type 'bool' is not iterable
File "/gradio_client/utils.py", line 863, in get_type
    if "const" in schema:
```

**原因**：
- Gradio版本不兼容（4.x vs 3.x API变化）
- gradio_client内部的schema处理错误
- 代码中使用了已弃用的Gradio API

**解决方案**：
1. **更新依赖包到兼容版本**：
   ```bash
   # 更新到支持的Gradio 4.x版本
   pip install "gradio>=4.0.0,<5.0.0"
   pip install --upgrade vertex
   ```

2. **完全重新安装**：
   ```bash
   pip uninstall vertex gradio gradio-client
   pip install vertex
   ```

3. **如果问题持续，降级到稳定版本**：
   ```bash
   pip install "gradio==4.44.0"  # 使用特定版本
   ```

4. **检查和清理环境**：
   ```bash
   # 检查当前版本
   pip list | grep gradio
   
   # 清理pip缓存
   pip cache purge
   
   # 重新安装
   pip install --no-cache-dir vertex
   ```

### 4. 端口冲突

**错误信息**：
```
OSError: [Errno 48] Address already in use
```

**解决方案**：
```bash
# 查找占用端口的进程
lsof -i :7860

# 终止进程（替换PID）
kill -9 <PID>

# 或使用其他端口
vertex run --port 8080
vertex workflow --port 8081
```

## 🔧 环境变量配置

### 端口覆盖
```bash
# 设置标准模式端口
export VERTEX_PORT=8080

# 设置工作流模式端口
export VERTEX_WORKFLOW_PORT=8081
```

### API密钥配置
```bash
export llm_deepseek_sk="your-deepseek-key"
export llm_openrouter_sk="your-openrouter-key"
export llm_tongyi_sk="your-tongyi-key"
```

## 🚀 快速诊断

遇到启动问题时，请按顺序尝试以下诊断步骤：

```bash
# 1. 基础检查
vertex --help                    # 检查CLI是否正常
vertex config check              # 检查配置状态

# 2. 网络和端口检查  
lsof -i :7860                   # 检查默认端口
netstat -tulpn | grep :7860     # 替代命令

# 3. 尝试不同启动方式
vertex run --port 8080          # 使用不同端口
vertex run --host 127.0.0.1     # 仅本地访问

# 4. 检查错误日志
tail -f ~/.vertex/logs/vertex.log  # 查看详细日志
```

## 🐛 调试技巧

### 1. 启用详细日志
```bash
# 设置日志级别
export VERTEX_LOG_LEVEL=DEBUG

# 查看日志文件
tail -f ~/.vertex/logs/vertex.log
```

### 2. 检查系统信息
```bash
# 检查Python版本
python --version  # 需要 >= 3.9

# 检查依赖包
pip list | grep -E "(gradio|vertex|torch)"

# 检查网络连接
ping localhost
```

### 3. 最小化测试
```bash
# 测试CLI是否正常
vertex --help

# 测试配置是否正确
vertex config check

# 测试基础功能
vertex rag --show-stats
```

## 📞 获取帮助

如果问题依然存在，请：

1. **收集信息**：
   - 错误的完整堆栈跟踪
   - 系统信息（OS、Python版本）
   - 使用的命令

2. **创建Issue**：
   - 访问 [GitHub Issues](https://github.com/ashione/vertex/issues)
   - 提供详细的错误描述和复现步骤

3. **查看文档**：
   - [CLI使用指南](CLI_USAGE.md)
   - [RAG使用指南](RAG_CLI_USAGE.md)
   - [性能优化](RAG_PERFORMANCE_OPTIMIZATION.md) 