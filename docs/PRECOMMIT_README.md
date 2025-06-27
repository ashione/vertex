# Pre-commit Hook 和配置脱敏使用指南

本项目包含一个 `precommit.sh` 脚本，用于在代码提交前自动执行代码质量检查和配置文件脱敏。

**重要说明**: 本项目使用统一的 `scripts/precommit.sh` 脚本进行代码质量检查，确保本地开发和GitHub Actions CI/CD环境的一致性。

## 功能特性

- 🎨 **代码格式化**: 使用 `black` 自动格式化 Python 代码
- 📝 **导入排序**: 使用 `isort` 自动排序 Python 导入语句
- 🔍 **代码检查**: 使用 `flake8` 进行代码风格和语法检查
- 🔒 **配置脱敏**: 自动对配置文件中的敏感信息进行脱敏处理
- 🔍 **敏感信息检测**: 检查是否包含 API 密钥、密码等敏感信息
- 📏 **大文件检测**: 检测并警告大文件（>1MB）

## 安装和配置

### 1. 手动运行

直接运行脚本检查当前暂存的文件：

```bash
./scripts/precommit.sh
```

### 2. 设置为 Git Hook（推荐）

将脚本设置为 Git 的 pre-commit hook，这样每次提交时会自动运行：

```bash
# 复制脚本到 Git hooks 目录
cp scripts/precommit.sh .git/hooks/pre-commit

# 确保有执行权限
chmod +x .git/hooks/pre-commit
```

### 3. 依赖安装

脚本会自动检查并安装所需的 Python 包，但你也可以手动安装：

```bash
pip3 install flake8 black isort
```

## 使用流程

1. **添加文件到暂存区**:
   ```bash
   git add .
   ```

2. **运行预提交检查**:
   ```bash
   ./scripts/precommit.sh
   ```
   或者如果设置了 Git hook，直接提交：
   ```bash
   git commit -m "your commit message"
   ```

3. **处理检查结果**:
   - ✅ 如果所有检查通过，可以正常提交
   - ⚠️ 如果发现问题，脚本会自动修复格式问题并重新暂存
   - ❌ 如果有无法自动修复的问题，需要手动修复后重新运行

## 检查项目详情

### 代码格式化
- **Black**: 自动格式化 Python 代码，确保一致的代码风格
- **isort**: 自动排序和格式化 import 语句

### 代码质量检查
- **Flake8**: 检查代码风格、语法错误和复杂度
- 配置文件: `.flake8`

### 配置文件脱敏

#### 脱敏机制

1. **Pre-commit Hook**: 在每次提交前，`scripts/precommit.sh` 会自动运行脱敏脚本
2. **CI/CD检查**: GitHub Actions 会检查配置文件是否已正确脱敏
3. **手动脱敏**: 可以手动运行脱敏脚本

#### 脱敏规则

脱敏脚本 `scripts/sanitize_config.py` 会处理以下类型的敏感信息：

**SK (Secret Key) 脱敏**

旧格式（冒号后直接是密钥）：
- **原始格式**: `sk: ${llm.deepseek.sk:sk-[ACTUAL_KEY]}`
- **脱敏后**: `sk: ${llm.deepseek.sk:sk-***SANITIZED***}`

新格式（冒号后使用 `:-` 分隔符）：
- **原始格式**: `sk: ${llm.deepseek.sk:sk-*****************}`
- **脱敏后**: `sk: ${llm.deepseek.sk:-sk-***SANITIZED***}`

**API Key 脱敏**

- **原始格式**: `api-key: ${vector.dashvector.api_key:-sk-abcd1234567890}`
- **脱敏后**: `api-key: ${vector.dashvector.api_key:-sk-***SANITIZED***}`

**占位符保护**

以下占位符**不会**被脱敏（保持原样）：
- `sk: ${llm.deepseek.sk:-YOUR_DEEPSEEK_API_KEY}`
- `api-key: ${vector.dashvector.api_key:-YOUR_DASHVECTOR_API_KEY}`

#### 支持的密钥格式

- `sk-` 开头的标准密钥（长度 > 10 字符）
- `sk-or-` 开头的 OpenRouter 密钥
- 其他长度 > 20 字符的通用API密钥
- 自动识别并保护 `YOUR_XXX_API_KEY` 形式的占位符

