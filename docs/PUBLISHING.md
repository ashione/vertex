# PyPI 发布指南

本文档介绍如何将 Vertex 项目发布到 PyPI。

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

#### 测试发布到 TestPyPI
```bash
# 使用uv环境（推荐）
python scripts/publish.py --test

# 或者直接运行
uv run python scripts/publish.py --test
```

#### 正式发布到 PyPI
```bash
# 使用uv环境（推荐）
python scripts/publish.py

# 或者直接运行
uv run python scripts/publish.py
```

#### 脚本选项
- `--test`: 发布到 TestPyPI
- `--skip-tests`: 跳过测试
- `--skip-clean`: 跳过清理构建目录

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

## 版本管理

### 更新版本号
在 `pyproject.toml` 中更新版本号：

```toml
[project]
name = "vertex"
version = "0.1.1"  # 更新这里
```

### 版本号规范
遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范：
- `MAJOR.MINOR.PATCH`
- MAJOR: 不兼容的 API 修改
- MINOR: 向下兼容的功能性新增
- PATCH: 向下兼容的问题修正

## 发布检查清单

发布前请确认：

- [ ] 代码已提交并推送到主分支
- [ ] 所有测试通过
- [ ] 更新了版本号
- [ ] 更新了 CHANGELOG（如果有）
- [ ] README 文档是最新的
- [ ] 依赖列表是正确的
- [ ] 在 TestPyPI 上测试过安装

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

# 添加依赖
uv add package-name

# 添加开发依赖
uv add --dev package-name
```

## 常见问题

### 1. 版本冲突
如果遇到版本已存在的错误，需要更新版本号。PyPI 不允许重复上传相同版本。

### 2. 认证失败
检查 API token 是否正确配置，确保 token 有足够的权限。

### 3. 包大小限制
PyPI 对包大小有限制，如果包太大，考虑：
- 移除不必要的文件
- 使用 `.gitignore` 和 `MANIFEST.in` 控制包含的文件
- 将大文件放到外部存储

### 4. 依赖问题
确保所有依赖都在 `pyproject.toml` 中正确声明，版本号要合理。

### 5. uv 环境问题
如果遇到 uv 相关问题：
- 确保已安装最新版本的 uv
- 使用 `uv sync` 重新同步依赖
- 检查 `pyproject.toml` 配置是否正确

## 相关链接

- [PyPI](https://pypi.org/)
- [TestPyPI](https://test.pypi.org/)
- [Python Packaging User Guide](https://packaging.python.org/)
- [Twine 文档](https://twine.readthedocs.io/)
- [语义化版本](https://semver.org/lang/zh-CN/)
- [uv 文档](https://docs.astral.sh/uv/)