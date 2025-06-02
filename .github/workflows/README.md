# GitHub Actions 工作流说明

## PR 预检查工作流 (pr-precheck.yml)

这个工作流会在每次创建或更新 Pull Request 时自动运行，执行以下检查：

### 1. 敏感信息检查

检查 PR 中是否包含以下敏感信息：
- API Keys (如 `sk-xxx`, `sk-or-xxx` 格式)
- 密钥和令牌
- 密码
- 数据库连接字符串
- 邮箱密码组合

**如果发现敏感信息，工作流会失败并提示具体位置。**

### 2. Python 代码格式检查

包含以下检查项：
- **语法检查**: 确保 Python 代码没有语法错误
- **代码风格检查**: 使用 flake8 检查代码风格
- **Import 排序检查**: 使用 isort 检查 import 语句排序
- **代码格式检查**: 使用 black 检查代码格式

## 本地开发建议

为了确保 PR 能通过预检查，建议在提交前在本地运行以下命令：

### 安装开发依赖

```bash
pip install flake8 black isort
```

### 代码格式化

```bash
# 自动格式化代码
black .

# 自动排序 import
isort .
```

### 代码检查

```bash
# 检查代码风格
flake8 .

# 检查 import 排序
isort --check-only --diff .

# 检查代码格式
black --check --diff .
```

### 敏感信息检查

在提交前，请确保：
1. 不要在代码中硬编码 API 密钥
2. 使用环境变量或配置文件管理敏感信息
3. 在 `.gitignore` 中排除包含敏感信息的文件

## 配置文件说明

- `.flake8`: flake8 代码风格检查配置
- `pyproject.toml`: black 和 isort 格式化配置
- `.github/workflows/pr-precheck.yml`: GitHub Actions 工作流配置

## 故障排除

如果预检查失败：

1. **敏感信息检查失败**:
   - 检查 PR 中是否包含 API 密钥或密码
   - 将敏感信息移动到环境变量或配置文件
   - 确保敏感文件已添加到 `.gitignore`

2. **Python 格式检查失败**:
   - 运行 `black .` 自动格式化代码
   - 运行 `isort .` 自动排序 import
   - 修复 flake8 报告的代码风格问题

3. **语法错误**:
   - 检查 Python 代码语法
   - 确保所有文件都是有效的 Python 代码

## 跳过检查 (不推荐)

如果确实需要跳过某些检查，可以在 commit 消息中添加 `[skip ci]`，但这不推荐用于正常开发流程。