#### 手动脱敏

```bash
# 运行脱敏脚本
python3 scripts/sanitize_config.py
```

### 敏感信息检测
检测以下模式的敏感信息：
- API 密钥 (`api_key`, `api-key`)
- 密钥 (`secret_key`, `secret-key`)
- 密码 (`password`)
- 令牌 (`token`)
- 访问密钥 (`access_key`, `access-key`)
- 私钥 (`private_key`, `private-key`)
- OpenAI 风格的密钥 (`sk-...`)
- 长字符串（可能是密钥）

### 大文件检测
- 检测大于 1MB 的文件
- 提醒用户是否真的需要提交大文件

## 配置文件

### 代码检查配置
项目中的相关配置文件：
- `.flake8`: Flake8 配置
- `pyproject.toml`: Black 和 isort 配置

### 脱敏配置文件
当前脱敏的配置文件包括：

**主要配置文件：**
- `vertex_flow/config/llm.yml.template`

如需添加其他配置文件，请修改 `scripts/sanitize_config.py` 中的 `config_files` 列表。

### 环境变量注入

脱敏后的配置文件仍然支持通过环境变量注入真实的密钥值：

```bash
# 例如，为 deepseek 注入真实的 API 密钥
export llm_deepseek_sk="sk-your-real-api-key"

# 启动应用
CONFIG_FILE=config/llm.yml vertex
```

## 跳过检查

如果需要跳过预提交检查（不推荐），可以使用：

```bash
git commit --no-verify -m "your commit message"
```

## 故障排除

### 常见问题

1. **权限错误**:
   ```bash
   chmod +x scripts/precommit.sh
   ```

2. **Python 包未安装**:
   ```bash
   pip3 install flake8 black isort
   ```

3. **Git hook 不工作**:
   检查 `.git/hooks/pre-commit` 文件是否存在且有执行权限

4. **格式化后仍有错误**:
   手动检查 flake8 报告的错误，某些问题需要手动修复

### 脱敏相关问题

1. **脱敏脚本执行失败**:
   ```bash
   # 检查 Python 环境
   python3 --version
   
   # 检查脚本权限
   ls -la scripts/sanitize_config.py
   
   # 手动运行并查看错误
   python3 scripts/sanitize_config.py
   ```

2. **CI 检查失败**:
   如果 GitHub Actions 中的脱敏检查失败：
   ```bash
   # 本地运行脱敏脚本
   python3 scripts/sanitize_config.py
   
   # 提交脱敏后的文件
   git add vertex_flow/config/
   git commit -m "Apply configuration sanitization"
   git push
   ```

3. **Git路径错误**:
   如果出现 `fatal: ambiguous argument 'config/'` 错误，这通常是因为配置目录为空或不存在，脚本已经包含了安全处理。

## 与 GitHub Actions 的关系

本地的 `precommit.sh` 与 GitHub Actions 中的 `pr-precheck.yml` 工作流保持一致，确保：
- 本地检查通过的代码在 CI 中也能通过
- 减少因格式问题导致的 CI 失败
- 提高代码质量和开发效率
- 确保敏感信息不会被意外提交

## 自定义配置

你可以根据项目需要修改相关脚本：

### 修改代码检查规则
编辑 `scripts/precommit.sh` 中的检查规则：
- 修改敏感信息检测模式
- 调整大文件大小阈值
- 添加其他检查项目

### 扩展脱敏规则
修改 `scripts/sanitize_config.py` 添加新的脱敏规则：

```python
# 例如，添加对 token 字段的脱敏
token_pattern = r'(\s*token:\s*\$\{[^:]+:)([a-zA-Z0-9\-]+)(\})'
sanitized_content = re.sub(token_pattern, lambda m: f"{m.group(1)}***SANITIZED***{m.group(3)}", sanitized_content)
```

## 注意事项

1. **备份重要配置**: 在首次运行脱敏前，建议备份原始配置文件
2. **检查脱敏结果**: 脱敏后请检查配置文件，确保脱敏正确且不影响应用功能
3. **环境变量**: 确保生产环境中正确设置了相应的环境变量
4. **CI/CD**: 如果 CI 检查失败，请运行脱敏脚本后重新提交