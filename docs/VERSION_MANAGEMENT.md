# 版本管理指南

本项目提供了完整的版本管理功能，支持自动化版本号递增和发布流程。

## 功能特性

- 🔄 自动版本号递增（patch、minor、major）
- 📝 同步更新多个文件中的版本信息
- 🔍 版本变更预览
- 🚀 集成发布流程
- 📋 便捷的 Makefile 命令

## 版本号格式

项目使用语义化版本号格式：`MAJOR.MINOR.PATCH`

- **MAJOR**: 不兼容的API修改
- **MINOR**: 向后兼容的功能性新增
- **PATCH**: 向后兼容的问题修正

## 使用方法

### 1. 查看当前版本

```bash
# 使用脚本
python scripts/version_bump.py show

# 使用 Makefile
make version-show
```

### 2. 版本递增

#### 递增补丁版本 (0.1.0 → 0.1.1)

```bash
# 预览变更
python scripts/version_bump.py patch --dry-run
make version-preview-patch

# 实际更新
python scripts/version_bump.py patch
make version-patch
```

#### 递增次版本 (0.1.0 → 0.2.0)

```bash
# 预览变更
python scripts/version_bump.py minor --dry-run
make version-preview-minor

# 实际更新
python scripts/version_bump.py minor
make version-minor
```

#### 递增主版本 (0.1.0 → 1.0.0)

```bash
# 预览变更
python scripts/version_bump.py major --dry-run
make version-preview-major

# 实际更新
python scripts/version_bump.py major
make version-major
```

### 3. 发布流程

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

### 4. 高级用法

#### 手动指定版本递增类型

```bash
# 发布时指定版本递增类型
python scripts/publish.py --bump minor
python scripts/publish.py --bump major
```

#### 跳过特定步骤

```bash
# 跳过测试
python scripts/publish.py --skip-tests

# 跳过清理
python scripts/publish.py --skip-clean

# 跳过版本递增
python scripts/publish.py --no-bump
```

## 自动更新的文件

版本管理脚本会自动更新以下文件中的版本信息：

1. **pyproject.toml** - 项目配置文件中的 `version` 字段
2. **setup.py** - 安装脚本中的 `version` 参数（如果存在）
3. **vertex_flow/__init__.py** - 包初始化文件中的 `__version__` 变量
4. **__init__.py** - 根目录初始化文件中的 `__version__` 变量（如果存在）

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

## 故障排除

### 常见问题

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

## 集成到 CI/CD

可以将版本管理集成到 CI/CD 流程中：

```yaml
# GitHub Actions 示例
- name: Bump version and publish
  run: |
    python scripts/version_bump.py patch
    python scripts/publish.py --no-bump
```

这样可以实现自动化的版本管理和发布流程。