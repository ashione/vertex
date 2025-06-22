# PyPI 发布和版本管理指南

本文档介绍如何将 Vertex 项目发布到 PyPI，以及完整的版本管理功能。

## 版本管理

### 版本号格式

项目使用语义化版本号格式：`MAJOR.MINOR.PATCH`

- **MAJOR**: 不兼容的API修改
- **MINOR**: 向后兼容的功能性新增
- **PATCH**: 向后兼容的问题修正

### 版本管理功能

- 🔄 自动版本号递增（patch、minor、major）
- 📝 同步更新多个文件中的版本信息
- 🔍 版本变更预览
- 🚀 集成发布流程
- 📋 便捷的 Makefile 命令

### 查看和更新版本

#### 查看当前版本

```bash
# 使用脚本
python scripts/version_bump.py show

# 使用 Makefile
make version-show
```

#### 版本递增

**递增补丁版本 (0.1.0 → 0.1.1)**

```bash
# 预览变更
python scripts/version_bump.py patch --dry-run
make version-preview-patch

# 实际更新
python scripts/version_bump.py patch
make version-patch
```

**递增次版本 (0.1.0 → 0.2.0)**

```bash
# 预览变更
python scripts/version_bump.py minor --dry-run
make version-preview-minor

# 实际更新
python scripts/version_bump.py minor
make version-minor
```

**递增主版本 (0.1.0 → 1.0.0)**

```bash
# 预览变更
python scripts/version_bump.py major --dry-run
make version-preview-major

# 实际更新
python scripts/version_bump.py major
make version-major
```

### 自动更新的文件

版本管理脚本会自动更新以下文件中的版本信息：

1. **pyproject.toml** - 项目配置文件中的 `version` 字段
2. **setup.py** - 安装脚本中的 `version` 参数（如果存在）
3. **vertex_flow/__init__.py** - 包初始化文件中的 `__version__` 变量
4. **__init__.py** - 根目录初始化文件中的 `__version__` 变量（如果存在）

## 准备工作

### 1. 注册账户

