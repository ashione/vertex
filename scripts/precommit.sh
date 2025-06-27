#!/bin/bash

# Pre-commit hook script
# This script runs before each commit to ensure code quality

set -e

echo "🔍 Running pre-commit checks..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# 检查并激活虚拟环境
activate_venv() {
    # 检查是否存在 venv 目录
    if [ -d "venv" ]; then
        print_status "Found venv directory, activating..."
        source venv/bin/activate
    elif [ -d ".venv" ]; then
        print_status "Found .venv directory, activating..."
        source .venv/bin/activate
    else
        print_warning "No virtual environment found"
    fi
}

# 检查 Python 是否可用
if ! command -v python3 &> /dev/null; then
    print_error "Python3 is not installed or not in PATH"
    exit 1
fi

# 激活虚拟环境
activate_venv

# 检查并安装包
check_package() {
    if ! python3 -c "import $1" &> /dev/null; then
        print_warning "$1 is not installed. Installing..."
        # 在CI环境中优先使用pip，避免uv的虚拟环境问题
        if command -v uv &> /dev/null && [ -z "$CI" ]; then
            uv pip install $1
        else
            pip3 install $1
        fi
    fi
}

# 检查项目依赖是否已安装
check_project_dependencies() {
    print_status "Checking project dependencies..."
    
    # 检查项目是否已安装
    if ! python3 -c "import vertex_flow" &> /dev/null; then
        print_warning "Project not installed. Installing in development mode..."
        # 在CI环境中优先使用pip
        if command -v uv &> /dev/null && [ -z "$CI" ]; then
            uv pip install -e .
        else
            pip3 install -e .
        fi
    fi
}

# 安装必需的包（与pyproject.toml保持一致）
check_package "flake8"
check_package "black"
check_package "isort"
check_package "autopep8"

# 检查项目依赖
check_project_dependencies

# 获取要检查的 Python 文件列表（暂存的文件，排除 pipeline 目录）
PYTHON_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.py$' | grep -v '^\.github/' || true)

# 如果没有暂存的 Python 文件，检查仓库中的所有 Python 文件（类似 CI 的行为）
if [ -z "$PYTHON_FILES" ]; then
    print_warning "No staged Python files found. Checking all Python files in repository..."
    PYTHON_FILES=$(find . -name "*.py" -not -path "./.*" -not -path "./.github/*" | head -50 || true)
    if [ -z "$PYTHON_FILES" ]; then
        print_status "No Python files found in repository"
        exit 0
    else
        echo "📝 Checking all Python files (first 50): $(echo $PYTHON_FILES | tr '\n' ' ')"
    fi
else
    echo "📝 Checking staged Python files: $PYTHON_FILES"
fi

if [ ! -z "$PYTHON_FILES" ]; then
    # 使用 isort 排序导入
    echo "🔧 Sorting imports with isort..."
    for file in $PYTHON_FILES; do
        if [ -f "$file" ]; then
            if command -v uv &> /dev/null && [ -z "$CI" ]; then
                uv run isort "$file"
            else
                isort "$file"
            fi
        fi
    done
    print_status "Import sorting completed"
    
    # 使用 black 格式化代码
    echo "🎨 Formatting code with black..."
    for file in $PYTHON_FILES; do
        if [ -f "$file" ]; then
            if command -v uv &> /dev/null && [ -z "$CI" ]; then
                uv run black "$file"
            else
                black "$file"
            fi
        fi
    done
    print_status "Code formatting completed"
    
    # 检查 import * 语句
    echo "🚫 Checking for prohibited 'import *' statements..."
    IMPORT_STAR_FILES=$(grep -l "from .* import \*" $PYTHON_FILES 2>/dev/null || true)
    if [ -n "$IMPORT_STAR_FILES" ]; then
        print_error "Found prohibited 'import *' statements in:"
        for file in $IMPORT_STAR_FILES; do
            echo "  - $file:"
            grep -n "from .* import \*" "$file" | sed 's/^/    /'
        done
        print_error "Please replace 'import *' with specific imports"
        exit 1
    else
        print_status "No 'import *' statements found"
    fi
    
    # 运行 flake8 进行代码检查
    echo "🔍 Running flake8 linting..."
    if ! (if command -v uv &> /dev/null && [ -z "$CI" ]; then uv run flake8 --config=pyproject.toml $PYTHON_FILES; else flake8 --config=pyproject.toml $PYTHON_FILES; fi); then
        print_warning "Flake8 found issues. Attempting to auto-fix..."
        
        # 尝试使用 autopep8 自动修复
        if command -v autopep8 &> /dev/null; then
            echo "🔧 Auto-fixing with autopep8..."
            for file in $PYTHON_FILES; do
                if [ -f "$file" ]; then
                    if command -v uv &> /dev/null && [ -z "$CI" ]; then
                        uv run autopep8 --in-place --aggressive --aggressive "$file"
                    else
                        autopep8 --in-place --aggressive --aggressive "$file"
                    fi
                fi
            done
            
            # 在 autopep8 后重新运行 black 和 isort
            echo "🔧 Re-running formatters after auto-fix..."
            for file in $PYTHON_FILES; do
                if [ -f "$file" ]; then
                    if command -v uv &> /dev/null && [ -z "$CI" ]; then
                        uv run isort "$file"
                        uv run black "$file"
                    else
                        isort "$file"
                        black "$file"
                    fi
                fi
            done
            
            # 再次检查 flake8
            echo "🔍 Re-checking with flake8..."
            if (if command -v uv &> /dev/null && [ -z "$CI" ]; then uv run flake8 --config=pyproject.toml $PYTHON_FILES; else flake8 --config=pyproject.toml $PYTHON_FILES; fi); then
                print_status "Auto-fix successful! Flake8 linting passed"
            else
                print_warning "Some issues remain after auto-fix. Continuing with commit..."
            fi
        else
            print_warning "autopep8 not available for auto-fixing. Installing..."
            if command -v uv &> /dev/null && [ -z "$CI" ]; then
                uv pip install autopep8
            else
                pip3 install autopep8
            fi
            print_warning "Please run the pre-commit hook again after autopep8 installation."
            exit 1
        fi
    else
        print_status "Flake8 linting passed"
    fi
