# 配置文件脱敏说明

## 概述

本项目提供了自动脱敏功能，用于在提交代码前自动对配置文件中的敏感信息（如API密钥、访问令牌等）进行脱敏处理，确保敏感信息不会被意外提交到代码仓库中。

## 脱敏机制

### 自动脱敏

1. **Pre-commit Hook**: 在每次提交前，`scripts/precommit.sh` 会自动运行脱敏脚本
2. **CI/CD检查**: GitHub Actions 会检查配置文件是否已正确脱敏
3. **手动脱敏**: 可以手动运行脱敏脚本

### 脱敏规则

脱敏脚本 `scripts/sanitize_config.py` 会处理以下类型的敏感信息：

#### SK (Secret Key) 脱敏
- **原始格式**: `sk: ${llm.deepseek.sk:sk-[ACTUAL_KEY]}`
- **脱敏后**: `sk: ${llm.deepseek.sk:sk-***SANITIZED***}`

- **原始格式**: `sk: ${llm.openrouter.sk:sk-or-v1-[ACTUAL_KEY]}`
- **脱敏后**: `sk: ${llm.openrouter.sk:sk-or-***SANITIZED***}`

#### API Key 脱敏
- **原始格式**: `api-key: ${vector.dashvector.api_key:sk-abcd1234}`
- **脱敏后**: `api-key: ${vector.dashvector.api_key:sk-***SANITIZED***}`

### 支持的密钥格式

- `sk-` 开头的标准密钥
- `sk-or-` 开头的 OpenRouter 密钥
- 其他以 `sk-` 开头的变体密钥

## 使用方法

### 手动脱敏

```bash
# 运行脱敏脚本
python3 scripts/sanitize_config.py
```

### 自动脱敏（推荐）

1. **设置 Pre-commit Hook**:
   ```bash
   cp scripts/precommit.sh .git/hooks/pre-commit
   chmod +x .git/hooks/pre-commit
   ```

2. **正常提交代码**:
   ```bash
   git add .
   git commit -m "your commit message"
   ```
   
   脱敏会在提交前自动执行。

## 配置文件

当前脱敏的配置文件包括：
- `config/llm.yml`

如需添加其他配置文件，请修改 `scripts/sanitize_config.py` 中的 `config_files` 列表。

## 环境变量注入

脱敏后的配置文件仍然支持通过环境变量注入真实的密钥值：

```bash
# 例如，为 deepseek 注入真实的 API 密钥
export llm_deepseek_sk="sk-your-real-api-key"

# 启动应用
docker run -e llm_deepseek_sk="$llm_deepseek_sk" your-app
```

## 注意事项

1. **备份重要配置**: 在首次运行脱敏前，建议备份原始配置文件
2. **检查脱敏结果**: 脱敏后请检查配置文件，确保脱敏正确且不影响应用功能
3. **环境变量**: 确保生产环境中正确设置了相应的环境变量
4. **CI/CD**: 如果 CI 检查失败，请运行脱敏脚本后重新提交

## 故障排除

### 脱敏脚本执行失败

```bash
# 检查 Python 环境
python3 --version

# 检查脚本权限
ls -la scripts/sanitize_config.py

# 手动运行并查看错误
python3 scripts/sanitize_config.py
```

### CI 检查失败

如果 GitHub Actions 中的脱敏检查失败：

1. 本地运行脱敏脚本：
   ```bash
   python3 scripts/sanitize_config.py
   ```

2. 提交脱敏后的文件：
   ```bash
   git add config/
   git commit -m "Apply configuration sanitization"
   git push
   ```

## 扩展脱敏规则

如需添加新的脱敏规则，请修改 `scripts/sanitize_config.py` 中的正则表达式和替换逻辑。

例如，添加对 `token` 字段的脱敏：

```python
# 在 sanitize_sk_values 函数中添加
token_pattern = r'(\s*token:\s*\$\{[^:]+:)([a-zA-Z0-9\-]+)(\})'
sanitized_content = re.sub(token_pattern, lambda m: f"{m.group(1)}***SANITIZED***{m.group(3)}", sanitized_content)
```