- 注册 [PyPI](https://pypi.org/account/register/) 账户
- 注册 [TestPyPI](https://test.pypi.org/account/register/) 账户（用于测试）

### 2. 生成 API Token

#### PyPI API Token
1. 登录 PyPI
2. 进入 Account settings → API tokens
3. 创建新的 API token，选择 "Entire account" 范围
4. 保存生成的 token

#### TestPyPI API Token
1. 登录 TestPyPI
2. 进入 Account settings → API tokens
3. 创建新的 API token
4. 保存生成的 token

### 3. 配置认证

#### 本地配置
创建 `~/.pypirc` 文件：

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-your-api-token-here

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-your-test-api-token-here
```

#### GitHub Secrets 配置
在 GitHub 仓库设置中添加以下 secrets：
- `PYPI_API_TOKEN`: PyPI API token
- `TEST_PYPI_API_TOKEN`: TestPyPI API token

## 发布流程

### 方法一：使用发布脚本（推荐）

#### 发布到 PyPI

```bash
# 自动递增 patch 版本并发布
make publish
python scripts/publish.py

# 指定版本递增类型并发布
make publish-patch    # 递增 patch 版本
make publish-minor    # 递增 minor 版本
make publish-major    # 递增 major 版本

# 不递增版本直接发布
make publish-no-bump
python scripts/publish.py --no-bump
```

#### 发布到 TestPyPI

```bash
# 发布到测试环境（不会自动递增版本）
make publish-test
python scripts/publish.py --test
```

#### 高级用法

```bash
# 手动指定版本递增类型
python scripts/publish.py --bump minor
python scripts/publish.py --bump major

# 跳过特定步骤
python scripts/publish.py --skip-tests
python scripts/publish.py --skip-clean
python scripts/publish.py --no-bump
```

### 方法二：手动发布

#### 1. 清理构建目录
```bash
rm -rf build/ dist/ *.egg-info/
```

#### 2. 安装构建工具
```bash
# 使用uv同步开发依赖（推荐）
uv sync --dev

# 或者使用pip安装
pip install build twine
```

#### 3. 运行测试
```bash
# 使用uv运行测试（推荐）
uv run python -m pytest vertex_flow/tests/ -v

# 或者直接运行
python -m pytest vertex_flow/tests/ -v
```

#### 4. 构建包
```bash
# 使用uv构建（推荐）
uv build

# 或者使用build模块
python -m build
```

#### 5. 检查包
```bash
# 使用uv运行twine（推荐）
uv run python -m twine check dist/*

# 或者直接运行
twine check dist/*
```

#### 6. 上传到 TestPyPI（测试）
```bash
# 使用uv运行twine（推荐）
uv run python -m twine upload --repository testpypi dist/*

# 或者直接运行
twine upload --repository testpypi dist/*
```

#### 7. 测试安装
```bash
pip install -i https://test.pypi.org/simple/ vertex
```

#### 8. 上传到 PyPI（正式）
```bash
# 使用uv运行twine（推荐）
uv run python -m twine upload dist/*

# 或者直接运行
twine upload dist/*
```

### 方法三：GitHub Actions 自动发布

#### 通过 Release 触发
1. 在 GitHub 上创建新的 Release
2. GitHub Actions 会自动构建并发布到 PyPI

#### 手动触发
1. 进入 GitHub Actions 页面
2. 选择 "Publish to PyPI" workflow
3. 点击 "Run workflow"
4. 选择是否发布到 TestPyPI

## 版本管理工作流

推荐的版本管理工作流：

1. **开发阶段**：使用 `patch` 递增进行 bug 修复
2. **功能发布**：使用 `minor` 递增添加新功能
3. **重大更新**：使用 `major` 递增进行不兼容的更改

### 完整发布流程示例

```bash
# 1. 查看当前版本
make version-show

# 2. 预览版本变更
make version-preview-minor

# 3. 递增版本并发布
make publish-minor

# 4. 提交到 Git（脚本会提示相关命令）
git add .
git commit -m "bump version to 0.2.0"
git tag v0.2.0
git push && git push --tags
```

## 发布检查清单

发布前请确认：

- [ ] 代码已提交并推送到主分支
- [ ] 所有测试通过
- [ ] 更新了版本号
- [ ] 更新了 CHANGELOG（如果有）
- [ ] README 文档是最新的
- [ ] 依赖列表是正确的
- [ ] 在 TestPyPI 上测试过安装

## 故障排除

### 版本管理问题

1. **找不到 pyproject.toml 文件**
   - 确保在项目根目录运行脚本
   - 检查文件是否存在

2. **版本号格式错误**
   - 确保版本号遵循 `MAJOR.MINOR.PATCH` 格式
   - 检查版本号中是否包含非数字字符

3. **权限错误**
   - 确保脚本有执行权限：`chmod +x scripts/version_bump.py`
   - 检查文件写入权限

### 调试模式

使用 `--dry-run` 参数可以预览版本变更而不实际修改文件：

```bash
python scripts/version_bump.py patch --dry-run
```

## 脚本参数说明

### version_bump.py 参数

- `show`: 显示当前版本
- `patch`: 递增补丁版本
- `minor`: 递增次版本
- `major`: 递增主版本
- `--dry-run`: 预览模式，不实际修改文件
- `--project-root`: 指定项目根目录（默认为当前目录）

### publish.py 参数

- `--test`: 上传到 TestPyPI
- `--bump {patch,minor,major}`: 发布前递增指定类型的版本
- `--no-bump`: 跳过版本递增
- `--skip-tests`: 跳过测试
- `--skip-clean`: 跳过清理构建目录

## uv 环境说明

本项目使用 [uv](https://docs.astral.sh/uv/) 作为包管理器，它提供了更快的依赖解析和安装速度。

### uv 基本命令
```bash
# 安装依赖
uv sync

# 安装开发依赖
uv sync --dev

# 运行Python脚本
uv run python script.py

# 构建包
uv build
```