fi

# 自动清理配置文件
echo "🔧 Auto-sanitizing configuration files..."
if [ -f "scripts/sanitize_config.py" ]; then
    if command -v uv &> /dev/null && [ -z "$CI" ]; then
        uv run python3 scripts/sanitize_config.py
    else
        python3 scripts/sanitize_config.py
    fi
    
    # 如果配置文件被修改，添加到暂存区
    SANITIZED_FILES=""
    
    # 检查根目录config/（如果存在）
    if [ -d "config/" ] && [ "$(ls -A config/ 2>/dev/null)" ]; then
        CONFIG_FILES=$(git diff --name-only -- config/ 2>/dev/null | head -20 || true)
        if [ -n "$CONFIG_FILES" ]; then
            SANITIZED_FILES="$SANITIZED_FILES $CONFIG_FILES"
        fi
    fi
    
    # 检查vertex_flow/config/
    if [ -d "vertex_flow/config/" ] && [ "$(ls -A vertex_flow/config/ 2>/dev/null)" ]; then
        VERTEX_CONFIG_FILES=$(git diff --name-only -- vertex_flow/config/ 2>/dev/null | head -20 || true)
        if [ -n "$VERTEX_CONFIG_FILES" ]; then
            SANITIZED_FILES="$SANITIZED_FILES $VERTEX_CONFIG_FILES"
        fi
    fi
    
    if [ -n "$SANITIZED_FILES" ]; then
        echo "📝 Adding sanitized files to staging area..."
        echo "   Files to add: $SANITIZED_FILES"
        git add $SANITIZED_FILES 2>/dev/null || true
        print_status "Configuration files sanitized and staged"
    else
        print_status "No configuration files were modified"
    fi
else
    print_warning "Sanitization script not found, skipping auto-sanitization"
fi

# 检查敏感信息
echo "🔒 Checking for sensitive information..."
SENSITIVE_PATTERNS=(
    "api[_-]?key"
    "secret[_-]?key"
    "password"
    "token"
    "access[_-]?key"
    "private[_-]?key"
    "sk-[a-zA-Z0-9]{32,}"
    "[a-zA-Z0-9]{32,}"
)

SENSITIVE_FOUND=false
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -v '^\.github/' || true)

for pattern in "${SENSITIVE_PATTERNS[@]}"; do
    if echo "$STAGED_FILES" | xargs grep -l -i "$pattern" 2>/dev/null; then
        print_warning "Potential sensitive information found with pattern: $pattern"
        SENSITIVE_FOUND=true
    fi
done

if [ "$SENSITIVE_FOUND" = true ]; then
    print_warning "Found potential sensitive information. Continuing with commit..."
fi

# 检查大文件
echo "📏 Checking for large files..."
LARGE_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -v '^\.github/' | xargs ls -la 2>/dev/null | awk '$5 > 1048576 {print $9, "(" $5 " bytes)"}' || true)

if [ -n "$LARGE_FILES" ]; then
    print_warning "Large files detected:"
    echo "$LARGE_FILES"
    print_warning "Continuing with commit..."
fi

# 重新添加修改后的文件到暂存区（仅针对暂存的文件，排除 pipeline 目录）
STAGED_PYTHON_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.py$' | grep -v '^\.github/' || true)
if [ -n "$STAGED_PYTHON_FILES" ]; then
    echo "📝 Re-adding formatted files to staging area..."
    for file in $STAGED_PYTHON_FILES; do
        if [ -f "$file" ] && [[ "$file" != .github/* ]]; then
            git add "$file"
        fi
    done
    print_status "Files re-added to staging area"
fi

print_status "All pre-commit checks passed! 🎉"
echo "Ready to commit!"