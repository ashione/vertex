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
        if command -v uv &> /dev/null; then
            uv add $1
        else
            pip3 install $1
        fi
    fi
}

# Install required packages if not present
check_package "flake8"
check_package "black"
check_package "isort"
check_package "autopep8"

# Get list of Python files to check (staged files, excluding pipeline directory)
PYTHON_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.py$' | grep -v '^\.github/' || true)

# If no staged Python files, check all Python files in the repository (like CI does)
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
    
    # Check for import * statements
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
    
    # Run flake8 for linting
    echo "🔍 Running flake8 linting..."
    if ! flake8 $PYTHON_FILES; then
        print_warning "Flake8 found issues. Attempting to auto-fix..."
        
        # Try to auto-fix with autopep8 if available
        if command -v autopep8 &> /dev/null; then
            echo "🔧 Auto-fixing with autopep8..."
            for file in $PYTHON_FILES; do
                if [ -f "$file" ]; then
                    autopep8 --in-place --aggressive --aggressive "$file"
                fi
            done
            
            # Re-run black and isort after autopep8
            echo "🔧 Re-running formatters after auto-fix..."
            for file in $PYTHON_FILES; do
                if [ -f "$file" ]; then
                    isort "$file"
                    black "$file"
                fi
            done
            
            # Check flake8 again
            echo "🔍 Re-checking with flake8..."
            if flake8 $PYTHON_FILES; then
                print_status "Auto-fix successful! Flake8 linting passed"
            else
                print_warning "Some issues remain after auto-fix. Please review manually."
                echo "You can continue with the commit or fix the remaining issues."
                read -p "Do you want to continue? (y/N): " -n 1 -r
                echo
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    print_error "Commit aborted by user"
                    exit 1
                fi
            fi
        else
            print_warning "autopep8 not available for auto-fixing. Installing..."
            if command -v uv &> /dev/null; then
                uv add autopep8
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
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -v '^\.github/' || true)

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
LARGE_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -v '^\.github/' | xargs ls -la 2>/dev/null | awk '$5 > 1048576 {print $9, "(" $5 " bytes)"}' || true)

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

# Re-add modified files to staging area (only for staged files, excluding pipeline directory)
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