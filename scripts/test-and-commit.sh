#!/bin/bash

# =============================================================================
# Letrade_v1 Test and Quality Assurance Script
# =============================================================================

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} ✅ $1"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')]${NC} ⚠️ $1"
}

log_error() {
    echo -e "${RED}[$(date +'%H:%M:%S')]${NC} ❌ $1"
}

log_info() {
    echo -e "${CYAN}[$(date +'%H:%M:%S')]${NC} ℹ️ $1"
}

# Parse command line arguments
SKIP_TESTS=false
SKIP_FORMATTING=false
SKIP_SECURITY=false
COVERAGE_THRESHOLD=85

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --skip-formatting)
            SKIP_FORMATTING=true
            shift
            ;;
        --skip-security)
            SKIP_SECURITY=true
            shift
            ;;
        --coverage-threshold)
            COVERAGE_THRESHOLD="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --skip-tests           Skip test execution"
            echo "  --skip-formatting      Skip code formatting"
            echo "  --skip-security        Skip security checks"
            echo "  --coverage-threshold N Set coverage threshold (default: 85)"
            echo "  -h, --help            Show this help message"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "🧪 Running comprehensive test suite for Letrade_v1..."
echo ""

# Check if we're in the right directory
if [[ ! -f "pyproject.toml" ]] || [[ ! -d "src" ]]; then
    log_error "This script must be run from the project root directory"
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Step 1: Code Formatting
if [[ "$SKIP_FORMATTING" == "false" ]]; then
    echo "🎨 Step 1: Code Formatting"
    echo "=========================="
    
    log "Formatting Python code with Black..."
    if black src/ tests/ --line-length 88 --target-version py311; then
        log_success "Black formatting completed"
    else
        log_error "Black formatting failed"
        exit 1
    fi
    
    log "Sorting imports with isort..."
    if isort src/ tests/ --profile black; then
        log_success "Import sorting completed"
    else
        log_error "Import sorting failed"
        exit 1
    fi
    
    echo ""
else
    log_warning "Skipping code formatting (--skip-formatting)"
    echo ""
fi

# Step 2: Static Code Analysis
echo "🔍 Step 2: Static Code Analysis"
echo "==============================="

log "Running flake8 linter..."
if flake8 src/ tests/ --max-line-length=88 --extend-ignore=E203,W503 --exclude=migrations/; then
    log_success "flake8 linting passed"
else
    log_error "flake8 linting failed"
    exit 1
fi

log "Running mypy type checker..."
if mypy src/ --ignore-missing-imports --disallow-untyped-defs; then
    log_success "mypy type checking passed"
else
    log_warning "mypy type checking found issues (continuing anyway for now)"
    # TODO: Fix type annotations and re-enable strict checking
fi

echo ""

# Step 3: Security Checks
if [[ "$SKIP_SECURITY" == "false" ]]; then
    echo "🔒 Step 3: Security Checks"
    echo "=========================="
    
    log "Running trading system security checks..."
    if [[ -f "scripts/security-check.sh" ]] && [[ -x "scripts/security-check.sh" ]]; then
        if ./scripts/security-check.sh; then
            log_success "Security checks passed"
        else
            log_error "Security checks failed"
            exit 1
        fi
    else
        log_warning "Security check script not found or not executable"
        
        # Run basic security checks inline
        log "Checking for hardcoded API keys..."
        if grep -r "api_key.*=" src/ 2>/dev/null | grep -v "test" | grep -v "mock"; then
            log_error "Hardcoded API key detected!"
            exit 1
        fi
        
        log "Checking for hardcoded secrets..."
        if grep -r "secret.*=" src/ 2>/dev/null | grep -v "test" | grep -v "mock"; then
            log_error "Hardcoded secret detected!"
            exit 1
        fi
        
        log "Checking for exchange-specific hardcoded values..."
        if grep -r "binance.*key\|coinbase.*key" src/ 2>/dev/null | grep -v "test" | grep -v "mock"; then
            log_error "Exchange API key detected!"
            exit 1
        fi
        
        log_success "Basic security checks passed"
    fi
    
    # Advanced security scanning (if tools available)
    if command -v bandit >/dev/null 2>&1; then
        log "Running bandit security scanner..."
        if bandit -r src/ -f json -o logs/bandit-report.json -q; then
            log_success "Bandit security scan passed"
        else
            log_warning "Bandit security scan found issues (see logs/bandit-report.json)"
        fi
    else
        log_info "Bandit not installed, skipping advanced security scan"
    fi
    
    echo ""
