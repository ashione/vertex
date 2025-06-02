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

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    print_error "Python3 is not installed or not in PATH"
    exit 1
fi

# Check if pip packages are installed
check_package() {
    if ! python3 -c "import $1" &> /dev/null; then
        print_warning "$1 is not installed. Installing..."
        pip3 install $1
    fi
}

# Install required packages if not present
check_package "flake8"
check_package "black"
check_package "isort"

# Get list of Python files to check (staged files)
PYTHON_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.py$' || true)

if [ -z "$PYTHON_FILES" ]; then
    print_status "No Python files to check"
else
    echo "📝 Checking Python files: $PYTHON_FILES"
    
    # Run isort to sort imports
    echo "🔧 Sorting imports with isort..."
    for file in $PYTHON_FILES; do
        if [ -f "$file" ]; then
            isort "$file"
        fi
    done
    print_status "Import sorting completed"
    
    # Run black for code formatting
    echo "🎨 Formatting code with black..."
    for file in $PYTHON_FILES; do
        if [ -f "$file" ]; then
            black "$file"
        fi
    done
    print_status "Code formatting completed"
    
    # Run flake8 for linting
    echo "🔍 Running flake8 linting..."
    if flake8 $PYTHON_FILES; then
        print_status "Flake8 linting passed"
    else
        print_error "Flake8 linting failed. Please fix the issues above."
        exit 1
    fi
fi

# Check for sensitive information
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
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM)

for pattern in "${SENSITIVE_PATTERNS[@]}"; do
    if echo "$STAGED_FILES" | xargs grep -l -i "$pattern" 2>/dev/null; then
        print_warning "Potential sensitive information found with pattern: $pattern"
        SENSITIVE_FOUND=true
    fi
done

if [ "$SENSITIVE_FOUND" = true ]; then
    print_warning "Please review the files above for sensitive information"
    echo "If you're sure these are not sensitive, you can proceed with the commit"
    read -p "Do you want to continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_error "Commit aborted by user"
        exit 1
    fi
else
    print_status "No sensitive information detected"
fi

# Check for large files
echo "📏 Checking for large files..."
LARGE_FILES=$(git diff --cached --name-only --diff-filter=ACM | xargs ls -la 2>/dev/null | awk '$5 > 1048576 {print $9, "(" $5 " bytes)"}' || true)

if [ -n "$LARGE_FILES" ]; then
    print_warning "Large files detected:"
    echo "$LARGE_FILES"
    read -p "Do you want to continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_error "Commit aborted by user"
        exit 1
    fi
else
    print_status "No large files detected"
fi

# Re-add modified files to staging area
if [ -n "$PYTHON_FILES" ]; then
    echo "📝 Re-adding formatted files to staging area..."
    for file in $PYTHON_FILES; do
        if [ -f "$file" ]; then
            git add "$file"
        fi
    done
    print_status "Files re-added to staging area"
fi

print_status "All pre-commit checks passed! 🎉"
echo "Ready to commit!"