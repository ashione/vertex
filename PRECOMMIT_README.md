# Pre-commit Hook 使用说明

本项目包含一个 `precommit.sh` 脚本，用于在代码提交前自动执行代码质量检查。

## 功能特性

- 🎨 **代码格式化**: 使用 `black` 自动格式化 Python 代码
- 📝 **导入排序**: 使用 `isort` 自动排序 Python 导入语句
- 🔍 **代码检查**: 使用 `flake8` 进行代码风格和语法检查
- 🔒 **敏感信息检测**: 检查是否包含 API 密钥、密码等敏感信息
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

项目中的相关配置文件：
- `.flake8`: Flake8 配置
- `pyproject.toml`: Black 和 isort 配置

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

## 与 GitHub Actions 的关系

本地的 `precommit.sh` 与 GitHub Actions 中的 `pr-precheck.yml` 工作流保持一致，确保：
- 本地检查通过的代码在 CI 中也能通过
- 减少因格式问题导致的 CI 失败
- 提高代码质量和开发效率

## 自定义配置

你可以根据项目需要修改 `scripts/precommit.sh` 中的检查规则：
- 修改敏感信息检测模式
- 调整大文件大小阈值
- 添加其他检查项目