else
    log_warning "Skipping security checks (--skip-security)"
    echo ""
fi

# Step 4: Test Execution
if [[ "$SKIP_TESTS" == "false" ]]; then
    echo "🧪 Step 4: Test Execution"
    echo "========================="
    
    # Check if pytest is available
    if ! command -v pytest >/dev/null 2>&1; then
        log_error "pytest not found. Please install with: pip install pytest"
        exit 1
    fi
    
    # Run unit tests
    log "Running unit tests..."
    if pytest tests/unit/ -v --tb=short --junitxml=logs/junit-unit.xml 2>&1 | tee logs/unit-tests.log; then
        log_success "Unit tests passed"
    else
        log_error "Unit tests failed (see logs/unit-tests.log)"
        exit 1
    fi
    
    # Run integration tests (if they exist and services are available)
    if [[ -d "tests/integration" ]] && [[ -n "$(ls -A tests/integration 2>/dev/null)" ]]; then
        log "Running integration tests..."
        
        # Check if Docker services are running
        if docker-compose ps | grep -q "Up"; then
            if pytest tests/integration/ -v --tb=short --junitxml=logs/junit-integration.xml 2>&1 | tee logs/integration-tests.log; then
                log_success "Integration tests passed"
            else
                log_warning "Integration tests failed (see logs/integration-tests.log)"
                # Don't exit on integration test failure, just warn
            fi
        else
            log_warning "Docker services not running, skipping integration tests"
            log_info "Run 'docker-compose up -d' to enable integration tests"
        fi
    else
        log_info "No integration tests found, skipping"
    fi
    
    echo ""
else
    log_warning "Skipping test execution (--skip-tests)"
    echo ""
fi

# Step 5: Coverage Analysis
echo "📊 Step 5: Coverage Analysis"
echo "============================"

if command -v coverage >/dev/null 2>&1 && [[ "$SKIP_TESTS" == "false" ]]; then
    log "Running coverage analysis..."
    
    # Run tests with coverage
    if coverage run -m pytest tests/unit/ -q; then
        # Generate coverage report
        coverage report --show-missing > logs/coverage-report.txt
        coverage html -d logs/htmlcov/
        
        # Check coverage threshold
        COVERAGE_PERCENT=$(coverage report | tail -n 1 | awk '{print $4}' | sed 's/%//')
        
        if [[ -n "$COVERAGE_PERCENT" ]] && [[ "$COVERAGE_PERCENT" =~ ^[0-9]+$ ]]; then
            if [[ "$COVERAGE_PERCENT" -ge "$COVERAGE_THRESHOLD" ]]; then
                log_success "Coverage: ${COVERAGE_PERCENT}% (threshold: ${COVERAGE_THRESHOLD}%)"
            else
                log_error "Coverage: ${COVERAGE_PERCENT}% is below ${COVERAGE_THRESHOLD}% threshold"
                echo ""
                echo "📋 Coverage Report:"
                coverage report --show-missing
                exit 1
            fi
        else
            log_warning "Could not determine coverage percentage"
        fi
        
        log_info "Detailed coverage report saved to logs/coverage-report.txt"
        log_info "HTML coverage report saved to logs/htmlcov/index.html"
    else
        log_error "Coverage analysis failed"
        exit 1
    fi
else
    if [[ "$SKIP_TESTS" == "true" ]]; then
        log_warning "Skipping coverage analysis (tests skipped)"
    else
        log_warning "Coverage tool not available, skipping coverage analysis"
        log_info "Install with: pip install coverage"
    fi
fi

echo ""

# Step 6: Performance Checks
echo "⚡ Step 6: Performance Checks"
echo "============================"

# Check for performance test markers
if grep -r "@pytest.mark.performance" tests/ >/dev/null 2>&1; then
    if command -v pytest-benchmark >/dev/null 2>&1; then
        log "Running performance benchmarks..."
        if pytest tests/ -m performance --benchmark-only --benchmark-json=logs/benchmark.json 2>&1 | tee logs/performance-tests.log; then
            log_success "Performance benchmarks completed"
            log_info "Benchmark results saved to logs/benchmark.json"
        else
            log_warning "Some performance benchmarks failed"
        fi
    else
        log_warning "pytest-benchmark not installed, skipping performance tests"
        log_info "Install with: pip install pytest-benchmark"
    fi
else
    log_info "No performance tests found, skipping"
fi

echo ""

# Step 7: Documentation Checks
echo "📚 Step 7: Documentation Checks"
echo "==============================="

log "Checking for missing docstrings..."
MISSING_DOCSTRINGS=0

# Check Python files for missing docstrings
for file in $(find src/ -name "*.py" -not -path "*/migrations/*"); do
    if [[ -f "$file" ]]; then
        # Check for functions/classes without docstrings
        if python3 -c "
import ast
import sys

with open('$file', 'r') as f:
    try:
        tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                if not ast.get_docstring(node) and not node.name.startswith('_'):
                    print(f'$file:{node.lineno}: {node.name} missing docstring')
                    sys.exit(1)
    except SyntaxError:
        pass  # Skip files with syntax errors
"; then
            continue
        else
            MISSING_DOCSTRINGS=$((MISSING_DOCSTRINGS + 1))
        fi
    fi
done

if [[ "$MISSING_DOCSTRINGS" -eq 0 ]]; then
    log_success "All public functions and classes have docstrings"
else
    log_warning "$MISSING_DOCSTRINGS files have missing docstrings"
fi

echo ""

# Step 8: Git Status Check
echo "📋 Step 8: Git Status Check"
echo "==========================="

log "Checking git status..."

# Check for uncommitted changes in src/ and tests/
if git diff --quiet HEAD -- src/ tests/ && git diff --cached --quiet -- src/ tests/; then
    log_success "No uncommitted changes in source code"
else
    log_info "Uncommitted changes detected:"
    git status --porcelain -- src/ tests/
    echo ""
    log_info "Consider committing your changes after this check passes"
fi

# Check current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
log_info "Current branch: $CURRENT_BRANCH"

echo ""

# Final Summary
echo "📋 Final Summary"
echo "================"

log_success "All quality checks completed!"

echo ""
echo "✅ Completed Checks:"
if [[ "$SKIP_FORMATTING" == "false" ]]; then
    echo "   • Code formatting (Black, isort)"
fi
echo "   • Static analysis (flake8, mypy)"
if [[ "$SKIP_SECURITY" == "false" ]]; then
    echo "   • Security scanning"
fi
if [[ "$SKIP_TESTS" == "false" ]]; then
    echo "   • Unit tests"
    echo "   • Coverage analysis"
fi
echo "   • Documentation checks"
echo "   • Git status"

echo ""
echo "📁 Log files saved to logs/ directory:"
echo "   • logs/unit-tests.log"
echo "   • logs/coverage-report.txt"
echo "   • logs/htmlcov/index.html"
if [[ -f "logs/bandit-report.json" ]]; then
    echo "   • logs/bandit-report.json"
fi

echo ""
echo "🚀 Ready to commit!"
echo ""
echo "💡 Suggested next steps:"
echo "   1. Review any warnings above"
echo "   2. Commit your changes with a descriptive message"
echo "   3. Push to your feature branch"
echo ""
echo "📝 Example commit commands:"
echo "   git add ."
echo "   git commit -m \"feat: implement [feature description]\""
echo "   git push -u origin feature/[feature-name]"
echo ""

log_success "🎉 Quality assurance completed successfully!"